# Quick Start Workflow

This guide is the shortest path from a fresh clone to the current end-to-end demo workflow in this repository.

If this is your first time reading the project, start with:

- [onboarding.md](onboarding.md)

## Goal

After following this document, you should be able to:

1. clone the repository
2. set up the Python environment
3. verify D405 and CAN connectivity
4. print the ChArUco board
5. complete intrinsics calibration
6. complete hand-eye calibration
7. validate the hand-eye result
8. estimate a TCP offset for the gripper center
9. capture `home / observe / drop_pose`
10. run the monitor and click-pick demos

## 1. Clone The Repository

```bash
git clone https://github.com/xsb2lyang/piper-vision-grasp-new.git
cd piper-vision-grasp-new
```

## 2. Install System Dependencies

See [installation.md](installation.md) for the full setup. The minimum path is:

```bash
sudo apt update
sudo apt install -y v4l-utils
sudo apt install -y librealsense2 librealsense2-dev librealsense2-utils librealsense2-udev-rules
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 3. Create The Python Environment

```bash
./scripts/setup_env.sh
```

If you need to rebuild the environment:

```bash
./scripts/setup_env.sh --recreate
```

## 4. Verify Hardware

### D405

```bash
rs-enumerate-devices
```

### Robot CAN

Make sure the robot is powered on and the CAN interface is up. In this project the default channel is `can0`.

## 5. Print The Calibration Board

The default printable board is already included in the repo:

- [assets/calibration/charuco_default/charuco_board.pdf](../assets/calibration/charuco_default/charuco_board.pdf)
- [assets/calibration/charuco_default/charuco_board.yaml](../assets/calibration/charuco_default/charuco_board.yaml)

Print the PDF at **100% scale** and verify one square is exactly `30 mm`.

More details:

- [assets/calibration/charuco_default/README.md](../assets/calibration/charuco_default/README.md)

## 6. Run Camera Intrinsics Calibration

```bash
./scripts/run_calibrate_intrinsics.sh
```

Output:

```text
configs/calibration/camera_intrinsics.yaml
```

## 7. Run Hand-Eye Calibration

```bash
./scripts/run_calibrate_handeye.sh
```

Output:

```text
configs/calibration/handeye_active.yaml
```

## 8. Validate Hand-Eye

```bash
./scripts/run_validate_handeye.sh
```

Goal:

- move to several viewpoints
- verify that the board pose in the base frame stays stable

## 9. Estimate TCP Offset

If the default TCP does not correspond to the gripper grasp center, estimate a better tool offset:

```bash
./scripts/run_estimate_tcp_offset.sh
```

This writes:

```text
configs/calibration/tcp_offset_estimate.yaml
```

If you accept the estimate, copy it into:

```text
configs/robot/piper_default.yaml
```

Then repeat:

- hand-eye calibration
- hand-eye validation
- keypoint capture

## 10. Capture Keypoints

Capture the standard task poses:

```bash
./scripts/run_capture_keypoints.sh
```

At minimum, save:

- `home`
- `observe`
- `drop_pose`

Output:

```text
configs/task/pick_demo_points.yaml
```

The repository also includes a tracked reference template:

```text
configs/task/pick_demo_template.yaml
```

Recommended practice:

- Use the included template as the default starting point when you first clone the project.
- Capture your own `configs/task/pick_demo_points.yaml` when you want to override the template with poses tuned to your robot and workspace.

## 11. Run The Monitor

Robot + camera monitor:

```bash
./scripts/run_monitor.sh
```

With YOLO11 overlay:

```bash
./scripts/run_monitor.sh --yolo
```

## 12. Run The Click-Pick Demo

First preview only:

```bash
./scripts/run_click_pick_demo.sh --yolo --dry-run
```

Then real execution:

```bash
./scripts/run_click_pick_demo.sh --yolo --no-dry-run
```

## Recommended Reading Order

1. [installation.md](installation.md)
2. [handeye.md](handeye.md)
3. [tcp_offset.md](tcp_offset.md)
4. [keypoints.md](keypoints.md)
5. [pick_demo.md](pick_demo.md)

## Expected Persistent Files

By the time the full workflow is complete, you should have these files:

- `configs/calibration/camera_intrinsics.yaml`
- `configs/calibration/handeye_active.yaml`
- `configs/task/pick_demo_points.yaml`

Optional generated files:

- `configs/calibration/handeye_tsai.yaml`
- `configs/calibration/handeye_park.yaml`
- `configs/calibration/tcp_offset_estimate.yaml`

## Notes

- If you change the TCP offset, you must redo:
  - hand-eye calibration
  - hand-eye validation
  - keypoint capture
- If you change the observe pose, you may need to retune the click-pick offset in the task config.
