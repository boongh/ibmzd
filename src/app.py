import inspect
import logging

import uvicorn

from fastapi import FastAPI
from loguru import logger

from src import auth, db, llm_models, rules, rulesets, sessions
from src.config import AppConfig
from src.privacy_service import PrivacyService


class _InterceptHandler(logging.Handler):
    """Forwards stdlib logging (uvicorn, src.privacy_engine, httpx) to loguru"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        # Report the caller of the stdlib logger, not this handler
        frame, depth = inspect.currentframe(), 0
        while frame is not None and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def _route_stdlib_logging(level: str) -> None:
    logging.basicConfig(handlers=[_InterceptHandler()], level=level, force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers = []  # propagate to the root handler above
    # Connection level details, too noisy at DEBUG
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def create_app(app_conf: AppConfig) -> FastAPI:
    engine = db.create_db_engine(app_conf.database.path)
    db.init_db(engine)
    logger.info(f"Database ready at {app_conf.database.path}")

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
    _route_stdlib_logging(app_conf.log.level)
    uvicorn.run(
        create_app(app_conf),
        host=str(app_conf.server.host),
        port=app_conf.server.port,
        log_level=app_conf.log.level.lower(),
        log_config=None,  # don't install uvicorn's own handlers, everything goes through loguru
    )
