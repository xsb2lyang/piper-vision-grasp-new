# Reproducibility Checklist

Use this checklist when a new user receives:

- a new computer
- a new Piper robot
- a D405 camera

and wants to reproduce the current workflow in this repository.

## What Must Be Re-Done On New Hardware

These steps are hardware-specific and should be treated as required on a new setup:

- camera intrinsics calibration
- hand-eye calibration
- hand-eye validation
- TCP offset estimation, unless your tool mounting is truly identical and already verified
- local keypoint capture, unless you intentionally want to start from the tracked template
- click-pick offset tuning if your camera viewpoint or observe pose changes

## What Can Be Reused Directly

These repository assets are meant to work immediately after `git clone`:

- environment setup script: `./scripts/setup_env.sh`
- doctor script: `./scripts/run_doctor.sh`
- CAN bringup helper: `sudo ./scripts/bringup_can.sh`
- printable ChArUco board under `assets/calibration/charuco_default/`
- tracked keypoint template: `configs/task/pick_demo_template.yaml`
- default YOLO11 weights path: `third_party/yolo/新松-检测/yolo11m.pt`

## First Bring-Up Checklist

1. Clone the repository and enter it.
2. Install system dependencies from [installation.md](installation.md).
3. Run `./scripts/setup_env.sh`.
4. Run `./scripts/run_doctor.sh`.
5. If CAN is present but down, run `sudo ./scripts/bringup_can.sh can0 1000000`.
6. Verify D405 with `rs-enumerate-devices`.
7. Print the ChArUco board at 100% scale.
8. Run intrinsics calibration.
9. Run hand-eye calibration.
10. Run hand-eye validation.
11. Estimate TCP offset if the gripper center is not already verified.
12. Either:
   - use the tracked `configs/task/pick_demo_template.yaml`, or
   - capture your own `configs/task/pick_demo_points.yaml`
13. Run the monitor.
14. Run click-pick in `--dry-run` first.
15. Run real grasping only after the dry-run plan looks correct.

## Common Failure Points

- `pyrealsense2` imports fail:
  - rebuild `.venv` with `./scripts/setup_env.sh --recreate`
- D405 is not detected:
  - check the USB cable, USB 3 port, and `librealsense2` installation
- `can0` is missing or down:
  - verify the USB-CAN adapter and run `sudo ./scripts/bringup_can.sh`
- the robot reaches weird poses:
  - re-capture `observe`, `staging`, `drop_staging`, and `drop_pose`
- the grasp point is consistently biased:
  - re-check TCP offset, hand-eye, and `pick_point_offset_m`

## Recommended Acceptance Gate

For a new hardware setup, consider the project “reproduced” only after all of these pass:

- `./scripts/run_doctor.sh`
- `./scripts/run_monitor.sh --yolo`
- `./scripts/run_calibrate_intrinsics.sh`
- `./scripts/run_calibrate_handeye.sh`
- `./scripts/run_validate_handeye.sh`
- `./scripts/run_click_pick_demo.sh --yolo --dry-run`
- at least one successful real grasp
