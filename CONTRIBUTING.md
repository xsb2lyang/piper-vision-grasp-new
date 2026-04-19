# Contributing

Thanks for contributing to `piper-vision-grasp-new`.

## Ground Rules

- Keep `third_party/pyAgxArm` and `third_party/yolo/新松-检测` as vendored upstream code.
- Add new application logic under `src/piper_app`, `scripts`, `configs`, or `docs`.
- Prefer adding new demos instead of mutating an existing workflow that users may already rely on.
- Keep hardware-facing changes conservative and document new assumptions in `docs/`.

## Typical Workflow

1. Create or recreate the local environment:

```bash
./scripts/setup_env.sh
```

2. Run lightweight checks before submitting:

```bash
python3 -m py_compile $(rg --files src scripts)
```

3. If your change affects real hardware workflows, update the matching guide in `docs/`.

## Documentation

- English onboarding: [docs/onboarding.md](docs/onboarding.md)
- Chinese onboarding: [docs/onboarding.zh-CN.md](docs/onboarding.zh-CN.md)
- Docs index: [docs/README.md](docs/README.md)

