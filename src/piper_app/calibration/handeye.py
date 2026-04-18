from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from piper_app.calibration.charuco import CharucoBoardConfig, CharucoDetection
from piper_app.calibration.session import write_yaml
from piper_app.calibration.transforms import (
    compose_matrix,
    matrix_to_yaml_dict,
    pose6_to_matrix,
    rotation_distance_deg,
    rvec_tvec_to_matrix,
    translation_rotation_delta,
)


_HAND_EYE_METHODS = {
    "Tsai": cv2.CALIB_HAND_EYE_TSAI,
    "Park": cv2.CALIB_HAND_EYE_PARK,
}


@dataclass
class HandEyeSample:
    index: int
    timestamp: str
    color_image_path: str
    depth_image_path: str
    summary_path: str
    T_base_tcp: np.ndarray
    T_camera_board: np.ndarray
    tcp_pose6: list[float]
    charuco_count: int
    distance_m: Optional[float]


@dataclass
class HandEyeMethodResult:
    method_name: str
    T_tcp_camera: np.ndarray
    translation_std_m: float
    rotation_mean_deg: float
    score_text: str


def build_handeye_quality_hint(
    detection: Optional[CharucoDetection],
    tcp_pose6: Optional[list[float]],
    samples: list[HandEyeSample],
    min_corners: int,
    near_z_m: float,
    far_z_m: float,
    min_translation_delta_m: float,
    min_rotation_delta_deg: float,
) -> str:
    if detection is None or not detection.success:
        return "Board not detected."
    if detection.charuco_count < int(min_corners):
        return f"Need at least {min_corners} corners, current {detection.charuco_count}."
    if not detection.pose_ok or detection.tvec is None:
        return "Board pose not solved yet."
    z_m = float(np.asarray(detection.tvec, dtype=np.float64).reshape(3)[2])
    if z_m < float(near_z_m):
        return "Board is too close to the camera."
    if z_m > float(far_z_m):
        return "Board is too far from the camera."
    if tcp_pose6 is None:
        return "Robot TCP pose unavailable."

    current_matrix = pose6_to_matrix(tcp_pose6)
    if samples:
        deltas = [translation_rotation_delta(sample.T_base_tcp, current_matrix) for sample in samples]
        min_translation = min(delta[0] for delta in deltas)
        min_rotation = min(delta[1] for delta in deltas)
        if min_translation < float(min_translation_delta_m) and min_rotation < float(min_rotation_delta_deg):
            return (
                "Current robot pose is too similar to an existing sample. "
                "Translate or rotate the wrist more before capturing."
            )
    return "Ready to capture."


def create_handeye_sample(
    index: int,
    color_image_path: str,
    depth_image_path: str,
    summary_path: str,
    tcp_pose6: list[float],
    detection: CharucoDetection,
) -> HandEyeSample:
    if not detection.pose_ok or detection.rvec is None or detection.tvec is None:
        raise ValueError("Detection pose is not available for hand-eye sampling.")
    return HandEyeSample(
        index=int(index),
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        color_image_path=str(color_image_path),
        depth_image_path=str(depth_image_path),
        summary_path=str(summary_path),
        T_base_tcp=pose6_to_matrix(tcp_pose6),
        T_camera_board=rvec_tvec_to_matrix(detection.rvec, detection.tvec),
        tcp_pose6=[float(value) for value in tcp_pose6],
        charuco_count=int(detection.charuco_count),
        distance_m=None if detection.distance_m is None else float(detection.distance_m),
    )


def calibrate_handeye_methods(
    samples: list[HandEyeSample],
    method_names: list[str],
) -> dict[str, HandEyeMethodResult]:
    if len(samples) < 3:
        raise ValueError("At least 3 samples are required for hand-eye calibration.")

    R_gripper2base = [sample.T_base_tcp[:3, :3].astype(np.float64) for sample in samples]
    t_gripper2base = [sample.T_base_tcp[:3, 3].astype(np.float64).reshape(3, 1) for sample in samples]
    R_target2cam = [sample.T_camera_board[:3, :3].astype(np.float64) for sample in samples]
    t_target2cam = [sample.T_camera_board[:3, 3].astype(np.float64).reshape(3, 1) for sample in samples]

    results: dict[str, HandEyeMethodResult] = {}
    for method_name in method_names:
        if method_name not in _HAND_EYE_METHODS:
            raise ValueError(f"Unsupported hand-eye method: {method_name}")
        rotation, translation = cv2.calibrateHandEye(
            R_gripper2base=R_gripper2base,
            t_gripper2base=t_gripper2base,
            R_target2cam=R_target2cam,
            t_target2cam=t_target2cam,
            method=_HAND_EYE_METHODS[method_name],
        )
        matrix = np.eye(4, dtype=np.float64)
        matrix[:3, :3] = np.asarray(rotation, dtype=np.float64)
        matrix[:3, 3] = np.asarray(translation, dtype=np.float64).reshape(3)
        translation_std_m, rotation_mean_deg = evaluate_board_consistency(samples, matrix)
        results[method_name] = HandEyeMethodResult(
            method_name=method_name,
            T_tcp_camera=matrix,
            translation_std_m=translation_std_m,
            rotation_mean_deg=rotation_mean_deg,
            score_text=f"translation_std={translation_std_m:.6f} m, rotation_mean={rotation_mean_deg:.4f} deg",
        )
    return results


def choose_best_handeye_result(results: dict[str, HandEyeMethodResult]) -> HandEyeMethodResult:
    if not results:
        raise ValueError("No hand-eye results are available.")
    return sorted(
        results.values(),
        key=lambda item: (item.translation_std_m, item.rotation_mean_deg, item.method_name),
    )[0]


def evaluate_board_consistency(
    samples: list[HandEyeSample],
    T_tcp_camera: np.ndarray,
) -> tuple[float, float]:
    base_board_matrices = [
        compose_matrix(compose_matrix(sample.T_base_tcp, T_tcp_camera), sample.T_camera_board)
        for sample in samples
    ]
    translations = np.array([matrix[:3, 3] for matrix in base_board_matrices], dtype=np.float64)
    translation_std_m = float(np.linalg.norm(np.std(translations, axis=0)))

    reference_rotation = base_board_matrices[0][:3, :3]
    angles = [
        rotation_distance_deg(reference_rotation, matrix[:3, :3])
        for matrix in base_board_matrices
    ]
    rotation_mean_deg = float(np.mean(angles))
    return translation_std_m, rotation_mean_deg


def save_handeye_yaml(
    output_path: str | Path,
    method_result: HandEyeMethodResult,
    board_config: CharucoBoardConfig,
    camera_serial: str,
    sample_count: int,
) -> Path:
    payload = {
        "kind": "handeye_tcp_camera",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "camera_serial": str(camera_serial),
        "reference_frame": "tcp",
        "method": method_result.method_name,
        "sample_count": int(sample_count),
        "board": board_config.to_dict(),
        "consistency": {
            "translation_std_m": float(method_result.translation_std_m),
            "rotation_mean_deg": float(method_result.rotation_mean_deg),
        },
        "T_tcp_camera": matrix_to_yaml_dict(method_result.T_tcp_camera),
    }
    return write_yaml(output_path, payload)


def save_handeye_sample_summary(
    output_path: str | Path,
    sample: HandEyeSample,
    camera_serial: str,
) -> Path:
    payload = {
        "timestamp": sample.timestamp,
        "camera_serial": str(camera_serial),
        "tcp_pose6": [float(value) for value in sample.tcp_pose6],
        "T_base_tcp": matrix_to_yaml_dict(sample.T_base_tcp),
        "T_camera_board": matrix_to_yaml_dict(sample.T_camera_board),
        "charuco_count": int(sample.charuco_count),
        "distance_m": None if sample.distance_m is None else float(sample.distance_m),
        "color_image_path": sample.color_image_path,
        "depth_image_path": sample.depth_image_path,
    }
    return write_yaml(output_path, payload)


def load_handeye_yaml(path_like: str | Path) -> dict[str, object]:
    path = Path(path_like)
    if not path.is_absolute():
        from piper_app.calibration.session import resolve_repo_path

        path = resolve_repo_path(path)
    if not path.exists():
        raise RuntimeError(
            f"Hand-eye file not found: {path}. Run ./scripts/run_calibrate_handeye.sh first."
        )
    with path.open("r", encoding="utf-8") as handle:
        import yaml

        data = yaml.safe_load(handle) or {}
    if "T_tcp_camera" not in data:
        raise ValueError(f"Invalid hand-eye file: {path}")
    return data


def extract_handeye_matrix(data: dict[str, object]) -> np.ndarray:
    block = data.get("T_tcp_camera")
    if not isinstance(block, dict) or "matrix" not in block:
        raise ValueError("Hand-eye YAML is missing T_tcp_camera.matrix.")
    return np.asarray(block["matrix"], dtype=np.float64)
