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
DEFAULT_VIEWER_WIDTH = 720
DEFAULT_VIEWER_HEIGHT = 360


class CalibrationViewerBase:
    def __init__(
        self,
        root: tk.Tk,
        args: argparse.Namespace,
        *,
        title: str,
        use_robot: bool,
        show_depth: bool,
        note_text: str,
        geometry: str = "1620x960",
        left_scrollable: bool = True,
    ):
        self.root = root
        self.args = args
        self.use_robot = bool(use_robot)
        self.show_depth = bool(show_depth)
        self.left_scrollable = bool(left_scrollable)
        self.root.title(title)
        self.root.geometry(geometry)
        self.root.minsize(1320, 820)

        self._client = None
        if self.use_robot:
            self._client = PiperRobotClient(
                PiperConnectionConfig(
                    robot=args.robot,
                    interface=args.interface,
                    channel=args.channel,
                    bitrate=args.bitrate,
                    firmware_timeout=args.firmware_timeout,
                    speed_percent=1,
                    tcp_offset=[float(value) for value in getattr(args, "tcp_offset", [0.0] * 6)],
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
        self._camera_connected = False

        self._firmware_info: dict = {}
        self._robot_status_text = "Not connected" if self.use_robot else "Disabled"
        self._last_event_text = "Ready."
        self._last_update_text = "--"
        self._measured_tcp_pose: Optional[list[float]] = None
        self._joint_angles: Optional[list[float]] = None
        self._enabled_list = [False] * 6

        self._camera_status_text = "Disconnected"
        self._camera_serial_text = "--"
        self._camera_frame_text = "--"
        self._hover_text = "pixel=(--, --) depth=-- point=(--, --, --)"
        self._camera_bundle: Optional[D405FrameBundle] = None
        self._hover_pixel: Optional[tuple[int, int]] = None
        self._color_photo: Optional[ImageTk.PhotoImage] = None
        self._depth_photo: Optional[ImageTk.PhotoImage] = None
        self._color_view_info: Optional[dict[str, int]] = None
        self._depth_view_info: Optional[dict[str, int]] = None
        self._note_text = note_text
        self._left_scroll_canvas: Optional[tk.Canvas] = None
        self._left_scroll_window_id: Optional[int] = None

        self._build_base_vars()
        self._build_layout()
        self.root.bind("<Key>", self._handle_key_event)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self.refresh_ui)

    @property
    def client(self) -> PiperRobotClient:
        if self._client is None:
            raise RuntimeError("Robot client is not enabled for this window.")
        return self._client

    @property
    def camera(self) -> D405RealSenseCamera:
        return self._camera

    def _build_base_vars(self) -> None:
        self.robot_var = tk.StringVar(value=getattr(self.args, "robot", ArmModel.PIPER))
        self.interface_var = tk.StringVar(value=getattr(self.args, "interface", "socketcan"))
        self.channel_var = tk.StringVar(value=getattr(self.args, "channel", "can0"))
        self.bitrate_var = tk.IntVar(value=int(getattr(self.args, "bitrate", 1_000_000)))

        self.connection_var = tk.StringVar(value="Disconnected")
        self.firmware_var = tk.StringVar(value="unknown")
        self.mode_var = tk.StringVar(value=self._robot_status_text)
        self.enabled_var = tk.StringVar(value=str(self._enabled_list))
        self.last_update_var = tk.StringVar(value=self._last_update_text)
        self.last_event_var = tk.StringVar(value=self._last_event_text)

        self.camera_status_var = tk.StringVar(value=self._camera_status_text)
        self.camera_serial_var = tk.StringVar(value=self._camera_serial_text)
        self.camera_frame_var = tk.StringVar(value=self._camera_frame_text)
        self.camera_hover_var = tk.StringVar(value=self._hover_text)

        self.pose_vars = [tk.StringVar(value="--") for _ in range(6)]
        self.joint_rad_vars = [tk.StringVar(value="--") for _ in range(6)]
        self.joint_deg_vars = [tk.StringVar(value="--") for _ in range(6)]

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.outer = ttk.Frame(self.root, padding=12)
        self.outer.grid(sticky="nsew")
        self.outer.columnconfigure(0, weight=2)
        self.outer.columnconfigure(1, weight=4)
        self.outer.rowconfigure(0, weight=1)
        self.outer.rowconfigure(1, weight=0)

        left_host = ttk.Frame(self.outer)
        left_host.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_host.columnconfigure(0, weight=1)
        left_host.rowconfigure(0, weight=1)

        if self.left_scrollable:
            self._left_scroll_canvas = tk.Canvas(left_host, highlightthickness=0, bd=0)
            scrollbar = ttk.Scrollbar(left_host, orient="vertical", command=self._left_scroll_canvas.yview)
            self._left_scroll_canvas.configure(yscrollcommand=scrollbar.set)
            self._left_scroll_canvas.grid(row=0, column=0, sticky="nsew")
            scrollbar.grid(row=0, column=1, sticky="ns")

            self.left_column = ttk.Frame(self._left_scroll_canvas)
            self.left_column.columnconfigure(0, weight=1)
            self._left_scroll_window_id = self._left_scroll_canvas.create_window(
                (0, 0),
                window=self.left_column,
                anchor="nw",
            )
            self.left_column.bind("<Configure>", self._on_left_frame_configure)
            self._left_scroll_canvas.bind("<Configure>", self._on_left_canvas_configure)
            self._left_scroll_canvas.bind("<Enter>", self._bind_left_mousewheel)
            self._left_scroll_canvas.bind("<Leave>", self._unbind_left_mousewheel)
        else:
            self.left_column = ttk.Frame(left_host)
            self.left_column.grid(row=0, column=0, sticky="nsew")
            self.left_column.columnconfigure(0, weight=1)

        self.right_column = ttk.Frame(self.outer)
        self.right_column.grid(row=0, column=1, sticky="nsew")
        self.right_column.columnconfigure(0, weight=1)
        self.right_column.rowconfigure(0, weight=1)

        self.build_left_panel(self.left_column)
        self.build_camera_panel(self.right_column)
        self.build_note_panel(self.outer)

    def build_left_panel(self, parent: ttk.Frame) -> None:
        raise NotImplementedError

    def build_note_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Notes", padding=10)
        frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Label(frame, text=self._note_text, wraplength=1500, justify="left").grid(sticky="w")

    def build_robot_connection_panel(self, parent: ttk.Frame, row: int, mode_label: str) -> None:
        frame = ttk.LabelFrame(parent, text="Connection", padding=10)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))
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
        ttk.Label(frame, text=mode_label).grid(row=0, column=8, sticky="w")

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=0, column=9, sticky="e")
        ttk.Button(button_frame, text="Refresh Now", command=self.poll_now).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(button_frame, text="Reconnect", command=lambda: self.run_action(self.reconnect_robot)).grid(
            row=0, column=1, padx=(0, 6)
        )
        ttk.Button(button_frame, text="Disconnect", command=lambda: self.run_action(self.disconnect_robot)).grid(
            row=0, column=2
        )

    def build_robot_status_panel(
        self,
        parent: ttk.Frame,
        row: int,
        extra_rows: Optional[list[tuple[str, tk.Variable]]] = None,
        title: str = "Robot Status",
    ) -> None:
        frame = ttk.LabelFrame(parent, text=title, padding=10)
        frame.grid(row=row, column=0, sticky="nsew", pady=(0, 10))
        frame.columnconfigure(1, weight=1)
        rows = [
            ("Connection", self.connection_var),
            ("Firmware", self.firmware_var),
            ("Robot Status", self.mode_var),
            ("Joint Enabled", self.enabled_var),
            ("Last Update", self.last_update_var),
            ("Last Event", self.last_event_var),
        ]
        if extra_rows:
            rows.extend(extra_rows)
        for row_idx, (label, variable) in enumerate(rows):
            ttk.Label(frame, text=label).grid(row=row_idx, column=0, sticky="nw", pady=3)
            ttk.Label(frame, textvariable=variable, wraplength=420, justify="left").grid(
                row=row_idx, column=1, sticky="w", pady=3
            )

    def build_pose_panel(self, parent: ttk.Frame, row: int, title: str = "Measured Pose") -> None:
        frame = ttk.LabelFrame(parent, text=title, padding=10)
        frame.grid(row=row, column=0, sticky="nsew", pady=(0, 10))
        for col in range(2):
            frame.columnconfigure(col, weight=1)
        ttk.Label(frame, text="Axis").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text="Value").grid(row=0, column=1, sticky="w")
        for row_idx, axis_name in enumerate(["x", "y", "z", "roll", "pitch", "yaw"], start=1):
            ttk.Label(frame, text=axis_name).grid(row=row_idx, column=0, sticky="w", pady=2)
            ttk.Label(frame, textvariable=self.pose_vars[row_idx - 1]).grid(row=row_idx, column=1, sticky="w", pady=2)

    def build_joint_panel(self, parent: ttk.Frame, row: int, title: str = "Joint Angles") -> None:
        frame = ttk.LabelFrame(parent, text=title, padding=10)
        frame.grid(row=row, column=0, sticky="nsew", pady=(0, 10))
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

    def build_camera_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="D405 Camera", padding=10)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        if self.show_depth:
            frame.rowconfigure(2, weight=1)

        meta = ttk.Frame(frame)
        meta.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        meta.columnconfigure(1, weight=1)

        for row_idx, (label, variable) in enumerate(
            [
                ("Camera", self.camera_status_var),
                ("Serial", self.camera_serial_var),
                ("Frame", self.camera_frame_var),
                ("Hover", self.camera_hover_var),
            ]
        ):
            ttk.Label(meta, text=label).grid(row=row_idx, column=0, sticky="nw", pady=2)
            ttk.Label(meta, textvariable=variable, wraplength=760, justify="left").grid(
                row=row_idx, column=1, sticky="w", pady=2, padx=(8, 0)
            )

        self.color_canvas = tk.Canvas(
            frame,
            width=DEFAULT_VIEWER_WIDTH,
            height=DEFAULT_VIEWER_HEIGHT,
            bg="black",
            highlightthickness=1,
            highlightbackground="#4b5563",
        )
        self.color_canvas.grid(row=1, column=0, sticky="nsew", pady=(0, 8 if self.show_depth else 0))
        self._draw_canvas_placeholder(self.color_canvas, "No color frame")
        self.color_canvas.bind("<Motion>", lambda event: self._on_canvas_motion("color", event))
        self.color_canvas.bind("<Leave>", self._on_canvas_leave)
        self.color_canvas.bind("<Configure>", self._on_display_canvas_resize)

        self.depth_canvas = None
        if self.show_depth:
            self.depth_canvas = tk.Canvas(
                frame,
                width=DEFAULT_VIEWER_WIDTH,
                height=DEFAULT_VIEWER_HEIGHT,
                bg="black",
                highlightthickness=1,
                highlightbackground="#4b5563",
            )
            self.depth_canvas.grid(row=2, column=0, sticky="nsew")
            self._draw_canvas_placeholder(self.depth_canvas, "No depth frame")
            self.depth_canvas.bind("<Motion>", lambda event: self._on_canvas_motion("depth", event))
            self.depth_canvas.bind("<Leave>", self._on_canvas_leave)
            self.depth_canvas.bind("<Configure>", self._on_display_canvas_resize)

    def start(self) -> None:
        self.root.after(150, lambda: self.run_action(self._connect_resources))
        self._schedule_poll()

    def run_action(self, callback) -> None:
        if self._busy:
            return
        self._busy = True
        try:
            callback()
        except Exception as exc:
            self._last_event_text = f"{type(exc).__name__}: {exc}"
            if self.use_robot:
                self._connected = False
                self._robot_status_text = f"Error: {type(exc).__name__}"
        finally:
            self._busy = False
            self.refresh_ui()

    def set_last_event(self, text: str) -> None:
        self._last_event_text = text

    def _connect_resources(self) -> None:
        errors: list[str] = []
        if self.use_robot:
            try:
                self.connect_robot()
            except Exception as exc:
                errors.append(f"robot: {exc}")
        try:
            self.connect_camera()
        except Exception as exc:
            errors.append(f"camera: {exc}")

        if errors:
            if (self.use_robot and self._connected) or self._camera_connected:
                self._last_event_text = "; ".join(errors)
                return
            raise RuntimeError("; ".join(errors))

    def connect_robot(self) -> None:
        if not self.use_robot:
            return
        self.connection_var.set("Connecting...")
        self._last_event_text = "Connecting to Piper..."
        self.client.config.robot = self.robot_var.get()
        self.client.config.interface = self.interface_var.get()
        self.client.config.channel = self.channel_var.get()
        self.client.config.bitrate = int(self.bitrate_var.get())
        self.client.config.firmware_timeout = float(self.args.firmware_timeout)
        self.client.connect(configure_robot=False, init_gripper=False)
        self._firmware_info = self.client.firmware_info
        self._connected = True
        self._robot_status_text = "Connected"
        self._last_event_text = "Robot connected."
        self._poll_data()

    def disconnect_robot(self) -> None:
        if not self.use_robot:
            return
        self.client.disconnect()
        self._connected = False
        self._firmware_info = {}
        self._robot_status_text = "Disconnected"
        self._last_event_text = "Robot disconnected."
        self._last_update_text = "--"
        self._measured_tcp_pose = None
        self._joint_angles = None
        self._enabled_list = [False] * 6

    def reconnect_robot(self) -> None:
        self.disconnect_robot()
        time.sleep(0.1)
        self.connect_robot()

    def connect_camera(self) -> None:
        try:
            serial = self._camera.open()
        except Exception as exc:
            self._camera_connected = False
            self._camera_status_text = f"Unavailable: {type(exc).__name__}"
            self._camera_serial_text = str(exc)
            self._camera_frame_text = "--"
            raise
        self._camera_connected = True
        self._camera_status_text = "Streaming"
        self._camera_serial_text = serial
        self._last_event_text = f"{self._last_event_text} Camera connected.".strip()

    def disconnect_camera(self) -> None:
        self._camera.close()
        self._camera_connected = False
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
        self._draw_canvas_placeholder(self.color_canvas, "No color frame")
        if self.depth_canvas is not None:
            self._draw_canvas_placeholder(self.depth_canvas, "No depth frame")

    def poll_now(self) -> None:
        self.run_action(self._poll_data)

    def _poll_data(self) -> None:
        if not self.use_robot or not self._connected:
            return
        status = self.client.get_arm_status()
        if status is not None:
            self._robot_status_text = (
                f"{status.msg.arm_status} | {status.msg.mode_feedback} | {status.msg.motion_status}"
            )
        measured_pose = self.client.get_tcp_pose()
        if measured_pose is not None:
            self._measured_tcp_pose = measured_pose
        joint_angles = self.client.get_joint_angles()
        if joint_angles is not None:
            self._joint_angles = joint_angles
        self._enabled_list = self.client.get_enabled_list()
        self._last_update_text = time.strftime("%H:%M:%S")
        self.on_robot_polled()

    def on_robot_polled(self) -> None:
        pass

    def on_camera_bundle(self, _bundle: D405FrameBundle) -> None:
        pass

    def get_display_images(self, bundle: D405FrameBundle) -> tuple[object, Optional[object]]:
        return bundle.color_rgb, bundle.depth_visual_rgb if self.show_depth else None

    def _update_camera_frame(self) -> None:
        if not self._camera_connected:
            return
        bundle = self._camera.read_frames()
        if bundle is None:
            self._camera_status_text = "Streaming error"
            return
        self._camera_bundle = bundle
        self._camera_frame_text = f"{bundle.width}x{bundle.height} @ {self.args.camera_fps} fps"
        self._camera_status_text = "Streaming"
        self._camera_serial_text = bundle.serial
        self.on_camera_bundle(bundle)
        color_rgb, depth_rgb = self.get_display_images(bundle)
        self._color_photo, self._color_view_info = self._render_canvas_image(self.color_canvas, color_rgb)
        if self.show_depth and self.depth_canvas is not None and depth_rgb is not None:
            self._depth_photo, self._depth_view_info = self._render_canvas_image(self.depth_canvas, depth_rgb)
        self._draw_hover_overlay()

    def _render_canvas_image(self, canvas: tk.Canvas, image_rgb):
        canvas.delete("all")
        pil_image = Image.fromarray(image_rgb)
        display_image, view_info = self._fit_image(canvas, pil_image)
        photo = ImageTk.PhotoImage(display_image)
        canvas_width, canvas_height = self._canvas_display_size(canvas)
        canvas.create_image(canvas_width / 2, canvas_height / 2, image=photo, anchor="center", tags=("frame",))
        return photo, view_info

    def _fit_image(self, canvas: tk.Canvas, image: Image.Image):
        src_width, src_height = image.size
        canvas_width, canvas_height = self._canvas_display_size(canvas)
        scale = min(canvas_width / src_width, canvas_height / src_height)
        disp_width = max(1, int(round(src_width * scale)))
        disp_height = max(1, int(round(src_height * scale)))
        resized = image.resize((disp_width, disp_height), Image.Resampling.BILINEAR)
        offset_x = (canvas_width - disp_width) // 2
        offset_y = (canvas_height - disp_height) // 2
        background = Image.new("RGB", (canvas_width, canvas_height), color=(0, 0, 0))
        background.paste(resized, (offset_x, offset_y))
        return background, {
            "src_width": src_width,
            "src_height": src_height,
            "disp_width": disp_width,
            "disp_height": disp_height,
            "offset_x": offset_x,
            "offset_y": offset_y,
        }

    def _canvas_display_size(self, canvas: tk.Canvas) -> tuple[int, int]:
        width = max(200, int(canvas.winfo_width() or DEFAULT_VIEWER_WIDTH))
        height = max(140, int(canvas.winfo_height() or DEFAULT_VIEWER_HEIGHT))
        return width, height

    def _draw_canvas_placeholder(self, canvas: tk.Canvas, text: str) -> None:
        canvas.delete("all")
        width, height = self._canvas_display_size(canvas)
        canvas.create_text(width / 2, height / 2, text=text, fill="white")

    def _on_display_canvas_resize(self, _event) -> None:
        if self._camera_bundle is None:
            return
        color_rgb, depth_rgb = self.get_display_images(self._camera_bundle)
        self._color_photo, self._color_view_info = self._render_canvas_image(self.color_canvas, color_rgb)
        if self.show_depth and self.depth_canvas is not None and depth_rgb is not None:
            self._depth_photo, self._depth_view_info = self._render_canvas_image(self.depth_canvas, depth_rgb)
        self._draw_hover_overlay()

    def _on_left_frame_configure(self, _event) -> None:
        if self._left_scroll_canvas is None:
            return
        self._left_scroll_canvas.configure(scrollregion=self._left_scroll_canvas.bbox("all"))

    def _on_left_canvas_configure(self, event) -> None:
        if self._left_scroll_canvas is None or self._left_scroll_window_id is None:
            return
        self._left_scroll_canvas.itemconfigure(self._left_scroll_window_id, width=event.width)

    def _bind_left_mousewheel(self, _event) -> None:
        if self._left_scroll_canvas is None:
            return
        self._left_scroll_canvas.bind_all("<MouseWheel>", self._on_left_mousewheel)
        self._left_scroll_canvas.bind_all("<Button-4>", self._on_left_mousewheel)
        self._left_scroll_canvas.bind_all("<Button-5>", self._on_left_mousewheel)

    def _unbind_left_mousewheel(self, _event) -> None:
        if self._left_scroll_canvas is None:
            return
        self._left_scroll_canvas.unbind_all("<MouseWheel>")
        self._left_scroll_canvas.unbind_all("<Button-4>")
        self._left_scroll_canvas.unbind_all("<Button-5>")

    def _on_left_mousewheel(self, event) -> None:
        if self._left_scroll_canvas is None:
            return
        if hasattr(event, "delta") and event.delta:
            direction = -1 if event.delta > 0 else 1
        elif getattr(event, "num", None) == 4:
            direction = -1
        else:
            direction = 1
        self._left_scroll_canvas.yview_scroll(direction, "units")

    def _on_canvas_motion(self, viewer_name: str, event) -> None:
        view_info = self._color_view_info if viewer_name == "color" else self._depth_view_info
        if view_info is None or self._camera_bundle is None:
            return
        src_point = self._display_to_source(view_info, event.x, event.y)
        if src_point is None:
            self._hover_pixel = None
            self._hover_text = "pixel=(--, --) depth=-- point=(--, --, --)"
        else:
            self._hover_pixel = src_point
            self._hover_text = self._format_hover(self._camera.query_point(*src_point))
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
        canvases = [self.color_canvas]
        if self.depth_canvas is not None:
            canvases.append(self.depth_canvas)
        for canvas in canvases:
            canvas.delete("overlay")
        if self._hover_pixel is None or self._color_view_info is None:
            return
        color_x, color_y = self._source_to_display(self._color_view_info, *self._hover_pixel)
        self._draw_crosshair(self.color_canvas, color_x, color_y)
        if self.depth_canvas is not None and self._depth_view_info is not None:
            depth_x, depth_y = self._source_to_display(self._depth_view_info, *self._hover_pixel)
            self._draw_crosshair(self.depth_canvas, depth_x, depth_y)

    def _draw_crosshair(self, canvas: tk.Canvas, x: float, y: float) -> None:
        color = "#f59e0b"
        canvas.create_line(x - 12, y, x + 12, y, fill=color, width=1, tags=("overlay",))
        canvas.create_line(x, y - 12, x, y + 12, fill=color, width=1, tags=("overlay",))
        canvas.create_oval(x - 3, y - 3, x + 3, y + 3, outline=color, width=1, tags=("overlay",))

    def refresh_ui(self) -> None:
        self.connection_var.set("Connected" if self._connected else "Disconnected")
        self.firmware_var.set(self.client.software_version if self.use_robot and self._connected else "unknown")
        self.mode_var.set(self._robot_status_text)
        self.enabled_var.set(str(self._enabled_list))
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
            else:
                value = pose[idx]
                self.pose_vars[idx].set(
                    f"{value:.4f} m" if idx < 3 else f"{value:.4f} rad ({math.degrees(value):.1f} deg)"
                )

        joints = self._joint_angles
        for idx in range(6):
            if joints is None:
                self.joint_rad_vars[idx].set("--")
                self.joint_deg_vars[idx].set("--")
            else:
                value = joints[idx]
                self.joint_rad_vars[idx].set(f"{value:.4f}")
                self.joint_deg_vars[idx].set(f"{math.degrees(value):.2f}")

        self.refresh_custom_ui()
        self.root.after(100, self.refresh_ui)

    def refresh_custom_ui(self) -> None:
        pass

    def _schedule_poll(self) -> None:
        if self._poll_after_id is not None:
            return
        self._poll_once()
        self._camera_once()

    def _poll_once(self) -> None:
        if self.use_robot and self._connected and not self._busy:
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
        if self._camera_connected and not self._busy:
            try:
                self._update_camera_frame()
            except Exception as exc:
                self._camera_status_text = f"Read error: {type(exc).__name__}"
                self._camera_serial_text = str(exc)
        interval_ms = int(max(50, int(getattr(self.args, "camera_update_interval_ms", 100))))
        self._camera_after_id = self.root.after(interval_ms, self._camera_once)

    def _handle_key_event(self, event) -> None:
        key = event.keysym.lower()
        try:
            self.handle_key_action(key)
        except Exception as exc:
            self._last_event_text = f"{type(exc).__name__}: {exc}"

    def handle_key_action(self, _key: str) -> None:
        pass

    def on_close(self) -> None:
        if self._poll_after_id is not None:
            self.root.after_cancel(self._poll_after_id)
            self._poll_after_id = None
        if self._camera_after_id is not None:
            self.root.after_cancel(self._camera_after_id)
            self._camera_after_id = None
        try:
            if self.use_robot:
                self.client.disconnect()
            self._camera.close()
        finally:
            self.root.destroy()
