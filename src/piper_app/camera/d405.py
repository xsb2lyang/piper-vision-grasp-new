from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import numpy as np


def _import_rs():
    try:
        import pyrealsense2 as rs
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "pyrealsense2 is not installed. Recreate the workspace with "
            "`./scripts/setup_env.sh --recreate` to get the supported Python 3.10 environment."
        ) from exc
    return rs


@dataclass
class D405CameraConfig:
    serial: str = "auto"
    width: int = 640
    height: int = 480
    fps: int = 30
    depth_min_m: float = 0.05
    depth_max_m: float = 0.50


@dataclass
class D405FrameBundle:
    color_rgb: np.ndarray
    depth_m: np.ndarray
    depth_visual_rgb: np.ndarray
    width: int
    height: int
    serial: str


@dataclass
class D405PointQuery:
    valid: bool
    pixel: tuple[int, int]
    depth_m: Optional[float]
    point_m: Optional[tuple[float, float, float]]


class D405RealSenseCamera:
    def __init__(self, config: D405CameraConfig):
        self.config = config
        self._pipeline = None
        self._align = None
        self._serial: Optional[str] = None
        self._depth_scale: float = 0.001
        self._intrinsics: Any = None
        self._last_depth_m: Optional[np.ndarray] = None

    @property
    def serial(self) -> Optional[str]:
        return self._serial

    def open(self) -> str:
        rs = _import_rs()
        ctx = rs.context()
        device = self._select_device(ctx)
        if device is None:
            raise RuntimeError("No Intel RealSense D405 device detected.")

        serial = str(device.get_info(rs.camera_info.serial_number))
        config = rs.config()
        config.enable_device(serial)
        config.enable_stream(
            rs.stream.color,
            int(self.config.width),
            int(self.config.height),
            rs.format.rgb8,
            int(self.config.fps),
        )
        config.enable_stream(
            rs.stream.depth,
            int(self.config.width),
            int(self.config.height),
            rs.format.z16,
            int(self.config.fps),
        )

        pipeline = rs.pipeline()
        try:
            profile = pipeline.start(config)
        except Exception as exc:
            raise RuntimeError(
                "Failed to start the D405 stream via pyrealsense2. Verify librealsense installation, "
                "udev rules, camera permissions, and that no other process is holding the device."
            ) from exc
        depth_sensor = profile.get_device().first_depth_sensor()
        self._depth_scale = float(depth_sensor.get_depth_scale())
        self._pipeline = pipeline
        self._align = rs.align(rs.stream.color)
        self._serial = serial
        self._last_depth_m = None
        self._prime_stream()
        return serial

    def _select_device(self, ctx) -> Any:
        rs = _import_rs()
        requested_serial = str(self.config.serial).strip()
        candidates = []
        for device in ctx.query_devices():
            try:
                name = str(device.get_info(rs.camera_info.name))
            except RuntimeError:
                continue
            if "D405" not in name and "Depth Camera 405" not in name:
                continue
            serial = str(device.get_info(rs.camera_info.serial_number))
            candidates.append((serial, device))

        if not candidates:
            return None
        if requested_serial and requested_serial.lower() != "auto":
            for serial, device in candidates:
                if serial == requested_serial:
                    return device
            raise RuntimeError(f"Requested D405 serial {requested_serial} was not found.")
        return candidates[0][1]

    def _prime_stream(self) -> None:
        # Warm up a couple of frames so the first rendered image has valid data.
        for _ in range(3):
            bundle = self.read_frames()
            if bundle is not None:
                return

    def read_frames(self) -> Optional[D405FrameBundle]:
        if self._pipeline is None or self._align is None or self._serial is None:
            return None

        rs = _import_rs()
        frames = self._pipeline.wait_for_frames(timeout_ms=1000)
        aligned = self._align.process(frames)
        color_frame = aligned.get_color_frame()
        depth_frame = aligned.get_depth_frame()
        if not color_frame or not depth_frame:
            return None

        video_profile = color_frame.profile.as_video_stream_profile()
        self._intrinsics = video_profile.get_intrinsics()

        color_rgb = np.asanyarray(color_frame.get_data()).copy()
        depth_m = np.asanyarray(depth_frame.get_data()).astype(np.float32) * self._depth_scale
        self._last_depth_m = depth_m
        depth_visual_rgb = self._colorize_depth(depth_m)

        return D405FrameBundle(
            color_rgb=color_rgb,
            depth_m=depth_m,
            depth_visual_rgb=depth_visual_rgb,
            width=int(color_rgb.shape[1]),
            height=int(color_rgb.shape[0]),
            serial=self._serial,
        )

    def query_point(self, u: int, v: int) -> D405PointQuery:
        pixel = (int(u), int(v))
        if self._last_depth_m is None or self._intrinsics is None:
            return D405PointQuery(valid=False, pixel=pixel, depth_m=None, point_m=None)

        height, width = self._last_depth_m.shape
        if not (0 <= u < width and 0 <= v < height):
            return D405PointQuery(valid=False, pixel=pixel, depth_m=None, point_m=None)

        depth = float(self._last_depth_m[v, u])
        if not np.isfinite(depth) or depth <= 0.0:
            return D405PointQuery(valid=False, pixel=pixel, depth_m=None, point_m=None)

        rs = _import_rs()
        point = rs.rs2_deproject_pixel_to_point(
            self._intrinsics,
            [float(u), float(v)],
            depth,
        )
        return D405PointQuery(
            valid=True,
            pixel=pixel,
            depth_m=depth,
            point_m=(float(point[0]), float(point[1]), float(point[2])),
        )

    def close(self) -> None:
        pipeline = self._pipeline
        self._pipeline = None
        self._align = None
        self._serial = None
        self._intrinsics = None
        self._last_depth_m = None
        if pipeline is not None:
            pipeline.stop()

    def _colorize_depth(self, depth_m: np.ndarray) -> np.ndarray:
        minimum = float(self.config.depth_min_m)
        maximum = float(self.config.depth_max_m)
        maximum = max(maximum, minimum + 1e-6)

        valid = np.isfinite(depth_m) & (depth_m > 0.0)
        normalized = np.clip((depth_m - minimum) / (maximum - minimum), 0.0, 1.0)

        red = np.zeros_like(normalized, dtype=np.float32)
        green = np.zeros_like(normalized, dtype=np.float32)
        blue = np.zeros_like(normalized, dtype=np.float32)

        first = valid & (normalized < (1.0 / 3.0))
        second = valid & (normalized >= (1.0 / 3.0)) & (normalized < (2.0 / 3.0))
        third = valid & (normalized >= (2.0 / 3.0))

        t1 = normalized[first] * 3.0
        red[first] = 0.0
        green[first] = t1
        blue[first] = 1.0

        t2 = (normalized[second] - (1.0 / 3.0)) * 3.0
        red[second] = t2
        green[second] = 1.0
        blue[second] = 1.0 - t2

        t3 = (normalized[third] - (2.0 / 3.0)) * 3.0
        red[third] = 1.0
        green[third] = 1.0 - t3
        blue[third] = 0.0

        colored = np.stack((red, green, blue), axis=-1)
        colored = np.clip(colored * 255.0, 0.0, 255.0).astype(np.uint8)
        colored[~valid] = 0
        return colored
