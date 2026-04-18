from __future__ import annotations

import math
from typing import Iterable

import cv2
import numpy as np
from pyAgxArm.utiles.tf import T16_to_pose6, pose6_to_T16


def pose6_to_matrix(pose: Iterable[float]) -> np.ndarray:
    return np.array(pose6_to_T16(list(pose)), dtype=np.float64).reshape(4, 4)


def matrix_to_pose6(matrix: np.ndarray) -> list[float]:
    return list(T16_to_pose6(matrix.astype(np.float64).reshape(-1).tolist()))


def inverse_matrix(matrix: np.ndarray) -> np.ndarray:
    return np.linalg.inv(matrix.astype(np.float64))


def compose_matrix(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return left.astype(np.float64) @ right.astype(np.float64)


def rvec_tvec_to_matrix(rvec: np.ndarray, tvec: np.ndarray) -> np.ndarray:
    rotation, _ = cv2.Rodrigues(np.asarray(rvec, dtype=np.float64).reshape(3, 1))
    translation = np.asarray(tvec, dtype=np.float64).reshape(3)
    matrix = np.eye(4, dtype=np.float64)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = translation
    return matrix


def matrix_to_rvec_tvec(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rotation = np.asarray(matrix[:3, :3], dtype=np.float64)
    translation = np.asarray(matrix[:3, 3], dtype=np.float64).reshape(3, 1)
    rvec, _ = cv2.Rodrigues(rotation)
    return rvec.reshape(3, 1), translation


def matrix_to_yaml_dict(matrix: np.ndarray) -> dict[str, list]:
    matrix = np.asarray(matrix, dtype=np.float64)
    pose = matrix_to_pose6(matrix)
    return {
        "matrix": [[float(value) for value in row] for row in matrix.tolist()],
        "pose6": [float(value) for value in pose],
    }


def rotation_distance_deg(rotation_a: np.ndarray, rotation_b: np.ndarray) -> float:
    relative = rotation_a.T @ rotation_b
    trace_value = float(np.trace(relative))
    cos_theta = max(-1.0, min(1.0, (trace_value - 1.0) * 0.5))
    return math.degrees(math.acos(cos_theta))


def translation_rotation_delta(
    matrix_a: np.ndarray,
    matrix_b: np.ndarray,
) -> tuple[float, float]:
    translation_delta = float(np.linalg.norm(matrix_a[:3, 3] - matrix_b[:3, 3]))
    rotation_delta = rotation_distance_deg(matrix_a[:3, :3], matrix_b[:3, :3])
    return translation_delta, rotation_delta

