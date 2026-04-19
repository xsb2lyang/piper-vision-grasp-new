from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import ttk
from typing import Optional

import numpy as np

from piper_app.calibration.handeye import extract_handeye_matrix, load_handeye_yaml
from piper_app.calibration.session import create_session_dir, display_repo_path, resolve_repo_path
from piper_app.calibration.viewer_base import CalibrationViewerBase
from piper_app.pick_demo.task import compute_base_point_from_camera
from piper_app.tcp_offset.estimate import (
    TcpOffsetSample,
    create_tcp_offset_sample,
    grade_tcp_offset_summary,
    save_tcp_offset_yaml,
    summarize_tcp_offset_samples,
)


class TcpOffsetEstimateGuiApp(CalibrationViewerBase):
    def __init__(self, root: tk.Tk, args: argparse.Namespace):
        self.handeye_data = load_handeye_yaml(args.handeye_path)
        self.T_tcp_camera = extract_handeye_matrix(self.handeye_data)
        self.session_dir = create_session_dir(args.session_base_dir, "tcp_offset")

        self.target_pixel: Optional[tuple[int, int]] = None
        self.target_camera_point_m: Optional[tuple[float, float, float]] = None
        self.target_base_point_m: Optional[tuple[float, float, float]] = None
        self.target_click_pose6: Optional[list[float]] = None
        self.samples: list[TcpOffsetSample] = []

        self.handeye_var = tk.StringVar(value=display_repo_path(resolve_repo_path(args.handeye_path)))
        self.session_var = tk.StringVar(value=display_repo_path(self.session_dir))
        self.output_var = tk.StringVar(value=display_repo_path(resolve_repo_path(args.output_path)))
        self.target_pixel_var = tk.StringVar(value="--")
        self.target_camera_var = tk.StringVar(value="--")
        self.target_base_var = tk.StringVar(value="--")
        self.click_pose_var = tk.StringVar(value="--")
        self.sample_count_var = tk.StringVar(value="0")
        self.current_candidate_var = tk.StringVar(value="--")
        self.mean_offset_var = tk.StringVar(value="--")
        self.std_offset_var = tk.StringVar(value="--")
        self.grade_var = tk.StringVar(value="Pending")
        self.grade_detail_var = tk.StringVar(value="Capture aligned samples to estimate the TCP translation offset.")

        super().__init__(
            root,
            args,
            title="Piper TCP Offset Estimator",
            use_robot=True,
            show_depth=True,
            note_text=(
                "Workflow: keep tcp_offset at zero, click a fixed target point, manually drag the robot until the "
                "intended grasp center reaches that point, then capture a sample. The tool computes a flange-frame "
                "translation offset candidate. Repeat from several poses and use the mean value."
            ),
            geometry="1680x980",
            left_scrollable=True,
        )
        self.color_canvas.bind("<Button-1>", self._on_canvas_click)
        if self.depth_canvas is not None:
            self.depth_canvas.bind("<Button-1>", self._on_canvas_click)

    def build_left_panel(self, parent: ttk.Frame) -> None:
        self.build_robot_connection_panel(parent, row=0, mode_label="Mode: tcp-offset")
        self.build_robot_status_panel(
            parent,
            row=1,
            extra_rows=[
                ("Hand-Eye", self.handeye_var),
                ("Session", self.session_var),
                ("Output", self.output_var),
                ("Target Pixel", self.target_pixel_var),
                ("Target Camera", self.target_camera_var),
                ("Target Base", self.target_base_var),
                ("Click Pose", self.click_pose_var),
                ("Sample Count", self.sample_count_var),
                ("Current Candidate", self.current_candidate_var),
                ("Mean Offset", self.mean_offset_var),
                ("Std XYZ", self.std_offset_var),
            ],
            title="TCP Offset Status",
        )
        self._build_controls(parent, 2)
        self.build_pose_panel(parent, 3, title="Current Flange Pose (tcp_offset=0)")
        self.build_joint_panel(parent, 4, title="Current Joint Angles")
        self._build_summary_panel(parent, 5)

    def _build_controls(self, parent: ttk.Frame, row: int) -> None:
        frame = ttk.LabelFrame(parent, text="Controls", padding=10)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        for idx in range(3):
            frame.columnconfigure(idx, weight=1)
        ttk.Button(frame, text="Capture Sample (S)", command=lambda: self.run_action(self.capture_sample)).grid(
            row=0, column=0, padx=(0, 6), pady=(0, 6), sticky="ew"
        )
        ttk.Button(frame, text="Delete Last (D)", command=lambda: self.run_action(self.delete_last_sample)).grid(
            row=0, column=1, padx=(0, 6), pady=(0, 6), sticky="ew"
        )
        ttk.Button(frame, text="Save YAML (W)", command=lambda: self.run_action(self.save_results)).grid(
            row=0, column=2, pady=(0, 6), sticky="ew"
        )
        ttk.Button(frame, text="Clear Target (C)", command=self.clear_target).grid(
            row=1, column=0, padx=(0, 6), sticky="ew"
        )
        ttk.Button(frame, text="Reset Session (R)", command=lambda: self.run_action(self.reset_session)).grid(
            row=1, column=1, padx=(0, 6), sticky="ew"
        )
        ttk.Button(frame, text="Quit (Q)", command=self.on_close).grid(row=1, column=2, sticky="ew")

    def _build_summary_panel(self, parent: ttk.Frame, row: int) -> None:
        frame = ttk.LabelFrame(parent, text="Recommendation", padding=10)
        frame.grid(row=row, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        self.grade_card = tk.Frame(frame, bg="#475569", bd=0, highlightthickness=0)
        self.grade_card.grid(row=0, column=0, sticky="ew")
        self.grade_title = tk.Label(
            self.grade_card,
            textvariable=self.grade_var,
            bg="#475569",
            fg="white",
            font=("TkDefaultFont", 11, "bold"),
            anchor="w",
            padx=12,
            pady=6,
        )
        self.grade_title.pack(fill="x")
        self.grade_detail = tk.Label(
            self.grade_card,
            textvariable=self.grade_detail_var,
            bg="#475569",
            fg="white",
            justify="left",
            wraplength=420,
            anchor="w",
            padx=12,
            pady=8,
        )
        self.grade_detail.pack(fill="x")

    def refresh_custom_ui(self) -> None:
        self.target_pixel_var.set("--" if self.target_pixel is None else f"{self.target_pixel}")
        if self.target_camera_point_m is None:
            self.target_camera_var.set("--")
        else:
            cp = self.target_camera_point_m
            self.target_camera_var.set(f"({cp[0]:.4f}, {cp[1]:.4f}, {cp[2]:.4f}) m")
        if self.target_base_point_m is None:
            self.target_base_var.set("--")
        else:
            bp = self.target_base_point_m
            self.target_base_var.set(f"({bp[0]:.4f}, {bp[1]:.4f}, {bp[2]:.4f}) m")
        if self.target_click_pose6 is None:
            self.click_pose_var.set("--")
        else:
            pose = self.target_click_pose6
            self.click_pose_var.set(f"({pose[0]:.3f}, {pose[1]:.3f}, {pose[2]:.3f})")

        self.sample_count_var.set(str(len(self.samples)))
        current_candidate = self._current_offset_candidate()
        self.current_candidate_var.set(
            "--"
            if current_candidate is None
            else f"({current_candidate[0]:.4f}, {current_candidate[1]:.4f}, {current_candidate[2]:.4f}) m"
        )
        summary = summarize_tcp_offset_samples(self.samples)
        if summary is None:
            self.mean_offset_var.set("--")
            self.std_offset_var.set("--")
        else:
            self.mean_offset_var.set(
                f"({summary.mean_xyz_m[0]:.4f}, {summary.mean_xyz_m[1]:.4f}, {summary.mean_xyz_m[2]:.4f}, 0, 0, 0)"
            )
            self.std_offset_var.set(
                f"({summary.std_xyz_m[0]:.4f}, {summary.std_xyz_m[1]:.4f}, {summary.std_xyz_m[2]:.4f}) m"
            )
        grade, color, detail = grade_tcp_offset_summary(summary)
        self.grade_var.set(grade)
        self.grade_detail_var.set(detail)
        self.grade_card.configure(bg=color)
        self.grade_title.configure(bg=color)
        self.grade_detail.configure(bg=color)

    def _on_canvas_click(self, event) -> None:
        viewer_name = "depth" if event.widget is self.depth_canvas else "color"
        self.select_target_from_canvas(viewer_name, event.x, event.y)

    def select_target_from_canvas(self, viewer_name: str, display_x: int, display_y: int) -> None:
        if self._camera_bundle is None or self._measured_tcp_pose is None:
            self.set_last_event("Need live camera and robot pose before selecting a target.")
            return
        view_info = self._color_view_info if viewer_name == "color" else self._depth_view_info
        if view_info is None:
            self.set_last_event("Display transform unavailable.")
            return
        src_point = self._display_to_source(view_info, display_x, display_y)
        if src_point is None:
            self.set_last_event("Click inside the image to select a target.")
            return
        query = self.camera.query_point(*src_point)
        if not query.valid or query.point_m is None:
            self.set_last_event(f"Depth is invalid at pixel {src_point}.")
            return
        base_point = compute_base_point_from_camera(self._measured_tcp_pose, self.T_tcp_camera, query.point_m)
        self.target_pixel = src_point
        self.target_camera_point_m = tuple(float(value) for value in query.point_m)
        self.target_base_point_m = tuple(float(value) for value in base_point.tolist())
        self.target_click_pose6 = list(self._measured_tcp_pose)
        self._hover_pixel = src_point
        self.set_last_event(
            f"Target frozen at pixel {src_point}. Drag the robot until the grasp center reaches this point, then capture."
        )
        self._draw_hover_overlay()
        self.refresh_ui()

    def _draw_hover_overlay(self) -> None:
        super()._draw_hover_overlay()
        if self.target_pixel is None or self._color_view_info is None:
            return
        color_x, color_y = self._source_to_display(self._color_view_info, *self.target_pixel)
        self._draw_marker(self.color_canvas, color_x, color_y, "#22c55e")
        if self.depth_canvas is not None and self._depth_view_info is not None:
            depth_x, depth_y = self._source_to_display(self._depth_view_info, *self.target_pixel)
            self._draw_marker(self.depth_canvas, depth_x, depth_y, "#22c55e")

    def _draw_marker(self, canvas: tk.Canvas, x: float, y: float, color: str) -> None:
        canvas.create_line(x - 14, y, x + 14, y, fill=color, width=2, tags=("overlay",))
        canvas.create_line(x, y - 14, x, y + 14, fill=color, width=2, tags=("overlay",))
        canvas.create_oval(x - 4, y - 4, x + 4, y + 4, outline=color, width=2, tags=("overlay",))

    def _current_offset_candidate(self) -> Optional[tuple[float, float, float]]:
        if self.target_pixel is None or self.target_base_point_m is None or self._measured_tcp_pose is None:
            return None
        candidate = create_tcp_offset_sample(
            index=0,
            target_pixel=self.target_pixel,
            target_base_point_m=self.target_base_point_m,
            flange_pose6=self._measured_tcp_pose,
        )
        return candidate.offset_flange_xyz_m

    def capture_sample(self) -> None:
        if self.target_pixel is None or self.target_base_point_m is None or self._measured_tcp_pose is None:
            raise RuntimeError("Select a target and align the robot before capturing.")
        sample = create_tcp_offset_sample(
            index=len(self.samples) + 1,
            target_pixel=self.target_pixel,
            target_base_point_m=self.target_base_point_m,
            flange_pose6=self._measured_tcp_pose,
        )
        self.samples.append(sample)
        self.set_last_event(
            "Captured sample "
            f"{sample.index}: offset=({sample.offset_flange_xyz_m[0]:.4f}, "
            f"{sample.offset_flange_xyz_m[1]:.4f}, {sample.offset_flange_xyz_m[2]:.4f}) m"
        )

    def delete_last_sample(self) -> None:
        if not self.samples:
            self.set_last_event("No samples to delete.")
            return
        removed = self.samples.pop()
        self.set_last_event(f"Deleted sample {removed.index}.")

    def clear_target(self) -> None:
        self.target_pixel = None
        self.target_camera_point_m = None
        self.target_base_point_m = None
        self.target_click_pose6 = None
        self._hover_pixel = None
        self.set_last_event("Cleared target.")
        self._draw_hover_overlay()
        self.refresh_ui()

    def reset_session(self) -> None:
        self.samples.clear()
        self.clear_target()
        self.session_dir = create_session_dir(self.args.session_base_dir, "tcp_offset")
        self.session_var.set(display_repo_path(self.session_dir))
        self.set_last_event("Started a fresh TCP offset estimation session.")

    def save_results(self) -> None:
        summary = summarize_tcp_offset_samples(self.samples)
        if summary is None:
            raise RuntimeError("Capture at least one sample before saving.")
        output_path = save_tcp_offset_yaml(
            self.args.output_path,
            self.samples,
            summary,
            handeye_path=display_repo_path(resolve_repo_path(self.args.handeye_path)),
            camera_serial=self._camera_serial_text,
        )
        self.output_var.set(display_repo_path(output_path))
        self.set_last_event(f"Saved TCP offset estimate to {display_repo_path(output_path)}.")

    def handle_key_action(self, key: str) -> None:
        if key == "s":
            self.run_action(self.capture_sample)
        elif key == "d":
            self.run_action(self.delete_last_sample)
        elif key == "c":
            self.clear_target()
        elif key == "r":
            self.run_action(self.reset_session)
        elif key == "w":
            self.run_action(self.save_results)


def run(args: argparse.Namespace) -> None:
    root = tk.Tk()
    app = TcpOffsetEstimateGuiApp(root, args)
    app.start()
    root.mainloop()
