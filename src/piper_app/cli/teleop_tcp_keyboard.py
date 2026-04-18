from __future__ import annotations

import argparse

from pyAgxArm import ArmModel

from piper_app.config import load_project_defaults
from piper_app.robot.factory import resolve_can_backend_defaults
from piper_app.teleop.keyboard import run


def build_parser() -> argparse.ArgumentParser:
    defaults = load_project_defaults()
    robot_defaults = defaults["robot"]
    teleop_defaults = defaults["teleop"]
    interface, channel = resolve_can_backend_defaults(
        robot_defaults.get("interface"),
        robot_defaults.get("channel"),
    )

    parser = argparse.ArgumentParser(
        description="Keyboard TCP pose teleop for Piper-series robotic arms."
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
        "--speed-percent",
        type=int,
        default=teleop_defaults.get("speed_percent", 10),
        help="Robot speed percent for move_p mode.",
    )
    parser.add_argument(
        "--pos-step",
        type=float,
        default=teleop_defaults.get("pos_step_m", 0.005),
        help="TCP translation step in meters for each key press.",
    )
    parser.add_argument(
        "--rot-step-deg",
        type=float,
        default=teleop_defaults.get("rot_step_deg", 2.0),
        help="TCP rotation step in degrees for each key press.",
    )
    parser.add_argument(
        "--refresh-hz",
        type=float,
        default=teleop_defaults.get("refresh_hz", 5.0),
        help="UI refresh rate in Hz.",
    )
    parser.add_argument(
        "--tcp-offset",
        type=float,
        nargs=6,
        metavar=("X", "Y", "Z", "ROLL", "PITCH", "YAW"),
        default=robot_defaults.get("tcp_offset", [0.0] * 6),
        help="TCP offset in flange frame [m, m, m, rad, rad, rad].",
    )
    parser.add_argument(
        "--firmware-timeout",
        type=float,
        default=robot_defaults.get("firmware_timeout", 5.0),
        help="Timeout in seconds for auto firmware probing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Update target pose locally but do not send motion commands.",
    )
    return parser


def main() -> None:
    try:
        run(build_parser().parse_args())
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting teleop.")


if __name__ == "__main__":
    main()
