from pathlib import Path

from sqlalchemy import Engine, event
from sqlmodel import Session, SQLModel, col, create_engine, select

from src.models import RegexRuleConfig, Rule, Ruleset, RulesetRule

# Built-in rules: (builtin_key, name, config). Patterns use Python re with explicit ASCII classes and
# lookarounds instead of \b, because \b doesn't separate a value from adjacent Chinese text
BUILTIN_RULES = [
    ("email", "Email", RegexRuleConfig(
        pattern=r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        label="EMAIL",
    )),
    ("card_number", "Card number (16 digits)", RegexRuleConfig(
        # contiguous, or in groups of four separated by the same space / dash
        pattern=r"(?<!\d)\d{4}([ -]?)\d{4}\1\d{4}\1\d{4}(?!\d)",
        label="CARD_NUMBER",
    )),
    ("uk_postcode", "UK postcode", RegexRuleConfig(
        # e.g. SW1A 1AA, M1 1AE, DN55 1PT, GIR 0AA; any case, optional space
        pattern=r"(?i)(?<![A-Z0-9])(?:GIR ?0AA|[A-PR-UWYZ][A-HK-Y]?[0-9][A-Z0-9]? ?[0-9][ABD-HJLNP-UW-Z]{2})(?![A-Z0-9])",
        label="POSTAL_CODE",
    )),
]


def create_db_engine(path: Path) -> Engine:
    # FastAPI could run on different threads in the pool, so that we require each request use its own session
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        # SQLite disables foreign keys by default
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.close()

    return engine


def init_db(engine: Engine):
    SQLModel.metadata.create_all(engine)
    _seed_builtin_rules(engine)


def _seed_builtin_rules(engine: Engine) -> None:
    # Idempotent: insert missing built-in rules, update existing ones to the definitions above
    with Session(engine) as session:
        for key, name, config in BUILTIN_RULES:
            rule = session.exec(select(Rule).where(Rule.builtin_key == key)).first()
            if rule is None:
                rule = Rule(builtin_key=key, name=name, config=config)
            else:
                rule.name, rule.config = name, config
            session.add(rule)
        session.commit()


def create_default_ruleset(session: Session, user_id: int) -> Ruleset:
    """A new user's "Default" ruleset with all built-in rules (the caller commits)"""
    ruleset = Ruleset(owner_id=user_id, name="Default", description="Built-in rules")
    session.add(ruleset)
    session.flush()
    builtin = session.exec(select(Rule).where(col(Rule.owner_id).is_(None)).order_by(col(Rule.id))).all()
    for priority, rule in enumerate(builtin):
        session.add(RulesetRule(ruleset_id=ruleset.id, rule_id=rule.id, priority=priority))
    return ruleset
