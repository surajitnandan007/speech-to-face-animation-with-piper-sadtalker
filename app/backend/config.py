from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]


def _load_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def _env_path(name: str, default: Optional[Path] = None) -> Optional[Path]:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    return Path(raw_value).expanduser().resolve()


def _env_text(name: str, default: str) -> str:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip()
    return normalized or default


@dataclass(slots=True)
class AppConfig:
    sadtalker_repo_path: Path
    sadtalker_python_executable: str
    checkpoint_dir: Optional[Path]
    default_source_image: Optional[Path]
    upload_dir: Path
    results_dir: Path


def load_config() -> AppConfig:
    _load_env_file()

    base_storage = BASE_DIR / "storage"
    return AppConfig(
        sadtalker_repo_path=_env_path("SADTALKER_REPO_PATH", Path("/opt/SadTalker"))
        or Path("/opt/SadTalker"),
        sadtalker_python_executable=_env_text(
            "SADTALKER_PYTHON_EXECUTABLE",
            sys.executable,
        ),
        checkpoint_dir=_env_path("SADTALKER_CHECKPOINT_DIR"),
        default_source_image=_env_path("DEFAULT_SOURCE_IMAGE"),
        upload_dir=_env_path("UPLOAD_DIR", base_storage / "uploads")
        or (base_storage / "uploads"),
        results_dir=_env_path("RESULTS_DIR", base_storage / "results")
        or (base_storage / "results"),
    )
