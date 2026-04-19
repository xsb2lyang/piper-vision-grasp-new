from __future__ import annotations

import argparse

from pyAgxArm import ArmModel

from piper_app.config import load_project_defaults
from piper_app.keypoints.gui import run
from piper_app.robot.factory import resolve_can_backend_defaults


def build_parser() -> argparse.ArgumentParser:
    defaults = load_project_defaults()
    robot_defaults = defaults["robot"]
    task_defaults = defaults["task"]
    interface, channel = resolve_can_backend_defaults(
        robot_defaults.get("interface"),
        robot_defaults.get("channel"),
    )

    parser = argparse.ArgumentParser(description="Read-only GUI for capturing Piper key poses into a YAML config.")
    parser.add_argument(
        "--robot",
        type=str,
        default=robot_defaults.get("robot", ArmModel.PIPER),
        choices=[ArmModel.PIPER, ArmModel.PIPER_H, ArmModel.PIPER_L, ArmModel.PIPER_X],
    )
    parser.add_argument("--interface", type=str, default=interface)
    parser.add_argument("--channel", type=str, default=channel)
    parser.add_argument("--bitrate", type=int, default=robot_defaults.get("bitrate", 1_000_000))
    parser.add_argument(
        "--tcp-offset",
        type=float,
        nargs=6,
        metavar=("X", "Y", "Z", "ROLL", "PITCH", "YAW"),
        default=robot_defaults.get("tcp_offset", [0.0] * 6),
    )
    parser.add_argument(
        "--firmware-timeout",
        type=float,
        default=robot_defaults.get("firmware_timeout", 5.0),
    )
    parser.add_argument(
        "--poll-interval-s",
        type=float,
        default=0.2,
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default=task_defaults.get("output_path", "configs/task/pick_demo_points.yaml"),
    )
    parser.add_argument(
        "--point-names",
        type=str,
        nargs="+",
        default=task_defaults.get("point_names", ["home", "observe", "drop_pose"]),
    )
    parser.add_argument(
        "--default-note",
        type=str,
        default=task_defaults.get("default_note", ""),
    )
    parser.set_defaults(task_defaults=task_defaults.get("task_defaults", {}))
    return parser


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
