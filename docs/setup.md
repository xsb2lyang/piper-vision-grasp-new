# Setup

1. Create or reuse the workspace virtual environment.
2. Install the vendored SDK first.
3. Install the application layer second.

```bash
./scripts/setup_env.sh
```

Manual equivalent:

```bash
.venv/bin/python -m pip install setuptools wheel PyYAML
.venv/bin/python -m pip install --no-build-isolation -e third_party/pyAgxArm
.venv/bin/python -m pip install --no-build-isolation -e .
```

This ordering matters because `piper_app` imports `pyAgxArm` as a normal installed package.
