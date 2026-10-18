"""Streaming client for OpenAI compatible /chat/completions"""

import json

from collections.abc import Iterator
from dataclasses import dataclass

import httpx

from src.models import LlmModel


class LlmError(Exception):
    """The message never contains request or response text, so it is safe to log / return"""


@dataclass(frozen=True)
class LlmEndpoint:
    base_url: str
    model: str
    api_key: str | None

    @classmethod
    def from_model(cls, model: LlmModel) -> "LlmEndpoint":
        return cls(model.base_url, model.model, model.api_key)


def stream_chat(endpoint: LlmEndpoint, messages: list[dict[str, str]], timeout: float = 60.0) -> Iterator[str]:
    """Yields the content deltas of the reply"""
    url = f"{endpoint.base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {endpoint.api_key}"} if endpoint.api_key else {}
    payload = {"model": endpoint.model, "messages": messages, "stream": True}
    try:
        with httpx.stream(
            "POST", url, json=payload, headers=headers, timeout=httpx.Timeout(timeout, connect=10.0)
        ) as response:
            if response.status_code >= 400:
                raise LlmError(f"LLM API returned HTTP {response.status_code}")
            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    return
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    raise LlmError("LLM API returned an invalid stream") from None
                if not isinstance(chunk, dict):
                    continue
                if "error" in chunk:
                    raise LlmError("LLM API returned an error in the stream")
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") if isinstance(choice, dict) else None
                    content = delta.get("content") if isinstance(delta, dict) else None
                    if isinstance(content, str) and content:
                        yield content
    except httpx.HTTPError as e:
        raise LlmError(f"LLM API request failed ({type(e).__name__})") from None
