from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class GenerationOptions:
    preprocess: str = "full"
    pose_style: int = 0
    expression_scale: float = 1.0
    size: int = 256
    still_mode: bool = True
    enhancer: Optional[str] = None


@dataclass(slots=True)
class GenerationResult:
    job_id: str
    audio_path: Path
    source_image_path: Path
    video_path: Path
    logs: str
