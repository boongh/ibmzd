"""Plain-Python data structures for the privacy engine.

They mirror the database tables but hold only the fields the engine needs. No DB
code lives here; whoever integrates the database builds these structs from rows
(and saves them back). See docs/privacy_engine.md.
"""

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class RegexRuleConfig:
    """rules.config with type "regex". `pattern` uses google-re2 syntax."""

    pattern: str
    label: str
    type: Literal["regex"] = "regex"


@dataclass(frozen=True)
class NerRuleConfig:
    """rules.config with type "ner". `entities` are type names such as "identity.person_name"."""

    entities: list[str]
    type: Literal["ner"] = "ner"


RuleConfig = RegexRuleConfig | NerRuleConfig


@dataclass(frozen=True)
class Rule:
    """rules row. `id` is what RedactionSpan.rule_id refers to."""

    id: int
    name: str
    config: RuleConfig


@dataclass(frozen=True)
class RulesetEntry:
    """ruleset_rules row, with the rule inlined.

    Lower `priority` runs first and wins overlaps. Entries with enabled=False are skipped.
    """

    rule: Rule
    priority: int = 0
    enabled: bool = True


@dataclass(frozen=True)
class Ruleset:
    """rulesets row plus its ruleset_rules entries."""

    id: int
    name: str
    entries: list[RulesetEntry] = field(default_factory=list)


@dataclass(frozen=True)
class Redaction:
    """redactions row: one original value <-> one placeholder within a session.

    `id` is local to the engine's session records (1, 2, 3, ...). The real DB id is
    assigned when the integrator persists it.
    """

    id: int
    label: str  # PERSON / EMAIL / PHONE ...
    placeholder: str  # [PERSON_1]
    original: str  # raw PII, memory only


@dataclass(frozen=True)
class RedactionSpan:
    """redaction_spans row: where one replacement sits in the ORIGINAL message text.

    Offsets are Python str indices into the text passed to apply_rules.
    """

    message_id: int
    redaction_id: int  # Redaction.id (local id, see above)
    rule_id: int
    start_pos: int
    end_pos: int


@dataclass
class SessionRecords:
    """Everything the engine holds in memory for one session."""
    redaction_spans: list[RedactionSpan] = field(default_factory=list)
    redactions: dict[str, Redaction] = field(default_factory=dict)  # keyed by original text
    llm_content: dict[int, str] = field(default_factory=dict)  # message_id -> redacted text
