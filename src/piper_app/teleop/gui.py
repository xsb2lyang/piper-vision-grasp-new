import argparse
import math
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import List, Optional, Tuple

from pyAgxArm import ArmModel

from piper_app.robot.client import PiperRobotClient
from piper_app.robot.factory import PiperConnectionConfig
from piper_app.robot.safety import clamp_tcp_pose
from piper_app.teleop.gripper import (
    DEFAULT_GRIPPER_FORCE_N,
    DEFAULT_GRIPPER_MAX_RANGE_M,
    DEFAULT_GRIPPER_STEP_M,
    build_gripper_snapshot,
)


DEFAULT_POS_STEP_M = 0.005
DEFAULT_ROT_STEP_DEG = 2.0
DEFAULT_SPEED_PERCENT = 10
DEFAULT_FW_TIMEOUT = 5.0
DEFAULT_POLL_INTERVAL_S = 0.2
DEFAULT_CONTINUOUS_INTERVAL_MS = 120
DEFAULT_GRIPPER_MAX_RANGE_M = 0.07


class TeleopGuiApp:
    def __init__(self, root: tk.Tk, args: argparse.Namespace):
        self.root = root
        self.args = args
        self.root.title("Piper TCP Teleop GUI")
        self.root.geometry("1120x780")
        self.root.minsize(980, 720)

        self._client = PiperRobotClient(
            PiperConnectionConfig(
                robot=args.robot,
                interface=args.interface,
                channel=args.channel,
                bitrate=args.bitrate,
                firmware_timeout=args.firmware_timeout,
                speed_percent=args.speed_percent,
                tcp_offset=list(args.tcp_offset),
            )
        )
        self._robot = None
        self._gripper = None
        self._poll_after_id: Optional[str] = None
        self._continuous_after_id: Optional[str] = None
        self._connected = False
        self._control_enabled = False
        self._busy = False

        self._firmware_info = {}
        self._measured_tcp_pose: Optional[List[float]] = None
        self._target_tcp_pose: Optional[List[float]] = None
        self._enabled_list = [False] * 6
        self._robot_status_text = "Not connected"
        self._last_action = "Ready."
        self._gripper_status_text = "Not connected"
        self._gripper_value: Optional[float] = None
        self._gripper_force_feedback: Optional[float] = None
        self._gripper_mode = "width"
        self._gripper_max_range_m = DEFAULT_GRIPPER_MAX_RANGE_M
        self._active_motion: Optional[Tuple[int, float]] = None
        self._active_gripper_direction: float = 0.0
        self._gripper_scale: Optional[ttk.Scale] = None
        self._gripper_target_initialized = False

        self._build_vars()
        self._build_ui()
        self._bind_keys()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.refresh_ui)
        self.root.after(200, lambda: self.run_async(self.connect_robot))

    def _build_vars(self) -> None:
        self.robot_var = tk.StringVar(value=self.args.robot)
        self.interface_var = tk.StringVar(value=self.args.interface)
        self.channel_var = tk.StringVar(value=self.args.channel)
        self.bitrate_var = tk.IntVar(value=self.args.bitrate)
        self.speed_var = tk.IntVar(value=max(1, min(100, self.args.speed_percent)))
        self.pos_step_var = tk.DoubleVar(value=max(0.0005, self.args.pos_step))
        self.rot_step_deg_var = tk.DoubleVar(value=max(0.1, self.args.rot_step_deg))
        self.dry_run_var = tk.BooleanVar(value=self.args.dry_run)
        self.connection_var = tk.StringVar(value="Connecting...")
        self.firmware_var = tk.StringVar(value="unknown")
        self.mode_var = tk.StringVar(value="Not connected")
        self.enabled_var = tk.StringVar(value="[False, False, False, False, False, False]")
        self.last_action_var = tk.StringVar(value=self._last_action)
        self.gripper_status_var = tk.StringVar(value="Not connected")
        self.gripper_mode_var = tk.StringVar(value="width")
        self.gripper_value_var = tk.StringVar(value="--")
        self.gripper_force_feedback_var = tk.StringVar(value="--")
        self.gripper_target_var = tk.DoubleVar(value=0.0)
        self.gripper_step_var = tk.DoubleVar(
            value=max(0.001, getattr(self.args, "gripper_step", DEFAULT_GRIPPER_STEP_M))
        )
        self.gripper_force_var = tk.DoubleVar(
            value=max(0.1, getattr(self.args, "gripper_force", DEFAULT_GRIPPER_FORCE_N))
        )
        self.gripper_max_range_var = tk.DoubleVar(value=DEFAULT_GRIPPER_MAX_RANGE_M)

        self.measured_pose_vars = [tk.StringVar(value="--") for _ in range(6)]
        self.target_pose_vars = [tk.StringVar(value="--") for _ in range(6)]
        self.tcp_offset_vars = [
            tk.DoubleVar(value=float(v)) for v in self.args.tcp_offset
        ]

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        outer = ttk.Frame(self.root, padding=12)
        outer.grid(sticky="nsew")
        outer.columnconfigure(0, weight=3)
        outer.columnconfigure(1, weight=2)
        outer.rowconfigure(3, weight=1)

        self._build_top_bar(outer)
        self._build_status_panel(outer)
        self._build_pose_panel(outer)
        self._build_control_panel(outer)
        self._build_gripper_panel(outer)
        self._build_help_panel(outer)

    def _build_top_bar(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Connection", padding=10)
        frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        for idx in range(10):
            frame.columnconfigure(idx, weight=1 if idx in (1, 3, 5) else 0)

        ttk.Label(frame, text="Robot").grid(row=0, column=0, sticky="w")
        robot_combo = ttk.Combobox(
            frame,
            textvariable=self.robot_var,
            values=[
                ArmModel.PIPER,
                ArmModel.PIPER_H,
                ArmModel.PIPER_L,
                ArmModel.PIPER_X,
            ],
            state="readonly",
            width=10,
        )
        robot_combo.grid(row=0, column=1, sticky="ew", padx=(6, 14))

        ttk.Label(frame, text="Interface").grid(row=0, column=2, sticky="w")
        ttk.Entry(frame, textvariable=self.interface_var, width=12).grid(
            row=0, column=3, sticky="ew", padx=(6, 14)
        )

        ttk.Label(frame, text="Channel").grid(row=0, column=4, sticky="w")
        ttk.Entry(frame, textvariable=self.channel_var, width=12).grid(
            row=0, column=5, sticky="ew", padx=(6, 14)
        )

        ttk.Label(frame, text="Bitrate").grid(row=0, column=6, sticky="w")
        ttk.Entry(frame, textvariable=self.bitrate_var, width=12).grid(
            row=0, column=7, sticky="ew", padx=(6, 14)
        )

        ttk.Checkbutton(frame, text="Dry Run", variable=self.dry_run_var).grid(
            row=0, column=8, sticky="w"
        )

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=0, column=9, sticky="e")
        ttk.Button(
            button_frame,
            text="Reconnect",
            command=lambda: self.run_async(self.reconnect_robot),
        ).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(
            button_frame,
            text="Disconnect",
            command=lambda: self.run_async(self.disconnect_robot),
        ).grid(row=0, column=1)

    def _build_status_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Robot Status", padding=10)
        frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        frame.columnconfigure(1, weight=1)

        status_rows = [
            ("Connection", self.connection_var),
            ("Firmware", self.firmware_var),
            ("Mode", self.mode_var),
            ("Joint Enabled", self.enabled_var),
            ("Gripper", self.gripper_status_var),
            ("Last Action", self.last_action_var),
        ]
        for row_idx, (label, variable) in enumerate(status_rows):
            ttk.Label(frame, text=label).grid(row=row_idx, column=0, sticky="nw", pady=3)
            ttk.Label(
                frame,
                textvariable=variable,
                wraplength=600,
                justify="left",
            ).grid(row=row_idx, column=1, sticky="w", pady=3)

    def _build_pose_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="TCP Pose", padding=10)
        frame.grid(row=2, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        for col in range(3):
            frame.columnconfigure(col, weight=1)

        ttk.Label(frame, text="Axis").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text="Measured").grid(row=0, column=1, sticky="w")
        ttk.Label(frame, text="Target").grid(row=0, column=2, sticky="w")

        axis_names = ["x", "y", "z", "roll", "pitch", "yaw"]
        for row_idx, axis_name in enumerate(axis_names, start=1):
            ttk.Label(frame, text=axis_name).grid(row=row_idx, column=0, sticky="w", pady=2)
            ttk.Label(frame, textvariable=self.measured_pose_vars[row_idx - 1]).grid(
                row=row_idx, column=1, sticky="w", pady=2
            )
            ttk.Label(frame, textvariable=self.target_pose_vars[row_idx - 1]).grid(
                row=row_idx, column=2, sticky="w", pady=2
            )

    def _build_control_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Teleop Controls", padding=10)
        frame.grid(row=1, column=1, rowspan=2, sticky="nsew", pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        settings = ttk.LabelFrame(frame, text="Motion Settings", padding=10)
        settings.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        for col in range(4):
            settings.columnconfigure(col, weight=1)

        ttk.Label(settings, text="Speed %").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            settings,
            from_=1,
            to=100,
            increment=1,
            textvariable=self.speed_var,
            width=8,
            command=lambda: self.run_async(self.apply_speed_percent),
        ).grid(row=0, column=1, sticky="ew", padx=(6, 12))
        ttk.Button(
            settings,
            text="Apply Speed",
            command=lambda: self.run_async(self.apply_speed_percent),
        ).grid(row=0, column=2, columnspan=2, sticky="ew")

        ttk.Label(settings, text="Pos Step (m)").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(
            settings,
            from_=0.0005,
            to=0.05,
            increment=0.0005,
            textvariable=self.pos_step_var,
            width=8,
        ).grid(row=1, column=1, sticky="ew", padx=(6, 12), pady=(8, 0))

        ttk.Label(settings, text="Rot Step (deg)").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Spinbox(
            settings,
            from_=0.1,
            to=30.0,
            increment=0.1,
            textvariable=self.rot_step_deg_var,
            width=8,
        ).grid(row=1, column=3, sticky="ew", pady=(8, 0))

        offset_frame = ttk.LabelFrame(frame, text="TCP Offset", padding=10)
        offset_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        labels = ["x", "y", "z", "roll", "pitch", "yaw"]
        for col in range(6):
            offset_frame.columnconfigure(col, weight=1)
            ttk.Label(offset_frame, text=labels[col]).grid(row=0, column=col, sticky="w")
            ttk.Entry(
                offset_frame,
                textvariable=self.tcp_offset_vars[col],
                width=9,
            ).grid(row=1, column=col, sticky="ew", padx=(0, 6), pady=(4, 8))
        ttk.Button(
            offset_frame,
            text="Apply TCP Offset",
            command=lambda: self.run_async(self.apply_tcp_offset),
        ).grid(row=2, column=0, columnspan=6, sticky="ew")

        safety = ttk.LabelFrame(frame, text="Safety", padding=10)
        safety.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        safety.columnconfigure(0, weight=1)
        safety.columnconfigure(1, weight=1)
        safety.columnconfigure(2, weight=1)
        ttk.Button(safety, text="Enable", command=lambda: self.run_async(self.enable_control)).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(
            safety,
            text="Disable",
            command=lambda: self.run_async(self.disable_control),
        ).grid(row=0, column=1, sticky="ew", padx=(0, 6))
        ttk.Button(
            safety,
            text="E-Stop",
            command=lambda: self.run_async(self.electronic_emergency_stop),
        ).grid(row=0, column=2, sticky="ew")
        ttk.Button(
            safety,
            text="Sync Target To Current",
            command=lambda: self.run_async(self.sync_target_to_current),
        ).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))

        motion = ttk.LabelFrame(frame, text="Hold-To-Move Buttons", padding=10)
        motion.grid(row=3, column=0, columnspan=2, sticky="nsew")
        for col in range(4):
            motion.columnconfigure(col, weight=1)

        motion_buttons = [
            ("X -", 0, 0, 0, -1.0),
            ("X +", 0, 1, 0, 1.0),
            ("Y -", 0, 2, 1, -1.0),
            ("Y +", 0, 3, 1, 1.0),
            ("Z -", 1, 0, 2, -1.0),
            ("Z +", 1, 1, 2, 1.0),
            ("Roll -", 1, 2, 3, -1.0),
            ("Roll +", 1, 3, 3, 1.0),
            ("Pitch -", 2, 0, 4, -1.0),
            ("Pitch +", 2, 1, 4, 1.0),
            ("Yaw -", 2, 2, 5, -1.0),
            ("Yaw +", 2, 3, 5, 1.0),
        ]
        for text, row, col, axis_index, direction in motion_buttons:
            btn = ttk.Button(motion, text=text)
            btn.grid(row=row, column=col, sticky="ew", padx=4, pady=4)
            self._bind_hold_motion_button(btn, axis_index, direction)

    def _build_gripper_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Gripper", padding=10)
        frame.grid(row=3, column=1, sticky="nsew", pady=(0, 10))
        for col in range(4):
            frame.columnconfigure(col, weight=1)

        ttk.Label(frame, text="Mode").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, textvariable=self.gripper_mode_var).grid(row=0, column=1, sticky="w")
        ttk.Label(frame, text="Value").grid(row=0, column=2, sticky="w")
        ttk.Label(frame, textvariable=self.gripper_value_var).grid(row=0, column=3, sticky="w")

        ttk.Label(frame, text="Force Feedback").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(frame, textvariable=self.gripper_force_feedback_var).grid(
            row=1, column=1, sticky="w", pady=(6, 0)
        )
        ttk.Label(frame, text="Max Range (m)").grid(row=1, column=2, sticky="w", pady=(6, 0))
        ttk.Label(frame, textvariable=self.gripper_max_range_var).grid(
            row=1, column=3, sticky="w", pady=(6, 0)
        )

        ttk.Label(frame, text="Status").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Label(frame, textvariable=self.gripper_status_var, wraplength=320, justify="left").grid(
            row=2, column=1, columnspan=3, sticky="w", pady=(6, 0)
        )

        ttk.Label(frame, text="Target Width (m)").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self._gripper_scale = ttk.Scale(
            frame,
            from_=0.0,
            to=max(0.001, self.gripper_max_range_var.get()),
            variable=self.gripper_target_var,
            orient="horizontal",
        )
        self._gripper_scale.grid(
            row=3, column=1, columnspan=2, sticky="ew", padx=(6, 6), pady=(10, 0)
        )
        ttk.Entry(frame, textvariable=self.gripper_target_var, width=10).grid(
            row=3, column=3, sticky="ew", pady=(10, 0)
        )

        ttk.Label(frame, text="Step (m)").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(
            frame,
            from_=0.001,
            to=0.05,
            increment=0.001,
            textvariable=self.gripper_step_var,
            width=8,
        ).grid(row=4, column=1, sticky="ew", padx=(6, 12), pady=(8, 0))
        ttk.Label(frame, text="Force (N)").grid(row=4, column=2, sticky="w", pady=(8, 0))
        ttk.Spinbox(
            frame,
            from_=0.1,
            to=3.0,
            increment=0.1,
            textvariable=self.gripper_force_var,
            width=8,
        ).grid(row=4, column=3, sticky="ew", pady=(8, 0))

        buttons = ttk.Frame(frame)
        buttons.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        for col in range(3):
            buttons.columnconfigure(col, weight=1)

        ttk.Button(
            buttons,
            text="Open Step",
            command=lambda: self.run_async(self.step_gripper, 1.0),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ttk.Button(
            buttons,
            text="Close Step",
            command=lambda: self.run_async(self.step_gripper, -1.0),
        ).grid(row=0, column=1, sticky="ew", padx=(0, 6))

        ttk.Button(
            buttons,
            text="Set Width",
            command=lambda: self.run_async(self.move_gripper_to_target),
        ).grid(row=0, column=2, sticky="ew")

        hold_open_btn = ttk.Button(buttons, text="Hold Open")
        hold_open_btn.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(6, 0))
        self._bind_hold_gripper_button(hold_open_btn, 1.0)

        hold_close_btn = ttk.Button(buttons, text="Hold Close")
        hold_close_btn.grid(row=1, column=1, sticky="ew", padx=(0, 6), pady=(6, 0))
        self._bind_hold_gripper_button(hold_close_btn, -1.0)

        ttk.Button(
            buttons,
            text="Sync Target",
            command=lambda: self.run_async(self.sync_gripper_target_to_current),
        ).grid(row=1, column=2, sticky="ew", pady=(6, 0))

        ttk.Button(
            buttons,
            text="Release Driver",
            command=lambda: self.run_async(self.prepare_gripper_zeroing),
        ).grid(row=2, column=0, sticky="ew", padx=(0, 6), pady=(6, 0))

        ttk.Button(
            buttons,
            text="Set Zero",
            command=lambda: self.run_async(self.calibrate_gripper_zero),
        ).grid(row=2, column=1, sticky="ew", padx=(0, 6), pady=(6, 0))

        ttk.Button(
            buttons,
            text="Stop Hold",
            command=self.stop_continuous_action,
        ).grid(row=2, column=2, sticky="ew", pady=(6, 0))

    def _build_help_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Keyboard Shortcuts", padding=10)
        frame.grid(row=3, column=0, sticky="nsew", padx=(0, 10))
        message = (
            "Movement hold: w/s x+/-   a/d y+/-   r/f z+/-\n"
            "Rotation hold: u/o roll-/+   i/k pitch+/-   j/l yaw-/+\n"
            "Safety: e enable   n disable   t sync target   b e-stop\n"
            "Gripper: comma/period hold close/open   use Open Step/Close Step for single-step\n"
            "Zeroing: click Release Driver, manually squeeze gripper fully closed, then click Set Zero\n"
            "The GUI starts in a safe blocked state. Press Enable before motion."
        )
        ttk.Label(frame, text=message, justify="left").grid(row=0, column=0, sticky="w")

    def _bind_keys(self) -> None:
        movement_bindings = {
            "w": (0, 1.0),
            "s": (0, -1.0),
            "a": (1, 1.0),
            "d": (1, -1.0),
            "r": (2, 1.0),
            "f": (2, -1.0),
            "u": (3, -1.0),
            "o": (3, 1.0),
            "i": (4, 1.0),
            "k": (4, -1.0),
            "j": (5, -1.0),
            "l": (5, 1.0),
        }
        for key, (axis_index, direction) in movement_bindings.items():
            self.root.bind_all(
                f"<KeyPress-{key}>",
                lambda _event, axis=axis_index, sign=direction: self.start_continuous_motion(axis, sign),
            )
            self.root.bind_all(
                f"<KeyRelease-{key}>",
                lambda _event, axis=axis_index, sign=direction: self.stop_continuous_motion(axis, sign),
            )

        gripper_bindings = {
            "comma": -1.0,
            "period": 1.0,
        }
        for key, direction in gripper_bindings.items():
            self.root.bind_all(
                f"<KeyPress-{key}>",
                lambda _event, sign=direction: self.start_continuous_gripper(sign),
            )
            self.root.bind_all(
                f"<KeyRelease-{key}>",
                lambda _event, sign=direction: self.stop_continuous_gripper(sign),
            )

        command_bindings = {
            "e": lambda: self.run_async(self.enable_control),
            "n": lambda: self.run_async(self.disable_control),
            "t": lambda: self.run_async(self.sync_target_to_current),
            "b": lambda: self.run_async(self.electronic_emergency_stop),
        }
        for key, callback in command_bindings.items():
            self.root.bind_all(f"<KeyPress-{key}>", lambda _event, fn=callback: fn())

    def _bind_hold_motion_button(
        self,
        button: ttk.Button,
        axis_index: int,
        direction: float,
    ) -> None:
        button.bind(
            "<ButtonPress-1>",
            lambda _event, axis=axis_index, sign=direction: self.start_continuous_motion(axis, sign),
        )
        button.bind(
            "<ButtonRelease-1>",
            lambda _event, axis=axis_index, sign=direction: self.stop_continuous_motion(axis, sign),
        )
        button.bind("<Leave>", lambda _event: self.stop_continuous_action())

    def _bind_hold_gripper_button(self, button: ttk.Button, direction: float) -> None:
        button.bind(
            "<ButtonPress-1>",
            lambda _event, sign=direction: self.start_continuous_gripper(sign),
        )
        button.bind(
            "<ButtonRelease-1>",
            lambda _event, sign=direction: self.stop_continuous_gripper(sign),
        )
        button.bind("<Leave>", lambda _event: self.stop_continuous_action())

    def set_last_action(self, text: str) -> None:
        self._last_action = text

    def run_async(self, func, *args) -> None:
        if self._busy:
            self.set_last_action("Busy. Wait for the current action to finish.")
            return
        self._busy = True
        try:
            func(*args)
        except Exception as exc:
            self.set_last_action(f"{type(exc).__name__}: {exc}")
        finally:
            self._busy = False

    def _start_poll_thread(self) -> None:
        if self._poll_after_id is not None:
            return
        self._poll_once()

    def _poll_once(self) -> None:
        if self._connected and self._robot is not None:
            try:
                measured = self._client.get_tcp_pose()
                if measured is not None:
                    self._measured_tcp_pose = measured
                status = self._client.get_arm_status()
                if status is not None:
                    self._robot_status_text = (
                        f"{status.msg.arm_status} | "
                        f"{status.msg.mode_feedback} | "
                        f"{status.msg.motion_status}"
                    )
                self._enabled_list = self._client.get_enabled_list()
                if self._gripper is not None:
                    gs = self._client.get_gripper_status()
                    if gs is not None:
                        snapshot = build_gripper_snapshot(gs)
                        self._gripper_value = snapshot.value
                        self._gripper_force_feedback = snapshot.force_feedback
                        self._gripper_mode = snapshot.mode
                        self._gripper_status_text = snapshot.status_text
                        if not self._gripper_target_initialized:
                            self.gripper_target_var.set(
                                min(max(0.0, snapshot.value or 0.0), self._gripper_max_range_m)
                            )
                            self._gripper_target_initialized = True
            except Exception as exc:
                self.stop_continuous_action()
                self._robot_status_text = f"Read error: {type(exc).__name__}"
                self.set_last_action(f"Polling stopped: {type(exc).__name__}: {exc}")
                self._connected = False
        self._poll_after_id = self.root.after(
            int(max(0.05, getattr(self.args, "poll_interval_s", DEFAULT_POLL_INTERVAL_S)) * 1000),
            self._poll_once,
        )

    def connect_robot(self) -> None:
        self.connection_var.set("Connecting...")
        self.set_last_action("Connecting to Piper...")
        self._client.config.robot = self.robot_var.get()
        self._client.config.interface = self.interface_var.get()
        self._client.config.channel = self.channel_var.get()
        self._client.config.bitrate = int(self.bitrate_var.get())
        self._client.config.firmware_timeout = float(self.args.firmware_timeout)
        self._client.config.speed_percent = int(self.speed_var.get())
        self._client.config.tcp_offset = [var.get() for var in self.tcp_offset_vars]
        self._client.connect()
        self._robot = self._client.robot
        self._gripper = self._client.gripper
        self._firmware_info = self._client.firmware_info
        self.firmware_var.set(self._client.software_version)
        self._connected = True
        self._control_enabled = False
        measured_tcp = self._client.get_tcp_pose()
        if measured_tcp is None:
            raise RuntimeError("Failed to read current TCP pose after connect.")
        self._measured_tcp_pose = measured_tcp
        self._target_tcp_pose = clamp_tcp_pose(measured_tcp)
        self._enabled_list = self._client.get_enabled_list()
        status = self._client.get_arm_status()
        if status is not None:
            self._robot_status_text = (
                f"{status.msg.arm_status} | "
                f"{status.msg.mode_feedback} | "
                f"{status.msg.motion_status}"
            )
        if self._gripper is not None:
            teaching = self._client.get_gripper_teaching_pendant_param(timeout=0.5, min_interval=0.0)
            if teaching is not None and teaching.msg.max_range_config > 0.0:
                self._gripper_max_range_m = teaching.msg.max_range_config
            else:
                self._gripper_max_range_m = DEFAULT_GRIPPER_MAX_RANGE_M
            self.gripper_max_range_var.set(self._gripper_max_range_m)
            self.gripper_target_var.set(
                min(max(0.0, self.gripper_target_var.get()), self._gripper_max_range_m)
            )
            if self._gripper_scale is not None:
                self._gripper_scale.configure(to=max(0.001, self._gripper_max_range_m))
            gs = self._client.get_gripper_status()
            if gs is not None:
                snapshot = build_gripper_snapshot(gs)
                self._gripper_value = snapshot.value
                self._gripper_force_feedback = snapshot.force_feedback
                self._gripper_mode = snapshot.mode
                self._gripper_status_text = snapshot.status_text
                self.gripper_target_var.set(
                    min(max(0.0, snapshot.value or 0.0), self._gripper_max_range_m)
                )
                self._gripper_target_initialized = True
        self.connection_var.set("Connected")
        self.set_last_action(
            "Connected. Press Enable before sending motion commands."
        )
        self._start_poll_thread()

    def disconnect_robot(self) -> None:
        self.stop_continuous_action()
        self._robot = None
        self._gripper = None
        self._connected = False
        self._control_enabled = False
        self._robot_status_text = "Disconnected"
        self._gripper_status_text = "Disconnected"
        self._gripper_value = None
        self._gripper_force_feedback = None
        self._gripper_target_initialized = False
        self._client.disconnect()
        self.connection_var.set("Disconnected")
        self.set_last_action("Disconnected.")

    def reconnect_robot(self) -> None:
        self.disconnect_robot()
        time.sleep(0.1)
        self.connect_robot()

    def apply_speed_percent(self) -> None:
        if not self._connected or self._robot is None:
            self.set_last_action("Cannot apply speed: not connected.")
            return
        speed = self._client.set_speed_percent(int(self.speed_var.get()))
        self.speed_var.set(speed)
        self.set_last_action(f"Speed set to {speed}%.")

    def apply_tcp_offset(self) -> None:
        if not self._connected or self._robot is None:
            self.set_last_action("Cannot apply TCP offset: not connected.")
            return
        offset = [var.get() for var in self.tcp_offset_vars]
        self._client.set_tcp_offset(offset)
        measured_tcp = self._client.get_tcp_pose()
        if measured_tcp is not None:
            self._measured_tcp_pose = measured_tcp
            self._target_tcp_pose = clamp_tcp_pose(measured_tcp)
        self.set_last_action(f"TCP offset applied: {offset}")

    def enable_control(self) -> None:
        if not self._connected or self._robot is None:
            self.set_last_action("Cannot enable: not connected.")
            return
        self._robot.enable()
        deadline = time.monotonic() + 3.0
        enabled = False
        while time.monotonic() < deadline:
            enabled_list = self._robot.get_joints_enable_status_list()
            if all(enabled_list):
                enabled = True
                self._enabled_list = enabled_list
                break
            time.sleep(0.05)
        self._control_enabled = enabled
        self.set_last_action("All joints enabled." if enabled else "Enable timeout.")

    def disable_control(self) -> None:
        if not self._connected or self._robot is None:
            self.set_last_action("Cannot disable: not connected.")
            return
        self.stop_continuous_action()
        self._robot.disable()
        deadline = time.monotonic() + 3.0
        disabled = False
        while time.monotonic() < deadline:
            enabled_list = self._robot.get_joints_enable_status_list()
            if not any(enabled_list):
                disabled = True
                self._enabled_list = enabled_list
                break
            time.sleep(0.05)
        self._control_enabled = False
        self.set_last_action("All joints disabled." if disabled else "Disable timeout.")

    def electronic_emergency_stop(self) -> None:
        if not self._connected or self._robot is None:
            self.set_last_action("Cannot send e-stop: not connected.")
            return
        self.stop_continuous_action()
        self._client.electronic_emergency_stop()
        self._control_enabled = False
        self.set_last_action(
            "Electronic emergency stop sent. Press Enable before moving again."
        )

    def sync_target_to_current(self) -> None:
        if not self._connected or self._robot is None:
            self.set_last_action("Cannot sync target: not connected.")
            return
        measured = self._client.get_tcp_pose()
        if measured is None:
            self.set_last_action("Cannot sync target: current TCP pose unavailable.")
            return
        self._measured_tcp_pose = measured
        self._target_tcp_pose = clamp_tcp_pose(measured)
        self.set_last_action("Target pose synced to current TCP pose.")

    def sync_gripper_target_to_current(self) -> None:
        if not self._connected or self._gripper is None:
            self.set_last_action("Cannot sync gripper target: not connected.")
            return
        gs = self._client.get_gripper_status()
        if gs is None:
            self.set_last_action("Cannot sync gripper target: current status unavailable.")
            return
        snapshot = build_gripper_snapshot(gs)
        self._gripper_value = snapshot.value
        self.gripper_target_var.set(
            min(max(0.0, snapshot.value or 0.0), self._gripper_max_range_m)
        )
        self._gripper_target_initialized = True
        self.set_last_action("Gripper target synced to current width.")

    def _refresh_gripper_snapshot(self) -> Optional[object]:
        if self._gripper is None:
            return None
        gs = self._client.get_gripper_status()
        if gs is None:
            return None
        snapshot = build_gripper_snapshot(gs)
        self._gripper_value = snapshot.value
        self._gripper_force_feedback = snapshot.force_feedback
        self._gripper_mode = snapshot.mode
        self._gripper_status_text = snapshot.status_text
        return gs

    def _wait_for_gripper_enable_state(self, expected: bool, timeout: float = 1.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            gs = self._refresh_gripper_snapshot()
            if gs is not None and gs.msg.foc_status.driver_enable_status == expected:
                return True
            time.sleep(0.05)
        return False

    def prepare_gripper_zeroing(self) -> None:
        if not self._connected or self._gripper is None:
            self.set_last_action("Cannot prepare gripper zeroing: not connected.")
            return
        self.stop_continuous_action()
        self._gripper.disable_gripper()
        disabled = self._wait_for_gripper_enable_state(False, timeout=1.0)
        if disabled:
            self.set_last_action(
                "Gripper driver released. Manually squeeze the gripper fully closed, then click Set Zero."
            )
        else:
            self.set_last_action(
                "Release command sent. If the gripper feels free, manually close it fully and click Set Zero."
            )

    def calibrate_gripper_zero(self) -> None:
        if not self._connected or self._gripper is None:
            self.set_last_action("Cannot set gripper zero: not connected.")
            return
        self.stop_continuous_action()
        confirmed = messagebox.askokcancel(
            "Set Gripper Zero",
            "Please fully close the gripper by hand first.\n\n"
            "Click OK only when the gripper is fully closed and clear of fingers/tools.",
            parent=self.root,
        )
        if not confirmed:
            self.set_last_action("Gripper zeroing cancelled.")
            return
        success = self._gripper.calibrate_gripper(timeout=1.5)
        time.sleep(0.2)
        gs = self._refresh_gripper_snapshot()
        if gs is not None:
            self.gripper_target_var.set(
                min(max(0.0, gs.msg.value), self._gripper_max_range_m)
            )
            self._gripper_target_initialized = True
        if success:
            self.set_last_action(
                "Gripper zero set successfully. You can now use Open Step/Close Step or Set Width."
            )
        else:
            self.set_last_action(
                "Set Zero timed out. Try Release Driver again, close the gripper fully by hand, then retry."
            )

    def move_delta(self, axis_index: int, direction: float) -> None:
        if not self._connected or self._robot is None:
            self.stop_continuous_action()
            self.set_last_action("Motion blocked: not connected.")
            return
        if not self._control_enabled:
            self.stop_continuous_action()
            self.set_last_action("Motion blocked: press Enable first.")
            return
        if not all(self._enabled_list):
            self.stop_continuous_action()
            self._control_enabled = False
            self.set_last_action("Motion blocked: some joints are not enabled.")
            return
        if self._target_tcp_pose is None:
            self.stop_continuous_action()
            self.set_last_action("Motion blocked: target TCP pose unavailable.")
            return

        pos_step = max(0.0005, float(self.pos_step_var.get()))
        rot_step_deg = max(0.1, float(self.rot_step_deg_var.get()))
        delta = pos_step if axis_index < 3 else math.radians(rot_step_deg)

        target_pose = self._target_tcp_pose[:]
        target_pose[axis_index] += direction * delta
        target_pose = clamp_tcp_pose(target_pose)

        if self.dry_run_var.get():
            self._target_tcp_pose = target_pose
            self.set_last_action("Dry-run: target updated, no motion sent.")
            return

        flange_pose = self._robot.get_tcp2flange_pose(target_pose)
        self._robot.move_p(flange_pose)
        self._target_tcp_pose = target_pose
        axis_names = ["x", "y", "z", "roll", "pitch", "yaw"]
        sign = "+" if direction > 0 else "-"
        self.set_last_action(f"Sent move_p: {axis_names[axis_index]}{sign}")

    def move_gripper_to_target(self) -> None:
        if not self._connected or self._gripper is None:
            self.stop_continuous_action()
            self.set_last_action("Gripper blocked: not connected.")
            return
        width = min(max(0.0, float(self.gripper_target_var.get())), self._gripper_max_range_m)
        force = min(max(0.1, float(self.gripper_force_var.get())), 3.0)
        self.gripper_target_var.set(width)
        self.gripper_force_var.set(force)
        if self.dry_run_var.get():
            self.set_last_action("Dry-run: gripper target updated, no command sent.")
            return
        self._gripper.move_gripper_m(value=width, force=force)
        self.set_last_action(f"Sent gripper width command: {width:.4f} m @ {force:.2f} N")

    def step_gripper(self, direction: float) -> None:
        if not self._connected or self._gripper is None:
            self.stop_continuous_action()
            self.set_last_action("Gripper blocked: not connected.")
            return
        base_value = self._gripper_value
        if base_value is None:
            base_value = float(self.gripper_target_var.get())
        step = max(0.001, float(self.gripper_step_var.get()))
        target = min(max(0.0, base_value + direction * step), self._gripper_max_range_m)
        self.gripper_target_var.set(target)
        self.move_gripper_to_target()

    def _continuous_tick(self) -> None:
        self._continuous_after_id = None
        if self._active_motion is not None:
            axis_index, direction = self._active_motion
            self.run_async(self.move_delta, axis_index, direction)
        elif self._active_gripper_direction != 0.0:
            self.run_async(self.step_gripper, self._active_gripper_direction)
        else:
            return
        if self._active_motion is None and self._active_gripper_direction == 0.0:
            return
        self._continuous_after_id = self.root.after(
            max(20, int(getattr(self.args, "continuous_interval_ms", DEFAULT_CONTINUOUS_INTERVAL_MS))),
            self._continuous_tick,
        )

    def _ensure_continuous_loop(self) -> None:
        if self._continuous_after_id is None:
            self._continuous_tick()

    def start_continuous_motion(self, axis_index: int, direction: float) -> None:
        self._active_gripper_direction = 0.0
        if self._active_motion == (axis_index, direction):
            return
        self._active_motion = (axis_index, direction)
        self._ensure_continuous_loop()

    def stop_continuous_motion(self, axis_index: int, direction: float) -> None:
        if self._active_motion == (axis_index, direction):
            self.stop_continuous_action()

    def start_continuous_gripper(self, direction: float) -> None:
        self._active_motion = None
        if self._active_gripper_direction == direction:
            return
        self._active_gripper_direction = direction
        self._ensure_continuous_loop()

    def stop_continuous_gripper(self, direction: float) -> None:
        if self._active_gripper_direction == direction:
            self.stop_continuous_action()

    def stop_continuous_action(self) -> None:
        self._active_motion = None
        self._active_gripper_direction = 0.0
        if self._continuous_after_id is not None:
            try:
                self.root.after_cancel(self._continuous_after_id)
            except Exception:
                pass
            self._continuous_after_id = None

    def refresh_ui(self) -> None:
        self.connection_var.set(
            "Connected" if self._connected else "Disconnected"
        )
        self.mode_var.set(self._robot_status_text)
        self.enabled_var.set(str(self._enabled_list))
        self.last_action_var.set(self._last_action)
        self.gripper_status_var.set(self._gripper_status_text)
        self.gripper_mode_var.set(self._gripper_mode)
        self.gripper_value_var.set(
            "--" if self._gripper_value is None else f"{self._gripper_value:.5f}"
        )
        self.gripper_force_feedback_var.set(
            "--" if self._gripper_force_feedback is None else f"{self._gripper_force_feedback:.3f} N"
        )
        self.gripper_max_range_var.set(self._gripper_max_range_m)
        if self._gripper_scale is not None:
            self._gripper_scale.configure(to=max(0.001, self._gripper_max_range_m))

        measured = self._measured_tcp_pose
        target = self._target_tcp_pose
        for idx in range(6):
            self.measured_pose_vars[idx].set(
                "--" if measured is None else f"{measured[idx]:.5f}"
            )
            self.target_pose_vars[idx].set(
                "--" if target is None else f"{target[idx]:.5f}"
            )
        self.gripper_target_var.set(
            min(max(0.0, self.gripper_target_var.get()), self._gripper_max_range_m)
        )

        self.root.after(100, self.refresh_ui)

    def on_close(self) -> None:
        self.stop_continuous_action()
        if self._poll_after_id is not None:
            try:
                self.root.after_cancel(self._poll_after_id)
            except Exception:
                pass
            self._poll_after_id = None
        try:
            self.disconnect_robot()
        finally:
            self.root.destroy()


def run(args: argparse.Namespace) -> None:
    root = tk.Tk()
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    app = TeleopGuiApp(root, args)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.on_close()
