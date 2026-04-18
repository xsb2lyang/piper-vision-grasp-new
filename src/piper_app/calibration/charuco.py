from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import yaml

from piper_app.calibration.session import resolve_repo_path


_ARUCO_DICTIONARIES = {
    name: getattr(cv2.aruco, name)
    for name in dir(cv2.aruco)
    if name.startswith("DICT_")
}


@dataclass(frozen=True)
class CharucoBoardConfig:
    squares_x: int
    squares_y: int
    square_length_m: float
    marker_length_m: float
    dictionary: str
    config_path: Path

    def to_dict(self) -> dict[str, object]:
        return {
            "squares_x": int(self.squares_x),
            "squares_y": int(self.squares_y),
            "square_length_m": float(self.square_length_m),
            "marker_length_m": float(self.marker_length_m),
            "dictionary": str(self.dictionary),
            "config_path": str(self.config_path),
        }


@dataclass
class CharucoDetection:
    success: bool
    overlay_rgb: np.ndarray
    marker_count: int
    charuco_count: int
    charuco_corners: Optional[np.ndarray]
    charuco_ids: Optional[np.ndarray]
    rvec: Optional[np.ndarray]
    tvec: Optional[np.ndarray]
    bbox_area_ratio: float
    center_uv: Optional[tuple[float, float]]
    distance_m: Optional[float]
    message: str

    @property
    def pose_ok(self) -> bool:
        return self.rvec is not None and self.tvec is not None


def load_board_config(path_like: str | Path) -> CharucoBoardConfig:
    path = resolve_repo_path(path_like)
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    dictionary = str(data.get("dictionary", "")).strip()
    if dictionary not in _ARUCO_DICTIONARIES:
        raise ValueError(f"Unsupported ArUco dictionary: {dictionary}")
    return CharucoBoardConfig(
        squares_x=int(data["squares_x"]),
        squares_y=int(data["squares_y"]),
        square_length_m=float(data["square_length_m"]),
        marker_length_m=float(data["marker_length_m"]),
        dictionary=dictionary,
        config_path=path,
    )


def build_dictionary(board_config: CharucoBoardConfig):
    return cv2.aruco.getPredefinedDictionary(_ARUCO_DICTIONARIES[board_config.dictionary])


def build_board(board_config: CharucoBoardConfig):
    return cv2.aruco.CharucoBoard(
        (int(board_config.squares_x), int(board_config.squares_y)),
        float(board_config.square_length_m),
        float(board_config.marker_length_m),
        build_dictionary(board_config),
    )


class CharucoDetector:
    def __init__(
        self,
        board_config: CharucoBoardConfig,
        camera_matrix: Optional[np.ndarray] = None,
        dist_coeffs: Optional[np.ndarray] = None,
    ):
        self.board_config = board_config
        self.dictionary = build_dictionary(board_config)
        self.board = build_board(board_config)
        self.detector = cv2.aruco.ArucoDetector(self.dictionary)
        self.camera_matrix = None if camera_matrix is None else np.asarray(camera_matrix, dtype=np.float64)
        self.dist_coeffs = None if dist_coeffs is None else np.asarray(dist_coeffs, dtype=np.float64)

    def detect(self, color_rgb: np.ndarray) -> CharucoDetection:
        rgb = np.asarray(color_rgb, dtype=np.uint8)
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        marker_corners, marker_ids, _rejected = self.detector.detectMarkers(gray)

        overlay_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        marker_count = 0 if marker_ids is None else int(len(marker_ids))
        charuco_count = 0
        charuco_corners = None
        charuco_ids = None
        rvec = None
        tvec = None
        bbox_area_ratio = 0.0
        center_uv = None
        distance_m = None
        message = "Board not detected."

        if marker_ids is not None and len(marker_ids) > 0:
            cv2.aruco.drawDetectedMarkers(overlay_bgr, marker_corners, marker_ids)
            interpolate_ret, charuco_corners, charuco_ids = cv2.aruco.interpolateCornersCharuco(
                marker_corners,
                marker_ids,
                gray,
                self.board,
            )
            charuco_count = 0 if charuco_ids is None else int(len(charuco_ids))
            if interpolate_ret and charuco_ids is not None and len(charuco_ids) > 0:
                cv2.aruco.drawDetectedCornersCharuco(overlay_bgr, charuco_corners, charuco_ids)
                bbox_area_ratio, center_uv = _compute_bbox_ratio(charuco_corners, gray.shape)
                message = f"Detected {charuco_count} ChArUco corners."

                if self.camera_matrix is not None and self.dist_coeffs is not None and charuco_count >= 4:
                    pose_ok, rvec, tvec = cv2.aruco.estimatePoseCharucoBoard(
                        charuco_corners,
                        charuco_ids,
                        self.board,
                        self.camera_matrix,
                        self.dist_coeffs,
                        None,
                        None,
                    )
                    if pose_ok:
                        axis_length = max(0.015, self.board_config.square_length_m)
                        cv2.drawFrameAxes(
                            overlay_bgr,
                            self.camera_matrix,
                            self.dist_coeffs,
                            rvec,
                            tvec,
                            axis_length,
                        )
                        distance_m = float(np.asarray(tvec, dtype=np.float64).reshape(3)[2])
                        message = f"Pose solved from {charuco_count} corners."
                    else:
                        rvec = None
                        tvec = None

        overlay_rgb = cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)
        return CharucoDetection(
            success=charuco_count > 0,
            overlay_rgb=overlay_rgb,
            marker_count=marker_count,
            charuco_count=charuco_count,
            charuco_corners=charuco_corners,
            charuco_ids=charuco_ids,
            rvec=rvec,
            tvec=tvec,
            bbox_area_ratio=bbox_area_ratio,
            center_uv=center_uv,
            distance_m=distance_m,
            message=message,
        )


def _compute_bbox_ratio(
    corners: np.ndarray,
    image_shape: tuple[int, int],
) -> tuple[float, Optional[tuple[float, float]]]:
    if corners is None or len(corners) == 0:
        return 0.0, None
    points = np.asarray(corners, dtype=np.float32).reshape(-1, 2)
    x_min = float(np.min(points[:, 0]))
    x_max = float(np.max(points[:, 0]))
    y_min = float(np.min(points[:, 1]))
    y_max = float(np.max(points[:, 1]))
    image_height, image_width = image_shape[:2]
    area = max(0.0, x_max - x_min) * max(0.0, y_max - y_min)
    ratio = 0.0 if image_width <= 0 or image_height <= 0 else area / float(image_width * image_height)
    center = (
        0.0 if image_width <= 0 else ((x_min + x_max) * 0.5) / float(image_width),
        0.0 if image_height <= 0 else ((y_min + y_max) * 0.5) / float(image_height),
    )
    return float(ratio), center
