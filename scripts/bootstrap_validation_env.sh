#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLCHAIN_FILE="$ROOT/scripts/validation-toolchain.env"
REQUIREMENTS_FILE="$ROOT/requirements-validation.txt"

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap_validation_env.sh

Create or update the repository-local validation environment.

Environment variables:
  PYTHON_BIN       Python interpreter used to create the virtual environment.
                   Default: python3
  VALIDATION_VENV  Installation directory. Default: .venv-validation
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi
if [[ $# -ne 0 ]]; then
  usage >&2
  exit 2
fi

# shellcheck source=validation-toolchain.env
source "$TOOLCHAIN_FILE"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VALIDATION_VENV="${VALIDATION_VENV:-$ROOT/.venv-validation}"
OPA_PATH="$VALIDATION_VENV/bin/opa"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    echo "Neither sha256sum nor shasum is available" >&2
    exit 1
  fi
}

select_opa_asset() {
  local os architecture
  os="$(uname -s)"
  architecture="$(uname -m)"

  case "$os/$architecture" in
    Darwin/x86_64)
      OPA_ASSET="opa_darwin_amd64"
      OPA_SHA256="$OPA_DARWIN_AMD64_SHA256"
      ;;
    Darwin/arm64)
      OPA_ASSET="opa_darwin_arm64"
      OPA_SHA256="$OPA_DARWIN_ARM64_SHA256"
      ;;
    Linux/x86_64)
      OPA_ASSET="opa_linux_amd64_static"
      OPA_SHA256="$OPA_LINUX_AMD64_STATIC_SHA256"
      ;;
    Linux/aarch64|Linux/arm64)
      OPA_ASSET="opa_linux_arm64_static"
      OPA_SHA256="$OPA_LINUX_ARM64_STATIC_SHA256"
      ;;
    *)
      echo "Unsupported validation platform: $os/$architecture" >&2
      exit 1
      ;;
  esac
}

require_command "$PYTHON_BIN"
require_command curl
select_opa_asset

if [[ ! -x "$VALIDATION_VENV/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$VALIDATION_VENV"
fi

"$VALIDATION_VENV/bin/python" -m pip install \
  --disable-pip-version-check \
  --requirement "$REQUIREMENTS_FILE"

if [[ ! -f "$OPA_PATH" ]] || [[ "$(sha256 "$OPA_PATH")" != "$OPA_SHA256" ]]; then
  temporary_opa="$(mktemp "${OPA_PATH}.tmp.XXXXXX")"
  trap 'rm -f "$temporary_opa"' EXIT
  opa_url="https://github.com/open-policy-agent/opa/releases/download/v${OPA_VERSION}/${OPA_ASSET}"
  curl --fail --location --silent --show-error "$opa_url" --output "$temporary_opa"

  actual_sha256="$(sha256 "$temporary_opa")"
  if [[ "$actual_sha256" != "$OPA_SHA256" ]]; then
    echo "OPA checksum mismatch for $OPA_ASSET" >&2
    echo "Expected: $OPA_SHA256" >&2
    echo "Actual:   $actual_sha256" >&2
    exit 1
  fi

  chmod 755 "$temporary_opa"
  mv "$temporary_opa" "$OPA_PATH"
  trap - EXIT
fi

actual_opa_version="$($OPA_PATH version | awk '/^Version:/ {print $2}')"
if [[ "$actual_opa_version" != "$OPA_VERSION" ]]; then
  echo "OPA version mismatch: expected $OPA_VERSION, got $actual_opa_version" >&2
  exit 1
fi

"$VALIDATION_VENV/bin/python" -m pip check
echo "Validation environment ready: $VALIDATION_VENV"
echo "Run: ./scripts/validate_all.sh"
