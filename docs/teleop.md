# Teleop

GUI:

```bash
./scripts/run_gui.sh
```

Keyboard:

```bash
./scripts/run_keyboard.sh
```

Dry-run examples:

```bash
./scripts/run_gui.sh --dry-run
./scripts/run_keyboard.sh --dry-run
```

Read-only drag monitor with D405 camera:

```bash
./scripts/run_monitor.sh
```

Installation and environment notes:

- [docs/installation.md](installation.md)

Gripper zeroing in GUI:

1. Click `Release Driver`
2. Manually close the gripper fully
3. Click `Set Zero`
4. Resume with `Open Step`, `Close Step`, or `Set Width`
