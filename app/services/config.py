import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


class Settings(BaseModel):
    openai_api_key: str | None
    openai_model: str
    openai_llm_enabled: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    raw_enabled = os.getenv("OPENAI_LLM_ENABLED", "true").strip().lower()
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        openai_llm_enabled=raw_enabled not in {"0", "false", "no", "off"},
    )
