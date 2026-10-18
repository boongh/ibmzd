"""API integration tests; the LLM is replaced by the fake_llm fixture. All PII here is synthetic."""

import logging

import pytest

from fastapi.testclient import TestClient
from loguru import logger

from src.app import _InterceptHandler, create_app
from src.llm import LlmError

EMAIL, PHONE = "zhang.san@example.com", "13812345678"
# ASCII classes: with Python re's Unicode semantics \w would also match the Chinese text around the value
EMAIL_RULE = {"type": "regex", "pattern": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "label": "EMAIL"}
PHONE_RULE = {"type": "regex", "pattern": r"(?<!\d)1[3-9]\d{9}(?!\d)", "label": "PHONE"}


def test_auth_flow(client):
    credentials = {"username": "alice", "password": "password-123"}
    assert client.post("/auth/register", json=credentials).status_code == 201
    assert client.post("/auth/register", json=credentials).status_code == 409
    assert client.post("/auth/login", json={**credentials, "password": "wrong-password"}).status_code == 401

    token = client.post("/auth/login", json=credentials).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/auth/me", headers=headers).json()["username"] == "alice"
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_llm_api_key_is_never_returned(client, login):
    headers = login()
    body = {"name": "m", "base_url": "https://api.example.com/v1", "model": "m", "api_key": "sk-test"}
    created = client.post("/llm-models", json=body, headers=headers).json()
    assert created["has_api_key"] and "api_key" not in created
    assert "api_key" not in client.get("/llm-models", headers=headers).json()[0]


def test_users_cannot_access_each_others_data(client, login, new_session):
    alice, bob = login("alice"), login("bob")
    bob_rule = client.post("/rules", json={"name": "bob", "config": EMAIL_RULE}, headers=bob).json()["id"]
    bob_session = new_session(bob, EMAIL_RULE)

    assert client.get(f"/rules/{bob_rule}", headers=alice).status_code == 404
    entries = [{"rule_id": bob_rule}]
    assert client.post("/rulesets", json={"name": "r", "entries": entries}, headers=alice).status_code == 422
    assert client.get(f"/sessions/{bob_session}/messages", headers=alice).status_code == 404
    assert client.get(f"/sessions/{bob_session}/redactions", headers=alice).status_code == 404


def test_chat_redacts_streams_and_restores(client, login, new_session, send, fake_llm):
    headers = login()
    session = new_session(headers, EMAIL_RULE, PHONE_RULE)
    events = send(headers, session, f"邮箱{EMAIL}，电话{PHONE}")

    assert events[0] == {"type": "user_message", "id": 1, "llm_content": "邮箱[EMAIL_1]，电话[PHONE_1]"}
    assert fake_llm.calls[-1][-1]["content"] == "邮箱[EMAIL_1]，电话[PHONE_1]"
    assert EMAIL not in str(fake_llm.calls) and PHONE not in str(fake_llm.calls)
    assert "".join(e["content"] for e in events if e["type"] == "delta") == "Got [EMAIL_1] [PHONE_1]"
    assert events[-1] == {"type": "done", "message_id": 2, "content": f"Got {EMAIL} {PHONE}"}

    table = client.get(f"/sessions/{session}/redactions", headers=headers).json()
    assert {r["placeholder"]: r["original"] for r in table} == {"[EMAIL_1]": EMAIL, "[PHONE_1]": PHONE}
    messages = client.get(f"/sessions/{session}/messages", headers=headers).json()
    assert [(m["role"], m["content"]) for m in messages] == [
        ("user", f"邮箱{EMAIL}，电话{PHONE}"),
        ("assistant", f"Got {EMAIL} {PHONE}"),
    ]


def test_placeholders_are_stable_across_messages_and_restarts(app, login, new_session, send, fake_llm):
    headers = login()
    session = new_session(headers, EMAIL_RULE)
    send(headers, session, f"Mail {EMAIL}")

    restarted = TestClient(create_app(app.state.config))
    send(headers, session, f"Again {EMAIL}, also li.si@example.com", via=restarted)

    history, last = fake_llm.calls[-1][:-1], fake_llm.calls[-1][-1]
    assert last["content"] == "Again [EMAIL_1], also [EMAIL_2]"
    assert [m["role"] for m in history] == ["user", "assistant"] and EMAIL not in str(history)


@pytest.mark.parametrize(
    "rule_config",
    [
        {"type": "regex", "pattern": "(", "label": "BROKEN"},  # invalid regex
        {"type": "ner", "entities": ["identity.person_name"]},  # no NER model configured
    ],
)
def test_chat_fails_closed(client, login, new_session, fake_llm, rule_config):
    headers = login()
    session = new_session(headers, rule_config)
    response = client.post(f"/sessions/{session}/messages", json={"content": f"Mail {EMAIL}"}, headers=headers)

    assert response.status_code == 422
    assert fake_llm.calls == []
    assert client.get(f"/sessions/{session}/messages", headers=headers).json() == []
    assert client.get(f"/sessions/{session}/redactions", headers=headers).json() == []


def test_llm_error_becomes_error_event(client, login, new_session, send, fake_llm):
    headers = login()
    session = new_session(headers, EMAIL_RULE)
    fake_llm.error = LlmError("LLM API returned HTTP 500")

    events = send(headers, session, "hello")
    assert events[-1] == {"type": "error", "detail": "LLM API returned HTTP 500"}
    roles = [m["role"] for m in client.get(f"/sessions/{session}/messages", headers=headers).json()]
    assert roles == ["user"]


@pytest.fixture
def captured_logs():
    """loguru output, including stdlib logging of src.* (e.g. the privacy engine)"""
    lines: list[str] = []
    sink = logger.add(lines.append, level="DEBUG", format="{level} {message}", diagnose=False)
    handler = _InterceptHandler()
    logging.getLogger("src").addHandler(handler)
    yield lines
    logging.getLogger("src").removeHandler(handler)
    logger.remove(sink)


def test_logs_have_metadata_but_no_pii(client, login, new_session, send, fake_llm, captured_logs):
    headers = login()
    send(headers, new_session(headers, EMAIL_RULE, PHONE_RULE), f"邮箱{EMAIL}，电话{PHONE}")
    broken = new_session(headers, {"type": "regex", "pattern": "(", "label": "BROKEN"})
    client.post(f"/sessions/{broken}/messages", json={"content": f"Mail {EMAIL}"}, headers=headers)
    client.post("/auth/login", json={"username": "alice", "password": "wrong-password"})

    logs = "\n".join(captured_logs)
    assert "redacted, 2 replacement(s) {'EMAIL': 1, 'PHONE': 1}" in logs
    assert "redaction failed, message rejected" in logs and "apply_rules failed" in logs
    assert "Login failed" in logs
    for secret in (EMAIL, PHONE, "邮箱", "alice", "password-123", "wrong-password"):
        assert secret not in logs


def test_register_creates_default_ruleset_with_builtin_rules(client, login, send, fake_llm):
    headers = login()
    builtin = [r for r in client.get("/rules", headers=headers).json() if r["owner_id"] is None]
    assert {r["builtin_key"] for r in builtin} == {"email", "card_number", "uk_postcode"}
    assert client.patch(f"/rules/{builtin[0]['id']}", json={"name": "x"}, headers=headers).status_code == 403

    (default,) = client.get("/rulesets", headers=headers).json()
    assert default["name"] == "Default"
    assert {e["rule"]["id"] for e in default["entries"]} == {r["id"] for r in builtin}

    model = {"name": "m", "base_url": "http://llm.invalid/v1", "model": "fake"}
    model_id = client.post("/llm-models", json=model, headers=headers).json()["id"]
    session = client.post("/sessions", json={"ruleset_id": default["id"], "llm_model_id": model_id}, headers=headers)
    events = send(headers, session.json()["id"], f"邮箱{EMAIL}，卡号1234 5678 9012 3456，邮编SW1A 1AA")
    assert events[0]["llm_content"] == "邮箱[EMAIL_1]，卡号[CARD_NUMBER_1]，邮编[POSTAL_CODE_1]"
