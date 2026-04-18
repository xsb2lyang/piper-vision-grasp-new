from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import ttk
from typing import Optional

import numpy as np

from piper_app.calibration.charuco import CharucoDetection, CharucoDetector, load_board_config
from piper_app.calibration.handeye import extract_handeye_matrix, load_handeye_yaml
from piper_app.calibration.intrinsics import load_intrinsics_yaml
from piper_app.calibration.session import (
    create_session_dir,
    display_repo_path,
    resolve_repo_path,
    save_color_png,
    save_depth_png,
)
from piper_app.calibration.transforms import compose_matrix, matrix_to_pose6, pose6_to_matrix, translation_rotation_delta
from piper_app.calibration.validation import (
    ValidationSample,
    create_validation_sample,
    save_validation_sample_summary,
    save_validation_summary_yaml,
    summarize_validation_samples,
)
from piper_app.calibration.viewer_base import CalibrationViewerBase
from piper_app.config import repo_root


class HandEyeValidationGuiApp(CalibrationViewerBase):
    def __init__(self, root: tk.Tk, args: argparse.Namespace):
        self.board_config = load_board_config(args.board_config)
        self.intrinsics_data = load_intrinsics_yaml(args.intrinsics_path)
        self.handeye_data = load_handeye_yaml(args.handeye_path)
        self.T_tcp_camera = extract_handeye_matrix(self.handeye_data)
        self.detector = CharucoDetector(
            self.board_config,
            camera_matrix=np.asarray(self.intrinsics_data["K"], dtype=np.float64),
            dist_coeffs=np.asarray(self.intrinsics_data["dist_coeffs"], dtype=np.float64),
        )
        self.current_detection: Optional[CharucoDetection] = None
        self.current_overlay_rgb = None
        self.current_T_base_board: Optional[np.ndarray] = None
        self.samples: list[ValidationSample] = []
        self.session_dir = create_session_dir(args.session_base_dir, "validate")

        self.board_status_var = tk.StringVar(value="Waiting for camera...")
        self.session_var = tk.StringVar(value=display_repo_path(self.session_dir))
        self.intrinsics_var = tk.StringVar(value=display_repo_path(resolve_repo_path(args.intrinsics_path)))
        self.handeye_var = tk.StringVar(value=display_repo_path(resolve_repo_path(args.handeye_path)))
        self.sample_count_var = tk.StringVar(value="0")
        self.validation_summary_var = tk.StringVar(value="No validation samples yet.")
        self.current_delta_var = tk.StringVar(value="Need a reference sample to compare drift.")
        self.board_pose_vars = [tk.StringVar(value="--") for _ in range(6)]

        super().__init__(
            root,
            args,
            title="Piper Hand-Eye Validation",
            use_robot=True,
            show_depth=True,
            note_text=(
                "This window validates the current hand-eye result in read-only mode. It computes "
                "T_base_board = T_base_tcp @ T_tcp_camera @ T_camera_board from live detections."
            ),
        )

    def build_left_panel(self, parent: ttk.Frame) -> None:
        self.build_robot_connection_panel(parent, row=0, mode_label="Mode: validation")
        self.build_robot_status_panel(
            parent,
            row=1,
            extra_rows=[
                ("Board", self.board_status_var),
                ("Intrinsics", self.intrinsics_var),
                ("Hand-Eye", self.handeye_var),
                ("Session", self.session_var),
                ("Sample Count", self.sample_count_var),
                ("Summary", self.validation_summary_var),
                ("Current Delta", self.current_delta_var),
            ],
            title="Validation Status",
        )
        self.build_pose_panel(parent, row=2, title="Current TCP Pose")
        self._build_board_pose_panel(parent, row=3)
        self.build_joint_panel(parent, row=4, title="Current Joint Angles")

        controls = ttk.LabelFrame(parent, text="Controls", padding=10)
        controls.grid(row=5, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(controls, text="Capture (S)", command=lambda: self.run_action(self.capture_sample)).grid(
            row=0, column=0, padx=(0, 6), pady=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Delete Last (D)", command=lambda: self.run_action(self.delete_last_sample)).grid(
            row=0, column=1, padx=(0, 6), pady=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Reset (R)", command=lambda: self.run_action(self.reset_session)).grid(
            row=1, column=0, padx=(0, 6), sticky="ew"
        )
        ttk.Button(controls, text="Quit (Q)", command=self.on_close).grid(row=1, column=1, sticky="ew")

        visuals = ttk.LabelFrame(parent, text="Validation Visuals", padding=10)
        visuals.grid(row=6, column=0, sticky="nsew")
        visuals.columnconfigure(0, weight=1)
        ttk.Label(visuals, text="Board XY In Base Frame").grid(row=0, column=0, sticky="w")
        self.board_xy_canvas = tk.Canvas(
            visuals,
            width=260,
            height=180,
            bg="#0f172a",
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.board_xy_canvas.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        ttk.Label(visuals, text="Board Z Samples").grid(row=2, column=0, sticky="w")
        self.board_z_canvas = tk.Canvas(
            visuals,
            width=260,
            height=80,
            bg="#0f172a",
            highlightthickness=1,
            highlightbackground="#334155",
        )
        self.board_z_canvas.grid(row=3, column=0, sticky="ew")

    def _build_board_pose_panel(self, parent: ttk.Frame, row: int) -> None:
        frame = ttk.LabelFrame(parent, text="Current T_base_board", padding=10)
        frame.grid(row=row, column=0, sticky="nsew", pady=(0, 10))
        for col in range(2):
            frame.columnconfigure(col, weight=1)
        ttk.Label(frame, text="Axis").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text="Value").grid(row=0, column=1, sticky="w")
        for row_idx, axis_name in enumerate(["x", "y", "z", "roll", "pitch", "yaw"], start=1):
            ttk.Label(frame, text=axis_name).grid(row=row_idx, column=0, sticky="w", pady=2)
            ttk.Label(frame, textvariable=self.board_pose_vars[row_idx - 1]).grid(
                row=row_idx, column=1, sticky="w", pady=2
            )

    def on_robot_polled(self) -> None:
        self._update_live_base_board()

    def on_camera_bundle(self, bundle) -> None:
        detection = self.detector.detect(bundle.color_rgb)
        self.current_detection = detection
        self.current_overlay_rgb = detection.overlay_rgb
        distance_text = "--" if detection.distance_m is None else f"{detection.distance_m:.4f} m"
        self.board_status_var.set(
            f"{detection.message} markers={detection.marker_count} corners={detection.charuco_count} z={distance_text}"
        )
        self._update_live_base_board()

    def get_display_images(self, bundle):
        return self.current_overlay_rgb if self.current_overlay_rgb is not None else bundle.color_rgb, bundle.depth_visual_rgb

    def _update_live_base_board(self) -> None:
        if self._measured_tcp_pose is None or self.current_detection is None or not self.current_detection.pose_ok:
            self.current_T_base_board = None
            return
        T_base_tcp = pose6_to_matrix(self._measured_tcp_pose)
        T_camera_board = self.detector.camera_matrix is not None and self.current_detection.rvec is not None
        if not T_camera_board:
            self.current_T_base_board = None
            return
        from piper_app.calibration.transforms import rvec_tvec_to_matrix

        T_camera_board_matrix = rvec_tvec_to_matrix(self.current_detection.rvec, self.current_detection.tvec)
        self.current_T_base_board = compose_matrix(compose_matrix(T_base_tcp, self.T_tcp_camera), T_camera_board_matrix)
        if self.samples:
            ref = self.samples[0].T_base_board
            trans_delta, rot_delta = translation_rotation_delta(ref, self.current_T_base_board)
            self.current_delta_var.set(
                f"vs first sample: translation={trans_delta:.4f} m rotation={rot_delta:.3f} deg"
            )

    def capture_sample(self) -> None:
        if self._camera_bundle is None or self.current_T_base_board is None or self.current_detection is None:
            raise RuntimeError("Live validation pose is unavailable.")
        sample_index = len(self.samples) + 1
        color_path = self.session_dir / f"sample_{sample_index:03d}_color.png"
        depth_path = self.session_dir / f"sample_{sample_index:03d}_depth.png"
        summary_path = self.session_dir / f"sample_{sample_index:03d}.yaml"
        save_color_png(color_path, self._camera_bundle.color_rgb)
        save_depth_png(depth_path, self._camera_bundle.depth_m)
        sample = create_validation_sample(
            index=sample_index,
            color_image_path=str(color_path.relative_to(repo_root())),
            depth_image_path=str(depth_path.relative_to(repo_root())),
            summary_path=str(summary_path.relative_to(repo_root())),
            T_base_board=self.current_T_base_board,
            charuco_count=int(self.current_detection.charuco_count),
            distance_m=self.current_detection.distance_m,
        )
        self.samples.append(sample)
        save_validation_sample_summary(summary_path, sample)
        summary = summarize_validation_samples(self.samples)
        save_validation_summary_yaml(self.session_dir / "validation_summary.yaml", summary, self.samples)
        self._last_event_text = f"Captured validation sample {sample_index}."

    def delete_last_sample(self) -> None:
        if not self.samples:
            self._last_event_text = "No sample to delete."
            return
        removed = self.samples.pop()
        if self.samples:
            summary = summarize_validation_samples(self.samples)
            save_validation_summary_yaml(self.session_dir / "validation_summary.yaml", summary, self.samples)
        else:
            self.validation_summary_var.set("No validation samples yet.")
            self.current_delta_var.set("Need a reference sample to compare drift.")
        self._last_event_text = f"Removed validation sample {removed.index}."

    def reset_session(self) -> None:
        self.samples.clear()
        self.session_dir = create_session_dir(self.args.session_base_dir, "validate")
        self.session_var.set(display_repo_path(self.session_dir))
        self.validation_summary_var.set("No validation samples yet.")
        self.current_delta_var.set("Need a reference sample to compare drift.")
        self._last_event_text = "Started a new validation session."

    def refresh_custom_ui(self) -> None:
        self.sample_count_var.set(str(len(self.samples)))
        if self.current_T_base_board is None:
            for variable in self.board_pose_vars:
                variable.set("--")
        else:
            pose = matrix_to_pose6(self.current_T_base_board)
            for idx, value in enumerate(pose):
                self.board_pose_vars[idx].set(f"{value:.4f} m" if idx < 3 else f"{value:.4f} rad")
        summary = summarize_validation_samples(self.samples)
        if summary.sample_count > 0:
            self.validation_summary_var.set(
                f"translation_std={summary.translation_std_m:.6f} m, "
                f"rotation_mean={summary.rotation_mean_deg:.4f} deg, "
                f"rotation_max={summary.rotation_max_deg:.4f} deg"
            )
        else:
            self.validation_summary_var.set("No validation samples yet.")
        self._draw_board_xy_canvas()
        self._draw_board_z_canvas()

    def _draw_board_xy_canvas(self) -> None:
        canvas = self.board_xy_canvas
        canvas.delete("all")
        width = int(canvas["width"])
        height = int(canvas["height"])
        margin = 16
        canvas.create_rectangle(margin, margin, width - margin, height - margin, outline="#475569")
        positions = [sample.T_base_board[:2, 3] for sample in self.samples]
        if self.current_T_base_board is not None:
            positions.append(self.current_T_base_board[:2, 3])
        if not positions:
            canvas.create_text(width / 2, height / 2, text="capture validation samples", fill="#94a3b8")
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
            x, y = project(sample.T_base_board[:2, 3])
            canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#38bdf8", outline="")
        if self.current_T_base_board is not None:
            x, y = project(self.current_T_base_board[:2, 3])
            canvas.create_line(x - 10, y, x + 10, y, fill="#f59e0b", width=2)
            canvas.create_line(x, y - 10, x, y + 10, fill="#f59e0b", width=2)

    def _draw_board_z_canvas(self) -> None:
        canvas = self.board_z_canvas
        canvas.delete("all")
        width = int(canvas["width"])
        height = int(canvas["height"])
        margin = 16
        canvas.create_rectangle(margin, margin, width - margin, height - margin, outline="#475569")
        z_values = [float(sample.T_base_board[2, 3]) for sample in self.samples]
        if self.current_T_base_board is not None:
            z_values.append(float(self.current_T_base_board[2, 3]))
        if not z_values:
            canvas.create_text(width / 2, height / 2, text="no z values yet", fill="#94a3b8")
            return
        z_min = min(z_values)
        z_max = max(z_values)
        span = max(z_max - z_min, 1e-6)
        for idx, sample in enumerate(self.samples):
            x = margin + (idx + 0.5) * (width - 2 * margin) / max(1, len(self.samples))
            z_value = float(sample.T_base_board[2, 3])
            y = height - margin - ((z_value - z_min) / span) * (height - 2 * margin)
            canvas.create_line(x, height - margin, x, y, fill="#38bdf8", width=3)
        if self.current_T_base_board is not None:
            z_value = float(self.current_T_base_board[2, 3])
            y = height - margin - ((z_value - z_min) / span) * (height - 2 * margin)
            y = max(margin, min(height - margin, y))
            canvas.create_line(margin, y, width - margin, y, fill="#f59e0b", dash=(4, 3))
        canvas.create_text(margin, 8, text=f"z range: {z_min:.4f}-{z_max:.4f} m", fill="#cbd5e1", anchor="nw")

    def handle_key_action(self, key: str) -> None:
        actions = {
            "s": self.capture_sample,
            "d": self.delete_last_sample,
            "r": self.reset_session,
        }
        if key == "q":
            self.on_close()
            return
        if key in actions:
            self.run_action(actions[key])


def run(args: argparse.Namespace) -> None:
    root = tk.Tk()
    app = HandEyeValidationGuiApp(root, args)
    app.start()
    root.mainloop()
