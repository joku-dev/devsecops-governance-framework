# Exact-source prepared runtime package v1 candidate

The package complements the [VM's exact-commit internal Git mirror](portable-consumer-service.md). It distributes the same tracked source, archived baselines and optional prepared core tools to Mac/Linux agents. It does not create another governance engine, replace Git/signatures, install a live VM or grant a provider/publisher role. The contract is `schemas/runtime-package-v1.schema.json`; the bootstrap implementation uses only Python's standard library and the existing bounded ZIP extractor.

## Build from an approved exact commit

For persistent installations, preprovision Python outside OS-managed temporary
directories and keep its base standard library available. A virtual environment
can refer to that base interpreter; the V2 source package and locked wheels do
not make Python self-contained. Temporary proof environments require a healthy
base interpreter for each run.

Prepare a wheelhouse for the target Python/OS/architecture using the repository's unchanged hash lock. Supply the checksum-verified target OPA from the existing installer/cache. The default package contains the validation/core dependencies; `--workbench` additionally requires the source-document-intake lock and its complete wheel set. Preparation may use explicitly configured internal indexes, artifact mirrors and verified caches. Keep that online preparation separate from offline installation.

```bash
PINNED_PYTHON -m pip --isolated download --only-binary=:all: --require-hashes \
  -r requirements-validation.lock --dest TARGET_WHEELHOUSE
PINNED_PYTHON scripts/package_governance_runtime.py build \
  --revision APPROVED_40_CHARACTER_COMMIT --destination FRESH_RUNTIME.zip \
  --opa VERIFIED_TARGET_OPA --wheelhouse TARGET_WHEELHOUSE \
  --system Linux --machine x86_64
```

The builder reads Git objects at the selected commit, so local edits and untracked drafts, credentials, operational state and editor files are not packaged. If private key/local-state paths are tracked, it refuses instead of silently excluding them from the claimed tree. Tracked symlinks/submodules are unsupported by format v1. All original source bytes, blob IDs and executable modes, the original raw commit object and tree are retained. Original signature bytes are preserved; package creation does not assert that a signature or human approval was independently verified.

The ZIP uses deterministic member ordering and fixed metadata. It includes a SHA-256/size manifest, target-specific OPA pin and wheel hashes from the selected source locks. A source-only package is possible, but cannot prepare dependencies offline. A supplied wheelhouse must represent every locked name/version; pip subsequently enforces actual target/ABI compatibility. A built `prepared_dependencies` flag means supplied artifacts, not a successful installation receipt.

## Admit with an independent package hash

```bash
python3 scripts/package_governance_runtime.py admit \
  --package RUNTIME.zip --sha256 INDEPENDENT_APPROVED_SHA256 \
  --destination FRESH_ADMISSION_ROOT
python3 scripts/package_governance_runtime.py prepare-environment \
  --root FRESH_ADMISSION_ROOT --package RUNTIME.zip \
  --sha256 INDEPENDENT_APPROVED_SHA256 --destination FRESH_VENV \
  --python PREPROVISIONED_TARGET_PYTHON
```

Get the expected hash from the reviewed build/release record through the chosen trusted channel. A manifest or checksum fetched from the same untrusted archive is not its own authority. Admission verifies the package hash before extraction or Git execution, bounds archive size/count/paths/types, rejects duplicates/unlisted members and checks every file digest. It reconstructs the original blob objects, index, tree and raw commit and verifies their exact Git IDs. A shallow boundary preserves the original commit without downloading parents. This keeps revision-bound runtime checks usable on a prepared offline agent.

Environment preparation requires the original package and independent hash again, checks the admitted manifest/content/file set and rejects untracked import shadows or altered admission data. Use a fresh admission root; do not add generated outputs or bytecode to it before preparation. Dependencies install with isolated pip, `--no-index`, `--require-hashes` and local wheels only. No index, OPA mirror or public fallback is tried. Missing wheels, wrong target/ABI, wrong OPA hash/version or an incomplete environment fail explicitly; the ready receipt is written last. Public runtime dependencies use a readable child umask; private credentials/configuration are not included or altered. Set `PYTHONDONTWRITEBYTECODE=1` or use `python -B` when executing source snapshots.

This is a prepared core runtime. Python, Git and the OS must already exist. VM apt packages, container/image runtime, scanner images, vulnerability databases, database freshness and application build hooks are separate prerequisites. A mirror with public fallback is not an offline installation. The VM IaC's internal-online path continues to select the same exact source commit; a full networkless VM/OS provisioning rollout is not claimed by this package test.

## Executed offline evidence

The recorded [macOS candidate proof](../../examples/portable-runtime/offline-package-macos-candidate.json) packages core source commit `b7d13de9dc77f043aa4b8cc6df8d536fd34a4329`, tree `d116a0d430df8e924be01acd0bee3cd14ad98088`. On Darwin arm64 with Python 3.13.18 and pinned OPA 1.18.2, the prepared package SHA-256 is `bcc03883523926513753cee19bc5e770553a8359d3d71f9e61c6be27835e3756`. It contains 1,995 files. The original Git identity was reconstructed and the environment installed under native `sandbox-exec` policy `deny network*`; a control connection failed with an OS denial. Both the pass and negative-finding result matched the reference **entire canonical result** with an empty provider environment. Inputs are explicitly synthetic and establish no compliance or native provider provenance.

`tests/integration/run_runtime_package.py` reproduces the test with a supplied local wheelhouse/OPA. On Mac it uses native network denial; the optional GitHub Ubuntu job uses an isolated network namespace with no external interfaces. Its controller prepares artifacts while online, then installs/evaluates offline. Target-specific Linux evidence and the exact CI revision must be reported after that job actually succeeds. Unit tests additionally exercise tampered/resigned archives, source/Git identity mismatch, unknown OPA/wheels, untracked private state, altered admission metadata, import shadows, unsafe paths and non-overwrite behavior.

The proof does not update the Proxmox VM, activate collection/publication, establish scanner database readiness or certify every target Python/architecture. Cross-platform canonical parity remains separate from host-specific tool and archive bytes.

The [actual Linux namespace proof](../../examples/portable-runtime/offline-package-linux-candidate.json) was captured by [PR #373 workflow run 43673708882](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/43673708882), job 132689143129. Its temporary GitHub PR merge commit `52d3ecb0deb652dc3d2649a0bc5608c43909a673` has the exact source tree `1e27036b8b6c389815c696b603c6c0f327d15169` of package head `41b53ef7e3460eeb1e1c6148c20892c96f60a8f1`. Both entire canonical pass/fail result hashes equal the Mac proof. Host-specific package hashes and OPA assets differ. This proves the prepared evaluation core on macOS arm64 and isolated Linux x86_64; it does not install the running Proxmox VM or prepare scanner databases.
