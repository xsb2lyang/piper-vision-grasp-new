# Hand-Eye Calibration

This workspace provides two calibration tools for the `eye-in-hand` Piper + D405 setup.

## Assets

The default ChArUco board is read from:

```text
assets/calibration/charuco_default/charuco_board.yaml
```

Expected board spec:

- `6 x 8`
- `DICT_4X4_50`
- square length `30 mm`
- marker length `22 mm`

## 1. Camera Intrinsics

Launch:

```bash
./scripts/run_calibrate_intrinsics.sh
```

Key bindings:

- `s`: capture a sample
- `d`: delete the last sample
- `c`: run calibration
- `r`: reset the session
- `q`: quit

Output:

```text
configs/calibration/camera_intrinsics.yaml
```

The GUI saves a session under:

```text
configs/calibration/sessions/<timestamp>_intrinsics/
```

Recommended capture strategy:

- vary distance, tilt, and in-plane rotation
- cover board center and edges of the image
- avoid collecting many nearly identical views

## 2. Hand-Eye Extrinsics

Prerequisite:

```text
configs/calibration/camera_intrinsics.yaml
```

Launch:

```bash
./scripts/run_calibrate_handeye.sh
```

Key bindings:

- `s`: capture a sample
- `d`: delete the last sample
- `c`: run hand-eye calibration
- `v`: show sample diversity summary
- `r`: reset the session
- `q`: quit

Each sample stores:

- color image
- depth image
- `T_base_tcp`
- `T_camera_board`
- capture metadata

Outputs:

```text
configs/calibration/handeye_tsai.yaml
configs/calibration/handeye_park.yaml
configs/calibration/handeye_active.yaml
```

The active result is chosen by board consistency. For each method, the tool evaluates:

```text
T_base_board = T_base_tcp @ T_tcp_camera @ T_camera_board
```

Because the board is fixed, the better method should produce a more consistent `T_base_board` across samples.

## 3. Hand-Eye Validation

Launch:

```bash
./scripts/run_validate_handeye.sh
```

This read-only window loads:

- `configs/calibration/camera_intrinsics.yaml`
- `configs/calibration/handeye_active.yaml`

It then computes the live board pose in the base frame:

```text
T_base_board = T_base_tcp @ T_tcp_camera @ T_camera_board
```

Recommended validation flow:

1. Move the wrist to a few different viewpoints.
2. Verify that the live `T_base_board` stays stable.
3. Press `s` to capture a validation sample at each viewpoint.
4. Check the reported translation and rotation spread.

Validation shortcuts:

- `s`: capture validation sample
- `d`: delete last sample
- `r`: reset validation session
- `q`: quit

Validation sessions are saved under:

```text
configs/calibration/sessions/<timestamp>_validate/
```

The UI now also includes lightweight sample-quality visualizations:

- intrinsics: image-plane coverage and board scale distribution
- hand-eye calibration: TCP XY spread and board distance distribution
- validation: base-frame board XY spread and board Z spread

## Runtime Transform Chain

Application code should continue to use:

```text
T_base_object = T_base_tcp @ T_tcp_camera @ T_camera_object
```

In this project, the hand-eye result is always expressed relative to the current business TCP, not the flange.
