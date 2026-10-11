#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_INTAKE_PYTHON_BIN="${SOURCE_INTAKE_PYTHON_BIN:-python3}"
SOURCE_INTAKE_VENV="${SOURCE_INTAKE_VENV:-$ROOT/.venv-source-document-intake}"

if ! command -v "$SOURCE_INTAKE_PYTHON_BIN" >/dev/null 2>&1; then
  echo "Required Python interpreter not found: $SOURCE_INTAKE_PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -x "$SOURCE_INTAKE_VENV/bin/python" ]]; then
  "$SOURCE_INTAKE_PYTHON_BIN" -m venv "$SOURCE_INTAKE_VENV"
fi

"$SOURCE_INTAKE_VENV/bin/python" -m pip install \
  --disable-pip-version-check \
  --require-hashes \
  --requirement "$ROOT/requirements-source-document-intake.lock"

echo "Source document intake environment ready: $SOURCE_INTAKE_VENV"
