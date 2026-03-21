from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.backend.config import AppConfig


def synthesize_wav_from_text(
    *,
    text: str,
    output_path: Path,
    config: AppConfig,
) -> Path:
    clean_text = text.replace("**", "").replace("*", "").strip()
    if not clean_text:
        raise ValueError("Provide non-empty text for speech synthesis.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    config.piper_data_dir.mkdir(parents=True, exist_ok=True)
    config.piper_download_dir.mkdir(parents=True, exist_ok=True)

    model_value = str(config.piper_voice)
    command = [
        "piper",
        "--model",
        model_value,
        "--json-input",
    ]

    # If the voice is an explicit .onnx file on the mounted volume, Piper can use
    # it directly and does not need lookup/download directories.
    if not model_value.lower().endswith(".onnx"):
        command.extend(
            [
                "--data-dir",
                str(config.piper_data_dir),
                "--download-dir",
                str(config.piper_download_dir),
            ]
        )

    payload = json.dumps(
        {
            "text": clean_text,
            "output_file": str(output_path),
        }
    )

    completed = subprocess.run(
        command,
        input=f"{payload}\n",
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        logs = "\n\n".join(
            part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
        )
        raise RuntimeError(f"Piper failed to synthesize audio.\n{logs}".strip())

    if not output_path.exists():
        raise RuntimeError("Piper finished without creating the output wav file.")

    return output_path
