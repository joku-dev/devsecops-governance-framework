#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATION_VENV="${VALIDATION_VENV:-$ROOT/.venv-validation}"
PYTHON="$VALIDATION_VENV/bin/python"
OPA="$VALIDATION_VENV/bin/opa"

usage() {
  cat <<'EOF'
Usage: scripts/validate_all.sh [--check-tools]

Run the complete local governance validation with the pinned toolchain.

Options:
  --check-tools  Verify the prepared toolchain without running validators.

Environment variables:
  VALIDATION_VENV  Validation environment directory. Default: .venv-validation
EOF
}

mode="validate"
case "${1:-}" in
  "") ;;
  --check-tools) mode="check-tools" ;;
  --help|-h)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
if [[ $# -gt 1 ]]; then
  usage >&2
  exit 2
fi

if [[ ! -x "$PYTHON" || ! -x "$OPA" ]]; then
  echo "Validation environment is incomplete: $VALIDATION_VENV" >&2
  echo "Run: ./scripts/bootstrap_validation_env.sh" >&2
  exit 1
fi

# shellcheck source=validation-toolchain.env
source "$ROOT/scripts/validation-toolchain.env"
actual_opa_version="$($OPA version | awk '/^Version:/ {print $2}')"
if [[ "$actual_opa_version" != "$OPA_VERSION" ]]; then
  echo "OPA version mismatch: expected $OPA_VERSION, got $actual_opa_version" >&2
  echo "Run: ./scripts/bootstrap_validation_env.sh" >&2
  exit 1
fi

"$PYTHON" - "$ROOT/requirements-validation.txt" <<'PY'
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys

errors = []
for requirement in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if not requirement or requirement.startswith("#"):
        continue
    package, expected = requirement.split("==", 1)
    try:
        actual = version(package)
    except PackageNotFoundError:
        errors.append(f"{package} is not installed")
        continue
    if actual != expected:
        errors.append(f"{package}=={actual}; expected {expected}")

if errors:
    raise SystemExit("Validation dependency mismatch:\n- " + "\n- ".join(errors))
PY
"$PYTHON" -m pip check
echo "Validation toolchain ready (OPA $actual_opa_version)."

if [[ "$mode" == "check-tools" ]]; then
  exit 0
fi

cd "$ROOT"
export PATH="$VALIDATION_VENV/bin:$PATH"

opa check policies/opa
"$PYTHON" scripts/validate_runtime_governance.py
"$PYTHON" scripts/validate_governance_repo.py
"$PYTHON" -m unittest discover -s tests
