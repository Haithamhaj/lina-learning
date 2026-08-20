#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Post-merge runs without an interactive stdin. Keep every dependency and
# migration command deterministic and safe to run repeatedly.
export CI="${CI:-true}"
export PIP_DISABLE_PIP_VERSION_CHECK=1

echo "Installing Node.js dependencies..."
npm ci --no-audit --no-fund

echo "Installing API dependencies..."
PYTHON_BIN="${PYTHON_BIN:-python}"
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$PYTHON_BIN" \
    --requirement apps/api/requirements.txt
elif "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  "$PYTHON_BIN" -m pip install --disable-pip-version-check --no-input \
    --requirement apps/api/requirements.txt
else
  echo "Neither uv nor pip is available for the configured Python runtime." >&2
  exit 1
fi

echo "Applying database migrations..."
alembic upgrade head

echo "Building the web application..."
npm run build

echo "Post-merge setup completed."