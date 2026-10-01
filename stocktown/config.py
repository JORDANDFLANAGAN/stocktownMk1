from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

# Vite's dev server. Override with a comma-separated CORS_ALLOWED_ORIGINS for deployments.
DEFAULT_CORS_ALLOWED_ORIGINS: Final[tuple[str, ...]] = ("http://localhost:5173",)
# Override with STOCKTOWN_DB_PATH, e.g. a mounted volume when deployed.
DEFAULT_DATABASE_PATH: Final[Path] = Path("data/stocktown.sqlite3")


@dataclass(frozen=True, slots=True)
class AlpacaCredentials:
    api_key: str
    api_secret: str

    def __repr__(self) -> str:
        return "AlpacaCredentials(api_key='***', api_secret='***')"


@dataclass(frozen=True, slots=True)
class FinnhubCredentials:
    api_key: str

    def __repr__(self) -> str:
        return "FinnhubCredentials(api_key='***')"


@dataclass(frozen=True, slots=True)
class Settings:
    alpaca: AlpacaCredentials
    finnhub: FinnhubCredentials


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load environment variables once and return typed application settings."""

    load_dotenv()
    return Settings(
        alpaca=AlpacaCredentials(
            api_key=require_env("ALPACA_API_KEY"),
            api_secret=require_env("ALPACA_API_SECRET"),
        ),
        finnhub=FinnhubCredentials(
            api_key=require_env("FINNHUB_API_KEY"),
        ),
    )


def get_cors_allowed_origins() -> tuple[str, ...]:
    """Kept apart from get_settings() so starting the app never requires API keys."""
    load_dotenv()
    configured = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    origins = tuple(origin.strip() for origin in configured.split(",") if origin.strip())
    return origins or DEFAULT_CORS_ALLOWED_ORIGINS


def get_database_path() -> Path:
    """Where the SQLite database lives. Like the CORS origins, it needs no API keys."""
    load_dotenv()
    return Path(os.environ.get("STOCKTOWN_DB_PATH") or DEFAULT_DATABASE_PATH)


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Environment variable {name!r} is not set. "
            f"Add it to your .env file or export it in your shell."
        )
    return value
