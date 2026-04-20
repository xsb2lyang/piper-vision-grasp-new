# piper-vision-grasp-new

[简体中文](README.zh-CN.md)

An application-layer workspace for **Piper eye-in-hand vision grasping** built on top of:

- a vendored `pyAgxArm` SDK in `third_party/pyAgxArm`
- a vendored YOLO codebase in `third_party/yolo/新松-检测`
- our own calibration, monitoring, teleoperation, and click-to-pick tools in `src/piper_app`

## Highlights

- D405/D435-style RealSense camera support through `pyrealsense2`
- ChArUco intrinsics calibration and eye-in-hand hand-eye calibration
- Read-only robot + camera monitor with optional YOLO11 detection overlay
- TCP offset estimation workflow for gripper-center alignment
- Keypoint capture for `home`, `observe`, and `drop_pose`
- Click-to-pick tabletop demo with depth, hand-eye, and gripper integration

## Repository Layout

```text
.
├── apps/                  # Thin local launchers
├── assets/                # Calibration boards and static assets
├── configs/               # Robot, camera, calibration, and task configs
├── docs/                  # Usage guides
├── scripts/               # Recommended entrypoint scripts
├── src/piper_app/         # Application-layer Python package
├── tests/                 # Lightweight import and config checks
└── third_party/           # Vendored upstream dependencies
```

## Quick Start

Recommended environment:

- Ubuntu
- `uv`
- Python `3.10`
- repo-local `.venv`

Create or recreate the environment:

```bash
./scripts/setup_env.sh
./scripts/setup_env.sh --recreate
```

Run the reproducibility doctor:

```bash
./scripts/run_doctor.sh
```

When you first connect the robot to a new computer, run these two CAN commands first:

```bash
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can0 up
```

If you prefer using the project helper script, run:

```bash
sudo ./scripts/bringup_can.sh can0 1000000
```

Start the monitor:

```bash
./scripts/run_monitor.sh
./scripts/run_monitor.sh --yolo
```

Start the click-pick demo:

```bash
./scripts/run_click_pick_demo.sh --yolo --dry-run
./scripts/run_click_pick_demo.sh --yolo --no-dry-run
```

## Core Workflows

### 1. Calibration

```bash
./scripts/run_calibrate_intrinsics.sh
./scripts/run_calibrate_handeye.sh
./scripts/run_validate_handeye.sh
./scripts/run_estimate_tcp_offset.sh
```

### 2. Keypoint Capture

```bash
./scripts/run_capture_keypoints.sh
```

Capture and save:

- `home`
- `observe`
- `drop_pose`

### 3. Teleoperation

```bash
./scripts/run_gui.sh
./scripts/run_keyboard.sh
```

### 4. Monitoring and Perception

```bash
./scripts/run_monitor.sh
./scripts/run_monitor.sh --yolo
```

### 5. Vision-Assisted Pick Demo

```bash
./scripts/run_click_pick_demo.sh --yolo --dry-run
./scripts/run_click_pick_demo.sh --yolo --no-dry-run
```

## Documentation

- [Documentation Index](docs/README.md)
- [中文文档导航](docs/README.zh-CN.md)
- [First-Time Onboarding](docs/onboarding.md)
- [第一次上手指南](docs/onboarding.zh-CN.md)
- [Quick Start Workflow](docs/quickstart.md)
- [快速上手流程](docs/quickstart.zh-CN.md)
- [Reproducibility Checklist](docs/reproduce_checklist.md)
- [新设备复现检查清单](docs/reproduce_checklist.zh-CN.md)
- [Installation](docs/installation.md)
- [Teleoperation](docs/teleop.md)
- [Hand-Eye Calibration](docs/handeye.md)
- [Keypoint Capture](docs/keypoints.md)
- [TCP Offset Estimation](docs/tcp_offset.md)
- [Click Pick Demo](docs/pick_demo.md)
- [YOLO Target Pick Demo](docs/yolo_target_pick_demo.md)

## Printable Calibration Board

The default ChArUco board is already included in the repository for direct printing and reuse:

- [assets/calibration/charuco_default/charuco_board.pdf](assets/calibration/charuco_default/charuco_board.pdf)
- [assets/calibration/charuco_default/charuco_board.png](assets/calibration/charuco_default/charuco_board.png)
- [assets/calibration/charuco_default/charuco_board.yaml](assets/calibration/charuco_default/charuco_board.yaml)
- [assets/calibration/charuco_default/README.md](assets/calibration/charuco_default/README.md)

## Project Notes

- The top-level project name is **`piper-vision-grasp-new`**.
- `pyAgxArm` remains vendored under `third_party/pyAgxArm` as an upstream SDK dependency.
- The internal Python package name remains `piper_app` for now, while the repository and distribution metadata use the new project name.

## Acknowledgements

- `pyAgxArm` from AgileX Robotics
- `Ultralytics YOLO11`
- the local vendored YOLO workspace in `third_party/yolo/新松-检测`
