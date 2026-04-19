# YOLO Target Pick Demo

This demo is a separate workflow from the original click-to-pick window.

Use it when you want to:

- pick an object by class name instead of manually clicking a pixel
- freeze the current camera frame
- auto-select the matching detection box center as the grasp point

## Launch

```bash
./scripts/run_yolo_target_pick_demo.sh --no-dry-run
```

Safe preview:

```bash
./scripts/run_yolo_target_pick_demo.sh --dry-run
```

## Workflow

1. Move the robot to the saved `observe` pose.
2. Choose a YOLO class from the dropdown, or type a recognized class name.
3. Press `Pause / Freeze`.
4. If the paused frame contains the chosen object, the demo auto-selects the bbox center.
5. Press `Execute Pick`.

If the paused frame does not contain the chosen object, the demo will refuse to run and show a clear message in `Last Event`.

## Notes

- This demo does not require manual point clicking.
- It reuses the same hand-eye, keypoint, TCP, and grasp configuration as the original click-pick demo.
- The original click-pick demo remains unchanged and is still launched with:

```bash
./scripts/run_click_pick_demo.sh --yolo --no-dry-run
```

