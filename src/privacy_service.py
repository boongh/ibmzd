"""Glue between the DB and the in-memory PrivacyEngine (src/privacy_engine.py)

The DB is the source of truth for the replacement table: for every call the session's
redactions are loaded into the engine, and the engine's records are dropped afterwards.
"""

import threading

from collections import Counter

from loguru import logger
from sqlmodel import Session, col, select

from src import privacy_models as pm
from src.privacy_engine import NerDetector, PrivacyEngine
from src.models import ChatSession, Message, Redaction, RedactionSpan, RegexRuleConfig, Rule, RuleConfig, Ruleset, RulesetRule


def load_ruleset(db: Session, ruleset_id: int) -> pm.Ruleset | None:
    """rulesets + ruleset_rules + rules rows -> the engine's Ruleset"""
    ruleset = db.get(Ruleset, ruleset_id)
    if ruleset is None:
        return None
    rows = db.exec(
        select(RulesetRule, Rule)
        .join(Rule, col(Rule.id) == col(RulesetRule.rule_id))
        .where(RulesetRule.ruleset_id == ruleset_id)
    ).all()
    entries = [
        pm.RulesetEntry(pm.Rule(rule.id, rule.name, _engine_config(rule.config)), link.priority, link.enabled)
        for link, rule in rows
    ]
    return pm.Ruleset(ruleset.id, ruleset.name, entries)


def _engine_config(config: RuleConfig) -> pm.RuleConfig:
    if isinstance(config, RegexRuleConfig):
        return pm.RegexRuleConfig(config.pattern, config.label)
    return pm.NerRuleConfig(list(config.entities))


class PrivacyService:
    """The engine isn't thread safe and FastAPI runs sync endpoints in a thread pool, so every
    call holds a lock (this also serializes NER inference and keeps placeholder numbering of
    concurrent messages in one session consistent)"""

    def __init__(self, ner_detector: NerDetector | None = None):
        self._engine = PrivacyEngine(ner_detector=ner_detector)
        self._lock = threading.Lock()

    def redact_message(self, db: Session, chat: ChatSession, ruleset: pm.Ruleset, text: str) -> Message | None:
        """Redacts `text` and stores the user message, its new redactions and spans (one commit)

        Returns None if redaction failed; nothing is stored then (callers must fail closed).
        """
        key = str(chat.id)
        with self._lock:
            try:
                db_ids = self._seed(db, key, chat.id)
                seeded = len(db_ids)
                self._engine.set_ruleset(key, ruleset)

                # Redact before writing anything: a flush takes SQLite's write lock, and NER inference
                # can take seconds, which would make other writers fail with "database is locked".
                # message_id is only needed for the engine to record spans; the real id is set below.
                redacted = self._engine.apply_rules(text, key, message_id=0)
                if redacted is None:
                    logger.warning(f"Session {chat.id}: redaction failed, message rejected (fail closed)")
                    return None

                message = Message(session_id=chat.id, role="user", content=text, llm_content=redacted)
                db.add(message)
                db.flush()

                records = self._engine.get_records(key)
                for r in sorted(records.redactions.values(), key=lambda r: r.id):
                    if r.id not in db_ids:  # new in this message
                        row = Redaction(session_id=chat.id, label=r.label, placeholder=r.placeholder, original=r.original)
                        db.add(row)
                        db.flush()
                        db_ids[r.id] = row.id
                for s in records.spans:
                    db.add(RedactionSpan(
                        session_id=chat.id, message_id=message.id, redaction_id=db_ids[s.redaction_id],
                        rule_id=s.rule_id, start_pos=s.start_pos, end_pos=s.end_pos,
                    ))
                db.commit()
                # Metadata only: counts and entity types (AGENTS.md)
                labels = {r.id: r.label for r in records.redactions.values()}
                counts = dict(Counter(labels[s.redaction_id] for s in records.spans))
                new = len(db_ids) - seeded
                logger.info(f"Session {chat.id}: message {message.id} redacted, {len(records.spans)} replacement(s) {counts}, {new} new placeholder(s)")
                return message
            finally:
                self._engine.forget_session(key)

    def restore(self, db: Session, session_id: int, text: str) -> str | None:
        """Replaces the session's placeholders in `text` (e.g. an LLM reply) with the originals"""
        key = str(session_id)
        with self._lock:
            try:
                self._seed(db, key, session_id)
                return self._engine.restore_text(text, key)
            finally:
                self._engine.forget_session(key)

    def _seed(self, db: Session, key: str, session_id: int) -> dict[int, int]:
        """Loads the session's redactions into the engine; returns engine id -> DB id"""
        rows = db.exec(select(Redaction).where(Redaction.session_id == session_id).order_by(col(Redaction.id))).all()
        records = pm.SessionRecords(
            redactions={r.original: pm.Redaction(i, r.label, r.placeholder, r.original) for i, r in enumerate(rows, 1)}
        )
        self._engine.set_records(key, records)
        return {i: r.id for i, r in enumerate(rows, 1)}
