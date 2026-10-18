#!/usr/bin/env bash
# Build before testing so an old installed extension cannot hide source changes.
set -euo pipefail
cd "$(dirname "$0")/.."

uv sync --locked --dev --no-install-project
uv run --no-sync maturin develop --uv --release --locked
uv run --no-sync python -c 'import litebook.litebook as native; print("Testing extension:", native.__file__)'
uv run --no-sync python -m pytest "$@"
