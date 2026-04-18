from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from piper_app.calibration.charuco import CharucoBoardConfig, CharucoDetection
from piper_app.calibration.session import write_yaml


@dataclass
class IntrinsicSample:
    index: int
    timestamp: str
    image_path: str
    center_uv: tuple[float, float]
    bbox_area_ratio: float
    charuco_corners: np.ndarray
    charuco_ids: np.ndarray
    charuco_count: int


@dataclass
class IntrinsicCalibrationResult:
    camera_matrix: np.ndarray
    dist_coeffs: np.ndarray
    rms: float
    resolution: tuple[int, int]
    sample_count: int


def build_intrinsics_quality_hint(
    detection: Optional[CharucoDetection],
    samples: list[IntrinsicSample],
    min_corners: int,
    near_area_ratio: float,
    far_area_ratio: float,
    duplicate_threshold: float,
) -> str:
    if detection is None or not detection.success:
        return "Board not detected."
    if detection.charuco_count < int(min_corners):
        return f"Need at least {min_corners} corners, current {detection.charuco_count}."
    if detection.center_uv is None:
        return "Board center unavailable."
    feature = _feature_vector(detection.center_uv, detection.bbox_area_ratio)
    if samples:
        distances = [
            float(np.linalg.norm(feature - _feature_vector(sample.center_uv, sample.bbox_area_ratio)))
            for sample in samples
        ]
        if min(distances) < float(duplicate_threshold):
            return "View is too similar to an existing sample. Move to a different angle."
    if detection.bbox_area_ratio < float(far_area_ratio):
        return "Board looks far away. Move closer or fill more of the image."
    if detection.bbox_area_ratio > float(near_area_ratio):
        return "Board looks too close. Step back to reduce distortion."
    return "Ready to capture."


def create_intrinsic_sample(
    index: int,
    image_path: str,
    detection: CharucoDetection,
) -> IntrinsicSample:
    if detection.charuco_corners is None or detection.charuco_ids is None or detection.center_uv is None:
        raise ValueError("Detection is incomplete for intrinsic sampling.")
    return IntrinsicSample(
        index=int(index),
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        image_path=str(image_path),
        center_uv=(float(detection.center_uv[0]), float(detection.center_uv[1])),
        bbox_area_ratio=float(detection.bbox_area_ratio),
        charuco_corners=np.asarray(detection.charuco_corners, dtype=np.float32).copy(),
        charuco_ids=np.asarray(detection.charuco_ids, dtype=np.int32).copy(),
        charuco_count=int(detection.charuco_count),
    )


def calibrate_intrinsics(
    samples: list[IntrinsicSample],
    board_config: CharucoBoardConfig,
    image_size: tuple[int, int],
) -> IntrinsicCalibrationResult:
    if len(samples) < 3:
        raise ValueError("At least 3 samples are required for intrinsics calibration.")

    board = cv2.aruco.CharucoBoard(
        (int(board_config.squares_x), int(board_config.squares_y)),
        float(board_config.square_length_m),
        float(board_config.marker_length_m),
        cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, board_config.dictionary)),
    )
    all_corners = [sample.charuco_corners for sample in samples]
    all_ids = [sample.charuco_ids for sample in samples]
    rms, camera_matrix, dist_coeffs, _rvecs, _tvecs = cv2.aruco.calibrateCameraCharuco(
        charucoCorners=all_corners,
        charucoIds=all_ids,
        board=board,
        imageSize=(int(image_size[0]), int(image_size[1])),
        cameraMatrix=None,
        distCoeffs=None,
    )
    return IntrinsicCalibrationResult(
        camera_matrix=np.asarray(camera_matrix, dtype=np.float64),
        dist_coeffs=np.asarray(dist_coeffs, dtype=np.float64).reshape(-1),
        rms=float(rms),
        resolution=(int(image_size[0]), int(image_size[1])),
        sample_count=len(samples),
    )


def save_intrinsics_yaml(
    output_path: str | Path,
    result: IntrinsicCalibrationResult,
    board_config: CharucoBoardConfig,
    camera_serial: str,
) -> Path:
    payload = {
        "kind": "camera_intrinsics",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "camera_serial": str(camera_serial),
        "resolution": {
            "width": int(result.resolution[0]),
            "height": int(result.resolution[1]),
        },
        "board": board_config.to_dict(),
        "K": [[float(value) for value in row] for row in result.camera_matrix.tolist()],
        "dist_coeffs": [float(value) for value in result.dist_coeffs.tolist()],
        "rms_reprojection_error": float(result.rms),
        "sample_count": int(result.sample_count),
    }
    return write_yaml(output_path, payload)


def load_intrinsics_yaml(path_like: str | Path) -> dict[str, object]:
    path = Path(path_like)
    if not path.is_absolute():
        from piper_app.calibration.session import resolve_repo_path

        path = resolve_repo_path(path)
    if not path.exists():
        raise RuntimeError(
            f"Camera intrinsics file not found: {path}. "
            "Run ./scripts/run_calibrate_intrinsics.sh first."
        )
    with path.open("r", encoding="utf-8") as handle:
        import yaml

        data = yaml.safe_load(handle) or {}
    if "K" not in data or "dist_coeffs" not in data:
        raise ValueError(f"Invalid intrinsics file: {path}")
    return data


def _feature_vector(center_uv: tuple[float, float], bbox_area_ratio: float) -> np.ndarray:
    return np.array(
        [float(center_uv[0]), float(center_uv[1]), float(bbox_area_ratio) * 1000.0],
        dtype=np.float64,
    )
