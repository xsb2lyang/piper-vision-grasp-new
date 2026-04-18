from __future__ import annotations

import argparse

from piper_app.calibration.gui_intrinsics import run
from piper_app.config import load_project_defaults, repo_root


def build_parser() -> argparse.ArgumentParser:
    defaults = load_project_defaults()
    camera_defaults = defaults["camera"]
    calibration_defaults = defaults["calibration"]

    parser = argparse.ArgumentParser(description="ChArUco-based D405 camera intrinsics calibration GUI.")
    parser.add_argument("--board-config", type=str, default=calibration_defaults["board_config_path"])
    parser.add_argument(
        "--session-base-dir",
        type=str,
        default=calibration_defaults["session_base_dir"],
        help="Base directory for saved calibration sessions.",
    )
    parser.add_argument(
        "--intrinsics-output-path",
        type=str,
        default=str(repo_root() / calibration_defaults["results_dir"] / "camera_intrinsics.yaml"),
        help="Output YAML for the calibrated camera intrinsics.",
    )
    parser.add_argument(
        "--camera-serial",
        type=str,
        default=camera_defaults.get("serial", "auto"),
        help="RealSense serial number, or auto.",
    )
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
        "--intrinsics-min-corners",
        type=int,
        default=calibration_defaults.get("intrinsics_min_corners", 12),
    )
    parser.add_argument(
        "--intrinsics-min-samples",
        type=int,
        default=calibration_defaults.get("intrinsics_min_samples", 12),
    )
    parser.add_argument(
        "--intrinsics-far-area-ratio",
        type=float,
        default=calibration_defaults.get("intrinsics_far_area_ratio", 0.05),
    )
    parser.add_argument(
        "--intrinsics-near-area-ratio",
        type=float,
        default=calibration_defaults.get("intrinsics_near_area_ratio", 0.60),
    )
    parser.add_argument(
        "--intrinsics-duplicate-threshold",
        type=float,
        default=calibration_defaults.get("intrinsics_duplicate_threshold", 0.08),
    )
    return parser


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
