#!/usr/bin/env bash
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHANNEL="${1:-can0}"
BITRATE="${2:-1000000}"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python"

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf '[PASS] %s\n' "$1"
}

warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
  printf '[WARN] %s\n' "$1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf '[FAIL] %s\n' "$1"
}

section() {
  printf '\n== %s ==\n' "$1"
}

section "Workspace"
if [[ -d "$REPO_ROOT/.git" ]]; then
  pass "Repository root detected at $REPO_ROOT"
else
  fail "Repository root is invalid: $REPO_ROOT"
fi

section "System Commands"
for cmd in uv ip rs-enumerate-devices; do
  if command -v "$cmd" >/dev/null 2>&1; then
    pass "Command available: $cmd"
  else
    fail "Missing required command: $cmd"
  fi
done

for optional_cmd in realsense-viewer candump; do
  if command -v "$optional_cmd" >/dev/null 2>&1; then
    pass "Optional command available: $optional_cmd"
  else
    warn "Optional command not found: $optional_cmd"
  fi
done

section "Python Environment"
if [[ -x "$PYTHON_BIN" ]]; then
  PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')" || PY_VERSION=""
  if [[ "$PY_VERSION" == 3.10.* ]]; then
    pass "Project virtualenv is ready: Python $PY_VERSION"
  else
    warn "Project virtualenv uses Python $PY_VERSION, expected Python 3.10.x"
  fi
else
  fail "Missing project virtualenv at .venv. Run ./scripts/setup_env.sh first."
fi

if [[ -x "$PYTHON_BIN" ]]; then
  if "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import importlib
mods = ["piper_app", "pyAgxArm", "pyrealsense2", "ultralytics"]
for name in mods:
    importlib.import_module(name)
PY
  then
    pass "Core Python imports succeeded: piper_app, pyAgxArm, pyrealsense2, ultralytics"
  else
    fail "Core Python imports failed. Re-run ./scripts/setup_env.sh or inspect .venv packages."
  fi
fi

section "Camera"
if command -v rs-enumerate-devices >/dev/null 2>&1; then
  RS_OUTPUT="$(rs-enumerate-devices 2>&1 || true)"
  if grep -Eq 'D405|Depth Camera 405' <<<"$RS_OUTPUT"; then
    pass "Intel RealSense D405 detected"
  elif [[ -n "$RS_OUTPUT" ]]; then
    warn "RealSense command ran, but D405 was not found"
  else
    fail "rs-enumerate-devices returned no output"
  fi
fi

section "CAN"
if command -v ip >/dev/null 2>&1; then
  if ip link show "$CHANNEL" >/dev/null 2>&1; then
    CAN_DETAIL="$(ip -details link show "$CHANNEL" 2>/dev/null || true)"
    if grep -q 'state UP' <<<"$CAN_DETAIL"; then
      pass "CAN interface $CHANNEL is UP"
    else
      warn "CAN interface $CHANNEL exists but is not UP. Try: sudo ./scripts/bringup_can.sh $CHANNEL $BITRATE"
    fi
    if grep -q "bitrate $BITRATE" <<<"$CAN_DETAIL"; then
      pass "CAN bitrate looks correct: $BITRATE"
    else
      warn "CAN bitrate does not clearly match $BITRATE"
    fi
  else
    fail "CAN interface $CHANNEL does not exist. Check the CAN adapter and system configuration."
  fi
fi

section "Tracked Assets"
for path in \
  "assets/calibration/charuco_default/charuco_board.pdf" \
  "configs/task/pick_demo_template.yaml" \
  "configs/camera/d405_default.yaml" \
  "third_party/yolo/新松-检测/yolo11m.pt"; do
  if [[ -e "$REPO_ROOT/$path" ]]; then
    pass "Found $path"
  else
    fail "Missing tracked asset: $path"
  fi
done

section "Generated / Local Files"
for path in \
  "configs/calibration/camera_intrinsics.yaml" \
  "configs/calibration/handeye_active.yaml"; do
  if [[ -e "$REPO_ROOT/$path" ]]; then
    pass "Found generated file: $path"
  else
    warn "Missing generated file: $path"
  fi
done

if [[ -e "$REPO_ROOT/configs/task/pick_demo_points.yaml" ]]; then
  pass "Found local keypoint override: configs/task/pick_demo_points.yaml"
else
  warn "Local keypoint override is missing. Demos will fall back to configs/task/pick_demo_template.yaml"
fi

section "Next Steps"
if [[ "$FAIL_COUNT" -eq 0 ]]; then
  pass "No blocking failures detected by run_doctor.sh"
else
  warn "Doctor found blocking failures. Resolve them before calibration or grasp demos."
fi
printf 'Summary: %d pass, %d warn, %d fail\n' "$PASS_COUNT" "$WARN_COUNT" "$FAIL_COUNT"

if [[ "$FAIL_COUNT" -ne 0 ]]; then
  exit 1
fi
