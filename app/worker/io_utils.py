from __future__ import annotations

import base64
import binascii
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests


def infer_suffix(
    *,
    path_value: Optional[str],
    url_value: Optional[str],
    fallback_suffix: str,
) -> str:
    candidate = path_value
    if not candidate and url_value:
        candidate = urlparse(url_value).path

    if candidate:
        suffix = Path(candidate).suffix.lower()
        if suffix:
            return suffix

    return fallback_suffix


def materialize_input_file(
    *,
    path_value: Optional[str],
    url_value: Optional[str],
    base64_value: Optional[str],
    suffix: str,
    label: str,
) -> Optional[Path]:
    provided = [value for value in (path_value, url_value, base64_value) if value]
    if not provided:
        return None

    if len(provided) > 1:
        raise ValueError(
            f"Provide only one of {label}_path, {label}_url, or {label}_base64."
        )

    temp_dir = Path(tempfile.mkdtemp(prefix=f"runpod-{label}-"))
    target_path = temp_dir / f"{label}{suffix}"

    if path_value:
        source_path = Path(path_value).expanduser().resolve()
        if not source_path.exists():
            raise ValueError(f"{label}_path does not exist: {source_path}")
        target_path.write_bytes(source_path.read_bytes())
        return target_path

    if url_value:
        response = requests.get(url_value, timeout=120)
        response.raise_for_status()
        target_path.write_bytes(response.content)
        return target_path

    try:
        payload = base64_value.split(",", 1)[1] if "," in base64_value else base64_value
        target_path.write_bytes(base64.b64decode(payload, validate=True))
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"{label}_base64 is not valid base64 data.") from exc

    return target_path


def encode_file_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")
