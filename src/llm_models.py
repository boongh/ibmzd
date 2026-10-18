from fastapi import APIRouter, status
from loguru import logger
from sqlmodel import select

from src.deps import CurrentUser, DbSession, commit_or_conflict, get_owned_llm_model
from src.models import LlmModel
from src.schemas import LlmModelCreate, LlmModelOut, LlmModelUpdate

router = APIRouter(prefix="/llm-models", tags=["llm-models"])

_NAME_TAKEN = "An LLM model with this name already exists"


def _out(model: LlmModel) -> LlmModelOut:
    return LlmModelOut(
        id=model.id, name=model.name, base_url=model.base_url, model=model.model, has_api_key=bool(model.api_key)
    )


@router.get("", response_model=list[LlmModelOut])
def list_llm_models(user: CurrentUser, db: DbSession) -> list[LlmModelOut]:
    models = db.exec(select(LlmModel).where(LlmModel.owner_id == user.id).order_by(LlmModel.id)).all()
    return [_out(m) for m in models]


@router.post("", response_model=LlmModelOut, status_code=status.HTTP_201_CREATED)
def create_llm_model(body: LlmModelCreate, user: CurrentUser, db: DbSession) -> LlmModelOut:
    model = LlmModel.model_validate(body, update={"owner_id": user.id})
    db.add(model)
    commit_or_conflict(db, _NAME_TAKEN)
    logger.info(f"User {user.id} added LLM model {model.id}")
    return _out(model)


@router.get("/{model_id}", response_model=LlmModelOut)
def get_llm_model(model_id: int, user: CurrentUser, db: DbSession) -> LlmModelOut:
    return _out(get_owned_llm_model(db, user, model_id))


@router.patch("/{model_id}", response_model=LlmModelOut)
def update_llm_model(model_id: int, body: LlmModelUpdate, user: CurrentUser, db: DbSession) -> LlmModelOut:
    model = get_owned_llm_model(db, user, model_id)
    model.sqlmodel_update(body.model_dump(exclude_unset=True))
    db.add(model)
    commit_or_conflict(db, _NAME_TAKEN)
    logger.info(f"User {user.id} updated LLM model {model.id} ({', '.join(sorted(body.model_fields_set))})")
    return _out(model)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_llm_model(model_id: int, user: CurrentUser, db: DbSession) -> None:
    db.delete(get_owned_llm_model(db, user, model_id))
    db.commit()
    logger.info(f"User {user.id} deleted LLM model {model_id}")
