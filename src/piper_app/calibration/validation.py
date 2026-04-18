from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from piper_app.calibration.session import write_yaml
from piper_app.calibration.transforms import matrix_to_pose6, matrix_to_yaml_dict, rotation_distance_deg


@dataclass
class ValidationSample:
    index: int
    timestamp: str
    color_image_path: str
    depth_image_path: str
    summary_path: str
    T_base_board: np.ndarray
    charuco_count: int
    distance_m: Optional[float]


@dataclass
class ValidationSummary:
    sample_count: int
    translation_std_m: float
    translation_mean_m: tuple[float, float, float]
    rotation_mean_deg: float
    rotation_max_deg: float


def create_validation_sample(
    index: int,
    color_image_path: str,
    depth_image_path: str,
    summary_path: str,
    T_base_board: np.ndarray,
    charuco_count: int,
    distance_m: Optional[float],
) -> ValidationSample:
    return ValidationSample(
        index=int(index),
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        color_image_path=str(color_image_path),
        depth_image_path=str(depth_image_path),
        summary_path=str(summary_path),
        T_base_board=np.asarray(T_base_board, dtype=np.float64),
        charuco_count=int(charuco_count),
        distance_m=None if distance_m is None else float(distance_m),
    )


def summarize_validation_samples(samples: list[ValidationSample]) -> ValidationSummary:
    if not samples:
        return ValidationSummary(
            sample_count=0,
            translation_std_m=0.0,
            translation_mean_m=(0.0, 0.0, 0.0),
            rotation_mean_deg=0.0,
            rotation_max_deg=0.0,
        )
    translations = np.array([sample.T_base_board[:3, 3] for sample in samples], dtype=np.float64)
    translation_std_m = float(np.linalg.norm(np.std(translations, axis=0)))
    translation_mean = tuple(float(value) for value in np.mean(translations, axis=0).tolist())
    reference_rotation = samples[0].T_base_board[:3, :3]
    angles = [rotation_distance_deg(reference_rotation, sample.T_base_board[:3, :3]) for sample in samples]
    return ValidationSummary(
        sample_count=len(samples),
        translation_std_m=translation_std_m,
        translation_mean_m=translation_mean,
        rotation_mean_deg=float(np.mean(angles)),
        rotation_max_deg=float(np.max(angles)),
    )


def save_validation_sample_summary(
    output_path: str | Path,
    sample: ValidationSample,
) -> Path:
    payload = {
        "timestamp": sample.timestamp,
        "charuco_count": int(sample.charuco_count),
        "distance_m": None if sample.distance_m is None else float(sample.distance_m),
        "T_base_board": matrix_to_yaml_dict(sample.T_base_board),
        "color_image_path": sample.color_image_path,
        "depth_image_path": sample.depth_image_path,
    }
    return write_yaml(output_path, payload)


def save_validation_summary_yaml(
    output_path: str | Path,
    summary: ValidationSummary,
    samples: list[ValidationSample],
) -> Path:
    payload = {
        "kind": "handeye_validation_summary",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sample_count": int(summary.sample_count),
        "translation_std_m": float(summary.translation_std_m),
        "translation_mean_m": [float(value) for value in summary.translation_mean_m],
        "rotation_mean_deg": float(summary.rotation_mean_deg),
        "rotation_max_deg": float(summary.rotation_max_deg),
        "reference_pose6": None if not samples else [float(value) for value in matrix_to_pose6(samples[0].T_base_board)],
    }
    return write_yaml(output_path, payload)
