from pathlib import Path

from sqlalchemy import Engine, event
from sqlmodel import SQLModel, create_engine

from src import models  # noqa: F401  registers all tables in SQLModel.metadata


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
