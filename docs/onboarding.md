# First-Time Onboarding

This document is for someone opening this repository for the first time and wanting to reproduce the current workflow step by step.

## Who This Is For

Use this document if you want to:

- clone the repository and understand where to start
- follow the docs in the right order
- reproduce the current Piper + D405 + hand-eye + click-pick setup

## Recommended Reading Order

Read the project in this order:

1. [README.md](../README.md)
2. [installation.md](installation.md)
3. [quickstart.md](quickstart.md)
4. [reproduce_checklist.md](reproduce_checklist.md)
5. [handeye.md](handeye.md)
6. [tcp_offset.md](tcp_offset.md)
7. [keypoints.md](keypoints.md)
8. [pick_demo.md](pick_demo.md)

## What To Do Step By Step

### Step 1. Clone The Repository

```bash
git clone https://github.com/xsb2lyang/piper-vision-grasp-new.git
cd piper-vision-grasp-new
```

### Step 2. Read The Root README

Start from [README.md](../README.md).

At this stage you only need to understand:

- what the project does
- where the main docs are
- which scripts are the standard entrypoints

### Step 3. Set Up The Environment

Follow [installation.md](installation.md).

The shortest path is:

```bash
./scripts/setup_env.sh
```

After that, confirm:

- the `.venv` exists
- `rs-enumerate-devices` can see the D405
- the robot CAN interface is available

Then run:

```bash
./scripts/run_doctor.sh
```

### Step 4. Print The ChArUco Board

Use the included printable asset:

- [../assets/calibration/charuco_default/charuco_board.pdf](../assets/calibration/charuco_default/charuco_board.pdf)

Before calibration, read:

- [../assets/calibration/charuco_default/README.md](../assets/calibration/charuco_default/README.md)

### Step 5. Follow The Quick Start Once

Now switch to [quickstart.md](quickstart.md).

This document is the best “do this, then do that” checklist for reproducing the current project state.

### Step 6. Do Calibration In Order

Use [handeye.md](handeye.md) and run:

```bash
./scripts/run_calibrate_intrinsics.sh
./scripts/run_calibrate_handeye.sh
./scripts/run_validate_handeye.sh
```

### Step 7. If Needed, Estimate TCP Offset

If the gripper center is not aligned with the business TCP, read [tcp_offset.md](tcp_offset.md) and run:

```bash
./scripts/run_estimate_tcp_offset.sh
```

If you adopt a new TCP offset, redo:

- hand-eye calibration
- hand-eye validation
- keypoint capture

### Step 8. Capture Key Poses

Read [keypoints.md](keypoints.md) and run:

```bash
./scripts/run_capture_keypoints.sh
```

Save at least:

- `home`
- `observe`
- `drop_pose`

You can also start from the tracked repository template:

- `configs/task/pick_demo_template.yaml`

The demos prefer your local `configs/task/pick_demo_points.yaml`. If you have not captured your own poses yet, they fall back to the tracked template automatically.

### Step 9. Verify The Monitor

Run:

```bash
./scripts/run_monitor.sh
./scripts/run_monitor.sh --yolo
```

Make sure:

- robot state updates normally
- D405 image is visible
- YOLO boxes appear when enabled

### Step 10. Run The Pick Demo

Finally, read [pick_demo.md](pick_demo.md) and run:

```bash
./scripts/run_click_pick_demo.sh --yolo --dry-run
./scripts/run_click_pick_demo.sh --yolo --no-dry-run
```

## Practical Advice

- Do not skip hand-eye validation after calibration.
- If you change the TCP offset, re-run calibration-related steps.
- If you change `observe`, you may need to retune the click-pick offset in the task config.
- When in doubt, return to [quickstart.md](quickstart.md) and replay the sequence from there.
