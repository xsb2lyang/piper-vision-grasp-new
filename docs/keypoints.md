# Keypoint Capture

This tool captures named robot poses into a YAML config for later pick-and-place scripts.

Launch:

```bash
./scripts/run_capture_keypoints.sh
```

Default output:

```text
configs/task/pick_demo_points.yaml
```

Repository-managed reference template:

```text
configs/task/pick_demo_template.yaml
```

Recommended usage:

- Use `configs/task/pick_demo_template.yaml` as the repo-provided starting point when you first clone the project.
- Capture your own `configs/task/pick_demo_points.yaml` when you want hardware-specific poses for your robot, camera mount, and workspace.
- The pick demos prefer your local `pick_demo_points.yaml`. If it does not exist, they fall back to the tracked template automatically.

Typical points to capture first:

- `home`
- `observe`
- `drop_pose`
- `staging`

You can also add custom names such as:

- `drop_staging`
- `inspect`
- `bin_left`
- `bin_right`

Recommended meaning:

- `staging`: transition waypoint after lifting and before moving into the place area
- `drop_staging`: optional second transition waypoint immediately before `drop_pose`

## What Gets Saved

Each named point stores:

- current TCP pose
- current joint angles
- note
- capture timestamp

The file also keeps task defaults such as:

- `pregrasp_offset_m`
- `descend_distance_m`
- `lift_distance_m`

## Suggested Workflow

1. Move the robot to a useful pose with your existing teleop tools.
2. Open the keypoint capture GUI.
3. Choose or type a point name.
4. Press `Capture / Update`.
5. Repeat for `home`, `observe`, and `drop_pose`.
6. Press `Save YAML`.

This tool is read-only with respect to motion. It does not move the robot.
