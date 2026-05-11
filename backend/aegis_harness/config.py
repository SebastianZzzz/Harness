from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def normalize_clod_base_url(value: str) -> str:
    base = value.rstrip("/")
    if base in {"https://clod.io", "http://clod.io"}:
        return "https://api.clod.io/v1"
    if base == "https://api.clod.io":
        return "https://api.clod.io/v1"
    if not base.endswith("/v1"):
        return f"{base}/v1"
    return base


def normalize_gemini_base_url(value: str) -> str:
    return value.rstrip("/")


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_model: str = "gemini-2.5-pro"
    clod_api_key: str = ""
    clod_base_url: str = "https://api.clod.io/v1"
    clod_model: str = "GPT OSS 120B"
    max_iterations: int = 3
    confidence_threshold: int = 70

    @classmethod
    def from_env(cls, root: Path) -> "Settings":
        load_dotenv(root / ".env")
        gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        clod_api_key = os.environ.get("CLOD_API_KEY", "").strip()
        if not gemini_api_key and not clod_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY or CLOD_API_KEY is missing. Add at least one provider key to .env."
            )
        return cls(
            gemini_api_key=gemini_api_key,
            gemini_base_url=normalize_gemini_base_url(
                os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
            ),
            gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-pro").strip()
            or "gemini-2.5-pro",
            clod_api_key=clod_api_key,
            clod_base_url=normalize_clod_base_url(
                os.environ.get("CLOD_BASE_URL", "https://api.clod.io/v1")
            ),
            clod_model=os.environ.get("CLOD_MODEL", "GPT OSS 120B").strip() or "GPT OSS 120B",
            max_iterations=int(os.environ.get("AEGIS_MAX_ITERATIONS", "3")),
            confidence_threshold=int(os.environ.get("AEGIS_CONFIDENCE_THRESHOLD", "70")),
        )
