from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_yaml_config(relative_path: str) -> Dict[str, Any]:
    path = repo_root() / relative_path
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config at {path} must be a mapping.")
    return data


def load_project_defaults() -> Dict[str, Dict[str, Any]]:
    return {
        "robot": load_yaml_config("configs/robot/piper_default.yaml"),
        "teleop": load_yaml_config("configs/teleop/default.yaml"),
        "camera": load_yaml_config("configs/camera/d405_default.yaml"),
        "calibration": load_yaml_config("configs/calibration/default.yaml"),
        "task": load_yaml_config("configs/task/pick_demo_default.yaml"),
    }
