from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from piper_app.calibration.session import resolve_repo_path


@dataclass
class KeypointRecord:
    name: str
    tcp_pose: list[float]
    joint_angles: list[float]
    note: str
    captured_at: str


def load_keypoint_config(path_like: str | Path) -> dict[str, Any]:
    path = resolve_repo_path(path_like)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Keypoint config at {path} must be a mapping.")
    return data


def save_keypoint_config(path_like: str | Path, payload: dict[str, Any]) -> Path:
    path = resolve_repo_path(path_like)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=True)
    return path


def build_keypoint_payload(
    *,
    robot: str,
    interface: str,
    channel: str,
    bitrate: int,
    tcp_offset: list[float],
    task_defaults: dict[str, Any],
    records: list[KeypointRecord],
) -> dict[str, Any]:
    return {
        "kind": "pick_demo_keypoints",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "robot": str(robot),
        "can": {
            "interface": str(interface),
            "channel": str(channel),
            "bitrate": int(bitrate),
        },
        "tcp_offset": [float(value) for value in tcp_offset],
        "task_defaults": task_defaults,
        "points": {
            record.name: {
                "tcp_pose": [float(value) for value in record.tcp_pose],
                "joint_angles": [float(value) for value in record.joint_angles],
                "note": record.note,
                "captured_at": record.captured_at,
            }
            for record in records
        },
    }


def parse_keypoint_records(payload: dict[str, Any]) -> list[KeypointRecord]:
    points = payload.get("points", {})
    if not isinstance(points, dict):
        return []
    records: list[KeypointRecord] = []
    for name, block in points.items():
        if not isinstance(block, dict):
            continue
        tcp_pose = [float(value) for value in block.get("tcp_pose", [])]
        joint_angles = [float(value) for value in block.get("joint_angles", [])]
        if len(tcp_pose) != 6 or len(joint_angles) != 6:
            continue
        records.append(
            KeypointRecord(
                name=str(name),
                tcp_pose=tcp_pose,
                joint_angles=joint_angles,
                note=str(block.get("note", "")),
                captured_at=str(block.get("captured_at", "")),
            )
        )
    return records


def find_record(records: list[KeypointRecord], name: str) -> Optional[KeypointRecord]:
    for record in records:
        if record.name == name:
            return record
    return None
