from fastapi import APIRouter, HTTPException, status
from loguru import logger
from sqlalchemy import delete
from sqlmodel import col, select

from src.deps import (
    CurrentUser,
    DbSession,
    commit_or_conflict,
    flush_or_conflict,
    get_owned_ruleset,
    visible_rules,
)
from src.models import Rule, Ruleset, RulesetRule, User
from src.schemas import RuleOut, RulesetCreate, RulesetEntryIn, RulesetEntryOut, RulesetOut, RulesetUpdate

router = APIRouter(prefix="/rulesets", tags=["rulesets"])

_NAME_TAKEN = "A ruleset with this name already exists"


def _out(db: DbSession, ruleset: Ruleset) -> RulesetOut:
    rows = db.exec(
        select(RulesetRule, Rule)
        .join(Rule, col(Rule.id) == col(RulesetRule.rule_id))
        .where(RulesetRule.ruleset_id == ruleset.id)
        .order_by(col(RulesetRule.priority), col(Rule.id))
    ).all()
    entries = [
        RulesetEntryOut(rule=RuleOut.model_validate(rule), priority=link.priority, enabled=link.enabled)
        for link, rule in rows
    ]
    return RulesetOut(id=ruleset.id, name=ruleset.name, description=ruleset.description, entries=entries)


def _replace_entries(db: DbSession, user: User, ruleset: Ruleset, entries: list[RulesetEntryIn]) -> None:
    rule_ids = [e.rule_id for e in entries]
    if len(set(rule_ids)) != len(rule_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Duplicate rule_id in entries")
    # A ruleset may only contain builtin rules and the owner's own rules
    allowed = set(db.exec(select(Rule.id).where(col(Rule.id).in_(rule_ids), visible_rules(user))).all())
    if unknown := sorted(set(rule_ids) - allowed):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown rule ids: {unknown}")

    db.exec(delete(RulesetRule).where(col(RulesetRule.ruleset_id) == ruleset.id))
    for e in entries:
        db.add(RulesetRule(ruleset_id=ruleset.id, rule_id=e.rule_id, priority=e.priority, enabled=e.enabled))


@router.get("", response_model=list[RulesetOut])
def list_rulesets(user: CurrentUser, db: DbSession) -> list[RulesetOut]:
    rulesets = db.exec(select(Ruleset).where(Ruleset.owner_id == user.id).order_by(Ruleset.id)).all()
    return [_out(db, rs) for rs in rulesets]


@router.post("", response_model=RulesetOut, status_code=status.HTTP_201_CREATED)
def create_ruleset(body: RulesetCreate, user: CurrentUser, db: DbSession) -> RulesetOut:
    ruleset = Ruleset(owner_id=user.id, name=body.name, description=body.description)
    db.add(ruleset)
    flush_or_conflict(db, _NAME_TAKEN)
    _replace_entries(db, user, ruleset, body.entries)
    db.commit()
    logger.info(f"User {user.id} created ruleset {ruleset.id} with {len(body.entries)} rule(s)")
    return _out(db, ruleset)


@router.get("/{ruleset_id}", response_model=RulesetOut)
def get_ruleset(ruleset_id: int, user: CurrentUser, db: DbSession) -> RulesetOut:
    return _out(db, get_owned_ruleset(db, user, ruleset_id))


@router.patch("/{ruleset_id}", response_model=RulesetOut)
def update_ruleset(ruleset_id: int, body: RulesetUpdate, user: CurrentUser, db: DbSession) -> RulesetOut:
    ruleset = get_owned_ruleset(db, user, ruleset_id)
    fields = body.model_fields_set
    if "name" in fields:
        ruleset.name = body.name
    if "description" in fields:
        ruleset.description = body.description
    if "entries" in fields:
        _replace_entries(db, user, ruleset, body.entries)
    db.add(ruleset)
    commit_or_conflict(db, _NAME_TAKEN)
    logger.info(f"User {user.id} updated ruleset {ruleset.id} ({', '.join(sorted(fields))})")
    return _out(db, ruleset)


@router.delete("/{ruleset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ruleset(ruleset_id: int, user: CurrentUser, db: DbSession) -> None:
    """Sessions bound to this ruleset are unbound (and refuse to chat until a new one is bound)"""
    db.delete(get_owned_ruleset(db, user, ruleset_id))
    db.commit()
    logger.info(f"User {user.id} deleted ruleset {ruleset_id}")
