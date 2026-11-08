#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATION_VENV="${VALIDATION_VENV:-$ROOT/.venv-validation}"

if [[ ! -x "$VALIDATION_VENV/bin/python" ]]; then
  echo "AXIOM Workbench: initial local setup is needed."
  "$ROOT/scripts/bootstrap_validation_env.sh"
fi

exec "$VALIDATION_VENV/bin/python" "$ROOT/scripts/serve_governance_workbench.py" "$@"
