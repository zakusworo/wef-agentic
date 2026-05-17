"""Central settings loaded from .env + llm.yaml."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]  # wef-agentic/
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXTERNAL_DIR = DATA_DIR / "external"
CONFIG_DIR = Path(__file__).resolve().parent

ProviderName = Literal["ollama-local", "ollama-cloud", "claude-agent-sdk"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        env_prefix="WEF_AGENTIC_",
        extra="ignore",
    )

    provider: ProviderName = "ollama-local"

    ollama_host: str = Field(default="http://localhost:11434", alias="OLLAMA_HOST")
    ollama_api_key: str = Field(default="", alias="OLLAMA_API_KEY")


def load_llm_config() -> dict:
    """Load per-agent LLM config from llm.yaml."""
    path = CONFIG_DIR / "llm.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


settings = Settings()
