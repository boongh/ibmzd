import time

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, or_

from src.models import AuthToken, ChatSession, LlmModel, Rule, Ruleset, User
from src.privacy_service import PrivacyService
from src.security import hash_token

_bearer = HTTPBearer(auto_error=False)


def get_db(request: Request) -> Iterator[Session]:
    # expire_on_commit=False: objects stay readable after commit, e.g. while FastAPI serializes them
    with Session(request.app.state.engine, expire_on_commit=False) as session:
        yield session


DbSession = Annotated[Session, Depends(get_db)]


def get_privacy(request: Request) -> PrivacyService:
    return request.app.state.privacy


Privacy = Annotated[PrivacyService, Depends(get_privacy)]


def get_current_token(
    db: DbSession, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> AuthToken:
    token = db.get(AuthToken, hash_token(credentials.credentials)) if credentials else None
    if token is None or token.expires_at <= time.time():
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"}
        )
    return token


CurrentToken = Annotated[AuthToken, Depends(get_current_token)]


def get_current_user(db: DbSession, token: CurrentToken) -> User:
    user = db.get(User, token.user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated", headers={"WWW-Authenticate": "Bearer"})
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def commit_or_conflict(db: Session, detail: str) -> None:
    """Commit; a unique constraint violation (e.g. duplicate name) becomes 409"""
    _or_conflict(db, db.commit, detail)


def flush_or_conflict(db: Session, detail: str) -> None:
    """Like commit_or_conflict, but keeps the transaction open (gets ids for follow-up rows)"""
    _or_conflict(db, db.flush, detail)


def _or_conflict(db: Session, action: Callable[[], None], detail: str) -> None:
    try:
        action()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail) from None


# Other users' objects are reported as 404, so that their existence isn't leaked

def visible_rules(user: User):
    """Builtin rules + the user's own rules"""
    return or_(col(Rule.owner_id).is_(None), col(Rule.owner_id) == user.id)


def get_visible_rule(db: Session, user: User, rule_id: int) -> Rule:
    rule = db.get(Rule, rule_id)
    if rule is None or rule.owner_id not in (None, user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    return rule


def get_owned_ruleset(db: Session, user: User, ruleset_id: int) -> Ruleset:
    ruleset = db.get(Ruleset, ruleset_id)
    if ruleset is None or ruleset.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ruleset not found")
    return ruleset


def get_owned_llm_model(db: Session, user: User, model_id: int) -> LlmModel:
    model = db.get(LlmModel, model_id)
    if model is None or model.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "LLM model not found")
    return model


def get_owned_session(db: Session, user: User, session_id: int) -> ChatSession:
    chat = db.get(ChatSession, session_id)
    if chat is None or chat.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return chat
