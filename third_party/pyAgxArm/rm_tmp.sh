#!/usr/bin/env bash
set -euo pipefail

# 清理 Python/构建产生的临时文件（不会删除源码）
# 用法：在项目任意目录执行 `./rm_tmp.sh`

# 定位到脚本所在目录（通常是项目根目录）
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "[clean] root: $ROOT_DIR"

# 常见构建产物/缓存目录
rm -rf \
  ./build \
  ./dist \
  ./*.egg-info \
  ./.eggs \
  ./.pytest_cache \
  ./.mypy_cache \
  ./.ruff_cache \
  ./.tox \
  ./htmlcov \
  ./.coverage \
  ./.coverage.* \
  ./pip-wheel-metadata \
  ./__pypackages__

# Python bytecode / cache
find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true

echo "[clean] done"