# ChArUco Board Asset

This folder contains the default printable ChArUco board used by the calibration tools:

- `charuco_board.pdf`: recommended printable version
- `charuco_board.png`: image preview
- `charuco_board.yaml`: board configuration consumed by the software

Board specification:

- grid: `6 x 8`
- dictionary: `DICT_4X4_50`
- square length: `30 mm`
- marker length: `22 mm`

## Printing Notes

- Print `charuco_board.pdf` at **100% scale**
- Disable any printer-side scaling such as:
  - `Fit to page`
  - `Shrink oversized pages`
  - `Scale to printable area`
- After printing, measure one square to confirm it is `30 mm`
- Mount the printed board on a flat, rigid backing before calibration

## Typical Usage

This board is used for:

- camera intrinsics calibration
- eye-in-hand hand-eye calibration
- hand-eye validation

The default project configuration points to:

```text
assets/calibration/charuco_default/charuco_board.yaml
```
