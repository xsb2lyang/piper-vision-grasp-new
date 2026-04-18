from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml
from PIL import Image

from piper_app.config import repo_root


def resolve_repo_path(path_like: str | Path) -> Path:
    path = Path(path_like)
    if path.is_absolute():
        return path
    return repo_root() / path


def display_repo_path(path_like: str | Path) -> str:
    path = resolve_repo_path(path_like)
    root = repo_root()
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def ensure_directory(path_like: str | Path) -> Path:
    path = resolve_repo_path(path_like)
    path.mkdir(parents=True, exist_ok=True)
    return path


def timestamp_string() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def create_session_dir(base_dir: str | Path, kind: str) -> Path:
    session_root = ensure_directory(base_dir) / f"{timestamp_string()}_{kind}"
    session_root.mkdir(parents=True, exist_ok=True)
    return session_root


def write_yaml(path_like: str | Path, payload: dict[str, Any]) -> Path:
    path = resolve_repo_path(path_like)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
    return path


def save_color_png(path_like: str | Path, rgb_image: np.ndarray) -> Path:
    path = resolve_repo_path(path_like)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb_image.astype(np.uint8), mode="RGB").save(path)
    return path


def save_depth_png(path_like: str | Path, depth_m: np.ndarray) -> Path:
    path = resolve_repo_path(path_like)
    path.parent.mkdir(parents=True, exist_ok=True)
    depth_mm = np.clip(np.rint(depth_m * 1000.0), 0.0, float(np.iinfo(np.uint16).max)).astype(np.uint16)
    cv2.imwrite(str(path), depth_mm)
    return path
