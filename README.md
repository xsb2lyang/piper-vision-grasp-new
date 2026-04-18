# Piper App Workspace

This repository is now organized as a two-layer workspace:

- `third_party/pyAgxArm`: vendored upstream SDK
- `src/piper_app`: our application-layer teleop and future perception/task code

Recommended setup:

```bash
./scripts/setup_env.sh
```

Run teleop:

```bash
./scripts/run_gui.sh
./scripts/run_keyboard.sh
```

More details:

- [docs/setup.md](docs/setup.md)
- [docs/teleop.md](docs/teleop.md)
