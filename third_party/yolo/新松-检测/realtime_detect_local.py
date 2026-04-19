#!/usr/bin/env python3
"""
本地实时检测脚本

用途：
1. 仅做本机实时检测，不依赖 cloud / arm 通信。
2. 默认支持 Intel RealSense D435，也支持普通摄像头索引或视频文件。
3. 默认使用仓库内置的 yolo11n.pt 做最小可运行验证。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    import pyrealsense2 as rs
except ImportError:  # pragma: no cover - depends on local hardware stack
    rs = None

from ultralytics import YOLO


DEFAULT_MODEL = SCRIPT_DIR / "yolo11n.pt"


class RealSenseColorStream:
    """使用 RealSense 彩色流作为检测输入。"""

    def __init__(self, width: int, height: int, fps: int):
        if rs is None:
            raise RuntimeError("当前环境未安装 pyrealsense2，无法使用 RealSense 作为视频源")
        self.width = width
        self.height = height
        self.fps = fps
        self.pipeline = rs.pipeline()
        self.config = rs.config()
        self.started = False

    def open(self) -> None:
        self.config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, self.fps)
        self.pipeline.start(self.config)
        self.started = True

    def read(self) -> Tuple[bool, Optional[object]]:
        frames = self.pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            return False, None
        image = np.asanyarray(color_frame.get_data())
        return True, image

    def release(self) -> None:
        if self.started:
            self.pipeline.stop()
            self.started = False


class OpenCVStream:
    """使用 OpenCV VideoCapture 打开普通摄像头、视频文件或 rtsp。"""

    def __init__(self, source: str):
        self.source = int(source) if source.isdigit() else source
        self.cap = cv2.VideoCapture(self.source)

    def open(self) -> None:
        if not self.cap.isOpened():
            raise RuntimeError(f"无法打开视频源: {self.source}")

    def read(self) -> Tuple[bool, Optional[object]]:
        return self.cap.read()

    def release(self) -> None:
        self.cap.release()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="本地实时 YOLO 检测")
    parser.add_argument(
        "--source",
        default="realsense",
        help="视频源。默认 realsense；也可传 0/1 这类摄像头索引，或视频文件路径。",
    )
    parser.add_argument(
        "--weights",
        default=str(DEFAULT_MODEL),
        help="模型权重路径。默认使用仓库自带 yolo11n.pt",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="推理输入尺寸")
    parser.add_argument("--conf", type=float, default=0.25, help="置信度阈值")
    parser.add_argument(
        "--device",
        default="cpu",
        help="推理设备。当前机器建议先用 cpu；若后续 CUDA 驱动正常可改为 0 或 cuda:0",
    )
    parser.add_argument("--width", type=int, default=1280, help="RealSense 彩色流宽度")
    parser.add_argument("--height", type=int, default=720, help="RealSense 彩色流高度")
    parser.add_argument("--fps", type=int, default=30, help="RealSense 彩色流帧率")
    parser.add_argument(
        "--classes",
        nargs="*",
        type=int,
        default=None,
        help="可选：仅保留指定类别 id，例如 --classes 0 2 5",
    )
    parser.add_argument("--headless", action="store_true", help="无窗口运行，适合 smoke test")
    parser.add_argument("--max-frames", type=int, default=0, help="处理多少帧后自动退出，0 表示不限")
    parser.add_argument(
        "--save-dir",
        default="",
        help="可选：保存标注后的帧到该目录。适合 headless 调试。",
    )
    return parser


def create_stream(args: argparse.Namespace):
    if args.source.lower() == "realsense":
        stream = RealSenseColorStream(width=args.width, height=args.height, fps=args.fps)
        source_label = f"realsense:{args.width}x{args.height}@{args.fps}"
    else:
        stream = OpenCVStream(args.source)
        source_label = str(args.source)
    stream.open()
    return stream, source_label


def overlay_runtime_info(frame, fps: float, device: str, source_label: str):
    cv2.putText(frame, f"FPS: {fps:.1f}", (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.putText(frame, f"Device: {device}", (16, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(frame, f"Source: {source_label}", (16, 88), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    return frame


def main() -> int:
    args = build_parser().parse_args()

    model_path = Path(args.weights).expanduser().resolve()
    if not model_path.exists():
        raise FileNotFoundError(f"模型权重不存在: {model_path}")

    save_dir = Path(args.save_dir).expanduser().resolve() if args.save_dir else None
    if save_dir is not None:
        save_dir.mkdir(parents=True, exist_ok=True)

    print(f"加载模型: {model_path}")
    model = YOLO(str(model_path))

    stream, source_label = create_stream(args)
    print(f"视频源已打开: {source_label}")
    print("按 q 或 ESC 退出")

    frame_count = 0
    last_time = time.time()
    fps = 0.0

    try:
        while True:
            ok, frame = stream.read()
            if not ok or frame is None:
                print("读取视频帧失败，退出")
                break

            results = model.predict(
                frame,
                imgsz=args.imgsz,
                conf=args.conf,
                classes=args.classes,
                device=args.device,
                verbose=False,
            )
            annotated = results[0].plot()

            now = time.time()
            dt = now - last_time
            if dt > 0:
                fps = 1.0 / dt
            last_time = now
            overlay_runtime_info(annotated, fps=fps, device=args.device, source_label=source_label)

            if save_dir is not None:
                out_path = save_dir / f"frame_{frame_count:04d}.jpg"
                cv2.imwrite(str(out_path), annotated)

            if not args.headless:
                cv2.imshow("YOLO Local Realtime Detect", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):
                    break

            frame_count += 1
            if args.max_frames > 0 and frame_count >= args.max_frames:
                break

        print(f"处理完成，总帧数: {frame_count}")
        return 0
    finally:
        stream.release()
        if not args.headless:
            try:
                cv2.destroyAllWindows()
            except cv2.error:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
