from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import ttk
from typing import Optional

from piper_app.calibration.charuco import CharucoDetection, CharucoDetector, load_board_config
from piper_app.calibration.intrinsics import (
    IntrinsicCalibrationResult,
    IntrinsicSample,
    build_intrinsics_quality_hint,
    calibrate_intrinsics,
    create_intrinsic_sample,
    save_intrinsics_yaml,
)
from piper_app.calibration.session import create_session_dir, display_repo_path, save_color_png, write_yaml
from piper_app.calibration.viewer_base import CalibrationViewerBase
from piper_app.config import repo_root


class IntrinsicsCalibrationGuiApp(CalibrationViewerBase):
    def __init__(self, root: tk.Tk, args: argparse.Namespace):
        self.board_config = load_board_config(args.board_config)
        self.detector = CharucoDetector(self.board_config)
        self.current_detection: Optional[CharucoDetection] = None
        self.current_overlay_rgb = None
        self.samples: list[IntrinsicSample] = []
        self.session_dir = create_session_dir(args.session_base_dir, "intrinsics")
        self.last_result: Optional[IntrinsicCalibrationResult] = None

        self.board_status_var = tk.StringVar(value="Waiting for camera...")
        self.capture_hint_var = tk.StringVar(value="Move the board into view.")
        self.sample_count_var = tk.StringVar(value="0")
        self.session_var = tk.StringVar(value=display_repo_path(self.session_dir))
        self.result_var = tk.StringVar(value="No calibration result yet.")
        self.quality_summary_var = tk.StringVar(value="No samples yet.")

        super().__init__(
            root,
            args,
            title="Piper Camera Intrinsics Calibration",
            use_robot=False,
            show_depth=False,
            note_text=(
                "This window only reads the D405 stream. Capture multiple ChArUco views with different angles "
                "and distances, then press Calibrate to write configs/calibration/camera_intrinsics.yaml."
            ),
            geometry="1540x920",
        )

    def build_left_panel(self, parent: ttk.Frame) -> None:
        panel = ttk.LabelFrame(parent, text="Intrinsics Session", padding=10)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.columnconfigure(1, weight=1)

        rows = [
            ("Board Config", tk.StringVar(value=display_repo_path(self.board_config.config_path))),
            ("Session", self.session_var),
            ("Detection", self.board_status_var),
            ("Capture Hint", self.capture_hint_var),
            ("Sample Count", self.sample_count_var),
            ("Coverage", self.quality_summary_var),
            ("Last Event", self.last_event_var),
            ("Result", self.result_var),
        ]
        for row_idx, (label, variable) in enumerate(rows):
            ttk.Label(panel, text=label).grid(row=row_idx, column=0, sticky="nw", pady=3)
            ttk.Label(panel, textvariable=variable, wraplength=420, justify="left").grid(
                row=row_idx, column=1, sticky="w", pady=3
            )

        controls = ttk.LabelFrame(parent, text="Controls", padding=10)
        controls.grid(row=1, column=0, sticky="ew", pady=(10, 10))
        ttk.Button(controls, text="Capture (S)", command=lambda: self.run_action(self.capture_sample)).grid(
            row=0, column=0, padx=(0, 6), pady=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Delete Last (D)", command=lambda: self.run_action(self.delete_last_sample)).grid(
            row=0, column=1, padx=(0, 6), pady=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Calibrate (C)", command=lambda: self.run_action(self.run_calibration)).grid(
            row=1, column=0, padx=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Reset (R)", command=lambda: self.run_action(self.reset_session)).grid(
            row=1, column=1, padx=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Quit (Q)", command=self.on_close).grid(row=2, column=0, columnspan=2, sticky="ew")

        visuals = ttk.LabelFrame(parent, text="Sample Quality", padding=10)
        visuals.grid(row=2, column=0, sticky="nsew")
        visuals.columnconfigure(0, weight=1)
        ttk.Label(visuals, text="Image Coverage").grid(row=0, column=0, sticky="w")
        self.coverage_canvas = tk.Canvas(
            visuals,
            width=260,
            height=200,
            bg="#0f172a",
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.coverage_canvas.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        ttk.Label(visuals, text="Board Scale Distribution").grid(row=2, column=0, sticky="w")
        self.scale_canvas = tk.Canvas(
            visuals,
            width=260,
            height=80,
            bg="#0f172a",
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.scale_canvas.grid(row=3, column=0, sticky="ew", pady=(4, 0))

    def on_camera_bundle(self, bundle) -> None:
        detection = self.detector.detect(bundle.color_rgb)
        self.current_detection = detection
        self.current_overlay_rgb = detection.overlay_rgb
        self.board_status_var.set(
            f"{detection.message} markers={detection.marker_count} corners={detection.charuco_count} "
            f"bbox_ratio={detection.bbox_area_ratio:.3f}"
        )
        hint = build_intrinsics_quality_hint(
            detection,
            self.samples,
            min_corners=int(self.args.intrinsics_min_corners),
            near_area_ratio=float(self.args.intrinsics_near_area_ratio),
            far_area_ratio=float(self.args.intrinsics_far_area_ratio),
            duplicate_threshold=float(self.args.intrinsics_duplicate_threshold),
        )
        self.capture_hint_var.set(hint)

    def get_display_images(self, bundle):
        return self.current_overlay_rgb if self.current_overlay_rgb is not None else bundle.color_rgb, None

    def capture_sample(self) -> None:
        if self._camera_bundle is None or self.current_detection is None:
            raise RuntimeError("No live camera frame is available.")
        if "Ready to capture." not in self.capture_hint_var.get():
            raise RuntimeError(self.capture_hint_var.get())
        sample_index = len(self.samples) + 1
        image_name = f"sample_{sample_index:03d}_color.png"
        summary_name = f"sample_{sample_index:03d}.yaml"
        image_path = self.session_dir / image_name
        summary_path = self.session_dir / summary_name
        save_color_png(image_path, self._camera_bundle.color_rgb)
        sample = create_intrinsic_sample(
            index=sample_index,
            image_path=str(image_path.relative_to(repo_root())),
            detection=self.current_detection,
        )
        self.samples.append(sample)
        write_yaml(
            summary_path,
            {
                "index": sample.index,
                "timestamp": sample.timestamp,
                "image_path": sample.image_path,
                "charuco_count": sample.charuco_count,
                "center_uv": [float(sample.center_uv[0]), float(sample.center_uv[1])],
                "bbox_area_ratio": float(sample.bbox_area_ratio),
            },
        )
        self._last_event_text = f"Captured intrinsic sample {sample_index}."

    def delete_last_sample(self) -> None:
        if not self.samples:
            self._last_event_text = "No sample to delete."
            return
        removed = self.samples.pop()
        self._last_event_text = f"Removed intrinsic sample {removed.index}."

    def reset_session(self) -> None:
        self.samples.clear()
        self.last_result = None
        self.session_dir = create_session_dir(self.args.session_base_dir, "intrinsics")
        self.session_var.set(display_repo_path(self.session_dir))
        self.result_var.set("No calibration result yet.")
        self._last_event_text = "Started a new intrinsics session."

    def run_calibration(self) -> None:
        min_samples = int(self.args.intrinsics_min_samples)
        if len(self.samples) < min_samples:
            raise RuntimeError(f"Need at least {min_samples} samples, current {len(self.samples)}.")
        if self._camera_bundle is None:
            raise RuntimeError("No camera frame available for image size.")
        result = calibrate_intrinsics(
            self.samples,
            self.board_config,
            (self._camera_bundle.width, self._camera_bundle.height),
        )
        output_path = save_intrinsics_yaml(
            self.args.intrinsics_output_path,
            result,
            self.board_config,
            self._camera_bundle.serial,
        )
        self.last_result = result
        self.result_var.set(
            f"Saved to {display_repo_path(output_path)}: rms={result.rms:.5f}, "
            f"samples={result.sample_count}, fx={result.camera_matrix[0,0]:.2f}, fy={result.camera_matrix[1,1]:.2f}"
        )
        self._last_event_text = f"Camera intrinsics written to {display_repo_path(output_path)}."

    def refresh_custom_ui(self) -> None:
        self.sample_count_var.set(str(len(self.samples)))
        self._refresh_quality_visuals()

    def handle_key_action(self, key: str) -> None:
        actions = {
            "s": self.capture_sample,
            "d": self.delete_last_sample,
            "c": self.run_calibration,
            "r": self.reset_session,
        }
        if key == "q":
            self.on_close()
            return
        if key in actions:
            self.run_action(actions[key])

    def _refresh_quality_visuals(self) -> None:
        sample_count = len(self.samples)
        if sample_count == 0:
            self.quality_summary_var.set("No samples yet.")
        else:
            xs = [sample.center_uv[0] for sample in self.samples]
            ys = [sample.center_uv[1] for sample in self.samples]
            areas = [sample.bbox_area_ratio for sample in self.samples]
            self.quality_summary_var.set(
                f"x=[{min(xs):.2f},{max(xs):.2f}] y=[{min(ys):.2f},{max(ys):.2f}] "
                f"area=[{min(areas):.3f},{max(areas):.3f}]"
            )
        self._draw_coverage_canvas()
        self._draw_scale_canvas()

    def _draw_coverage_canvas(self) -> None:
        canvas = self.coverage_canvas
        canvas.delete("all")
        width = int(canvas["width"])
        height = int(canvas["height"])
        margin = 16
        canvas.create_rectangle(margin, margin, width - margin, height - margin, outline="#475569")
        canvas.create_text(width / 2, 10, text="normalized image plane", fill="#cbd5e1")
        for sample in self.samples:
            x = margin + sample.center_uv[0] * (width - 2 * margin)
            y = margin + sample.center_uv[1] * (height - 2 * margin)
            radius = max(4, min(14, int(6 + sample.bbox_area_ratio * 20)))
            canvas.create_oval(x - radius, y - radius, x + radius, y + radius, outline="#38bdf8", width=2)
        if self.current_detection is not None and self.current_detection.center_uv is not None:
            cx = margin + self.current_detection.center_uv[0] * (width - 2 * margin)
            cy = margin + self.current_detection.center_uv[1] * (height - 2 * margin)
            canvas.create_line(cx - 10, cy, cx + 10, cy, fill="#f59e0b", width=2)
            canvas.create_line(cx, cy - 10, cx, cy + 10, fill="#f59e0b", width=2)
        if not self.samples:
            canvas.create_text(width / 2, height / 2, text="capture samples to build coverage", fill="#94a3b8")

    def _draw_scale_canvas(self) -> None:
        canvas = self.scale_canvas
        canvas.delete("all")
        width = int(canvas["width"])
        height = int(canvas["height"])
        margin = 16
        canvas.create_rectangle(margin, margin, width - margin, height - margin, outline="#475569")
        if not self.samples:
            canvas.create_text(width / 2, height / 2, text="no scale samples yet", fill="#94a3b8")
            return
        for idx, sample in enumerate(self.samples):
            x = margin + (idx + 0.5) * (width - 2 * margin) / max(1, len(self.samples))
            usable_height = height - 2 * margin
            y = height - margin - sample.bbox_area_ratio * usable_height / max(0.01, float(self.args.intrinsics_near_area_ratio))
            y = max(margin, min(height - margin, y))
            canvas.create_line(x, height - margin, x, y, fill="#38bdf8", width=3)
        far_y = height - margin - float(self.args.intrinsics_far_area_ratio) * (height - 2 * margin) / max(
            0.01, float(self.args.intrinsics_near_area_ratio)
        )
        near_y = height - margin - float(self.args.intrinsics_near_area_ratio) * (height - 2 * margin) / max(
            0.01, float(self.args.intrinsics_near_area_ratio)
        )
        canvas.create_line(margin, far_y, width - margin, far_y, fill="#f59e0b", dash=(4, 3))
        canvas.create_line(margin, near_y, width - margin, near_y, fill="#ef4444", dash=(4, 3))
        canvas.create_text(width - margin, far_y - 8, text="far threshold", fill="#f59e0b", anchor="ne")
        canvas.create_text(width - margin, max(margin + 10, near_y - 8), text="near threshold", fill="#ef4444", anchor="ne")


def run(args: argparse.Namespace) -> None:
    root = tk.Tk()
    app = IntrinsicsCalibrationGuiApp(root, args)
    app.start()
    root.mainloop()
