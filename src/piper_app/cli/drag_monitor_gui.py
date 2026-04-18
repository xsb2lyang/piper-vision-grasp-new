from __future__ import annotations

import argparse

from pyAgxArm import ArmModel

from piper_app.config import load_project_defaults
from piper_app.monitor.gui import run
from piper_app.robot.factory import resolve_can_backend_defaults


def build_parser() -> argparse.ArgumentParser:
    defaults = load_project_defaults()
    robot_defaults = defaults["robot"]
    teleop_defaults = defaults["teleop"]
    camera_defaults = defaults["camera"]
    interface, channel = resolve_can_backend_defaults(
        robot_defaults.get("interface"),
        robot_defaults.get("channel"),
    )

    parser = argparse.ArgumentParser(
        description="Read-only GUI monitor for hand-guided Piper observation."
    )
    parser.add_argument(
        "--robot",
        type=str,
        default=robot_defaults.get("robot", ArmModel.PIPER),
        choices=[ArmModel.PIPER, ArmModel.PIPER_H, ArmModel.PIPER_L, ArmModel.PIPER_X],
        help="Piper-series robot model.",
    )
    parser.add_argument("--interface", type=str, default=interface, help="CAN interface backend.")
    parser.add_argument(
        "--channel",
        type=str,
        default=channel,
        help="CAN channel, for example can0 on Linux.",
    )
    parser.add_argument("--bitrate", type=int, default=robot_defaults.get("bitrate", 1_000_000))
    parser.add_argument(
        "--poll-interval-s",
        type=float,
        default=teleop_defaults.get("poll_interval_s", 0.2),
        help="Robot status poll interval in seconds.",
    )
    parser.add_argument(
        "--firmware-timeout",
        type=float,
        default=robot_defaults.get("firmware_timeout", 5.0),
        help="Timeout in seconds for auto firmware probing.",
    )
    parser.add_argument(
        "--camera",
        action=argparse.BooleanOptionalAction,
        default=camera_defaults.get("enabled", True),
        help="Enable or disable the D405 camera panel.",
    )
    parser.add_argument(
        "--camera-serial",
        type=str,
        default=camera_defaults.get("serial", "auto"),
        help="RealSense serial number, or auto.",
    )
    parser.add_argument(
        "--camera-width",
        type=int,
        default=camera_defaults.get("width", 640),
        help="Requested D405 color/depth width.",
    )
    parser.add_argument(
        "--camera-height",
        type=int,
        default=camera_defaults.get("height", 480),
        help="Requested D405 color/depth height.",
    )
    parser.add_argument(
        "--camera-fps",
        type=int,
        default=camera_defaults.get("fps", 30),
        help="Requested D405 color/depth frame rate.",
    )
    parser.add_argument(
        "--depth-min-m",
        type=float,
        default=camera_defaults.get("depth_min_m", 0.05),
        help="Minimum depth value for visualization, in meters.",
    )
    parser.add_argument(
        "--depth-max-m",
        type=float,
        default=camera_defaults.get("depth_max_m", 0.50),
        help="Maximum depth value for visualization, in meters.",
    )
    parser.add_argument(
        "--camera-update-interval-ms",
        type=int,
        default=camera_defaults.get("update_interval_ms", 100),
        help="GUI camera refresh interval in milliseconds.",
    )
    return parser


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
