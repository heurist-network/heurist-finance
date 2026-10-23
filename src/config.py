"""Environment configuration. The repo `.env` is the only env file read."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_FILE)

HEURIST_API_KEY = os.getenv("HEURIST_API_KEY")
HEURIST_MESH_API_ENDPOINT = os.getenv("MESH_API_ENDPOINT", "https://mesh.heurist.xyz")
HEURIST_MESH_SCHEMA_ENDPOINT = os.getenv(
    "MESH_SCHEMA_ENDPOINT", f"{HEURIST_MESH_API_ENDPOINT.rstrip('/')}/mesh_schema"
)
EODHD_API_KEY = os.getenv("EODHD_API_KEY", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def require_env(name: str, value: str | None) -> str:
    if value and value.strip():
        return value
    raise RuntimeError(f"Missing required environment variable: {name}. Set it in {ENV_FILE}.")
