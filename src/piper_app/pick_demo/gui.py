from __future__ import annotations

import argparse
import time
import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional

import numpy as np

from piper_app.camera.d405 import D405FrameBundle, D405PointQuery
from piper_app.calibration.session import display_repo_path
from piper_app.calibration.viewer_base import CalibrationViewerBase
from piper_app.perception.yolo import YoloConfig, YoloDetection, YoloDetector, YoloPrediction
from piper_app.pick_demo.task import (
    PickDemoWorkspace,
    PickPlan,
    build_pick_plan,
    compute_base_point_from_camera,
    is_near_observe_pose,
    load_pick_workspace,
    validate_workspace_point,
)


class ClickPickDemoGuiApp(CalibrationViewerBase):
    def __init__(self, root: tk.Tk, args: argparse.Namespace):
        self.workspace: Optional[PickDemoWorkspace] = None
        self.selected_plan: Optional[PickPlan] = None
        self.selected_warning_text = "No target selected."
        self.observe_ready_text = "Unknown"
        self.plan_text = "No pick plan."
        self._selected_pixel: Optional[tuple[int, int]] = None
        self._gripper_value_m: Optional[float] = None
        self._gripper_driver_enabled = False
        self._gripper_homing = False
        self._gripper_driver_error = False
        self._gripper_max_range_m = 0.03
        self._action_running = False
        self._yolo_enabled = bool(getattr(args, "yolo", False))
        self._yolo_detector = YoloDetector(
            YoloConfig(
                enabled=self._yolo_enabled,
                weights_path=str(getattr(args, "yolo_weights", "third_party/yolo/新松-检测/yolo11m.pt")),
                imgsz=int(getattr(args, "yolo_imgsz", 640)),
                conf=float(getattr(args, "yolo_conf", 0.25)),
                iou=float(getattr(args, "yolo_iou", 0.45)),
                max_det=int(getattr(args, "yolo_max_det", 50)),
                device=str(getattr(args, "yolo_device", "auto")),
            )
        )
        self._live_prediction: Optional[YoloPrediction] = None
        self._frozen_prediction: Optional[YoloPrediction] = None
        self._frozen_bundle: Optional[D405FrameBundle] = None
        self._paused = False
        self._yolo_status_text = "Disabled"
        self._selected_detection: Optional[YoloDetection] = None
        self._selected_detection_text = "No detection selected."

        super().__init__(
            root,
            args,
            title="Piper Click Pick Demo",
            use_robot=True,
            show_depth=True,
            note_text=(
                "Recommended flow: move to Observe, click a tabletop target, review the plan, then run Execute Pick. "
                "This first demo uses a fixed top-down grasp orientation from the saved observe pose."
            ),
            geometry="1680x980",
            left_scrollable=True,
        )
        self.color_canvas.bind("<Button-1>", self._on_canvas_click)
        if self.depth_canvas is not None:
            self.depth_canvas.bind("<Button-1>", self._on_canvas_click)

    def run_action(self, callback) -> None:
        try:
            callback()
        except Exception as exc:
            self._last_event_text = f"{type(exc).__name__}: {exc}"
            self._robot_status_text = f"Action error: {type(exc).__name__}"
        self.refresh_ui()

    def _request_ui_refresh(self) -> None:
        self.root.after(0, self.refresh_ui)

    def run_background_action(self, callback) -> None:
        if self._action_running:
            self._last_event_text = "Another robot action is still running."
            self.refresh_ui()
            return

        self._action_running = True
        self._robot_status_text = "Running action..."
        self.refresh_ui()

        def worker() -> None:
            try:
                callback()
            except Exception as exc:
                self._last_event_text = f"{type(exc).__name__}: {exc}"
                self._robot_status_text = f"Action error: {type(exc).__name__}"
            finally:
                self._action_running = False
                self._request_ui_refresh()

        threading.Thread(target=worker, name="click-pick-action", daemon=True).start()

    def _build_base_vars(self) -> None:
        super()._build_base_vars()
        self.config_path_var = tk.StringVar(value="")
        self.handeye_path_var = tk.StringVar(value="")
        self.observe_ready_var = tk.StringVar(value=self.observe_ready_text)
        self.view_mode_var = tk.StringVar(value="Live")
        self.yolo_status_var = tk.StringVar(value=self._yolo_status_text)
        self.selected_pixel_var = tk.StringVar(value="--")
        self.selected_detection_var = tk.StringVar(value=self._selected_detection_text)
        self.selected_camera_point_var = tk.StringVar(value="--")
        self.selected_base_point_var = tk.StringVar(value="--")
        self.selected_warning_var = tk.StringVar(value=self.selected_warning_text)
        self.plan_var = tk.StringVar(value=self.plan_text)
        self.gripper_state_var = tk.StringVar(value="--")
        self.gripper_width_var = tk.StringVar(value="--")
        self.gripper_max_range_var = tk.StringVar(value="--")
        self.dry_run_var = tk.BooleanVar(value=bool(getattr(self.args, "dry_run", True)))

    def build_left_panel(self, parent: ttk.Frame) -> None:
        for row in range(7):
            parent.rowconfigure(row, weight=0)
        parent.rowconfigure(6, weight=1)

        self.build_robot_connection_panel(parent, 0, mode_label="Mode: click-pick")
        self.build_robot_status_panel(
            parent,
            1,
            extra_rows=[
                ("Workspace", self.config_path_var),
                ("Hand-Eye", self.handeye_path_var),
                ("Observe Readiness", self.observe_ready_var),
                ("View Mode", self.view_mode_var),
                ("YOLO", self.yolo_status_var),
                ("Selected Pixel", self.selected_pixel_var),
                ("Selected Detection", self.selected_detection_var),
                ("Camera Point", self.selected_camera_point_var),
                ("Base Point", self.selected_base_point_var),
                ("Selection", self.selected_warning_var),
                ("Plan", self.plan_var),
                ("Gripper", self.gripper_state_var),
                ("Gripper Width", self.gripper_width_var),
                ("Gripper Max", self.gripper_max_range_var),
            ],
            title="Pick Status",
        )
        self._build_action_panel(parent, 2)
        self.build_pose_panel(parent, 3, title="Current TCP Pose")
        self.build_joint_panel(parent, 4, title="Current Joint Angles")

    def _build_action_panel(self, parent: ttk.Frame, row: int) -> None:
        frame = ttk.LabelFrame(parent, text="Actions", padding=10)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
        for idx in range(4):
            frame.columnconfigure(idx, weight=1)

        ttk.Button(frame, text="Reload Config", command=lambda: self.run_action(self.reload_workspace)).grid(
            row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 6)
        )
        ttk.Button(frame, text="Pause / Freeze", command=self.toggle_pause).grid(
            row=0, column=1, sticky="ew", padx=(0, 6), pady=(0, 6)
        )
        ttk.Button(frame, text="Move Home", command=lambda: self.run_background_action(self.move_home)).grid(
            row=0, column=2, sticky="ew", padx=(0, 6), pady=(0, 6)
        )
        ttk.Button(frame, text="Move Observe", command=lambda: self.run_background_action(self.move_observe)).grid(
            row=0, column=3, sticky="ew", pady=(0, 6)
        )

        ttk.Button(frame, text="Open Gripper", command=lambda: self.run_background_action(self.open_gripper)).grid(
            row=1, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(frame, text="Clear Target", command=self.clear_selection).grid(
            row=1, column=1, sticky="ew", padx=(0, 6)
        )
        ttk.Button(frame, text="Close Gripper", command=lambda: self.run_background_action(self.close_gripper)).grid(
            row=1, column=2, sticky="ew", padx=(0, 6)
        )
        ttk.Button(frame, text="Execute Pick", command=lambda: self.run_background_action(self.execute_pick_sequence)).grid(
            row=1, column=3, sticky="ew"
        )
        ttk.Label(
            frame,
            text="Flow: live detect -> pause frame -> click a detection box -> Execute Pick",
            wraplength=520,
            justify="left",
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Checkbutton(frame, text="Dry-run", variable=self.dry_run_var).grid(row=2, column=3, sticky="e", pady=(8, 0))

    def connect_robot(self) -> None:
        self.connection_var.set("Connecting...")
        self._last_event_text = "Connecting to Piper..."
        self.client.config.robot = self.robot_var.get()
        self.client.config.interface = self.interface_var.get()
        self.client.config.channel = self.channel_var.get()
        self.client.config.bitrate = int(self.bitrate_var.get())
        self.client.config.firmware_timeout = float(self.args.firmware_timeout)
        self.client.config.speed_percent = int(self.args.speed_percent)
        if self.workspace is not None:
            self.client.config.tcp_offset = [float(value) for value in self.workspace.tcp_offset]
        self.client.connect(configure_robot=True, init_gripper=True)
        self._firmware_info = self.client.firmware_info
        self._connected = True
        self._robot_status_text = "Connected"
        self._last_event_text = "Robot connected."
        self._poll_data()

    def start(self) -> None:
        self.run_action(self.reload_workspace)
        super().start()

    def reload_workspace(self) -> None:
        self.workspace = load_pick_workspace(self.args.keypoints_path, self.args.handeye_path)
        self.config_path_var.set(display_repo_path(self.workspace.config_path))
        self.handeye_path_var.set(display_repo_path(self.workspace.handeye_path))
        self.client.config.tcp_offset = [float(value) for value in self.workspace.tcp_offset]
        self.selected_warning_text = "Workspace loaded. Move to Observe, then click a target."
        self._last_event_text = "Pick workspace reloaded."
        self._update_selection_vars()

    def on_robot_polled(self) -> None:
        if self.workspace is None:
            self.observe_ready_text = "Workspace not loaded"
            return
        self.observe_ready_text = (
            "Near observe pose" if is_near_observe_pose(self._measured_tcp_pose, self.workspace) else "Not at observe pose"
        )
        teaching = self.client.get_gripper_teaching_pendant_param(timeout=0.2, min_interval=0.0)
        if teaching is not None:
            self._gripper_max_range_m = float(teaching.msg.max_range_config)
        gs = self.client.get_gripper_status()
        if gs is not None:
            self._gripper_value_m = float(gs.msg.value)
            foc = gs.msg.foc_status
            self._gripper_driver_enabled = bool(foc.driver_enable_status)
            self._gripper_homing = bool(foc.homing_status)
            self._gripper_driver_error = bool(foc.driver_error_status)

    def refresh_custom_ui(self) -> None:
        self.observe_ready_var.set(self.observe_ready_text)
        self.view_mode_var.set("Paused" if self._paused else "Live")
        self.yolo_status_var.set(self._yolo_status_text)
        self.gripper_state_var.set(
            f"enabled={self._gripper_driver_enabled} homed={self._gripper_homing} error={self._gripper_driver_error}"
        )
        self.gripper_width_var.set("--" if self._gripper_value_m is None else f"{self._gripper_value_m:.4f} m")
        self.gripper_max_range_var.set(f"{self._gripper_max_range_m:.4f} m")
        self._update_selection_vars()

    def _update_selection_vars(self) -> None:
        self.selected_detection_var.set(self._selected_detection_text)
        if self.selected_plan is None:
            self.selected_pixel_var.set("--")
            self.selected_camera_point_var.set("--")
            self.selected_base_point_var.set("--")
            self.plan_var.set("No pick plan.")
        else:
            self.selected_pixel_var.set(f"{self.selected_plan.selected_pixel}")
            cp = self.selected_plan.camera_point_m
            bp = self.selected_plan.base_point_m
            self.selected_camera_point_var.set(f"({cp[0]:.4f}, {cp[1]:.4f}, {cp[2]:.4f}) m")
            self.selected_base_point_var.set(f"({bp[0]:.4f}, {bp[1]:.4f}, {bp[2]:.4f}) m")
            self.plan_var.set(
                "pregrasp="
                f"({self.selected_plan.pregrasp_pose[0]:.3f}, {self.selected_plan.pregrasp_pose[1]:.3f}, {self.selected_plan.pregrasp_pose[2]:.3f}) "
                "grasp="
                f"({self.selected_plan.grasp_pose[0]:.3f}, {self.selected_plan.grasp_pose[1]:.3f}, {self.selected_plan.grasp_pose[2]:.3f}) "
                "drop="
                f"({self.selected_plan.drop_pose[0]:.3f}, {self.selected_plan.drop_pose[1]:.3f}, {self.selected_plan.drop_pose[2]:.3f})"
            )
        self.selected_warning_var.set(self.selected_warning_text)

    def _on_canvas_click(self, event) -> None:
        viewer_name = "depth" if event.widget is self.depth_canvas else "color"
        self.select_target_from_canvas(viewer_name, event.x, event.y)

    def toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self._frozen_bundle = self._camera_bundle
            self._frozen_prediction = self._live_prediction
            self._last_event_text = "Paused current frame. Click a YOLO box or a raw pixel."
        else:
            self._frozen_bundle = None
            self._frozen_prediction = None
            self._last_event_text = "Returned to live camera view."
        self.refresh_ui()

    def on_camera_bundle(self, bundle: D405FrameBundle) -> None:
        if self._yolo_enabled and not self._paused:
            try:
                self._live_prediction = self._yolo_detector.predict(bundle.color_rgb)
                self._yolo_status_text = (
                    f"Running ({self._live_prediction.device_label}) | {len(self._live_prediction.detections)} detections"
                )
            except Exception as exc:
                self._yolo_status_text = f"Error: {type(exc).__name__}"
                self._last_event_text = f"YOLO inference failed: {type(exc).__name__}: {exc}"
                self._live_prediction = None
                self._yolo_enabled = False
        elif not self._yolo_enabled:
            self._yolo_status_text = "Disabled"

    def get_display_images(self, bundle: D405FrameBundle) -> tuple[object, Optional[object]]:
        if self._paused and self._frozen_bundle is not None:
            bundle = self._frozen_bundle
            prediction = self._frozen_prediction
        else:
            prediction = self._live_prediction
        color_rgb = prediction.annotated_rgb if prediction is not None else bundle.color_rgb
        depth_rgb = bundle.depth_visual_rgb
        return color_rgb, depth_rgb

    def _pick_detection_at_pixel(self, pixel: tuple[int, int]) -> Optional[YoloDetection]:
        prediction = self._frozen_prediction if self._paused and self._frozen_prediction is not None else self._live_prediction
        if prediction is None:
            return None
        px, py = pixel
        matching: list[YoloDetection] = []
        for detection in prediction.detections:
            x1, y1, x2, y2 = detection.bbox_xyxy
            if x1 <= px <= x2 and y1 <= py <= y2:
                matching.append(detection)
        if not matching:
            return None
        return max(matching, key=lambda det: det.confidence)

    def select_target_from_canvas(self, viewer_name: str, display_x: int, display_y: int) -> None:
        if self.workspace is None:
            self.selected_warning_text = "Workspace not loaded."
            self.refresh_ui()
            return
        if not self._camera_connected or self._camera_bundle is None:
            self.selected_warning_text = "Camera is not streaming."
            self.refresh_ui()
            return
        if self._measured_tcp_pose is None:
            self.selected_warning_text = "Current TCP pose is unavailable."
            self.refresh_ui()
            return

        view_info = self._color_view_info if viewer_name == "color" else self._depth_view_info
        if view_info is None:
            self.selected_warning_text = "Display transform unavailable."
            self.refresh_ui()
            return
        src_point = self._display_to_source(view_info, display_x, display_y)
        if src_point is None:
            self.selected_warning_text = "Click inside the image to select a point."
            self.refresh_ui()
            return

        detection = self._pick_detection_at_pixel(src_point) if self._yolo_enabled else None
        if detection is not None:
            self._selected_detection = detection
            self._selected_detection_text = f"{detection.label} @ {detection.confidence:.2f} box={detection.bbox_xyxy}"
        else:
            self._selected_detection = None
            self._selected_detection_text = "No detection selected."

        query = self.camera.query_point(*src_point)
        if not query.valid or query.point_m is None:
            self.selected_warning_text = f"Depth is invalid at pixel {src_point}."
            self.selected_plan = None
            self._selected_pixel = None
            self.refresh_ui()
            return

        base_point = compute_base_point_from_camera(self._measured_tcp_pose, self.workspace.T_tcp_camera, query.point_m)
        self.selected_plan = build_pick_plan(
            selected_pixel=src_point,
            camera_point_m=query.point_m,
            base_point_m=base_point,
            workspace=self.workspace,
        )
        warning = validate_workspace_point(self.selected_plan.base_point_m, self.workspace)
        self._selected_pixel = src_point
        if warning:
            self.selected_warning_text = warning
        elif detection is not None:
            self.selected_warning_text = "Detection selected. Ready to run Execute Pick."
        else:
            self.selected_warning_text = "Pixel selected. Ready to run Execute Pick."
        self._last_event_text = f"Selected pixel {src_point}."
        self._draw_hover_overlay()
        self.refresh_ui()

    def clear_selection(self) -> None:
        self.selected_plan = None
        self._selected_pixel = None
        self._selected_detection = None
        self._selected_detection_text = "No detection selected."
        self.selected_warning_text = "Selection cleared."
        self._last_event_text = "Cleared selected target."
        self._draw_hover_overlay()
        self.refresh_ui()

    def _draw_hover_overlay(self) -> None:
        super()._draw_hover_overlay()
        if self._selected_pixel is None or self._color_view_info is None:
            return
        color_x, color_y = self._source_to_display(self._color_view_info, *self._selected_pixel)
        self._draw_marker(self.color_canvas, color_x, color_y, "#22c55e")
        if self.depth_canvas is not None and self._depth_view_info is not None:
            depth_x, depth_y = self._source_to_display(self._depth_view_info, *self._selected_pixel)
            self._draw_marker(self.depth_canvas, depth_x, depth_y, "#22c55e")

    def _draw_marker(self, canvas: tk.Canvas, x: float, y: float, color: str) -> None:
        canvas.create_line(x - 16, y, x + 16, y, fill=color, width=2, tags=("overlay",))
        canvas.create_line(x, y - 16, x, y + 16, fill=color, width=2, tags=("overlay",))
        canvas.create_oval(x - 4, y - 4, x + 4, y + 4, outline=color, width=2, tags=("overlay",))

    def _require_workspace(self) -> PickDemoWorkspace:
        if self.workspace is None:
            raise RuntimeError("Pick workspace is not loaded.")
        return self.workspace

    def _is_joint_pose_near(self, joint_angles: list[float], tol_rad: float = 0.06) -> bool:
        if self._joint_angles is None:
            return False
        current = np.asarray(self._joint_angles, dtype=np.float64)
        target = np.asarray(joint_angles, dtype=np.float64)
        return current.shape == target.shape and float(np.max(np.abs(current - target))) <= tol_rad

    def _move_to_joint_pose(self, pose_name: str, joint_angles: list[float]) -> None:
        if self.dry_run_var.get():
            self._last_event_text = f"Dry-run: would move to {pose_name}."
            self._request_ui_refresh()
            return
        if self._is_joint_pose_near(joint_angles):
            self._last_event_text = f"Already near {pose_name}."
            self._request_ui_refresh()
            return
        timeout = float(self._require_workspace().task_defaults["move_timeout_s"])
        if not self.client.move_joint_pose(joint_angles, timeout=timeout):
            raise RuntimeError(f"Timed out while moving to {pose_name}.")
        self._last_event_text = f"Reached {pose_name}."
        self._poll_data()
        self._request_ui_refresh()

    def _move_to_tcp_pose(self, pose_name: str, tcp_pose: list[float], *, linear: bool) -> None:
        if self.dry_run_var.get():
            mode = "move_l" if linear else "move_p"
            self._last_event_text = f"Dry-run: would {mode} to {pose_name}."
            self._request_ui_refresh()
            return
        workspace = self._require_workspace()
        timeout_key = "place_timeout_s" if pose_name in {"drop_prepose", "drop_pose"} else "move_timeout_s"
        timeout = float(workspace.task_defaults[timeout_key])
        ok = self.client.move_linear_tcp_pose(tcp_pose, timeout=timeout) if linear else self.client.move_tcp_pose(
            tcp_pose, timeout=timeout
        )
        if not ok:
            if linear and pose_name in {"grasp", "drop_pose"}:
                self._last_event_text = f"Linear move to {pose_name} timed out, retrying with move_p."
                self._request_ui_refresh()
                ok = self.client.move_tcp_pose(tcp_pose, timeout=timeout)
            if not ok:
                raise RuntimeError(f"Timed out while moving to {pose_name}.")
        self._last_event_text = f"Reached {pose_name}."
        self._poll_data()
        self._request_ui_refresh()

    def _set_gripper_width(self, width_m: float, force_n: float) -> None:
        target_width = min(max(0.0, float(width_m)), max(0.001, float(self._gripper_max_range_m)))
        if self._gripper_value_m is not None and abs(self._gripper_value_m - target_width) < 0.001:
            self._last_event_text = f"Gripper already near {target_width:.4f} m."
            self._request_ui_refresh()
            return
        if self.dry_run_var.get():
            self._last_event_text = f"Dry-run: would set gripper to {target_width:.4f} m."
            self._request_ui_refresh()
            return
        if not self._gripper_driver_enabled:
            raise RuntimeError("Gripper driver is not enabled. Re-enable or zero the gripper first.")
        if self._gripper_driver_error:
            raise RuntimeError("Gripper reports a driver error. Clear the fault before retrying.")
        settle_s = float(self._require_workspace().task_defaults["gripper_settle_s"])
        self.client.move_gripper_width(target_width, force_n=force_n, settle_s=settle_s)
        self._last_event_text = f"Set gripper width to {target_width:.4f} m."
        gs = self.client.get_gripper_status()
        if gs is not None:
            self._gripper_value_m = float(gs.msg.value)
        self._request_ui_refresh()

    def _close_gripper_gradually(self, width_m: float, force_n: float) -> None:
        workspace = self._require_workspace()
        steps = max(1, int(workspace.task_defaults.get("gripper_close_steps", 1)))
        step_pause_s = max(0.0, float(workspace.task_defaults.get("gripper_close_step_pause_s", 0.0)))
        current_width = self._gripper_value_m
        if current_width is None or steps <= 1:
            self._set_gripper_width(width_m, force_n)
            return
        target_width = min(max(0.0, float(width_m)), max(0.001, float(self._gripper_max_range_m)))
        if target_width >= current_width - 0.001:
            self._set_gripper_width(target_width, force_n)
            return
        widths = np.linspace(current_width, target_width, steps + 1, dtype=np.float64)[1:]
        for index, intermediate_width in enumerate(widths, start=1):
            self._last_event_text = (
                f"Step 5/8: close gripper ({index}/{len(widths)}) to {float(intermediate_width):.4f} m."
            )
            self._request_ui_refresh()
            self._set_gripper_width(float(intermediate_width), force_n)
            if index < len(widths) and step_pause_s > 0.0:
                time.sleep(step_pause_s)

    def _resolved_open_gripper_width(self, workspace: PickDemoWorkspace) -> float:
        configured = float(workspace.task_defaults["gripper_open_width_m"])
        if configured <= 0.0:
            return float(self._gripper_max_range_m)
        return min(configured, float(self._gripper_max_range_m))

    def move_home(self) -> None:
        workspace = self._require_workspace()
        if self.dry_run_var.get():
            self._last_event_text = "Dry-run: would command home."
            self._request_ui_refresh()
            return
        if not self.client.enable_and_wait(timeout=3.0):
            raise RuntimeError("Enable timed out before moving to home.")
        self.client.command_joint_pose(workspace.home.joint_angles)
        self._last_event_text = "Home command sent."
        self._request_ui_refresh()

    def move_observe(self) -> None:
        workspace = self._require_workspace()
        if self.dry_run_var.get():
            self._last_event_text = "Dry-run: would command observe."
            self._request_ui_refresh()
            return
        if not self.client.enable_and_wait(timeout=3.0):
            raise RuntimeError("Enable timed out before moving to observe.")
        self.client.command_joint_pose(workspace.observe.joint_angles)
        self._last_event_text = "Observe command sent."
        self._request_ui_refresh()

    def open_gripper(self) -> None:
        workspace = self._require_workspace()
        self._set_gripper_width(
            self._resolved_open_gripper_width(workspace),
            float(workspace.task_defaults["gripper_force_n"]),
        )

    def close_gripper(self) -> None:
        workspace = self._require_workspace()
        self._set_gripper_width(
            float(workspace.task_defaults["gripper_close_width_m"]),
            float(workspace.task_defaults["gripper_force_n"]),
        )

    def execute_pick_sequence(self) -> None:
        workspace = self._require_workspace()
        if self.selected_plan is None:
            raise RuntimeError("Select a target in the image before executing the pick.")
        for pose_name, tcp_pose in [
            ("pregrasp", self.selected_plan.pregrasp_pose),
            ("grasp", self.selected_plan.grasp_pose),
            ("lift", self.selected_plan.lift_pose),
        ]:
            warning = validate_workspace_point(tuple(tcp_pose[:3]), workspace)
            if warning:
                raise RuntimeError(f"{pose_name} is unsafe: {warning}")

        if not self.dry_run_var.get():
            if not self.client.enable_and_wait(timeout=3.0):
                raise RuntimeError("Enable timed out before starting the pick sequence.")
            self.client.set_speed_percent(int(self.args.speed_percent))
            self.client.set_tcp_offset(workspace.tcp_offset)
        else:
            self._last_event_text = "Dry-run enabled: previewing the pick sequence without robot motion."
            self._request_ui_refresh()

        self._last_event_text = "Running pick sequence..."
        self._request_ui_refresh()

        open_width = self._resolved_open_gripper_width(workspace)
        close_width = float(workspace.task_defaults["gripper_close_width_m"])
        force_n = float(workspace.task_defaults["gripper_force_n"])

        self._last_event_text = "Step 1/8: observe ready."
        self._request_ui_refresh()
        self._last_event_text = "Step 2/8: open gripper."
        self._request_ui_refresh()
        self._set_gripper_width(open_width, force_n)
        self._last_event_text = "Step 3/8: move to pregrasp."
        self._request_ui_refresh()
        self._move_to_tcp_pose("pregrasp", self.selected_plan.pregrasp_pose, linear=False)
        grasp_linear_move = bool(workspace.task_defaults.get("grasp_linear_move", False))
        self._last_event_text = "Step 4/8: descend to grasp." if grasp_linear_move else "Step 4/8: move to grasp."
        self._request_ui_refresh()
        self._move_to_tcp_pose("grasp", self.selected_plan.grasp_pose, linear=grasp_linear_move)
        self._last_event_text = "Step 5/8: close gripper."
        self._request_ui_refresh()
        self._close_gripper_gradually(close_width, force_n)
        self._last_event_text = "Step 6/8: lift object."
        self._request_ui_refresh()
        self._move_to_tcp_pose("lift", self.selected_plan.lift_pose, linear=True)
        place_linear_move = bool(workspace.task_defaults.get("place_linear_move", False))
        self._last_event_text = "Step 7/10: move above drop pose."
        self._request_ui_refresh()
        self._move_to_tcp_pose("drop_prepose", self.selected_plan.drop_prepose, linear=False)
        self._last_event_text = "Step 8/10: descend to drop pose." if place_linear_move else "Step 8/10: move to drop pose."
        self._request_ui_refresh()
        self._move_to_tcp_pose("drop_pose", self.selected_plan.drop_pose, linear=place_linear_move)
        self._last_event_text = "Step 9/10: release object."
        self._request_ui_refresh()
        self._set_gripper_width(open_width, force_n)
        if self.dry_run_var.get():
            self._last_event_text = "Step 10/10: dry-run would return to observe."
            self._request_ui_refresh()
        else:
            self.client.command_joint_pose(workspace.observe.joint_angles)
            self._last_event_text = "Step 10/10: pick sequence completed. Observe command sent."
        self._request_ui_refresh()

    def handle_key_action(self, key: str) -> None:
        if key == "h":
            self.run_background_action(self.move_home)
        elif key == "o":
            self.run_background_action(self.move_observe)
        elif key == "space":
            self.toggle_pause()
        elif key == "g":
            self.run_background_action(self.open_gripper)
        elif key in ("return", "kp_enter", "p"):
            self.run_background_action(self.execute_pick_sequence)
        elif key == "c":
            self.clear_selection()

    def on_close(self) -> None:
        try:
            self._yolo_detector.close()
        finally:
            super().on_close()


def run(args: argparse.Namespace) -> None:
    root = tk.Tk()
    app = ClickPickDemoGuiApp(root, args)
    app.start()
    root.mainloop()
