from __future__ import annotations

import argparse
import math
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional

from PIL import Image, ImageTk
from pyAgxArm import ArmModel

from piper_app.camera.d405 import D405CameraConfig, D405FrameBundle, D405PointQuery, D405RealSenseCamera
from piper_app.robot.client import PiperRobotClient
from piper_app.robot.factory import PiperConnectionConfig

DEFAULT_POLL_INTERVAL_S = 0.2
VIEWER_WIDTH = 720
VIEWER_HEIGHT = 360


class DragMonitorGuiApp:
    def __init__(self, root: tk.Tk, args: argparse.Namespace):
        self.root = root
        self.args = args
        self.root.title("Piper Drag Monitor")
        self.root.geometry("1560x940")
        self.root.minsize(1320, 820)

        self._client = PiperRobotClient(
            PiperConnectionConfig(
                robot=args.robot,
                interface=args.interface,
                channel=args.channel,
                bitrate=args.bitrate,
                firmware_timeout=args.firmware_timeout,
                speed_percent=1,
                tcp_offset=[0.0] * 6,
            )
        )
        self._camera = D405RealSenseCamera(
            D405CameraConfig(
                serial=str(getattr(args, "camera_serial", "auto")),
                width=int(getattr(args, "camera_width", 640)),
                height=int(getattr(args, "camera_height", 480)),
                fps=int(getattr(args, "camera_fps", 30)),
                depth_min_m=float(getattr(args, "depth_min_m", 0.05)),
                depth_max_m=float(getattr(args, "depth_max_m", 0.50)),
            )
        )

        self._connected = False
        self._busy = False
        self._poll_after_id: Optional[str] = None
        self._camera_after_id: Optional[str] = None
        self._camera_enabled = bool(getattr(args, "camera", True))

        self._firmware_info: dict = {}
        self._robot_status_text = "Not connected"
        self._drag_hint_text = "Unknown"
        self._last_event_text = "Read-only monitor ready."
        self._last_update_text = "--"
        self._measured_tcp_pose: Optional[list[float]] = None
        self._joint_angles: Optional[list[float]] = None
        self._enabled_list = [False] * 6

        self._camera_status_text = "Disabled"
        self._camera_serial_text = "--"
        self._camera_frame_text = "--"
        self._hover_text = "pixel=(--, --) depth=-- point=(--, --, --)"
        self._camera_bundle: Optional[D405FrameBundle] = None
        self._hover_pixel: Optional[tuple[int, int]] = None
        self._color_photo: Optional[ImageTk.PhotoImage] = None
        self._depth_photo: Optional[ImageTk.PhotoImage] = None
        self._color_view_info: Optional[dict[str, int]] = None
        self._depth_view_info: Optional[dict[str, int]] = None

        self._build_vars()
        self._build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.refresh_ui)
        self.root.after(200, lambda: self.run_action(self.connect_robot))

    def _build_vars(self) -> None:
        self.robot_var = tk.StringVar(value=self.args.robot)
        self.interface_var = tk.StringVar(value=self.args.interface)
        self.channel_var = tk.StringVar(value=self.args.channel)
        self.bitrate_var = tk.IntVar(value=self.args.bitrate)

        self.connection_var = tk.StringVar(value="Connecting...")
        self.firmware_var = tk.StringVar(value="unknown")
        self.mode_var = tk.StringVar(value=self._robot_status_text)
        self.enabled_var = tk.StringVar(value="[False, False, False, False, False, False]")
        self.drag_hint_var = tk.StringVar(value=self._drag_hint_text)
        self.last_update_var = tk.StringVar(value=self._last_update_text)
        self.last_event_var = tk.StringVar(value=self._last_event_text)

        self.camera_status_var = tk.StringVar(value=self._camera_status_text)
        self.camera_serial_var = tk.StringVar(value=self._camera_serial_text)
        self.camera_frame_var = tk.StringVar(value=self._camera_frame_text)
        self.camera_hover_var = tk.StringVar(value=self._hover_text)

        self.pose_vars = [tk.StringVar(value="--") for _ in range(6)]
        self.joint_rad_vars = [tk.StringVar(value="--") for _ in range(6)]
        self.joint_deg_vars = [tk.StringVar(value="--") for _ in range(6)]

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        outer = ttk.Frame(self.root, padding=12)
        outer.grid(sticky="nsew")
        outer.columnconfigure(0, weight=2)
        outer.columnconfigure(1, weight=4)
        outer.rowconfigure(2, weight=1)
        outer.rowconfigure(3, weight=1)

        self._build_top_bar(outer)
        self._build_status_panel(outer)
        self._build_pose_panel(outer)
        self._build_joint_panel(outer)
        self._build_camera_panel(outer)
        self._build_note_panel(outer)

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

        ttk.Label(frame, text="Mode: read-only").grid(row=0, column=8, sticky="w")

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=0, column=9, sticky="e")
        ttk.Button(button_frame, text="Refresh Now", command=self.poll_now).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(
            button_frame,
            text="Reconnect",
            command=lambda: self.run_action(self.reconnect_robot),
        ).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(
            button_frame,
            text="Disconnect",
            command=lambda: self.run_action(self.disconnect_robot),
        ).grid(row=0, column=2)

    def _build_status_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Monitor Status", padding=10)
        frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        frame.columnconfigure(1, weight=1)

        rows = [
            ("Connection", self.connection_var),
            ("Firmware", self.firmware_var),
            ("Robot Status", self.mode_var),
            ("Joint Enabled", self.enabled_var),
            ("Drag Readiness", self.drag_hint_var),
            ("Last Update", self.last_update_var),
            ("Last Event", self.last_event_var),
        ]
        for row_idx, (label, variable) in enumerate(rows):
            ttk.Label(frame, text=label).grid(row=row_idx, column=0, sticky="nw", pady=3)
            ttk.Label(frame, textvariable=variable, wraplength=440, justify="left").grid(
                row=row_idx, column=1, sticky="w", pady=3
            )

    def _build_pose_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Measured Pose", padding=10)
        frame.grid(row=2, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        for col in range(2):
            frame.columnconfigure(col, weight=1)

        ttk.Label(frame, text="Axis").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text="Value").grid(row=0, column=1, sticky="w")

        for row_idx, axis_name in enumerate(["x", "y", "z", "roll", "pitch", "yaw"], start=1):
            ttk.Label(frame, text=axis_name).grid(row=row_idx, column=0, sticky="w", pady=2)
            ttk.Label(frame, textvariable=self.pose_vars[row_idx - 1]).grid(
                row=row_idx, column=1, sticky="w", pady=2
            )

    def _build_joint_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Joint Angles", padding=10)
        frame.grid(row=3, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        for col in range(3):
            frame.columnconfigure(col, weight=1)

        ttk.Label(frame, text="Joint").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text="Radians").grid(row=0, column=1, sticky="w")
        ttk.Label(frame, text="Degrees").grid(row=0, column=2, sticky="w")

        for row_idx in range(6):
            ttk.Label(frame, text=f"J{row_idx + 1}").grid(row=row_idx + 1, column=0, sticky="w", pady=2)
            ttk.Label(frame, textvariable=self.joint_rad_vars[row_idx]).grid(
                row=row_idx + 1, column=1, sticky="w", pady=2
            )
            ttk.Label(frame, textvariable=self.joint_deg_vars[row_idx]).grid(
                row=row_idx + 1, column=2, sticky="w", pady=2
            )

    def _build_camera_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="D405 Camera", padding=10)
        frame.grid(row=1, column=1, rowspan=3, sticky="nsew", pady=(0, 10))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)

        meta = ttk.Frame(frame)
        meta.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        meta.columnconfigure(1, weight=1)

        rows = [
            ("Camera", self.camera_status_var),
            ("Serial", self.camera_serial_var),
            ("Frame", self.camera_frame_var),
            ("Hover", self.camera_hover_var),
        ]
        for row_idx, (label, variable) in enumerate(rows):
            ttk.Label(meta, text=label).grid(row=row_idx, column=0, sticky="nw", pady=2)
            ttk.Label(meta, textvariable=variable, wraplength=760, justify="left").grid(
                row=row_idx, column=1, sticky="w", pady=2, padx=(8, 0)
            )

        self.color_canvas = tk.Canvas(
            frame,
            width=VIEWER_WIDTH,
            height=VIEWER_HEIGHT,
            bg="black",
            highlightthickness=1,
            highlightbackground="#4b5563",
        )
        self.color_canvas.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        self.color_canvas.create_text(VIEWER_WIDTH / 2, VIEWER_HEIGHT / 2, text="No color frame", fill="white")
        self.color_canvas.bind("<Motion>", lambda event: self._on_canvas_motion("color", event))
        self.color_canvas.bind("<Leave>", self._on_canvas_leave)

        self.depth_canvas = tk.Canvas(
            frame,
            width=VIEWER_WIDTH,
            height=VIEWER_HEIGHT,
            bg="black",
            highlightthickness=1,
            highlightbackground="#4b5563",
        )
        self.depth_canvas.grid(row=2, column=0, sticky="nsew")
        self.depth_canvas.create_text(VIEWER_WIDTH / 2, VIEWER_HEIGHT / 2, text="No depth frame", fill="white")
        self.depth_canvas.bind("<Motion>", lambda event: self._on_canvas_motion("depth", event))
        self.depth_canvas.bind("<Leave>", self._on_canvas_leave)

    def _build_note_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Notes", padding=10)
        frame.grid(row=4, column=0, columnspan=2, sticky="ew")
        note = (
            "This window is read-only. It does not send enable, disable, motion, or drag-mode commands. "
            "The D405 panel uses pyrealsense2 with color-depth alignment, and hover coordinates are reported "
            "in the D405 camera frame."
        )
        ttk.Label(frame, text=note, wraplength=1200, justify="left").grid(sticky="w")

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
        self._last_event_text = "Connecting to Piper in read-only monitor mode..."
        self._client.config.robot = self.robot_var.get()
        self._client.config.interface = self.interface_var.get()
        self._client.config.channel = self.channel_var.get()
        self._client.config.bitrate = int(self.bitrate_var.get())
        self._client.config.firmware_timeout = float(self.args.firmware_timeout)
        self._client.connect(configure_robot=False, init_gripper=False)
        self._firmware_info = self._client.firmware_info
        self._connected = True
        self.firmware_var.set(self._client.software_version)
        self._last_event_text = "Connected. Monitoring only."
        self._poll_data()
        self._connect_camera_if_needed()

    def disconnect_robot(self) -> None:
        self._client.disconnect()
        self._connected = False
        self._firmware_info = {}
        self._robot_status_text = "Disconnected"
        self._drag_hint_text = "Unknown"
        self._last_event_text = "Disconnected."
        self._last_update_text = "--"
        self._measured_tcp_pose = None
        self._joint_angles = None
        self._enabled_list = [False] * 6
        self._disconnect_camera()

    def reconnect_robot(self) -> None:
        self.disconnect_robot()
        time.sleep(0.1)
        self.connect_robot()

    def poll_now(self) -> None:
        self.run_action(self._poll_data)

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
        self._drag_hint_text = self._build_drag_hint()
        self._last_update_text = time.strftime("%H:%M:%S")

    def _build_drag_hint(self) -> str:
        if not self._connected:
            return "Unknown"
        if all(not enabled for enabled in self._enabled_list):
            return (
                "All joints report disabled. The app still did not command drag mode; manual dragging depends "
                "on the arm hardware and current controller state."
            )
        return (
            "One or more joints are still enabled. This app will not switch the robot into zero-force drag mode, "
            "so do not assume it is safe to hand-drag."
        )

    def _connect_camera_if_needed(self) -> None:
        if not self._camera_enabled:
            self._camera_status_text = "Disabled by CLI/config"
            self._camera_serial_text = "--"
            return
        try:
            serial = self._camera.open()
        except Exception as exc:
            self._camera_status_text = f"Unavailable: {type(exc).__name__}"
            self._camera_serial_text = str(exc)
            self._camera_frame_text = "--"
            return
        self._camera_status_text = "Streaming"
        self._camera_serial_text = serial

    def _disconnect_camera(self) -> None:
        self._camera.close()
        self._camera_status_text = "Disconnected"
        self._camera_serial_text = "--"
        self._camera_frame_text = "--"
        self._hover_text = "pixel=(--, --) depth=-- point=(--, --, --)"
        self._camera_bundle = None
        self._hover_pixel = None
        self._color_photo = None
        self._depth_photo = None
        self._color_view_info = None
        self._depth_view_info = None
        self.color_canvas.delete("all")
        self.depth_canvas.delete("all")
        self.color_canvas.create_text(VIEWER_WIDTH / 2, VIEWER_HEIGHT / 2, text="No color frame", fill="white")
        self.depth_canvas.create_text(VIEWER_WIDTH / 2, VIEWER_HEIGHT / 2, text="No depth frame", fill="white")

    def _update_camera_frame(self) -> None:
        if not self._camera_enabled or self._camera.serial is None:
            return
        bundle = self._camera.read_frames()
        if bundle is None:
            self._camera_status_text = "Streaming error"
            return

        self._camera_bundle = bundle
        self._camera_frame_text = f"{bundle.width}x{bundle.height} @ {self.args.camera_fps} fps"
        self._camera_status_text = "Streaming"
        self._camera_serial_text = bundle.serial

        self._color_photo, self._color_view_info = self._render_canvas_image(self.color_canvas, bundle.color_rgb)
        self._depth_photo, self._depth_view_info = self._render_canvas_image(self.depth_canvas, bundle.depth_visual_rgb)
        self._draw_hover_overlay()

    def _render_canvas_image(self, canvas: tk.Canvas, image_rgb, text: str = ""):
        canvas.delete("all")
        pil_image = Image.fromarray(image_rgb)
        display_image, view_info = self._fit_image(pil_image)
        photo = ImageTk.PhotoImage(display_image)
        canvas.create_image(
            VIEWER_WIDTH / 2,
            VIEWER_HEIGHT / 2,
            image=photo,
            anchor="center",
            tags=("frame",),
        )
        if text:
            canvas.create_text(10, 10, anchor="nw", text=text, fill="white")
        return photo, view_info

    def _fit_image(self, image: Image.Image):
        src_width, src_height = image.size
        scale = min(VIEWER_WIDTH / src_width, VIEWER_HEIGHT / src_height)
        disp_width = max(1, int(round(src_width * scale)))
        disp_height = max(1, int(round(src_height * scale)))
        resized = image.resize((disp_width, disp_height), Image.Resampling.BILINEAR)
        offset_x = (VIEWER_WIDTH - disp_width) // 2
        offset_y = (VIEWER_HEIGHT - disp_height) // 2
        background = Image.new("RGB", (VIEWER_WIDTH, VIEWER_HEIGHT), color=(0, 0, 0))
        background.paste(resized, (offset_x, offset_y))
        return background, {
            "src_width": src_width,
            "src_height": src_height,
            "disp_width": disp_width,
            "disp_height": disp_height,
            "offset_x": offset_x,
            "offset_y": offset_y,
        }

    def _on_canvas_motion(self, viewer_name: str, event) -> None:
        view_info = self._color_view_info if viewer_name == "color" else self._depth_view_info
        bundle = self._camera_bundle
        if view_info is None or bundle is None:
            return

        src_point = self._display_to_source(view_info, event.x, event.y)
        if src_point is None:
            self._hover_pixel = None
            self._hover_text = "pixel=(--, --) depth=-- point=(--, --, --)"
        else:
            self._hover_pixel = src_point
            query = self._camera.query_point(*src_point)
            self._hover_text = self._format_hover(query)
        self._draw_hover_overlay()

    def _on_canvas_leave(self, _event) -> None:
        self._hover_pixel = None
        self._hover_text = "pixel=(--, --) depth=-- point=(--, --, --)"
        self._draw_hover_overlay()

    def _display_to_source(self, view_info: dict[str, int], display_x: int, display_y: int):
        if not (
            view_info["offset_x"] <= display_x < view_info["offset_x"] + view_info["disp_width"]
            and view_info["offset_y"] <= display_y < view_info["offset_y"] + view_info["disp_height"]
        ):
            return None
        rel_x = (display_x - view_info["offset_x"]) / view_info["disp_width"]
        rel_y = (display_y - view_info["offset_y"]) / view_info["disp_height"]
        src_x = min(view_info["src_width"] - 1, max(0, int(rel_x * view_info["src_width"])))
        src_y = min(view_info["src_height"] - 1, max(0, int(rel_y * view_info["src_height"])))
        return (src_x, src_y)

    def _source_to_display(self, view_info: dict[str, int], source_x: int, source_y: int):
        display_x = view_info["offset_x"] + ((source_x + 0.5) / view_info["src_width"]) * view_info["disp_width"]
        display_y = view_info["offset_y"] + ((source_y + 0.5) / view_info["src_height"]) * view_info["disp_height"]
        return display_x, display_y

    def _format_hover(self, query: D405PointQuery) -> str:
        if not query.valid or query.depth_m is None or query.point_m is None:
            return f"pixel=({query.pixel[0]}, {query.pixel[1]}) depth=-- point=(--, --, --)"
        point = query.point_m
        return (
            f"pixel=({query.pixel[0]}, {query.pixel[1]}) depth={query.depth_m:.4f} m "
            f"point=({point[0]:.4f}, {point[1]:.4f}, {point[2]:.4f}) m"
        )

    def _draw_hover_overlay(self) -> None:
        for canvas in (self.color_canvas, self.depth_canvas):
            canvas.delete("overlay")

        if self._hover_pixel is None or self._color_view_info is None or self._depth_view_info is None:
            return

        color_x, color_y = self._source_to_display(self._color_view_info, *self._hover_pixel)
        depth_x, depth_y = self._source_to_display(self._depth_view_info, *self._hover_pixel)
        self._draw_crosshair(self.color_canvas, color_x, color_y)
        self._draw_crosshair(self.depth_canvas, depth_x, depth_y)

    def _draw_crosshair(self, canvas: tk.Canvas, x: float, y: float) -> None:
        line_color = "#f59e0b"
        canvas.create_line(x - 12, y, x + 12, y, fill=line_color, width=1, tags=("overlay",))
        canvas.create_line(x, y - 12, x, y + 12, fill=line_color, width=1, tags=("overlay",))
        canvas.create_oval(x - 3, y - 3, x + 3, y + 3, outline=line_color, width=1, tags=("overlay",))

    def refresh_ui(self) -> None:
        self.connection_var.set("Connected" if self._connected else "Disconnected")
        self.firmware_var.set(self._client.software_version if self._connected else "unknown")
        self.mode_var.set(self._robot_status_text)
        self.enabled_var.set(str(self._enabled_list))
        self.drag_hint_var.set(self._drag_hint_text)
        self.last_update_var.set(self._last_update_text)
        self.last_event_var.set(self._last_event_text)

        self.camera_status_var.set(self._camera_status_text)
        self.camera_serial_var.set(self._camera_serial_text)
        self.camera_frame_var.set(self._camera_frame_text)
        self.camera_hover_var.set(self._hover_text)

        pose = self._measured_tcp_pose
        for idx in range(6):
            if pose is None:
                self.pose_vars[idx].set("--")
                continue
            value = pose[idx]
            if idx < 3:
                self.pose_vars[idx].set(f"{value:.4f} m")
            else:
                self.pose_vars[idx].set(f"{value:.4f} rad ({math.degrees(value):.1f} deg)")

        joints = self._joint_angles
        for idx in range(6):
            if joints is None:
                self.joint_rad_vars[idx].set("--")
                self.joint_deg_vars[idx].set("--")
                continue
            value = joints[idx]
            self.joint_rad_vars[idx].set(f"{value:.4f}")
            self.joint_deg_vars[idx].set(f"{math.degrees(value):.2f}")

        self.root.after(100, self.refresh_ui)

    def _schedule_poll(self) -> None:
        if self._poll_after_id is not None:
            return
        self._poll_once()
        self._camera_once()

    def _poll_once(self) -> None:
        if self._connected and not self._busy:
            try:
                self._poll_data()
            except Exception as exc:
                self._connected = False
                self._robot_status_text = f"Read error: {type(exc).__name__}"
                self._last_event_text = f"Polling stopped: {type(exc).__name__}: {exc}"
        self._poll_after_id = self.root.after(
            int(max(0.05, float(getattr(self.args, "poll_interval_s", DEFAULT_POLL_INTERVAL_S))) * 1000),
            self._poll_once,
        )

    def _camera_once(self) -> None:
        if self._camera_enabled and self._connected:
            try:
                self._update_camera_frame()
            except Exception as exc:
                self._camera_status_text = f"Read error: {type(exc).__name__}"
                self._camera_serial_text = str(exc)
        interval_ms = int(max(50, int(getattr(self.args, "camera_update_interval_ms", 100))))
        self._camera_after_id = self.root.after(interval_ms, self._camera_once)

    def on_close(self) -> None:
        if self._poll_after_id is not None:
            self.root.after_cancel(self._poll_after_id)
            self._poll_after_id = None
        if self._camera_after_id is not None:
            self.root.after_cancel(self._camera_after_id)
            self._camera_after_id = None
        try:
            self._client.disconnect()
            self._camera.close()
        finally:
            self.root.destroy()


def run(args: argparse.Namespace) -> None:
    root = tk.Tk()
    app = DragMonitorGuiApp(root, args)
    app._schedule_poll()
    root.mainloop()
