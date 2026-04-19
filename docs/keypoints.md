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

Typical points to capture first:

- `home`
- `observe`
- `drop_pose`

You can also add custom names such as:

- `staging`
- `inspect`
- `bin_left`
- `bin_right`

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
