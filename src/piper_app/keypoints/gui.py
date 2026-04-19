from __future__ import annotations

import argparse
import math
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from pyAgxArm import ArmModel

from piper_app.calibration.session import display_repo_path
from piper_app.keypoints.store import (
    KeypointRecord,
    build_keypoint_payload,
    find_record,
    load_keypoint_config,
    parse_keypoint_records,
    save_keypoint_config,
)
from piper_app.robot.client import PiperRobotClient
from piper_app.robot.factory import PiperConnectionConfig


class KeypointCaptureGuiApp:
    def __init__(self, root: tk.Tk, args: argparse.Namespace):
        self.root = root
        self.args = args
        self.root.title("Piper Keypoint Capture")
        self.root.geometry("1280x860")
        self.root.minsize(1120, 760)

        self._client = PiperRobotClient(
            PiperConnectionConfig(
                robot=args.robot,
                interface=args.interface,
                channel=args.channel,
                bitrate=args.bitrate,
                firmware_timeout=args.firmware_timeout,
                speed_percent=1,
                tcp_offset=list(args.tcp_offset),
            )
        )
        self._connected = False
        self._busy = False
        self._poll_after_id: Optional[str] = None
        self._measured_tcp_pose: Optional[list[float]] = None
        self._joint_angles: Optional[list[float]] = None
        self._enabled_list = [False] * 6
        self._robot_status_text = "Not connected"
        self._last_event_text = "Ready."

        self._records: list[KeypointRecord] = []
        self._build_vars()
        self._build_ui()
        self._load_existing_config()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.refresh_ui)
        self.root.after(200, lambda: self.run_action(self.connect_robot))

    def _build_vars(self) -> None:
        self.robot_var = tk.StringVar(value=self.args.robot)
        self.interface_var = tk.StringVar(value=self.args.interface)
        self.channel_var = tk.StringVar(value=self.args.channel)
        self.bitrate_var = tk.IntVar(value=self.args.bitrate)
        self.output_path_var = tk.StringVar(value=self.args.output_path)
        self.point_name_var = tk.StringVar(value=self.args.point_names[0] if self.args.point_names else "observe")
        self.point_note_var = tk.StringVar(value=getattr(self.args, "default_note", ""))

        self.connection_var = tk.StringVar(value="Connecting...")
        self.firmware_var = tk.StringVar(value="unknown")
        self.mode_var = tk.StringVar(value=self._robot_status_text)
        self.enabled_var = tk.StringVar(value=str(self._enabled_list))
        self.last_event_var = tk.StringVar(value=self._last_event_text)
        self.record_count_var = tk.StringVar(value="0")
        self.selected_record_var = tk.StringVar(value="No point selected.")
        self.pose_vars = [tk.StringVar(value="--") for _ in range(6)]
        self.joint_rad_vars = [tk.StringVar(value="--") for _ in range(6)]
        self.joint_deg_vars = [tk.StringVar(value="--") for _ in range(6)]

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        outer = ttk.Frame(self.root, padding=12)
        outer.grid(sticky="nsew")
        outer.columnconfigure(0, weight=3)
        outer.columnconfigure(1, weight=2)
        outer.rowconfigure(2, weight=1)

        self._build_top_bar(outer)
        self._build_status_panel(outer)
        self._build_pose_panel(outer)
        self._build_right_panel(outer)
        self._build_notes_panel(outer)

    def _build_top_bar(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Connection", padding=10)
        frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        for idx in range(10):
            frame.columnconfigure(idx, weight=1 if idx in (1, 3, 5) else 0)

        ttk.Label(frame, text="Robot").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            frame,
            textvariable=self.robot_var,
            values=[ArmModel.PIPER, ArmModel.PIPER_H, ArmModel.PIPER_L, ArmModel.PIPER_X],
            state="readonly",
            width=10,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 14))
        ttk.Label(frame, text="Interface").grid(row=0, column=2, sticky="w")
        ttk.Entry(frame, textvariable=self.interface_var, width=12).grid(row=0, column=3, sticky="ew", padx=(6, 14))
        ttk.Label(frame, text="Channel").grid(row=0, column=4, sticky="w")
        ttk.Entry(frame, textvariable=self.channel_var, width=12).grid(row=0, column=5, sticky="ew", padx=(6, 14))
        ttk.Label(frame, text="Bitrate").grid(row=0, column=6, sticky="w")
        ttk.Entry(frame, textvariable=self.bitrate_var, width=12).grid(row=0, column=7, sticky="ew", padx=(6, 14))
        ttk.Label(frame, text="Mode: capture only").grid(row=0, column=8, sticky="w")

        buttons = ttk.Frame(frame)
        buttons.grid(row=0, column=9, sticky="e")
        ttk.Button(buttons, text="Reconnect", command=lambda: self.run_action(self.reconnect_robot)).grid(
            row=0, column=0, padx=(0, 6)
        )
        ttk.Button(buttons, text="Disconnect", command=lambda: self.run_action(self.disconnect_robot)).grid(
            row=0, column=1
        )

    def _build_status_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Robot Status", padding=10)
        frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        rows = [
            ("Connection", self.connection_var),
            ("Firmware", self.firmware_var),
            ("Mode", self.mode_var),
            ("Joint Enabled", self.enabled_var),
            ("Output", self.output_path_var),
            ("Saved Points", self.record_count_var),
            ("Last Event", self.last_event_var),
        ]
        for row_idx, (label, variable) in enumerate(rows):
            ttk.Label(frame, text=label).grid(row=row_idx, column=0, sticky="nw", pady=3)
            ttk.Label(frame, textvariable=variable, wraplength=540, justify="left").grid(
                row=row_idx, column=1, sticky="w", pady=3
            )

    def _build_pose_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Current Robot Pose", padding=10)
        frame.grid(row=2, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)
        ttk.Label(frame, text="Axis").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text="TCP Pose").grid(row=0, column=1, sticky="w")
        ttk.Label(frame, text="Joint").grid(row=0, column=2, sticky="w")
        for idx, axis_name in enumerate(["x", "y", "z", "roll", "pitch", "yaw"], start=1):
            ttk.Label(frame, text=axis_name).grid(row=idx, column=0, sticky="w", pady=2)
            ttk.Label(frame, textvariable=self.pose_vars[idx - 1]).grid(row=idx, column=1, sticky="w", pady=2)
            joint_text = ttk.Frame(frame)
            joint_text.grid(row=idx, column=2, sticky="w", pady=2)
            ttk.Label(joint_text, textvariable=self.joint_rad_vars[idx - 1]).grid(row=0, column=0, sticky="w")
            ttk.Label(joint_text, text=" / ").grid(row=0, column=1)
            ttk.Label(joint_text, textvariable=self.joint_deg_vars[idx - 1]).grid(row=0, column=2, sticky="w")

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=1, column=1, rowspan=2, sticky="nsew", pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        capture = ttk.LabelFrame(frame, text="Capture Current Point", padding=10)
        capture.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        capture.columnconfigure(1, weight=1)
        ttk.Label(capture, text="Point Name").grid(row=0, column=0, sticky="w")
        self.point_combo = ttk.Combobox(
            capture,
            textvariable=self.point_name_var,
            values=list(self.args.point_names),
        )
        self.point_combo.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(capture, text="Note").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(capture, textvariable=self.point_note_var).grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
        button_row = ttk.Frame(capture)
        button_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        ttk.Button(button_row, text="Capture / Update", command=lambda: self.run_action(self.capture_current_point)).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(button_row, text="Save YAML", command=lambda: self.run_action(self.save_points)).grid(
            row=0, column=1, sticky="ew"
        )

        quick = ttk.LabelFrame(frame, text="Quick Names", padding=10)
        quick.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        quick.columnconfigure(0, weight=1)
        quick.columnconfigure(1, weight=1)
        quick.columnconfigure(2, weight=1)
        for idx, name in enumerate(self.args.point_names[:9]):
            ttk.Button(
                quick,
                text=name,
                command=lambda value=name: self._choose_name(value),
            ).grid(row=idx // 3, column=idx % 3, sticky="ew", padx=(0, 6), pady=(0, 6))

        saved = ttk.LabelFrame(frame, text="Saved Points", padding=10)
        saved.grid(row=2, column=0, sticky="nsew")
        saved.columnconfigure(0, weight=1)
        saved.rowconfigure(0, weight=1)
        self.points_listbox = tk.Listbox(saved, exportselection=False, height=12)
        self.points_listbox.grid(row=0, column=0, sticky="nsew")
        self.points_listbox.bind("<<ListboxSelect>>", self._on_select_record)
        scrollbar = ttk.Scrollbar(saved, orient="vertical", command=self.points_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.points_listbox.configure(yscrollcommand=scrollbar.set)

        actions = ttk.Frame(saved)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        actions.columnconfigure(2, weight=1)
        ttk.Button(actions, text="Delete Selected", command=lambda: self.run_action(self.delete_selected_record)).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(actions, text="Reload YAML", command=lambda: self.run_action(self.reload_points)).grid(
            row=0, column=1, sticky="ew", padx=(0, 6)
        )
        ttk.Button(actions, text="Clear Note", command=self._clear_note).grid(row=0, column=2, sticky="ew")

        selected = ttk.LabelFrame(frame, text="Selected Point", padding=10)
        selected.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(selected, textvariable=self.selected_record_var, wraplength=420, justify="left").grid(sticky="w")

    def _build_notes_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Notes", padding=10)
        frame.grid(row=3, column=0, columnspan=2, sticky="ew")
        ttk.Label(
            frame,
            text=(
                "This window does not move the robot. Use it to capture key poses such as home, observe, and "
                "drop_pose into a YAML config for later pick-and-place scripts."
            ),
            wraplength=1180,
            justify="left",
        ).grid(sticky="w")

    def _choose_name(self, value: str) -> None:
        self.point_name_var.set(value)

    def _clear_note(self) -> None:
        self.point_note_var.set("")

    def run_action(self, callback) -> None:
        if self._busy:
            return
        self._busy = True
        try:
            callback()
        except Exception as exc:
            self._connected = False
            self._robot_status_text = f"Error: {type(exc).__name__}"
            self._last_event_text = f"{type(exc).__name__}: {exc}"
        finally:
            self._busy = False
            self.refresh_ui()

    def connect_robot(self) -> None:
        self.connection_var.set("Connecting...")
        self._last_event_text = "Connecting to Piper keypoint capture..."
        self._client.config.robot = self.robot_var.get()
        self._client.config.interface = self.interface_var.get()
        self._client.config.channel = self.channel_var.get()
        self._client.config.bitrate = int(self.bitrate_var.get())
        self._client.config.firmware_timeout = float(self.args.firmware_timeout)
        self._client.connect(configure_robot=False, init_gripper=False)
        self._connected = True
        self._last_event_text = "Connected. Ready to capture keypoints."
        self._poll_data()

    def disconnect_robot(self) -> None:
        self._client.disconnect()
        self._connected = False
        self._robot_status_text = "Disconnected"
        self._last_event_text = "Disconnected."
        self._measured_tcp_pose = None
        self._joint_angles = None
        self._enabled_list = [False] * 6

    def reconnect_robot(self) -> None:
        self.disconnect_robot()
        time.sleep(0.1)
        self.connect_robot()

    def _poll_data(self) -> None:
        if not self._connected:
            return
        status = self._client.get_arm_status()
        if status is not None:
            self._robot_status_text = (
                f"{status.msg.arm_status} | {status.msg.mode_feedback} | {status.msg.motion_status}"
            )
        measured_pose = self._client.get_tcp_pose()
        if measured_pose is not None:
            self._measured_tcp_pose = measured_pose
        joint_angles = self._client.get_joint_angles()
        if joint_angles is not None:
            self._joint_angles = joint_angles
        self._enabled_list = self._client.get_enabled_list()

    def capture_current_point(self) -> None:
        name = self.point_name_var.get().strip()
        if not name:
            raise RuntimeError("Point name cannot be empty.")
        if self._measured_tcp_pose is None or self._joint_angles is None:
            raise RuntimeError("Robot pose is unavailable. Wait for a fresh status update.")
        record = KeypointRecord(
            name=name,
            tcp_pose=[float(value) for value in self._measured_tcp_pose],
            joint_angles=[float(value) for value in self._joint_angles],
            note=self.point_note_var.get().strip(),
            captured_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        existing = find_record(self._records, name)
        if existing is None:
            self._records.append(record)
            self._last_event_text = f"Captured new point: {name}"
        else:
            self._records = [record if item.name == name else item for item in self._records]
            self._last_event_text = f"Updated point: {name}"
        self._records.sort(key=lambda item: item.name)
        self._refresh_points_list()

    def save_points(self) -> None:
        payload = build_keypoint_payload(
            robot=self.robot_var.get(),
            interface=self.interface_var.get(),
            channel=self.channel_var.get(),
            bitrate=int(self.bitrate_var.get()),
            tcp_offset=list(self.args.tcp_offset),
            task_defaults=self.args.task_defaults,
            records=sorted(self._records, key=lambda item: item.name),
        )
        path = save_keypoint_config(self.output_path_var.get(), payload)
        self._last_event_text = f"Saved {len(self._records)} keypoints to {display_repo_path(path)}"

    def reload_points(self) -> None:
        self._load_existing_config()
        self._last_event_text = f"Reloaded {len(self._records)} keypoints from {self.output_path_var.get()}"

    def delete_selected_record(self) -> None:
        selection = self.points_listbox.curselection()
        if not selection:
            messagebox.showinfo("Delete Point", "Select a point to delete.")
            return
        index = int(selection[0])
        name = self.points_listbox.get(index)
        target = find_record(self._records, name)
        if target is None:
            return
        self._records = [record for record in self._records if record.name != name]
        self._refresh_points_list()
        self.selected_record_var.set("No point selected.")
        self._last_event_text = f"Deleted point: {name}"

    def _load_existing_config(self) -> None:
        payload = load_keypoint_config(self.output_path_var.get())
        self._records = sorted(parse_keypoint_records(payload), key=lambda item: item.name)
        self._refresh_points_list()

    def _refresh_points_list(self) -> None:
        self.points_listbox.delete(0, tk.END)
        for record in sorted(self._records, key=lambda item: item.name):
            self.points_listbox.insert(tk.END, record.name)

    def _on_select_record(self, _event=None) -> None:
        selection = self.points_listbox.curselection()
        if not selection:
            self.selected_record_var.set("No point selected.")
            return
        index = int(selection[0])
        name = self.points_listbox.get(index)
        record = find_record(self._records, name)
        if record is None:
            return
        self.point_name_var.set(record.name)
        self.point_note_var.set(record.note)
        pose_text = ", ".join(f"{value:.4f}" for value in record.tcp_pose[:3])
        self.selected_record_var.set(
            f"{record.name}: tcp=[{pose_text}, ...], captured_at={record.captured_at}, note={record.note or '--'}"
        )

    def refresh_ui(self) -> None:
        self.connection_var.set("Connected" if self._connected else "Disconnected")
        self.firmware_var.set(self._client.software_version if self._connected else "unknown")
        self.mode_var.set(self._robot_status_text)
        self.enabled_var.set(str(self._enabled_list))
        self.last_event_var.set(self._last_event_text)
        self.record_count_var.set(str(len(self._records)))

        pose = self._measured_tcp_pose
        joints = self._joint_angles
        for idx in range(6):
            if pose is None:
                self.pose_vars[idx].set("--")
            else:
                value = pose[idx]
                self.pose_vars[idx].set(f"{value:.4f} m" if idx < 3 else f"{value:.4f} rad ({math.degrees(value):.1f} deg)")
            if joints is None:
                self.joint_rad_vars[idx].set("--")
                self.joint_deg_vars[idx].set("--")
            else:
                value = joints[idx]
                self.joint_rad_vars[idx].set(f"{value:.4f} rad")
                self.joint_deg_vars[idx].set(f"{math.degrees(value):.2f} deg")

        self.root.after(100, self.refresh_ui)

    def _poll_once(self) -> None:
        if self._connected and not self._busy:
            try:
                self._poll_data()
            except Exception as exc:
                self._connected = False
                self._robot_status_text = f"Read error: {type(exc).__name__}"
                self._last_event_text = f"Polling stopped: {type(exc).__name__}: {exc}"
        self._poll_after_id = self.root.after(
            int(max(0.05, float(getattr(self.args, "poll_interval_s", 0.2))) * 1000),
            self._poll_once,
        )

    def on_close(self) -> None:
        if self._poll_after_id is not None:
            self.root.after_cancel(self._poll_after_id)
            self._poll_after_id = None
        try:
            self._client.disconnect()
        finally:
            self.root.destroy()


def run(args: argparse.Namespace) -> None:
    root = tk.Tk()
    app = KeypointCaptureGuiApp(root, args)
    app._poll_once()
    root.mainloop()
