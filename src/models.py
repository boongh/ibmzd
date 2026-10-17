from typing import Any, Literal

from pydantic import TypeAdapter
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, String, Text, UniqueConstraint
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, SQLModel


# ======= Rule
class RegexRuleConfig(SQLModel):
    type: Literal["regex"] = "regex"
    pattern: str
    label: str


class NerRuleConfig(SQLModel):
    type: Literal["ner"] = "ner"
    entities: list[str]  # Selected type names to be reduct, e.g. ["identity.person_name", "contact.phone"]


RuleConfig = RegexRuleConfig | NerRuleConfig

_rule_config = TypeAdapter(RuleConfig)


class RuleConfigType(TypeDecorator[Any]):
    """RuleConfig <-> JSON"""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        if value is None:
            return None
        return _rule_config.dump_json(_rule_config.validate_python(value)).decode()

    def process_result_value(self, value: str | None, dialect: Any) -> Any:
        return None if value is None else _rule_config.validate_json(value)


# ---- 表 ----
# For models w/ 'table=True' will not be validated
# Use Xxx.model_validate(create, update={...})

class UserBase(SQLModel):
    username: str = Field(unique=True, min_length=3, max_length=32)


class User(UserBase, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    password_hash: str


class RuleBase(SQLModel):
    name: str = Field(min_length=1, max_length=64)
    config: RuleConfig = Field(sa_type=RuleConfigType)


class Rule(RuleBase, table=True):
    """owner_id is NULL --> it is a builtin rule"""

    __tablename__ = "rules"
    __table_args__ = (
        UniqueConstraint("owner_id", "name"),
        CheckConstraint("(owner_id IS NULL) = (builtin_key IS NOT NULL)", name="builtin_rule_has_key"),
    )

    id: int | None = Field(default=None, primary_key=True)
    owner_id: int | None = Field(default=None, foreign_key="users.id", ondelete="CASCADE")
    builtin_key: str | None = Field(default=None, unique=True)


class RulesetBase(SQLModel):
    name: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=256)


class Ruleset(RulesetBase, table=True):
    __tablename__ = "rulesets"
    __table_args__ = (UniqueConstraint("owner_id", "name"),)

    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="users.id", ondelete="CASCADE")


class RulesetRule(SQLModel, table=True):
    """A mapping from ruleset to rule"""

    __tablename__ = "ruleset_rules"

    ruleset_id: int = Field(foreign_key="rulesets.id", ondelete="CASCADE", primary_key=True)
    rule_id: int = Field(foreign_key="rules.id", ondelete="CASCADE", primary_key=True, index=True)
    priority: int = 0
    enabled: bool = True


class ChatSession(SQLModel, table=True):
    """The user of the session can only use their own rulesets"""

    __tablename__ = "chat_sessions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    ruleset_id: int | None = Field(default=None, foreign_key="rulesets.id", ondelete="SET NULL")
    title: str | None = None


Role = Literal["system", "user", "assistant"]


class Message(SQLModel, table=True):
    """content：local original text
    llm_content：redacted request to LLM / LLM original response"""

    __tablename__ = "messages"
    __table_args__ = (
        # For redaction_spans' composite foreign key ref & For indexing session -> message
        UniqueConstraint("session_id", "id"),
        CheckConstraint("role IN ('system', 'user', 'assistant')", name="message_role"),
    )

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chat_sessions.id", ondelete="CASCADE")
    role: Role = Field(sa_type=String)
    content: str
    llm_content: str


class Redaction(SQLModel, table=True):
    """A mapping dict within a session
    where the same source text consistently corresponds to
    the same placeholder throughout that session"""

    __tablename__ = "redactions"
    __table_args__ = (
        UniqueConstraint("session_id", "placeholder"),
        UniqueConstraint("session_id", "original"),
        UniqueConstraint("session_id", "id"),  # For redaction_spans' composite foreign key ref
    )

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="chat_sessions.id", ondelete="CASCADE")
    label: str  # PERSON / EMAIL / PHONE ...
    placeholder: str  # [PERSON_1]
    original: str


class RedactionSpan(SQLModel, table=True):
    """The specific location of each replacement (Python string index within `Message.content`)
    A composite foreign key ensures that the `message` and the `redaction` belong to the same conversation
    """

    __tablename__ = "redaction_spans"
    __table_args__ = (
        ForeignKeyConstraint(
            ["session_id", "message_id"], ["messages.session_id", "messages.id"], ondelete="CASCADE"
        ),
        ForeignKeyConstraint(
            ["session_id", "redaction_id"], ["redactions.session_id", "redactions.id"], ondelete="CASCADE"
        ),
        CheckConstraint("0 <= start_pos AND start_pos < end_pos", name="span_range"),
    )

    id: int | None = Field(default=None, primary_key=True)
    session_id: int
    message_id: int = Field(index=True)
    redaction_id: int = Field(index=True)
    rule_id: int | None = Field(default=None, foreign_key="rules.id", ondelete="SET NULL")
    start_pos: int
    end_pos: int
