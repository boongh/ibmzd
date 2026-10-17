import tomllib

from typing import Literal
from pathlib import Path
from pydantic import BaseModel, Field, IPvAnyAddress

class ServerConfig(BaseModel):
    host: IPvAnyAddress
    port: int = Field(..., ge=1, le=65535)

class DatabaseConfig(BaseModel):
    path: Path

class LogConfig(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

class AppConfig(BaseModel):
    server: ServerConfig
    database: DatabaseConfig
    log: LogConfig

    @classmethod
    def load_config(cls, filepath: str) -> "AppConfig":
        with open(filepath, "rb") as r:
            data = tomllib.load(r)

        return cls.model_validate(data)
