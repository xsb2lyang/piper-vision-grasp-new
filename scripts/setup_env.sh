#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -d "$REPO_ROOT/.venv" ]]; then
  python3 -m venv "$REPO_ROOT/.venv"
fi

source "$REPO_ROOT/.venv/bin/activate"
python -m pip install setuptools wheel PyYAML
python -m pip install --no-build-isolation -e "$REPO_ROOT/third_party/pyAgxArm"
python -m pip install --no-build-isolation -e "$REPO_ROOT"
