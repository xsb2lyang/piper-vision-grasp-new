#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_VERSION="${PYTHON_VERSION:-3.10}"
RECREATE=0

for arg in "$@"; do
  case "$arg" in
    --recreate)
      RECREATE=1
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Usage: ./scripts/setup_env.sh [--recreate]" >&2
      exit 1
      ;;
  esac
done

if ! command -v uv >/dev/null 2>&1; then
  echo "Required tool not found: uv" >&2
  echo "Install uv first: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

if [[ -d "$REPO_ROOT/.venv" && "$RECREATE" -eq 1 ]]; then
  rm -rf "$REPO_ROOT/.venv"
fi

if [[ -d "$REPO_ROOT/.venv" && "$RECREATE" -eq 0 ]]; then
  if [[ ! -x "$REPO_ROOT/.venv/bin/python" ]]; then
    echo "Existing .venv is incomplete. Run ./scripts/setup_env.sh --recreate" >&2
    exit 1
  fi
  VENV_VERSION="$("$REPO_ROOT/.venv/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "$VENV_VERSION" != "$PYTHON_VERSION" ]]; then
    echo "Existing .venv uses Python $VENV_VERSION, but this project baseline is Python 3.10." >&2
    echo "Run ./scripts/setup_env.sh --recreate to rebuild the environment with uv Python $PYTHON_VERSION." >&2
    exit 1
  fi
fi

if [[ ! -d "$REPO_ROOT/.venv" ]]; then
  uv python install "$PYTHON_VERSION"
  uv venv --python "$PYTHON_VERSION" "$REPO_ROOT/.venv"
fi

uv pip install --python "$REPO_ROOT/.venv/bin/python" --upgrade pip setuptools wheel
uv pip install --python "$REPO_ROOT/.venv/bin/python" --no-build-isolation -e "$REPO_ROOT/third_party/pyAgxArm"
uv pip install --python "$REPO_ROOT/.venv/bin/python" --no-build-isolation -e "$REPO_ROOT"

echo "Environment ready with $("$REPO_ROOT/.venv/bin/python" -V 2>&1)"
