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

class AuthConfig(BaseModel):
    token_ttl_hours: int = Field(default=24 * 7, ge=1)

class NerConfig(BaseModel):
    # Local dir of LiquidAI/LFM2.5-Encoder-350M-PII-Detector (needs torch + transformers).
    # Not set -> NER disabled, and sessions whose ruleset has an NER rule fail closed
    model_path: Path | None = None

class AppConfig(BaseModel):
    server: ServerConfig
    database: DatabaseConfig
    log: LogConfig
    auth: AuthConfig = Field(default_factory=AuthConfig)
    ner: NerConfig = Field(default_factory=NerConfig)

    @classmethod
    def load_config(cls, filepath: str) -> "AppConfig":
        with open(filepath, "rb") as r:
            data = tomllib.load(r)

        return cls.model_validate(data)
