from __future__ import annotations

import uuid
from typing import Any

import runpod

from app.backend.config import load_config
from app.backend.exceptions import ConfigurationError, GenerationError
from app.backend.models import GenerationOptions
from app.backend.sadtalker_service import SadTalkerService
from app.worker.io_utils import encode_file_to_base64, infer_suffix, materialize_input_file
from app.worker.text_to_speech import synthesize_wav_from_text


SERVICE = SadTalkerService(load_config())


def _parse_options(job_input: dict[str, Any]) -> GenerationOptions:
    options_input = job_input.get("options") or {}
    return GenerationOptions(
        preprocess=str(options_input.get("preprocess", "full")),
        pose_style=int(options_input.get("pose_style", 0)),
        expression_scale=float(options_input.get("expression_scale", 1.0)),
        size=int(options_input.get("size", 256)),
        still_mode=bool(options_input.get("still_mode", True)),
        enhancer=options_input.get("enhancer") or None,
    )


def _materialize_audio(job_input: dict[str, Any]):
    text_input = (job_input.get("text") or "").strip()
    if text_input:
        return synthesize_wav_from_text(
            text=text_input,
            output_path=SERVICE.config.upload_dir / "tts" / f"{uuid.uuid4().hex}.wav",
            config=SERVICE.config,
        )

    return materialize_input_file(
        path_value=job_input.get("audio_path"),
        url_value=job_input.get("audio_url"),
        base64_value=job_input.get("audio_base64"),
        suffix=".wav",
        label="audio",
    )


def handler(job: dict[str, Any]) -> dict[str, Any]:
    job_input = job.get("input", {})

    try:
        audio_path = _materialize_audio(job_input)
    except (RuntimeError, ValueError) as exc:
        return {
            "status": "error",
            "message": str(exc),
            "logs": "",
            "setup": SERVICE.describe_setup(),
        }

    if audio_path is None:
        return {"error": "Provide text or audio_path, audio_url, or audio_base64."}

    source_image_path = materialize_input_file(
        path_value=job_input.get("source_image_path"),
        url_value=job_input.get("source_image_url"),
        base64_value=job_input.get("source_image_base64"),
        suffix=infer_suffix(
            path_value=job_input.get("source_image_path"),
            url_value=job_input.get("source_image_url"),
            fallback_suffix=".png",
        ),
        label="source_image",
    )

    try:
        result = SERVICE.generate(
            audio_file=audio_path,
            source_image=source_image_path,
            options=_parse_options(job_input),
        )
    except (ConfigurationError, GenerationError, ValueError) as exc:
        return {
            "status": "error",
            "message": str(exc),
            "logs": getattr(exc, "logs", ""),
            "setup": SERVICE.describe_setup(),
        }

    response: dict[str, Any] = {
        "status": "completed",
        "job_id": result.job_id,
        "video_path": str(result.video_path),
        "audio_path": str(result.audio_path),
        "source_image_path": str(result.source_image_path),
        "logs": result.logs,
    }

    if bool(job_input.get("return_video_base64", False)):
        response["video_base64"] = encode_file_to_base64(result.video_path)

    return response


runpod.serverless.start({"handler": handler})
