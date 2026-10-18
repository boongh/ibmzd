"""Shared fixtures. All PII used in tests is synthetic."""

import json
import re
import secrets

import pytest

from fastapi.testclient import TestClient

from src import sessions
from src.app import create_app
from src.config import AppConfig


@pytest.fixture
def app(tmp_path):
    config = AppConfig.model_validate(
        {
            "server": {"host": "127.0.0.1", "port": 8000},
            "database": {"path": tmp_path / "test.db"},
            "log": {"level": "INFO"},
        }
    )
    return create_app(config)


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def login(client):
    """Registers a user and returns its auth headers"""

    def _login(username: str = "alice", password: str = "password-123") -> dict[str, str]:
        client.post("/auth/register", json={"username": username, "password": password})
        token = client.post("/auth/login", json={"username": username, "password": password}).json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login


class FakeLlm:
    """Stands in for the OpenAI compatible client: records what the LLM receives and echoes
    the placeholders of the last message back in small chunks (splitting placeholders)"""

    def __init__(self):
        self.calls: list[list[dict[str, str]]] = []
        self.error: Exception | None = None

    def __call__(self, endpoint, messages):
        self.calls.append(messages)
        if self.error:
            raise self.error
        reply = "Got " + " ".join(re.findall(r"\[[A-Z_]+_\d+\]", messages[-1]["content"]))
        for i in range(0, len(reply), 4):
            yield reply[i : i + 4]


@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeLlm()
    monkeypatch.setattr(sessions, "stream_chat", fake)
    return fake


@pytest.fixture
def new_session(client):
    """Creates rules, a ruleset and an LLM model, and returns a session bound to them"""

    def _new_session(headers: dict[str, str], *rule_configs: dict) -> int:
        suffix = secrets.token_hex(4)  # names are unique per user
        entries = []
        for i, config in enumerate(rule_configs):
            rule = client.post("/rules", json={"name": f"rule-{suffix}-{i}", "config": config}, headers=headers)
            entries.append({"rule_id": rule.json()["id"], "priority": i})
        ruleset = client.post("/rulesets", json={"name": f"ruleset-{suffix}", "entries": entries}, headers=headers)
        model = client.post(
            "/llm-models",
            json={"name": f"model-{suffix}", "base_url": "http://llm.invalid/v1", "model": "fake"},
            headers=headers,
        )
        body = {"ruleset_id": ruleset.json()["id"], "llm_model_id": model.json()["id"]}
        return client.post("/sessions", json=body, headers=headers).json()["id"]

    return _new_session


@pytest.fixture
def send(client):
    """Sends a chat message and returns the parsed SSE events"""

    def _send(headers: dict[str, str], session_id: int, text: str, via: TestClient | None = None) -> list[dict]:
        with (via or client).stream(
            "POST", f"/sessions/{session_id}/messages", json={"content": text}, headers=headers
        ) as response:
            assert response.status_code == 200, response.read()
            return [json.loads(line[5:]) for line in response.iter_lines() if line.startswith("data:")]

    return _send
