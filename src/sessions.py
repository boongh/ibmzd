import json

from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import Engine
from sqlmodel import Session, col, select

from src.deps import (
    CurrentUser,
    DbSession,
    Privacy,
    get_owned_llm_model,
    get_owned_ruleset,
    get_owned_session,
)
from src.llm import LlmEndpoint, LlmError, stream_chat
from src.models import ChatSession, LlmModel, Message, Redaction
from src.privacy_service import PrivacyService, load_ruleset
from src.schemas import MessageCreate, MessageOut, RedactionOut, SessionCreate, SessionOut, SessionUpdate

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(user: CurrentUser, db: DbSession) -> list[ChatSession]:
    return list(db.exec(select(ChatSession).where(ChatSession.user_id == user.id).order_by(col(ChatSession.id).desc())))


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(body: SessionCreate, user: CurrentUser, db: DbSession) -> ChatSession:
    get_owned_ruleset(db, user, body.ruleset_id)
    if body.llm_model_id is not None:
        get_owned_llm_model(db, user, body.llm_model_id)
    chat = ChatSession.model_validate(body, update={"user_id": user.id})
    db.add(chat)
    db.commit()
    return chat


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, user: CurrentUser, db: DbSession) -> ChatSession:
    return get_owned_session(db, user, session_id)


@router.patch("/{session_id}", response_model=SessionOut)
def update_session(session_id: int, body: SessionUpdate, user: CurrentUser, db: DbSession) -> ChatSession:
    chat = get_owned_session(db, user, session_id)
    fields = body.model_fields_set
    if "ruleset_id" in fields:
        chat.ruleset_id = get_owned_ruleset(db, user, body.ruleset_id).id
    if "llm_model_id" in fields:
        model_id = body.llm_model_id
        chat.llm_model_id = None if model_id is None else get_owned_llm_model(db, user, model_id).id
    if "title" in fields:
        chat.title = body.title
    db.add(chat)
    db.commit()
    return chat


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, user: CurrentUser, db: DbSession) -> None:
    """Also deletes its messages and replacement table"""
    db.delete(get_owned_session(db, user, session_id))
    db.commit()


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def list_messages(session_id: int, user: CurrentUser, db: DbSession, response: Response) -> list[Message]:
    """History; `content` contains the raw originals"""
    chat = get_owned_session(db, user, session_id)
    response.headers["Cache-Control"] = "no-store"
    return list(db.exec(select(Message).where(Message.session_id == chat.id).order_by(col(Message.id))))


@router.get("/{session_id}/redactions", response_model=list[RedactionOut])
def list_redactions(session_id: int, user: CurrentUser, db: DbSession, response: Response) -> list[Redaction]:
    """The session's replacement table (placeholder -> original value); raw PII, for the session owner only"""
    chat = get_owned_session(db, user, session_id)
    response.headers["Cache-Control"] = "no-store"
    return list(db.exec(select(Redaction).where(Redaction.session_id == chat.id).order_by(col(Redaction.id))))


@router.post("/{session_id}/messages")
def send_message(
    session_id: int, body: MessageCreate, user: CurrentUser, db: DbSession, privacy: Privacy, request: Request
) -> StreamingResponse:
    """Redacts the message, sends it with the history to the LLM and streams the reply as SSE

    Events (`data:` JSON):
      user_message {id, llm_content}  the stored message and the redacted text sent to the LLM
      delta {content}...              raw reply chunks (placeholders, see /redactions)
      done {message_id, content}      the stored reply, `content` restored with the originals
      error {detail}
    """
    chat = get_owned_session(db, user, session_id)
    if chat.ruleset_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Session has no ruleset; bind one before chatting")
    if chat.llm_model_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Session has no LLM model; bind one before chatting")
    model = db.get(LlmModel, chat.llm_model_id)  # ownership is checked when it is bound

    history = db.exec(select(Message).where(Message.session_id == chat.id).order_by(col(Message.id))).all()
    llm_messages = [{"role": m.role, "content": m.llm_content} for m in history]

    ruleset = load_ruleset(db, chat.ruleset_id)
    message = privacy.redact_message(db, chat, ruleset, body.content) if ruleset else None
    if message is None:
        # Fail closed (AGENTS.md): nothing is stored or sent to the LLM
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "The message could not be redacted with this session's ruleset; nothing was sent",
        )
    llm_messages.append({"role": "user", "content": message.llm_content})

    return StreamingResponse(
        _stream_reply(
            request.app.state.engine, privacy, chat.id, message, LlmEndpoint.from_model(model), llm_messages
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream_reply(
    engine: Engine,
    privacy: PrivacyService,
    session_id: int,
    message: Message,
    endpoint: LlmEndpoint,
    llm_messages: list[dict[str, str]],
) -> Iterator[str]:
    yield _sse({"type": "user_message", "id": message.id, "llm_content": message.llm_content})

    parts: list[str] = []
    try:
        for delta in stream_chat(endpoint, llm_messages):
            parts.append(delta)
            yield _sse({"type": "delta", "content": delta})
    except LlmError as e:
        logger.warning(f"Session {session_id}: {e}")  # LlmError never contains message text
        yield _sse({"type": "error", "detail": str(e)})
        return
    except Exception as e:
        logger.error(f"Session {session_id}: LLM stream failed: {type(e).__name__}")  # type only, no text
        yield _sse({"type": "error", "detail": "LLM request failed"})
        return

    # The request's DB session may already be closed while streaming, so use a new one
    raw = "".join(parts)
    try:
        with Session(engine, expire_on_commit=False) as db:
            restored = privacy.restore(db, session_id, raw)
            if restored is None:
                raise RuntimeError("restore failed")
            reply = Message(session_id=session_id, role="assistant", content=restored, llm_content=raw)
            db.add(reply)
            db.commit()
    except Exception as e:
        logger.error(f"Session {session_id}: failed to save the reply: {type(e).__name__}")
        yield _sse({"type": "error", "detail": "Failed to save the reply"})
        return
    yield _sse({"type": "done", "message_id": reply.id, "content": restored})
