from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import numpy as np

from piper_app.config import repo_root


@dataclass
class YoloConfig:
    enabled: bool = False
    weights_path: str = "third_party/yolo/新松-检测/yolo11m.pt"
    imgsz: int = 640
    conf: float = 0.25
    iou: float = 0.45
    max_det: int = 50
    device: str = "auto"


@dataclass
class YoloDetection:
    label: str
    confidence: float
    bbox_xyxy: tuple[int, int, int, int]


@dataclass
class YoloPrediction:
    annotated_rgb: np.ndarray
    detections: list[YoloDetection]
    device_label: str


def _vendor_root() -> Path:
    return repo_root() / "third_party" / "yolo" / "新松-检测"


def _import_yolo_runtime():
    try:
        from ultralytics import YOLO

        return YOLO
    except ModuleNotFoundError as primary_exc:
        vendor_root = _vendor_root()
        if str(vendor_root) not in sys.path:
            sys.path.insert(0, str(vendor_root))
        try:
            from ultralytics import YOLO

            return YOLO
        except ModuleNotFoundError as fallback_exc:
            raise RuntimeError(
                "Ultralytics is not installed. Re-run `./scripts/setup_env.sh --recreate` "
                "to install the YOLO monitor dependencies."
            ) from fallback_exc


class YoloDetector:
    def __init__(self, config: YoloConfig):
        self.config = config
        self._model = None
        self._torch = None
        self._device_label = "uninitialized"

    @property
    def device_label(self) -> str:
        return self._device_label

    def open(self) -> None:
        if self._model is not None:
            return

        weights_path = Path(self.config.weights_path)
        if not weights_path.is_absolute():
            weights_path = repo_root() / weights_path
        weights_path = weights_path.resolve()
        if not weights_path.exists():
            raise RuntimeError(f"YOLO weights not found: {weights_path}")

        try:
            import torch
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Torch is not installed. Re-run `./scripts/setup_env.sh --recreate` "
                "to install the YOLO monitor dependencies."
            ) from exc

        YOLO = _import_yolo_runtime()
        self._torch = torch
        resolved_device = self._resolve_device()
        self._model = YOLO(str(weights_path))
        self._device_label = resolved_device

    def predict(self, image_rgb: np.ndarray) -> YoloPrediction:
        if self._model is None:
            self.open()

        image_bgr = image_rgb[:, :, ::-1]
        results = self._model.predict(
            image_bgr,
            imgsz=int(self.config.imgsz),
            conf=float(self.config.conf),
            iou=float(self.config.iou),
            max_det=int(self.config.max_det),
            device=self._device_label,
            verbose=False,
        )
        result = results[0]
        plotted_bgr = result.plot()
        annotated_rgb = plotted_bgr[:, :, ::-1].copy()

        detections: list[YoloDetection] = []
        boxes = result.boxes
        if boxes is not None and len(boxes) > 0:
            names = getattr(result, "names", {}) or {}
            xyxy_list = boxes.xyxy.detach().cpu().tolist()
            conf_list = boxes.conf.detach().cpu().tolist()
            cls_list = boxes.cls.detach().cpu().tolist()
            for xyxy, conf, cls_idx in zip(xyxy_list, conf_list, cls_list):
                cls_id = int(cls_idx)
                label = str(names.get(cls_id, cls_id))
                detections.append(
                    YoloDetection(
                        label=label,
                        confidence=float(conf),
                        bbox_xyxy=tuple(int(round(value)) for value in xyxy),
                    )
                )

        return YoloPrediction(
            annotated_rgb=annotated_rgb,
            detections=detections,
            device_label=self._device_label,
        )

    def close(self) -> None:
        self._model = None
        self._torch = None
        self._device_label = "uninitialized"

    def _resolve_device(self) -> str:
        requested = str(self.config.device).strip().lower()
        if requested and requested != "auto":
            return requested
        if self._torch is not None and self._torch.cuda.is_available():
            return "cuda:0"
        return "cpu"
