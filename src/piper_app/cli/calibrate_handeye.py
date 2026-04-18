from __future__ import annotations

import argparse

from pyAgxArm import ArmModel

from piper_app.calibration.gui_handeye import run
from piper_app.config import load_project_defaults, repo_root
from piper_app.robot.factory import resolve_can_backend_defaults


def build_parser() -> argparse.ArgumentParser:
    defaults = load_project_defaults()
    robot_defaults = defaults["robot"]
    teleop_defaults = defaults["teleop"]
    camera_defaults = defaults["camera"]
    calibration_defaults = defaults["calibration"]
    interface, channel = resolve_can_backend_defaults(
        robot_defaults.get("interface"),
        robot_defaults.get("channel"),
    )

    parser = argparse.ArgumentParser(description="Eye-in-hand ChArUco hand-eye calibration GUI for Piper.")
    parser.add_argument(
        "--robot",
        type=str,
        default=robot_defaults.get("robot", ArmModel.PIPER),
        choices=[ArmModel.PIPER, ArmModel.PIPER_H, ArmModel.PIPER_L, ArmModel.PIPER_X],
    )
    parser.add_argument("--interface", type=str, default=interface)
    parser.add_argument("--channel", type=str, default=channel)
    parser.add_argument("--bitrate", type=int, default=robot_defaults.get("bitrate", 1_000_000))
    parser.add_argument("--poll-interval-s", type=float, default=teleop_defaults.get("poll_interval_s", 0.2))
    parser.add_argument("--firmware-timeout", type=float, default=robot_defaults.get("firmware_timeout", 5.0))

    parser.add_argument("--board-config", type=str, default=calibration_defaults["board_config_path"])
    parser.add_argument(
        "--intrinsics-path",
        type=str,
        default=str(repo_root() / calibration_defaults["results_dir"] / "camera_intrinsics.yaml"),
        help="Input intrinsics YAML produced by the camera intrinsics tool.",
    )
    parser.add_argument(
        "--session-base-dir",
        type=str,
        default=calibration_defaults["session_base_dir"],
        help="Base directory for saved hand-eye sessions.",
    )
    parser.add_argument(
        "--handeye-tsai-output-path",
        type=str,
        default=str(repo_root() / calibration_defaults["results_dir"] / "handeye_tsai.yaml"),
    )
    parser.add_argument(
        "--handeye-park-output-path",
        type=str,
        default=str(repo_root() / calibration_defaults["results_dir"] / "handeye_park.yaml"),
    )
    parser.add_argument(
        "--handeye-active-output-path",
        type=str,
        default=str(repo_root() / calibration_defaults["results_dir"] / "handeye_active.yaml"),
    )
    parser.add_argument(
        "--handeye-methods",
        type=str,
        default=",".join(calibration_defaults.get("default_method_names", ["Tsai", "Park"])),
        help="Comma-separated OpenCV hand-eye method names to evaluate.",
    )

    parser.add_argument("--camera-serial", type=str, default=camera_defaults.get("serial", "auto"))
    parser.add_argument("--camera-width", type=int, default=camera_defaults.get("width", 640))
    parser.add_argument("--camera-height", type=int, default=camera_defaults.get("height", 480))
    parser.add_argument("--camera-fps", type=int, default=camera_defaults.get("fps", 30))
    parser.add_argument("--depth-min-m", type=float, default=camera_defaults.get("depth_min_m", 0.05))
    parser.add_argument("--depth-max-m", type=float, default=camera_defaults.get("depth_max_m", 0.50))
    parser.add_argument(
        "--camera-update-interval-ms",
        type=int,
        default=camera_defaults.get("update_interval_ms", 100),
    )

    parser.add_argument(
        "--handeye-min-corners",
        type=int,
        default=calibration_defaults.get("handeye_min_corners", 12),
    )
    parser.add_argument(
        "--handeye-min-samples",
        type=int,
        default=calibration_defaults.get("handeye_min_samples", 8),
    )
    parser.add_argument(
        "--handeye-near-z-m",
        type=float,
        default=calibration_defaults.get("handeye_near_z_m", 0.18),
    )
    parser.add_argument(
        "--handeye-far-z-m",
        type=float,
        default=calibration_defaults.get("handeye_far_z_m", 0.70),
    )
    parser.add_argument(
        "--handeye-min-translation-delta-m",
        type=float,
        default=calibration_defaults.get("handeye_min_translation_delta_m", 0.03),
    )
    parser.add_argument(
        "--handeye-min-rotation-delta-deg",
        type=float,
        default=calibration_defaults.get("handeye_min_rotation_delta_deg", 8.0),
    )
    return parser


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
