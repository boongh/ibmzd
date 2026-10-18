import logging

import uvicorn

from fastapi import FastAPI
from loguru import logger

from src import auth, db, llm_models, rules, rulesets, sessions
from src.config import AppConfig
from src.privacy_service import PrivacyService


class _InterceptHandler(logging.Handler):
    """Forwards stdlib logging (used by src.privacy_engine) to loguru"""

    def emit(self, record: logging.LogRecord) -> None:
        logger.opt(exception=record.exc_info).log(record.levelname, record.getMessage())


def create_app(app_conf: AppConfig) -> FastAPI:
    engine = db.create_db_engine(app_conf.database.path)
    db.init_db(engine)

    ner_detector = None
    if app_conf.ner.model_path is not None:
        from src.ner import LfmPiiDetector

        logger.info(f"Loading NER model from {app_conf.ner.model_path}")
        ner_detector = LfmPiiDetector(app_conf.ner.model_path)
    else:
        logger.info("NER disabled; sessions whose ruleset has an NER rule will refuse to chat")

    app = FastAPI(title="GateKeeper")
    app.state.config = app_conf
    app.state.engine = engine
    app.state.privacy = PrivacyService(ner_detector)
    for module in (auth, llm_models, rules, rulesets, sessions):
        app.include_router(module.router)
    return app


def run(app_conf: AppConfig):
    logging.getLogger("src").addHandler(_InterceptHandler())
    uvicorn.run(
        create_app(app_conf),
        host=str(app_conf.server.host),
        port=app_conf.server.port,
        log_level=app_conf.log.level.lower(),
    )
