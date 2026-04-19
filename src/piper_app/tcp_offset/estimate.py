from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from piper_app.calibration.session import write_yaml
from piper_app.calibration.transforms import matrix_to_yaml_dict, pose6_to_matrix


@dataclass
class TcpOffsetSample:
    index: int
    timestamp: str
    target_pixel: tuple[int, int]
    target_base_point_m: tuple[float, float, float]
    flange_pose6: list[float]
    offset_flange_xyz_m: tuple[float, float, float]


@dataclass
class TcpOffsetSummary:
    mean_xyz_m: tuple[float, float, float]
    std_xyz_m: tuple[float, float, float]
    std_norm_m: float
    sample_count: int


def create_tcp_offset_sample(
    *,
    index: int,
    target_pixel: tuple[int, int],
    target_base_point_m: tuple[float, float, float],
    flange_pose6: list[float],
) -> TcpOffsetSample:
    T_base_flange = pose6_to_matrix(flange_pose6)
    p_target_base = np.asarray(target_base_point_m, dtype=np.float64).reshape(3)
    p_flange_base = np.asarray(T_base_flange[:3, 3], dtype=np.float64).reshape(3)
    R_base_flange = np.asarray(T_base_flange[:3, :3], dtype=np.float64)

    delta_base = p_target_base - p_flange_base
    delta_flange = R_base_flange.T @ delta_base
    return TcpOffsetSample(
        index=int(index),
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        target_pixel=(int(target_pixel[0]), int(target_pixel[1])),
        target_base_point_m=tuple(float(value) for value in p_target_base.tolist()),
        flange_pose6=[float(value) for value in flange_pose6],
        offset_flange_xyz_m=tuple(float(value) for value in delta_flange.tolist()),
    )


def summarize_tcp_offset_samples(samples: list[TcpOffsetSample]) -> Optional[TcpOffsetSummary]:
    if not samples:
        return None
    values = np.asarray([sample.offset_flange_xyz_m for sample in samples], dtype=np.float64)
    mean_xyz = np.mean(values, axis=0)
    std_xyz = np.std(values, axis=0)
    return TcpOffsetSummary(
        mean_xyz_m=tuple(float(value) for value in mean_xyz.tolist()),
        std_xyz_m=tuple(float(value) for value in std_xyz.tolist()),
        std_norm_m=float(np.linalg.norm(std_xyz)),
        sample_count=len(samples),
    )


def grade_tcp_offset_summary(summary: Optional[TcpOffsetSummary]) -> tuple[str, str, str]:
    if summary is None or summary.sample_count == 0:
        return ("Pending", "#475569", "Capture aligned samples to estimate the TCP translation offset.")
    if summary.std_norm_m <= 0.005:
        return ("Good", "#166534", f"Sample agreement is tight ({summary.std_norm_m * 1000.0:.1f} mm std norm).")
    if summary.std_norm_m <= 0.015:
        return ("Fair", "#a16207", f"Usable, but sample spread is still {summary.std_norm_m * 1000.0:.1f} mm.")
    return ("Poor", "#b91c1c", f"Sample spread is {summary.std_norm_m * 1000.0:.1f} mm; re-align and recapture.")


def save_tcp_offset_yaml(
    output_path: str | Path,
    samples: list[TcpOffsetSample],
    summary: TcpOffsetSummary,
    *,
    handeye_path: str,
    camera_serial: str,
) -> Path:
    payload = {
        "kind": "tcp_offset_estimate",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "camera_serial": str(camera_serial),
        "handeye_path": str(handeye_path),
        "reference_frame": "flange",
        "suggested_tcp_offset": [
            float(summary.mean_xyz_m[0]),
            float(summary.mean_xyz_m[1]),
            float(summary.mean_xyz_m[2]),
            0.0,
            0.0,
            0.0,
        ],
        "statistics": {
            "sample_count": int(summary.sample_count),
            "mean_xyz_m": [float(value) for value in summary.mean_xyz_m],
            "std_xyz_m": [float(value) for value in summary.std_xyz_m],
            "std_norm_m": float(summary.std_norm_m),
        },
        "samples": [
            {
                "index": int(sample.index),
                "timestamp": sample.timestamp,
                "target_pixel": [int(sample.target_pixel[0]), int(sample.target_pixel[1])],
                "target_base_point_m": [float(value) for value in sample.target_base_point_m],
                "flange_pose6": [float(value) for value in sample.flange_pose6],
                "T_base_flange": matrix_to_yaml_dict(pose6_to_matrix(sample.flange_pose6)),
                "offset_flange_xyz_m": [float(value) for value in sample.offset_flange_xyz_m],
            }
            for sample in samples
        ],
    }
    return write_yaml(output_path, payload)
