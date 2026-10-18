import time

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import delete
from sqlmodel import col, select

from src.deps import CurrentToken, CurrentUser, DbSession, commit_or_conflict
from src.models import AuthToken, User
from src.schemas import LoginRequest, TokenOut, UserCreate, UserOut
from src.security import DUMMY_PASSWORD_HASH, hash_password, hash_token, new_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: DbSession) -> User:
    user = User.model_validate(body, update={"password_hash": hash_password(body.password)})
    db.add(user)
    commit_or_conflict(db, "Username already exists")
    return user


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, db: DbSession, request: Request) -> TokenOut:
    user = db.exec(select(User).where(User.username == body.username)).first()
    # Always run scrypt, so the response time doesn't reveal whether the username exists
    password_ok = verify_password(body.password, user.password_hash if user else DUMMY_PASSWORD_HASH)
    if user is None or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password")

    now = int(time.time())
    db.exec(delete(AuthToken).where(col(AuthToken.expires_at) <= now))
    token = new_token()
    expires_at = now + request.app.state.config.auth.token_ttl_hours * 3600
    db.add(AuthToken(token_hash=hash_token(token), user_id=user.id, expires_at=expires_at))
    db.commit()
    return TokenOut(access_token=token, expires_at=expires_at)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: CurrentToken, db: DbSession) -> None:
    db.delete(token)
    db.commit()


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
