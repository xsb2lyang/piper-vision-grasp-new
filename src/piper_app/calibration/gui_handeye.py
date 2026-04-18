from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import ttk
from typing import Optional

import numpy as np

from piper_app.calibration.charuco import CharucoDetection, CharucoDetector, load_board_config
from piper_app.calibration.handeye import (
    HandEyeMethodResult,
    HandEyeSample,
    build_handeye_quality_hint,
    calibrate_handeye_methods,
    choose_best_handeye_result,
    create_handeye_sample,
    save_handeye_sample_summary,
    save_handeye_yaml,
)
from piper_app.calibration.intrinsics import load_intrinsics_yaml
from piper_app.calibration.session import (
    create_session_dir,
    display_repo_path,
    save_color_png,
    save_depth_png,
    resolve_repo_path,
    write_yaml,
)
from piper_app.calibration.transforms import translation_rotation_delta
from piper_app.calibration.viewer_base import CalibrationViewerBase
from piper_app.config import repo_root


class HandEyeCalibrationGuiApp(CalibrationViewerBase):
    def __init__(self, root: tk.Tk, args: argparse.Namespace):
        self.board_config = load_board_config(args.board_config)
        self.intrinsics_data = load_intrinsics_yaml(args.intrinsics_path)
        self.detector = CharucoDetector(
            self.board_config,
            camera_matrix=np.asarray(self.intrinsics_data["K"], dtype=np.float64),
            dist_coeffs=np.asarray(self.intrinsics_data["dist_coeffs"], dtype=np.float64),
        )
        self.current_detection: Optional[CharucoDetection] = None
        self.current_overlay_rgb = None
        self.samples: list[HandEyeSample] = []
        self.session_dir = create_session_dir(args.session_base_dir, "handeye")
        self.last_results: dict[str, HandEyeMethodResult] = {}

        self.board_status_var = tk.StringVar(value="Waiting for camera...")
        self.capture_hint_var = tk.StringVar(value="Move the board into view.")
        self.sample_count_var = tk.StringVar(value="0")
        self.session_var = tk.StringVar(value=display_repo_path(self.session_dir))
        self.intrinsics_var = tk.StringVar(value=display_repo_path(resolve_repo_path(args.intrinsics_path)))
        self.result_var = tk.StringVar(value="No calibration result yet.")
        self.diversity_var = tk.StringVar(value="No samples yet.")
        self.consistency_var = tk.StringVar(value="No method scores yet.")
        self.capture_ready_var = tk.StringVar(value="Not recommended")

        super().__init__(
            root,
            args,
            title="Piper Hand-Eye Calibration",
            use_robot=True,
            show_depth=True,
            note_text=(
                "This window is read-only with respect to robot motion. Manually move the eye-in-hand camera to "
                "diverse viewpoints, capture samples, then compute Tsai and Park hand-eye solutions."
            ),
        )

    def build_left_panel(self, parent: ttk.Frame) -> None:
        self.build_robot_connection_panel(parent, row=0, mode_label="Mode: read-only")
        self.build_robot_status_panel(
            parent,
            row=1,
            extra_rows=[
                ("Board", self.board_status_var),
                ("Capture Hint", self.capture_hint_var),
                ("Capture Light", self.capture_ready_var),
                ("Sample Count", self.sample_count_var),
                ("Intrinsics", self.intrinsics_var),
                ("Session", self.session_var),
                ("Diversity", self.diversity_var),
                ("Scores", self.consistency_var),
                ("Result", self.result_var),
            ],
            title="Hand-Eye Status",
        )
        light_panel = ttk.Frame(parent)
        light_panel.grid(row=2, column=0, sticky="w", pady=(0, 10))
        self.capture_light_canvas = tk.Canvas(
            light_panel,
            width=18,
            height=18,
            bg=self.root.cget("bg"),
            highlightthickness=0,
            bd=0,
        )
        self.capture_light_canvas.grid(row=0, column=0, padx=(0, 8))
        ttk.Label(light_panel, text="Green: recommend capture. Red: do not capture.").grid(
            row=0, column=1, sticky="w"
        )
        self.build_pose_panel(parent, row=3, title="Current TCP Pose")
        self.build_joint_panel(parent, row=4, title="Current Joint Angles")

        controls = ttk.LabelFrame(parent, text="Controls", padding=10)
        controls.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(controls, text="Capture (S)", command=lambda: self.run_action(self.capture_sample)).grid(
            row=0, column=0, padx=(0, 6), pady=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Delete Last (D)", command=lambda: self.run_action(self.delete_last_sample)).grid(
            row=0, column=1, padx=(0, 6), pady=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Calibrate (C)", command=lambda: self.run_action(self.run_calibration)).grid(
            row=1, column=0, padx=(0, 6), pady=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="View Quality (V)", command=lambda: self.run_action(self.update_diversity_summary)).grid(
            row=1, column=1, padx=(0, 6), pady=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Reset (R)", command=lambda: self.run_action(self.reset_session)).grid(
            row=2, column=0, padx=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Quit (Q)", command=self.on_close).grid(row=2, column=1, sticky="ew")

        visuals = ttk.LabelFrame(parent, text="Sample Quality", padding=10)
        visuals.grid(row=6, column=0, sticky="nsew")
        visuals.columnconfigure(0, weight=1)
        ttk.Label(visuals, text="TCP XY Spread").grid(row=0, column=0, sticky="w")
        self.tcp_xy_canvas = tk.Canvas(
            visuals,
            width=260,
            height=180,
            bg="#0f172a",
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.tcp_xy_canvas.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        ttk.Label(visuals, text="Board Distance Samples").grid(row=2, column=0, sticky="w")
        self.distance_canvas = tk.Canvas(
            visuals,
            width=260,
            height=80,
            bg="#0f172a",
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.distance_canvas.grid(row=3, column=0, sticky="ew")

    def on_robot_polled(self) -> None:
        self.capture_hint_var.set(
            build_handeye_quality_hint(
                self.current_detection,
                self._measured_tcp_pose,
                self.samples,
                min_corners=int(self.args.handeye_min_corners),
                near_z_m=float(self.args.handeye_near_z_m),
                far_z_m=float(self.args.handeye_far_z_m),
                min_translation_delta_m=float(self.args.handeye_min_translation_delta_m),
                min_rotation_delta_deg=float(self.args.handeye_min_rotation_delta_deg),
            )
        )

    def on_camera_bundle(self, bundle) -> None:
        detection = self.detector.detect(bundle.color_rgb)
        self.current_detection = detection
        self.current_overlay_rgb = detection.overlay_rgb
        distance_text = "--" if detection.distance_m is None else f"{detection.distance_m:.4f} m"
        self.board_status_var.set(
            f"{detection.message} markers={detection.marker_count} corners={detection.charuco_count} z={distance_text}"
        )
        self.capture_hint_var.set(
            build_handeye_quality_hint(
                detection,
                self._measured_tcp_pose,
                self.samples,
                min_corners=int(self.args.handeye_min_corners),
                near_z_m=float(self.args.handeye_near_z_m),
                far_z_m=float(self.args.handeye_far_z_m),
                min_translation_delta_m=float(self.args.handeye_min_translation_delta_m),
                min_rotation_delta_deg=float(self.args.handeye_min_rotation_delta_deg),
            )
        )

    def get_display_images(self, bundle):
        return self.current_overlay_rgb if self.current_overlay_rgb is not None else bundle.color_rgb, bundle.depth_visual_rgb

    def capture_sample(self) -> None:
        if self._camera_bundle is None or self.current_detection is None:
            raise RuntimeError("No live camera frame is available.")
        if self._measured_tcp_pose is None:
            raise RuntimeError("Robot TCP pose is unavailable.")
        if "Ready to capture." not in self.capture_hint_var.get():
            raise RuntimeError(self.capture_hint_var.get())

        sample_index = len(self.samples) + 1
        color_path = self.session_dir / f"sample_{sample_index:03d}_color.png"
        depth_path = self.session_dir / f"sample_{sample_index:03d}_depth.png"
        summary_path = self.session_dir / f"sample_{sample_index:03d}.yaml"
        save_color_png(color_path, self._camera_bundle.color_rgb)
        save_depth_png(depth_path, self._camera_bundle.depth_m)
        sample = create_handeye_sample(
            index=sample_index,
            color_image_path=str(color_path.relative_to(repo_root())),
            depth_image_path=str(depth_path.relative_to(repo_root())),
            summary_path=str(summary_path.relative_to(repo_root())),
            tcp_pose6=self._measured_tcp_pose,
            detection=self.current_detection,
        )
        self.samples.append(sample)
        save_handeye_sample_summary(summary_path, sample, self._camera_bundle.serial)
        self._last_event_text = f"Captured hand-eye sample {sample_index}."
        self.update_diversity_summary()

    def delete_last_sample(self) -> None:
        if not self.samples:
            self._last_event_text = "No sample to delete."
            return
        removed = self.samples.pop()
        self._last_event_text = f"Removed hand-eye sample {removed.index}."
        self.update_diversity_summary()

    def reset_session(self) -> None:
        self.samples.clear()
        self.last_results = {}
        self.session_dir = create_session_dir(self.args.session_base_dir, "handeye")
        self.session_var.set(display_repo_path(self.session_dir))
        self.result_var.set("No calibration result yet.")
        self.diversity_var.set("No samples yet.")
        self._last_event_text = "Started a new hand-eye session."

    def update_diversity_summary(self) -> None:
        if len(self.samples) < 2:
            self.diversity_var.set("Need at least 2 samples to summarize diversity.")
            return
        deltas = []
        for idx, left in enumerate(self.samples):
            for right in self.samples[idx + 1 :]:
                deltas.append(translation_rotation_delta(left.T_base_tcp, right.T_base_tcp))
        min_translation = min(delta[0] for delta in deltas)
        max_translation = max(delta[0] for delta in deltas)
        min_rotation = min(delta[1] for delta in deltas)
        max_rotation = max(delta[1] for delta in deltas)
        self.diversity_var.set(
            f"translation delta range={min_translation:.4f}-{max_translation:.4f} m, "
            f"rotation delta range={min_rotation:.2f}-{max_rotation:.2f} deg"
        )

    def run_calibration(self) -> None:
        min_samples = int(self.args.handeye_min_samples)
        if len(self.samples) < min_samples:
            raise RuntimeError(f"Need at least {min_samples} samples, current {len(self.samples)}.")
        methods = [name.strip() for name in self.args.handeye_methods.split(",") if name.strip()]
        results = calibrate_handeye_methods(self.samples, methods)
        best = choose_best_handeye_result(results)
        self.last_results = results

        if self._camera_bundle is None:
            raise RuntimeError("No camera bundle is available for result metadata.")
        if "Tsai" in results:
            save_handeye_yaml(
                self.args.handeye_tsai_output_path,
                results["Tsai"],
                self.board_config,
                self._camera_bundle.serial,
                len(self.samples),
            )
        if "Park" in results:
            save_handeye_yaml(
                self.args.handeye_park_output_path,
                results["Park"],
                self.board_config,
                self._camera_bundle.serial,
                len(self.samples),
            )
        active_path = save_handeye_yaml(
            self.args.handeye_active_output_path,
            best,
            self.board_config,
            self._camera_bundle.serial,
            len(self.samples),
        )
        write_yaml(
            self.session_dir / "session_summary.yaml",
            {
                "sample_count": len(self.samples),
                "methods": {
                    name: {
                        "translation_std_m": float(item.translation_std_m),
                        "rotation_mean_deg": float(item.rotation_mean_deg),
                    }
                    for name, item in results.items()
                },
                "selected_method": best.method_name,
                "active_output_path": display_repo_path(active_path),
            },
        )
        self.result_var.set(
            f"Best={best.method_name} ({best.score_text}). Saved active result to {display_repo_path(active_path)}."
        )
        self._last_event_text = "Hand-eye calibration completed."

    def refresh_custom_ui(self) -> None:
        self.sample_count_var.set(str(len(self.samples)))
        self._refresh_capture_light()
        self._refresh_quality_visuals()

    def handle_key_action(self, key: str) -> None:
        actions = {
            "s": self.capture_sample,
            "d": self.delete_last_sample,
            "c": self.run_calibration,
            "v": self.update_diversity_summary,
            "r": self.reset_session,
        }
        if key == "q":
            self.on_close()
            return
        if key in actions:
            self.run_action(actions[key])

    def _refresh_quality_visuals(self) -> None:
        if self.last_results:
            lines = [f"{name}: {item.score_text}" for name, item in sorted(self.last_results.items())]
            self.consistency_var.set(" | ".join(lines))
        else:
            self.consistency_var.set("No method scores yet.")
        self._draw_tcp_xy_canvas()
        self._draw_distance_canvas()

    def _refresh_capture_light(self) -> None:
        ready = self.capture_hint_var.get().strip() == "Ready to capture."
        fill = "#22c55e" if ready else "#ef4444"
        outline = "#166534" if ready else "#7f1d1d"
        self.capture_ready_var.set("Recommended" if ready else "Not recommended")
        self.capture_light_canvas.delete("all")
        self.capture_light_canvas.create_oval(2, 2, 16, 16, fill=fill, outline=outline, width=2)

    def _draw_tcp_xy_canvas(self) -> None:
        canvas = self.tcp_xy_canvas
        canvas.delete("all")
        width = int(canvas["width"])
        height = int(canvas["height"])
        margin = 16
        canvas.create_rectangle(margin, margin, width - margin, height - margin, outline="#475569")

        positions = [sample.T_base_tcp[:2, 3] for sample in self.samples]
        if self._measured_tcp_pose is not None:
            positions.append(np.asarray(self._measured_tcp_pose[:2], dtype=np.float64))
        if not positions:
            canvas.create_text(width / 2, height / 2, text="capture samples to visualize spread", fill="#94a3b8")
            return

        points = np.asarray(positions, dtype=np.float64)
        mins = points.min(axis=0)
        maxs = points.max(axis=0)
        spans = np.maximum(maxs - mins, 1e-6)

        def project(point_xy):
            px = margin + ((point_xy[0] - mins[0]) / spans[0]) * (width - 2 * margin)
            py = height - margin - ((point_xy[1] - mins[1]) / spans[1]) * (height - 2 * margin)
            return float(px), float(py)

        for sample in self.samples:
            x, y = project(sample.T_base_tcp[:2, 3])
            canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#38bdf8", outline="")
        if self._measured_tcp_pose is not None:
            x, y = project(np.asarray(self._measured_tcp_pose[:2], dtype=np.float64))
            canvas.create_line(x - 10, y, x + 10, y, fill="#f59e0b", width=2)
            canvas.create_line(x, y - 10, x, y + 10, fill="#f59e0b", width=2)
        canvas.create_text(margin, 8, text="x-y in base frame", fill="#cbd5e1", anchor="nw")

    def _draw_distance_canvas(self) -> None:
        canvas = self.distance_canvas
        canvas.delete("all")
        width = int(canvas["width"])
        height = int(canvas["height"])
        margin = 16
        canvas.create_rectangle(margin, margin, width - margin, height - margin, outline="#475569")
        distances = [sample.distance_m for sample in self.samples if sample.distance_m is not None]
        if not distances:
            canvas.create_text(width / 2, height / 2, text="no board distance samples yet", fill="#94a3b8")
            return
        z_min = min(distances)
        z_max = max(distances)
        span = max(z_max - z_min, 1e-6)
        for idx, distance in enumerate(distances):
            x = margin + (idx + 0.5) * (width - 2 * margin) / max(1, len(distances))
            y = height - margin - ((distance - z_min) / span) * (height - 2 * margin)
            canvas.create_line(x, height - margin, x, y, fill="#38bdf8", width=3)
        if self.current_detection is not None and self.current_detection.distance_m is not None:
            current_y = height - margin - ((self.current_detection.distance_m - z_min) / span) * (height - 2 * margin)
            current_y = max(margin, min(height - margin, current_y))
            canvas.create_line(margin, current_y, width - margin, current_y, fill="#f59e0b", dash=(4, 3))
        canvas.create_text(margin, 8, text=f"z range: {z_min:.3f}-{z_max:.3f} m", fill="#cbd5e1", anchor="nw")


def run(args: argparse.Namespace) -> None:
    root = tk.Tk()
    app = HandEyeCalibrationGuiApp(root, args)
    app.start()
    root.mainloop()
