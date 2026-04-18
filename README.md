# Piper App Workspace

This repository is now organized as a two-layer workspace:

- `third_party/pyAgxArm`: vendored upstream SDK
- `src/piper_app`: our application-layer teleop and future perception/task code

Recommended setup:

```bash
./scripts/setup_env.sh
```

This project now uses `uv` as the recommended Python environment manager and installs into the repo-local `.venv`.

If you are migrating from an older `.venv`, rebuild it with:

```bash
./scripts/setup_env.sh --recreate
```

Run teleop:

```bash
./scripts/run_gui.sh
./scripts/run_keyboard.sh
./scripts/run_monitor.sh
./scripts/run_calibrate_intrinsics.sh
./scripts/run_calibrate_handeye.sh
./scripts/run_validate_handeye.sh
```

More details:

- [docs/installation.md](docs/installation.md)
- [docs/handeye.md](docs/handeye.md)
- [docs/teleop.md](docs/teleop.md)
