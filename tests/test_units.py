from contextlib import contextmanager
from types import SimpleNamespace

import httpx
import pytest

from pydantic import ValidationError

from src import llm
from src.ner import short_label, token_windows
from src.schemas import LlmModelCreate, RulesetUpdate
from src.security import hash_password, verify_password

ENDPOINT = llm.LlmEndpoint("http://llm.invalid/v1", "fake", None)


def test_password_hash_roundtrip():
    stored = hash_password("correct horse")
    assert verify_password("correct horse", stored)
    assert not verify_password("wrong horse", stored)
    assert stored != hash_password("correct horse")  # salted


def test_patch_rejects_null_for_required_fields():
    assert RulesetUpdate.model_validate({"description": None}).model_fields_set == {"description"}
    with pytest.raises(ValidationError):
        RulesetUpdate.model_validate({"name": None})


def test_base_url_is_normalized():
    assert LlmModelCreate(name="m", base_url="https://api.example.com/v1/", model="m").base_url == "https://api.example.com/v1"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com", "example.com"])
def test_base_url_must_be_http(url):
    with pytest.raises(ValidationError):
        LlmModelCreate(name="m", base_url=url, model="m")


def _fake_stream(status_code: int, lines: list[str]):
    @contextmanager
    def stream(*args, **kwargs):
        yield SimpleNamespace(status_code=status_code, iter_lines=lambda: iter(lines))

    return stream


def test_stream_chat_yields_deltas_and_skips_malformed_chunks(monkeypatch):
    lines = [
        'data: {"choices": [{"delta": {"role": "assistant"}}]}',
        'data: {"choices": [{"delta": {"content": "Hel"}}]}',
        'data: {"choices": ["malformed"]}',
        "",
        'data: {"choices": [{"delta": {"content": "lo"}}]}',
        "data: [DONE]",
        'data: {"choices": [{"delta": {"content": "after done"}}]}',
    ]
    monkeypatch.setattr(httpx, "stream", _fake_stream(200, lines))
    assert list(llm.stream_chat(ENDPOINT, [])) == ["Hel", "lo"]


def test_stream_chat_raises_llm_error_on_http_error(monkeypatch):
    monkeypatch.setattr(httpx, "stream", _fake_stream(401, []))
    with pytest.raises(llm.LlmError, match="HTTP 401"):
        list(llm.stream_chat(ENDPOINT, []))


def test_token_windows_cover_all_tokens_with_overlap():
    offsets = [(i, i + 1) for i in range(25)]
    windows = token_windows(offsets, size=10, overlap=3)
    assert windows[0][0] == 0 and windows[-1][1] == 25
    assert all(prev[1] > nxt[0] for prev, nxt in zip(windows, windows[1:]))
    assert token_windows([], size=10, overlap=3) == []


def test_short_label():
    assert short_label("identity.person_name") == "PERSON_NAME"
