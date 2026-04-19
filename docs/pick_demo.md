# Click Pick Demo

The first pick-and-place demo uses a conservative tabletop flow:

1. Move the robot to `observe`
2. Click a target in the D405 image
3. Convert the clicked depth pixel into a base-frame 3D point using the active hand-eye result
4. Move to `pregrasp`
5. Descend linearly
6. Close the gripper
7. Lift
8. Move to `drop_pose`
9. Open the gripper
10. Return to `observe`

Launch it with:

```bash
./scripts/run_click_pick_demo.sh
```

Recommended first use:

- Keep the default `Dry-run` enabled and verify that clicking produces a reasonable plan.
- Move to `Observe`.
- Click a target on the tabletop.
- Confirm the computed base point and plan in the left status panel.
- Disable `Dry-run` only after the preview looks correct.

The demo reads:

- `configs/task/pick_demo_points.yaml`
- `configs/calibration/handeye_active.yaml`

Key keyboard shortcuts:

- `h`: move to `home`
- `o`: move to `observe`
- `g`: open gripper
- `p` or `Enter`: execute the pick sequence
- `c`: clear the current target
