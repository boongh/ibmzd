from fastapi import APIRouter, HTTPException, status
from loguru import logger
from sqlmodel import select

from src.deps import CurrentUser, DbSession, commit_or_conflict, get_visible_rule, visible_rules
from src.models import Rule, User
from src.schemas import RuleCreate, RuleOut, RuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"])

_NAME_TAKEN = "A rule with this name already exists"


def _get_own_rule(db: DbSession, user: User, rule_id: int) -> Rule:
    rule = get_visible_rule(db, user, rule_id)
    if rule.owner_id is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Builtin rules are read only")
    return rule


@router.get("", response_model=list[RuleOut])
def list_rules(user: CurrentUser, db: DbSession) -> list[Rule]:
    """Builtin rules + the user's own rules"""
    return list(db.exec(select(Rule).where(visible_rules(user)).order_by(Rule.id)).all())


@router.post("", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
def create_rule(body: RuleCreate, user: CurrentUser, db: DbSession) -> Rule:
    rule = Rule.model_validate(body, update={"owner_id": user.id})
    db.add(rule)
    commit_or_conflict(db, _NAME_TAKEN)
    logger.info(f"User {user.id} created {rule.config.type} rule {rule.id}")
    return rule


@router.get("/{rule_id}", response_model=RuleOut)
def get_rule(rule_id: int, user: CurrentUser, db: DbSession) -> Rule:
    return get_visible_rule(db, user, rule_id)


@router.patch("/{rule_id}", response_model=RuleOut)
def update_rule(rule_id: int, body: RuleUpdate, user: CurrentUser, db: DbSession) -> Rule:
    rule = _get_own_rule(db, user, rule_id)
    if "name" in body.model_fields_set:
        rule.name = body.name
    if "config" in body.model_fields_set:
        rule.config = body.config
    db.add(rule)
    commit_or_conflict(db, _NAME_TAKEN)
    logger.info(f"User {user.id} updated {rule.config.type} rule {rule.id} ({', '.join(sorted(body.model_fields_set))})")
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, user: CurrentUser, db: DbSession) -> None:
    """Also removes the rule from all rulesets"""
    db.delete(_get_own_rule(db, user, rule_id))
    db.commit()
    logger.info(f"User {user.id} deleted rule {rule_id}")
