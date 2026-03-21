from __future__ import annotations

import shutil
import subprocess
import uuid
import wave
from pathlib import Path
from typing import Optional

from .config import AppConfig
from .exceptions import ConfigurationError, GenerationError
from .models import GenerationOptions, GenerationResult


ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class SadTalkerService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.config.upload_dir.mkdir(parents=True, exist_ok=True)
        self.config.results_dir.mkdir(parents=True, exist_ok=True)

    def describe_setup(self) -> dict[str, str]:
        return {
            "sadtalker_repo_path": str(self.config.sadtalker_repo_path),
            "sadtalker_python_executable": self.config.sadtalker_python_executable,
            "checkpoint_dir": (
                str(self.config.checkpoint_dir) if self.config.checkpoint_dir else ""
            ),
            "default_source_image": (
                str(self.config.default_source_image)
                if self.config.default_source_image
                else ""
            ),
            "piper_voice": self.config.piper_voice,
            "piper_data_dir": str(self.config.piper_data_dir),
            "piper_download_dir": str(self.config.piper_download_dir),
            "upload_dir": str(self.config.upload_dir),
            "results_dir": str(self.config.results_dir),
        }

    def generate(
        self,
        audio_file: str | Path,
        source_image: Optional[str | Path],
        options: GenerationOptions,
    ) -> GenerationResult:
        self._validate_runtime()

        job_id = uuid.uuid4().hex[:12]
        upload_job_dir = self.config.upload_dir / job_id
        result_job_dir = self.config.results_dir / job_id
        upload_job_dir.mkdir(parents=True, exist_ok=True)
        result_job_dir.mkdir(parents=True, exist_ok=True)

        audio_path = self._prepare_audio_file(Path(audio_file), upload_job_dir / "input.wav")
        image_path = self._prepare_source_image(
            Path(source_image) if source_image else None,
            upload_job_dir,
        )
        command = self._build_command(audio_path, image_path, result_job_dir, options)

        completed = subprocess.run(
            command,
            cwd=str(self.config.sadtalker_repo_path),
            capture_output=True,
            text=True,
            check=False,
        )

        logs = self._combine_logs(completed.stdout, completed.stderr)
        if completed.returncode != 0:
            raise GenerationError(
                "SadTalker finished with an error. Check the logs below for details.",
                logs=logs,
            )

        output_video = self._find_output_video(result_job_dir)
        if output_video is None:
            raise GenerationError(
                "SadTalker completed, but no output video was found in the results folder.",
                logs=logs,
            )

        return GenerationResult(
            job_id=job_id,
            audio_path=audio_path,
            source_image_path=image_path,
            video_path=output_video,
            logs=logs or "SadTalker completed successfully.",
        )

    def _validate_runtime(self) -> None:
        repo_path = self.config.sadtalker_repo_path
        if not repo_path.exists():
            raise ConfigurationError(
                f"SADTALKER_REPO_PATH does not exist: {repo_path}"
            )

        inference_script = repo_path / "inference.py"
        if not inference_script.exists():
            raise ConfigurationError(
                f"SadTalker inference script was not found at {inference_script}."
            )

        if self.config.checkpoint_dir:
            if not self.config.checkpoint_dir.exists():
                raise ConfigurationError(
                    f"SADTALKER_CHECKPOINT_DIR does not exist: {self.config.checkpoint_dir}"
                )
            if not any(self.config.checkpoint_dir.iterdir()):
                raise ConfigurationError(
                    "SADTALKER_CHECKPOINT_DIR exists but is empty. Add the SadTalker model "
                    "files before deploying this worker."
                )

    def _prepare_audio_file(self, source_path: Path, target_path: Path) -> Path:
        if not str(source_path):
            raise ValueError("Provide a .wav audio file before starting generation.")

        if source_path.suffix.lower() != ".wav":
            raise ValueError("Only .wav audio files are supported.")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)

        try:
            with wave.open(str(target_path), "rb"):
                pass
        except wave.Error as exc:
            raise ValueError("The uploaded file is not a valid .wav audio file.") from exc

        return target_path

    def _prepare_source_image(
        self,
        source_path: Optional[Path],
        upload_job_dir: Path,
    ) -> Path:
        if source_path:
            if source_path.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
                supported = ", ".join(sorted(ALLOWED_IMAGE_SUFFIXES))
                raise ValueError(f"Supported source image types are: {supported}")

            destination = upload_job_dir / f"source{source_path.suffix.lower()}"
            shutil.copy2(source_path, destination)
            return destination

        if self.config.default_source_image and self.config.default_source_image.exists():
            return self.config.default_source_image

        raise ConfigurationError(
            "SadTalker needs a source face image. Provide one in the job input or set "
            "DEFAULT_SOURCE_IMAGE."
        )

    def _build_command(
        self,
        audio_path: Path,
        image_path: Path,
        result_dir: Path,
        options: GenerationOptions,
    ) -> list[str]:
        inference_script = self.config.sadtalker_repo_path / "inference.py"

        command = [
            self.config.sadtalker_python_executable,
            str(inference_script),
            "--driven_audio",
            str(audio_path),
            "--source_image",
            str(image_path),
            "--result_dir",
            str(result_dir),
            "--preprocess",
            options.preprocess,
            "--pose_style",
            str(options.pose_style),
            "--expression_scale",
            str(options.expression_scale),
            "--size",
            str(options.size),
        ]

        if self.config.checkpoint_dir:
            command.extend(["--checkpoint_dir", str(self.config.checkpoint_dir)])

        if options.still_mode:
            command.append("--still")

        if options.enhancer:
            command.extend(["--enhancer", options.enhancer])

        return command

    @staticmethod
    def _combine_logs(stdout: str, stderr: str) -> str:
        parts = [part.strip() for part in (stdout, stderr) if part.strip()]
        return "\n\n".join(parts)

    @staticmethod
    def _find_output_video(result_dir: Path) -> Optional[Path]:
        candidates = sorted(
            result_dir.rglob("*.mp4"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return candidates[0] if candidates else None
