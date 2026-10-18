"""API request / response bodies (the tables are in models.py)"""

from typing import ClassVar, Literal, Self
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from sqlmodel import Field, SQLModel

from src.models import LlmModelBase, Role, RuleBase, RuleConfig, RulesetBase, UserBase


class Patch(SQLModel):
    """PATCH body: omitted fields are left unchanged, fields in `not_null` can't be set to null"""

    not_null: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _reject_nulls(self) -> Self:
        nulls = sorted(f for f in self.not_null if f in self.model_fields_set and getattr(self, f) is None)
        if nulls:
            raise ValueError(f"{', '.join(nulls)} cannot be null")
        return self


# ---- auth ----

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(SQLModel):
    username: str = Field(max_length=32)
    password: str = Field(max_length=128)


class UserOut(UserBase):
    id: int


class TokenOut(SQLModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: int  # unix timestamp


# ---- LLM models ----

def _check_base_url(value: str | None) -> str | None:
    if value is None:
        return None
    url = urlparse(value)
    if url.scheme not in ("http", "https") or not url.netloc:
        raise ValueError("base_url must be an http(s) URL")
    return value.rstrip("/")


class LlmModelCreate(LlmModelBase):
    api_key: str | None = Field(default=None, max_length=512)

    validate_base_url = field_validator("base_url")(_check_base_url)


class LlmModelUpdate(Patch):
    not_null: ClassVar[frozenset[str]] = frozenset({"name", "base_url", "model"})

    name: str | None = Field(default=None, min_length=1, max_length=64)
    base_url: str | None = Field(default=None, min_length=1, max_length=512)
    model: str | None = Field(default=None, min_length=1, max_length=128)
    api_key: str | None = Field(default=None, max_length=512)  # null removes the key

    validate_base_url = field_validator("base_url")(_check_base_url)


class LlmModelOut(LlmModelBase):
    id: int
    has_api_key: bool  # the key itself is never returned


# ---- rules / rulesets ----

class RuleCreate(RuleBase):
    pass


class RuleUpdate(Patch):
    not_null: ClassVar[frozenset[str]] = frozenset({"name", "config"})

    name: str | None = Field(default=None, min_length=1, max_length=64)
    config: RuleConfig | None = None


class RuleOut(RuleBase):
    id: int
    owner_id: int | None  # null -> builtin rule (read only)
    builtin_key: str | None


class RulesetEntryIn(SQLModel):
    rule_id: int
    priority: int = 0  # lower runs first and wins overlaps
    enabled: bool = True


class RulesetCreate(RulesetBase):
    entries: list[RulesetEntryIn] = Field(default_factory=list)


class RulesetUpdate(Patch):
    not_null: ClassVar[frozenset[str]] = frozenset({"name", "entries"})

    name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=256)
    entries: list[RulesetEntryIn] | None = None  # replaces all entries when given


class RulesetEntryOut(SQLModel):
    rule: RuleOut
    priority: int
    enabled: bool


class RulesetOut(RulesetBase):
    id: int
    entries: list[RulesetEntryOut]


# ---- sessions ----

class SessionCreate(SQLModel):
    title: str | None = Field(default=None, max_length=128)
    ruleset_id: int
    llm_model_id: int | None = None  # required before chatting


class SessionUpdate(Patch):
    not_null: ClassVar[frozenset[str]] = frozenset({"ruleset_id"})

    title: str | None = Field(default=None, max_length=128)
    ruleset_id: int | None = None
    llm_model_id: int | None = None


class SessionOut(SQLModel):
    id: int
    title: str | None
    ruleset_id: int | None
    llm_model_id: int | None


class MessageCreate(SQLModel):
    content: str = Field(min_length=1, max_length=100_000)


class MessageOut(SQLModel):
    """content: original text (user) / restored reply (assistant); llm_content: what the LLM saw / said"""

    id: int
    role: Role
    content: str
    llm_content: str


class RedactionOut(SQLModel):
    """One row of a session's replacement table; `original` is raw PII for the session owner only"""

    id: int
    placeholder: str
    label: str
    original: str
