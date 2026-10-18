import logging
import re
from dataclasses import dataclass
from typing import Callable

from ibmzd.privacy_models import (
    NerRuleConfig,
    Redaction,
    RedactionSpan,
    RegexRuleConfig,
    Ruleset,
    SessionRecords,
)

logger = logging.getLogger(__name__)

## Interface for DB integration

# (text, entity type names) -> [(start, end, label), ...] with offsets into `text`
NerDetector = Callable[[str, list[str]], list[tuple[int, int, str]]]
# (session) -> Ruleset | None
RulesetLoader = Callable[[str], Ruleset | None]
# (redactions) -> None
_db_insert_redaction_map = Callable[[list[Redaction]], None]
# (message_id, redacted text) -> None
_db_insert_redacted_content = Callable[[int, str], None]

##-------------------------------------

@dataclass(frozen=True)
class _Match:
    start: int
    end: int
    label: str
    rule_id: int
    priority: int


class PrivacyEngine:
    """In-memory only. Nothing is ever written to disk."""

    def __init__(
        self,
        ruleset_loader: RulesetLoader | None = None,
        ner_detector: NerDetector | None = None,
        db_insert_redaction_map: _db_insert_redaction_map | None = None,
        db_insert_redacted_content: _db_insert_redacted_content | None = None,
    ):
        self._ruleset_loader = ruleset_loader
        self._ner_detector = ner_detector
        self._db_insert_redaction_map = db_insert_redaction_map
        self._db_insert_redacted_content = db_insert_redacted_content
        self._rulesets: dict[str, Ruleset] = {}  # ruleset cache, per session
        self._records: dict[str, SessionRecords] = {}  # held until the integrator persists/evicts them

    # ---- ruleset cache -------------------------------------------------------------

    def set_ruleset(self, session: str, ruleset: Ruleset) -> None:
        """Manually put (or replace) the cached ruleset of a session."""
        self._rulesets[session] = ruleset

    def refresh_ruleset(self, session: str) -> bool:
        """Drop the cached ruleset and reload it through the ruleset_loader.

        Returns False (and leaves the cache empty for that session) if there is no loader
        or the loader returns nothing / fails.
        """
        self._rulesets.pop(session, None)
        if self._ruleset_loader is None:
            return False
        try:
            ruleset = self._ruleset_loader(session)
        except Exception as e:
            logger.error("ruleset refresh failed: %s: %s", type(e).__name__, e)
            return False
        if ruleset is None:
            return False
        self._rulesets[session] = ruleset
        return True

    def invalidate_ruleset(self, session: str) -> None:
        """Drop the cached ruleset of one session (reloaded lazily on the next apply_rules)."""
        self._rulesets.pop(session, None)

    def clear_ruleset_cache(self) -> None:
        self._rulesets.clear()

    def get_ruleset(self, session: str) -> Ruleset | None:
        """Cached ruleset, loading it through the loader on a cache miss."""
        if session not in self._rulesets:
            self.refresh_ruleset(session)
        return self._rulesets.get(session)

    # ---- held records --------------------------------------------------------------

    def get_records(self, session: str) -> SessionRecords | None:
        """Redactions, spans and llm_content held for a session (the live object, treat as read-only)."""
        return self._records.get(session)

    def forget_session(self, session: str) -> None:
        """Evict a session's records and cached ruleset from memory."""
        self._records.pop(session, None)
        self._rulesets.pop(session, None)

    # TODO(DB): the integrator persists get_records(session) (redactions, spans, llm_content),
    # mapping local Redaction.id values to the real DB ids, then calls forget_session when the
    # session ends. Where raw `original` values may be stored is an open AGENTS.md decision.

    # ---- redaction -----------------------------------------------------------------

    def _find_matches(self, text: str, ruleset: Ruleset) -> list[_Match]:
        found: list[_Match] = []
        for entry in ruleset.entries:
            if not entry.enabled:
                continue
            rule, config = entry.rule, entry.rule.config
            if isinstance(config, RegexRuleConfig):
                for m in re.finditer(config.pattern, text):
                    if m.end() > m.start():
                        found.append(_Match(m.start(), m.end(), config.label, rule.id, entry.priority))
            elif isinstance(config, NerRuleConfig):
                if self._ner_detector is None:
                    raise RuntimeError("ruleset has an NER rule but no NER detector is configured")
                for start, end, label in self._ner_detector(text, config.entities):
                    if end > start:
                        found.append(_Match(start, end, label, rule.id, entry.priority))
            else:
                raise ValueError(f"unknown rule config {type(config).__name__}")
        return found

    @staticmethod
    def _resolve_overlaps(matches: list[_Match]) -> list[_Match]:
        """Lower priority number wins, then longer match, then earlier start."""
        accepted: list[_Match] = []
        for m in sorted(matches, key=lambda m: (-(m.end - m.start), m.start)):
            if all(m.end <= a.start or m.start >= a.end for a in accepted):
                accepted.append(m)
        return sorted(accepted, key=lambda m: m.start)

    # Returns the redacted text, or None if the session has no ruleset or anything fails.
    # With message_id, the spans and the redacted text (llm_content) are also held in memory.
    # On failure nothing is changed.
    def apply_rules(self, text: str, session: str, *, message_id: int | None = None) -> str | None:
        try:
            ruleset = self.get_ruleset(session)
            if ruleset is None:
                return None

            matches = self._resolve_overlaps(self._find_matches(text, ruleset))

            records = self._records.get(session)
            known = records.redactions if records else {}
            new: dict[str, Redaction] = {}
            counts: dict[str, int] = {}

            ##Count unique redaction labels already known in the session, to continue numbering new redactions correctly
            for r in known.values():
                counts[r.label] = counts.get(r.label, 0) + 1
            next_id = len(known) + 1

            ##Build the redacted text, the new redactions, and the spans for this message
            parts: list[str] = []
            spans: list[RedactionSpan] = []
            pos = 0
            for m in matches:
                original = text[m.start : m.end]
                redaction = known.get(original) or new.get(original)
                if redaction is None:
                    label = m.label.upper()
                    counts[label] = counts.get(label, 0) + 1
                    redaction = Redaction(next_id, label, f"[{label}_{counts[label]}]", original)
                    next_id += 1
                    new[original] = redaction
                parts.append(text[pos : m.start])
                parts.append(redaction.placeholder)
                if message_id is not None:
                    spans.append(RedactionSpan(message_id, redaction.id, m.rule_id, m.start, m.end))
                pos = m.end
            parts.append(text[pos:])
            redacted = "".join(parts)

            # commit only after everything succeeded
            if records is None:
                records = self._records.setdefault(session, SessionRecords())
            records.redactions.update(new)
            if message_id is not None:
                self._db_insert_redaction_map(new.values())
                self._db_insert_redacted_content(message_id, redacted)
            return redacted
        except Exception as e:
            # Messages come from re2/rule config, not user text; no traceback (locals) is logged.
            logger.error("apply_rules failed: %s: %s", type(e).__name__, e)
            return None

    def restore_text(self, text: str, session: str) -> str | None:
        """Replace the session's placeholders in `text` with their original values.

        `text` can be any text containing placeholders, e.g. an LLM reply. Placeholders are
        matched case-insensitively; unknown placeholders and all other text are left as-is.
        Replacement is a single pass, so an original that looks like a placeholder is not
        substituted again. Returns None if the session has no records or anything fails.
        """
        try:
            records = self._records.get(session)
            if records is None:
                return None
            by_placeholder = {r.placeholder.upper(): r.original for r in records.redactions.values()}
            if not by_placeholder:
                return text
            pattern = re.compile(
                "|".join(re.escape(p) for p in sorted(by_placeholder, key=len, reverse=True)),
                re.IGNORECASE,
            )
            return pattern.sub(lambda m: by_placeholder[m.group().upper()], text)
        except Exception as e:
            logger.error("restore_text failed: %s: %s", type(e).__name__, e)
            return None
