from __future__ import annotations

import argparse
import tkinter as tk
from tkinter import ttk
from typing import Optional

from piper_app.camera.d405 import D405FrameBundle
from piper_app.perception.yolo import YoloDetection, YoloPrediction
from piper_app.pick_demo.gui import ClickPickDemoGuiApp
from piper_app.pick_demo.task import build_pick_plan, compute_base_point_from_camera, validate_workspace_point


class YoloTargetPickDemoGuiApp(ClickPickDemoGuiApp):
    def __init__(self, root: tk.Tk, args: argparse.Namespace):
        self._available_yolo_labels: list[str] = []
        self._target_object_text = str(getattr(args, "target_label", "")).strip()
        super().__init__(root, args)
        self.root.title("Piper YOLO Target Pick Demo")

    def _build_base_vars(self) -> None:
        super()._build_base_vars()
        self.target_object_var = tk.StringVar(value=self._target_object_text)

    def build_left_panel(self, parent: ttk.Frame) -> None:
        for row in range(7):
            parent.rowconfigure(row, weight=0)
        parent.rowconfigure(6, weight=1)

        self.build_robot_connection_panel(parent, 0, mode_label="Mode: yolo-target-pick")
        self.build_robot_status_panel(
            parent,
            1,
            extra_rows=[
                ("Workspace", self.config_path_var),
                ("Hand-Eye", self.handeye_path_var),
                ("Observe Readiness", self.observe_ready_var),
                ("View Mode", self.view_mode_var),
                ("YOLO", self.yolo_status_var),
                ("Target Object", self.target_object_var),
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
            title="YOLO Pick Status",
        )
        self._build_action_panel(parent, 2)
        self.build_pose_panel(parent, 3, title="Current TCP Pose")
        self.build_joint_panel(parent, 4, title="Current Joint Angles")

    def build_note_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Notes", padding=10)
        frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Label(
            frame,
            text=(
                "Recommended flow: move to Observe, choose a YOLO class from the dropdown or type a recognized "
                "class name, pause the frame, let the demo auto-select the matching bbox center, then run Execute Pick. "
                "If the paused frame does not contain the chosen object, Execute Pick will refuse to run."
            ),
            wraplength=1500,
            justify="left",
        ).grid(sticky="w")

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

        ttk.Label(frame, text="Target Object").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.target_object_combo = ttk.Combobox(frame, textvariable=self.target_object_var, state="normal")
        self.target_object_combo.grid(row=2, column=1, columnspan=3, sticky="ew", pady=(8, 0))
        self.target_object_combo.bind("<<ComboboxSelected>>", self._on_target_object_input)
        self.target_object_combo.bind("<Return>", self._on_target_object_input)
        self.target_object_combo.bind("<FocusOut>", self._on_target_object_input)

        ttk.Label(
            frame,
            text="Flow: choose a class -> pause frame -> auto-select the matching bbox center -> Execute Pick",
            wraplength=520,
            justify="left",
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Checkbutton(frame, text="Dry-run", variable=self.dry_run_var).grid(row=3, column=3, sticky="e", pady=(8, 0))

    def reload_workspace(self) -> None:
        super().reload_workspace()
        self.selected_warning_text = "Workspace loaded. Choose a target object, pause the frame, then execute the pick."
        self._last_event_text = "YOLO target-pick workspace reloaded."
        self.refresh_ui()

    def refresh_custom_ui(self) -> None:
        self._target_object_text = self._current_target_label()
        super().refresh_custom_ui()

    def _normalize_label(self, label: str) -> str:
        return str(label).strip().casefold()

    def _current_prediction(self) -> Optional[YoloPrediction]:
        if self._paused and self._frozen_prediction is not None:
            return self._frozen_prediction
        return self._live_prediction

    def _current_bundle(self) -> Optional[D405FrameBundle]:
        if self._paused and self._frozen_bundle is not None:
            return self._frozen_bundle
        return self._camera_bundle

    def _current_target_label(self) -> str:
        return str(self.target_object_var.get()).strip()

    def _sync_yolo_label_options(self) -> None:
        labels = self._yolo_detector.class_names
        if not labels or labels == self._available_yolo_labels:
            return
        self._available_yolo_labels = list(labels)
        if hasattr(self, "target_object_combo"):
            self.target_object_combo["values"] = self._available_yolo_labels

    def _find_matching_detection(self, prediction: Optional[YoloPrediction], target_label: str) -> Optional[YoloDetection]:
        if prediction is None or not target_label:
            return None
        normalized_target = self._normalize_label(target_label)
        matches = [
            detection for detection in prediction.detections
            if self._normalize_label(detection.label) == normalized_target
        ]
        if not matches:
            return None
        return max(matches, key=lambda detection: detection.confidence)

    def _select_target_from_source_pixel(
        self,
        src_point: tuple[int, int],
        *,
        bundle: D405FrameBundle,
        detection: Optional[YoloDetection],
    ) -> bool:
        if self.workspace is None:
            self.selected_warning_text = "Workspace not loaded."
            self.refresh_ui()
            return False
        if self._measured_tcp_pose is None:
            self.selected_warning_text = "Current TCP pose is unavailable."
            self.refresh_ui()
            return False

        query = self.camera.query_point_from_bundle(bundle, *src_point)
        if not query.valid or query.point_m is None:
            self.selected_warning_text = f"Depth is invalid at pixel {src_point}."
            self.selected_plan = None
            self._selected_pixel = None
            self._selected_detection = detection
            self.refresh_ui()
            return False

        base_point = compute_base_point_from_camera(self._measured_tcp_pose, self.workspace.T_tcp_camera, query.point_m)
        self.selected_plan = build_pick_plan(
            selected_pixel=src_point,
            camera_point_m=query.point_m,
            base_point_m=base_point,
            workspace=self.workspace,
        )
        warning = validate_workspace_point(self.selected_plan.base_point_m, self.workspace)
        self._selected_pixel = src_point
        self._selected_detection = detection
        if detection is not None:
            self._selected_detection_text = f"{detection.label} @ {detection.confidence:.2f} box={detection.bbox_xyxy}"
        else:
            self._selected_detection_text = "No detection selected."
        if warning:
            self.selected_warning_text = warning
        else:
            self.selected_warning_text = "Target object selected from the paused detection frame."
        self._last_event_text = f"Selected paused bbox center pixel {src_point}."
        self._draw_hover_overlay()
        self.refresh_ui()
        return warning is None

    def _auto_select_target_in_current_view(self) -> bool:
        target_label = self._current_target_label()
        prediction = self._current_prediction()
        bundle = self._current_bundle()
        if not target_label or prediction is None or bundle is None:
            return False
        detection = self._find_matching_detection(prediction, target_label)
        if detection is None:
            self.selected_plan = None
            self._selected_pixel = None
            self._selected_detection = None
            self._selected_detection_text = "No detection selected."
            self.selected_warning_text = f"No '{target_label}' detection in the current frame."
            self.refresh_ui()
            return False
        x1, y1, x2, y2 = detection.bbox_xyxy
        center_pixel = ((x1 + x2) // 2, (y1 + y2) // 2)
        return self._select_target_from_source_pixel(center_pixel, bundle=bundle, detection=detection)

    def _on_target_object_input(self, _event=None) -> None:
        target_label = self._current_target_label()
        self._target_object_text = target_label
        if target_label and self._available_yolo_labels:
            valid_labels = {self._normalize_label(label) for label in self._available_yolo_labels}
            if self._normalize_label(target_label) not in valid_labels:
                self.selected_warning_text = f"'{target_label}' is not in the current model label list."
                self.selected_plan = None
                self.refresh_ui()
                return
        if self._paused and target_label:
            if self._auto_select_target_in_current_view():
                self._last_event_text = f"Auto-selected paused target '{target_label}'."
            else:
                self._last_event_text = f"No paused detection found for '{target_label}'."
            self.refresh_ui()

    def _on_canvas_click(self, _event) -> None:
        self._last_event_text = "Manual point clicks are disabled in this demo."
        self.selected_warning_text = "Choose a target object, pause the frame, and let the demo auto-select the bbox center."
        self.refresh_ui()

    def toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self._frozen_bundle = self._camera_bundle
            self._frozen_prediction = self._live_prediction
            target_label = self._current_target_label()
            if target_label:
                if self._auto_select_target_in_current_view():
                    self._last_event_text = f"Paused current frame and auto-selected '{target_label}'."
                else:
                    self._last_event_text = f"Paused current frame. No '{target_label}' detection found."
            else:
                self._last_event_text = "Paused current frame. Choose a target object to auto-select a bbox center."
        else:
            self._frozen_bundle = None
            self._frozen_prediction = None
            self._last_event_text = "Returned to live camera view."
        self.refresh_ui()

    def on_camera_bundle(self, bundle: D405FrameBundle) -> None:
        super().on_camera_bundle(bundle)
        if self._yolo_enabled:
            self._sync_yolo_label_options()

    def execute_pick_sequence(self) -> None:
        target_label = self._current_target_label()
        if not target_label:
            raise RuntimeError("Choose a target object from the dropdown, or type a recognized class name, before executing.")
        if not self._paused:
            raise RuntimeError("Pause the frame first so the target object is locked before executing the pick.")
        if not self._auto_select_target_in_current_view():
            raise RuntimeError(self.selected_warning_text or f"No paused '{target_label}' object is available to pick.")
        super().execute_pick_sequence()


def run(args: argparse.Namespace) -> None:
    root = tk.Tk()
    app = YoloTargetPickDemoGuiApp(root, args)
    app.start()
    root.mainloop()
