#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  exec python3 "$ROOT/scripts/deploy_vm.py" --help
fi
DEPLOY_PYTHON="${AXIOM_DEPLOY_PYTHON:-python3.13}"
DEPLOY_VENV="${AXIOM_DEPLOY_VENV:-$ROOT/.venv-deployment}"
if ! command -v "$DEPLOY_PYTHON" >/dev/null 2>&1; then
  echo 'Install Python 3.13 on the controller, or set AXIOM_DEPLOY_PYTHON to it.' >&2
  exit 2
fi
"$DEPLOY_PYTHON" -c 'import sys; assert sys.version_info[:2] == (3, 13), "Controller requires Python 3.13"'
if [[ ! -x "$DEPLOY_VENV/bin/python" ]]; then
  "$DEPLOY_PYTHON" -m venv "$DEPLOY_VENV"
fi
"$DEPLOY_VENV/bin/python" -m pip install --disable-pip-version-check --require-hashes -r "$ROOT/requirements-deployment.lock"
exec "$DEPLOY_VENV/bin/python" "$ROOT/scripts/deploy_vm.py" "$@"
