# Installation

This repository uses a vendored `pyAgxArm` SDK plus our own application layer. The official recommended environment for this project is **uv + Python 3.10**.

## 1. System Dependencies

On Ubuntu, install the RealSense runtime first:

```bash
sudo apt update
sudo apt install -y v4l-utils
sudo apt install -y librealsense2 librealsense2-dev librealsense2-utils librealsense2-udev-rules
```

Install `uv`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart the shell, then confirm:

```bash
uv --version
```

After plugging in the D405, verify the camera is visible:

```bash
rs-enumerate-devices
realsense-viewer
```

## 2. Create Or Recreate `.venv`

The setup script always targets Python 3.10 through `uv`.

First-time setup:

```bash
./scripts/setup_env.sh
```

If you already have an older or wrong-version `.venv`, recreate it:

```bash
./scripts/setup_env.sh --recreate
```

This is required when migrating from the earlier Python 3.13 environment to the project baseline.

You can also override the target Python version explicitly:

```bash
PYTHON_VERSION=3.10 ./scripts/setup_env.sh --recreate
```

## 3. What Gets Installed

The setup script installs:

- a uv-managed Python 3.10 interpreter if needed
- editable vendored SDK: `third_party/pyAgxArm`
- editable application layer: current repo root
- Python packages from `pyproject.toml`, including:
  - `numpy`
  - `Pillow`
  - `PyYAML`
  - `pyrealsense2`

Manual equivalent:

```bash
uv python install 3.10
uv venv --python 3.10 .venv
uv pip install --python .venv/bin/python --upgrade pip setuptools wheel
uv pip install --python .venv/bin/python --no-build-isolation -e third_party/pyAgxArm
uv pip install --python .venv/bin/python --no-build-isolation -e .
```

## 4. Validate The Environment

Check the Python version:

```bash
.venv/bin/python -V
```

It should report Python 3.10.

Check RealSense Python bindings:

```bash
uv pip show --python .venv/bin/python pyrealsense2
```

Check the camera:

```bash
rs-enumerate-devices
```

## 5. Run The Monitor

Start the read-only robot and D405 monitor:

```bash
./scripts/run_monitor.sh
```

Useful options:

```bash
./scripts/run_monitor.sh --camera-serial auto
./scripts/run_monitor.sh --camera-width 640 --camera-height 480 --camera-fps 30
./scripts/run_monitor.sh --depth-min-m 0.05 --depth-max-m 0.50
./scripts/run_monitor.sh --no-camera
```
