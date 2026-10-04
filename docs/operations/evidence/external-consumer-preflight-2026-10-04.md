# External Consumer Preflight — 4 October 2026

## Scope And Interpretation

This dated record documents an offline diagnostic of the existing demo
release-input collector against two external source snapshots, followed by
separate local application builds and core tests. One collector input per
snapshot was evaluated by OPA three times with identical semantic results. A separate two-file probe
demonstrated that the collector can derive positive evidence flags from an
`approved` declaration without generating the corresponding evidence.

These observations identify integration assumptions to address before a live
consumer pilot. They are not compliance assessments of the upstream projects,
validated consumer results, execution of the released baseline gate, or central
Evidence Trust verification. Application builds are reported separately below.
No vulnerability scanner, GitHub Actions run, central intake, or consumer
admission formed part of this measurement. No core logic, baseline, schema, accepted index, or lifecycle
acceptance was changed.

## Captured Sources And Method

| Field | Captured value |
| --- | --- |
| Observation date | 4 October 2026 |
| Governance repository | `joku-dev/devsecops-governance-framework` |
| Governance source commit | `55743673bec6600c9a98dccd1d97df8953368e65` |
| OPA version | `1.18.2`, repository validation environment |
| Execution mode | `local_legacy_collector_diagnostic_only` |
| Collector | `scripts/collect_devsecops_release_input.py` |
| Equivalent report generator for reproduction | `scripts/generate_devsecops_governance_report.py` |
| Evaluated policy | `policies/opa/devsecops_release_readiness.rego` |

The collector reads the target directory and optionally
`.governance/devsecops/release-evidence.json`. The measurement called OPA
directly with the collected input. The equivalent report generator evaluates
`data.devsecops.release_readiness.deny` from the single policy listed above.
The collector sets `release_candidate: true`; this diagnostic setting does not
establish that either upstream snapshot is an actual release candidate.

| Source snapshot | Exact upstream commit | Repetitions | Recorded result |
| --- | --- | ---: | --- |
| [DaveGamble/cJSON](https://github.com/DaveGamble/cJSON/tree/c859b25da02955fef659d658b8f324b5cde87be3) | `c859b25da02955fef659d658b8f324b5cde87be3` | 3 | Four identical findings per run |
| [mccutchen/go-httpbin](https://github.com/mccutchen/go-httpbin/tree/34888fd21d6667e9f0c842db483ba595b9c8c094) | `34888fd21d6667e9f0c842db483ba595b9c8c094` | 3 | Four identical findings per run |

The measurement was consolidated in an external working record,
`research/preflight-observations.json`, outside this repository. This page
preserves the observations and reproduction procedure; it is not an
append-only evidence custody store. The recorded SHA-256 values of the first
collector inputs were:

| Snapshot | Collector input SHA-256 |
| --- | --- |
| cJSON | `88251d3d5053b82b100a86191c23e8e2dc8a30ae0e17ccedaaacbc0022a49bc0` |
| go-httpbin | `b3bfc87568ee318f2dc06f76066b2d38c567756ccc080e36f5dc43706ca2b4ca` |

These inputs contain absolute source paths and release identifiers. A replay
under different directories may therefore produce different input hashes
while preserving the same findings.

## Measured Observations

### Repeated Findings

All six source-snapshot runs returned the following messages:

| Control identifier | Recorded diagnostic message |
| --- | --- |
| `DSCB-L1-REQ-006` | Release candidates require an SBOM. |
| `DSCB-L1-REQ-009` | Release candidates require vulnerability scan evidence. |
| `DSCB-L1-REQ-011` | Releasable artifacts require checksum, digest, or signature evidence. |
| `DSCB-L2-REQ-011` | DevSecOps pipelines must enforce security gates. |

The result demonstrates repeatability of this small, fixed collector-policy
path. It does not measure CI reliability, concurrency, intake recovery,
throughput, independent onboarding, or correctness of a complete control
assessment. The L2 identifier is part of this legacy policy's output; it does
not imply that a released L2 baseline was selected or evaluated.

### Workflow And Dependency Discovery

The collector tests only the exact path `.github/workflows/ci.yml` and lists
dependencies by searching for `**/requirements.txt`. Both snapshots expose
different relevant files:

| Snapshot | Observed workflow files | Observed build/dependency manifest | Collector observation |
| --- | --- | --- | --- |
| cJSON | `.github/workflows/CI.yml`, `.github/workflows/ci-fuzz.yml` | `CMakeLists.txt` | Exact CI path absent; zero dependency entries |
| go-httpbin | `.github/workflows/ci.yaml`, `.github/workflows/release.yaml` | `go.mod` | Exact CI path absent; zero dependency entries |

The uppercase filename and alternative YAML extension were not discovered by
that exact-path check. Zero enumerated dependency entries describes the
collector's `requirements.txt` search, not absence of dependencies. Presence
of a workflow file also does not establish that it ran or enforced a gate.
Furthermore, the collector combines its CI-path observation with an
`approved` declaration when deriving `security_gates.enforced`; filename
discovery alone is not the complete cause of the recorded gate finding.

### Controlled Approved-Defaults Probe

A separate temporary directory contained only two source files:

```text
.governance/devsecops/release-evidence.json
.github/workflows/ci.yml
```

The first declared `status: approved`; the second satisfied the collector's
path-existence check. No SBOM was generated, no vulnerability scan was run,
and no application-artifact digest was computed. Nevertheless, the collector
derived `sbom.exists`, `vulnerability_scan.exists`, `artifact.digest.exists`,
and `pipeline.security_gates.enforced` as `true`. The report contained zero
findings.

This isolated probe demonstrates declaration-based defaults in the legacy
collector and their effect on this policy. It does not establish a bypass of
the released reusable workflow, central verification, or accepted consumer
controls. It must never be submitted as operational consumer evidence. The
implementation is visible in
[`collect_devsecops_release_input.py`](https://github.com/joku-dev/devsecops-governance-framework/blob/55743673bec6600c9a98dccd1d97df8953368e65/scripts/collect_devsecops_release_input.py).

## Additional Integration Boundaries From Source Inspection

These four observations came from reading the pinned governance source. They
were not measured through live consumer workflows.

| Boundary | Source evidence | Consequence for the pilot |
| --- | --- | --- |
| First-run placeholders | `adoption-package/workflows/devsecops-baseline.yml` contains an empty SBOM, placeholder scan, and fixed positive repository claims. | Replace them with application-owned outputs before claiming meaningful evidence coverage. |
| Unknown claims | `schemas/governance-run-input.schema.json` requires Boolean branch-protection, direct-push, and review claims. `scripts/control_evaluation.py` does not itself validate that schema and treats several missing claims as false. | Record unavailable measurements explicitly; do not invent Boolean facts or assume every unknown becomes `not_tested`. Validate a complete input separately. |
| Intake artifact routing | The released wrapper produces `devsecops-pipeline-evidence` and a separate optional `devsecops-governance-run-input`; `scripts/intake_github_actions_run.py` defaults to `governance-control-evaluation`. | Select the actual artifact. Pipeline-only intake requires `--artifact-name devsecops-pipeline-evidence`; its fallback represents one gate, not all L1 controls. |
| Test-result isolation | `scripts/generate_repository_results_index.py` reads every result directory below `status/results/`. | A test name or note is not an exclusion filter. Keep diagnostic outputs outside accepted result roots. |

The intake script searches its selected artifact for a control report, or a
baseline-gate fallback, and an optional governance input. It does not derive a
complete control report from the separately uploaded input artifact. Full
control evaluation needs the existing
`scripts/generate_control_evaluation_report.py`, with report and input packaged
together for the chosen intake route. See the
[evidence contract](governance-evidence-contract.md) and
[public quickstart](../../onboarding/public-repo-quickstart.md).

## Reproduction With Existing Scripts

Use a checkout of the recorded governance SHA and clean source checkouts at
the exact upstream SHAs above. Set `PREFLIGHT_SOURCES` to their absolute parent
directory, containing `cjson/` and `go-httpbin/`. Run from the governance
repository root. Outputs go to a new temporary directory outside the repo.

```bash
PREFLIGHT_GOV="$(pwd -P)"
PREFLIGHT_SOURCES=/absolute/path/to/consumers
PREFLIGHT_OUT="$(mktemp -d /tmp/external-consumer-preflight.XXXXXX)"
./scripts/bootstrap_validation_env.sh
export PATH="$PREFLIGHT_GOV/.venv-validation/bin:$PATH"
.venv-validation/bin/opa version
git rev-parse HEAD
git -C "$PREFLIGHT_SOURCES/cjson" rev-parse HEAD
git -C "$PREFLIGHT_SOURCES/go-httpbin" rev-parse HEAD

for PREFLIGHT_CASE in cjson go-httpbin; do
  for PREFLIGHT_ATTEMPT in 1 2 3; do
    PREFLIGHT_BASE="$PREFLIGHT_OUT/$PREFLIGHT_CASE-$PREFLIGHT_ATTEMPT"
    .venv-validation/bin/python scripts/collect_devsecops_release_input.py \
      --repo "$PREFLIGHT_SOURCES/$PREFLIGHT_CASE" \
      --release-id "external-validation-preflight-$PREFLIGHT_CASE" \
      --output "$PREFLIGHT_BASE-input.json"
    .venv-validation/bin/python scripts/generate_devsecops_governance_report.py \
      --input "$PREFLIGHT_BASE-input.json" \
      --output-json "$PREFLIGHT_BASE-report.json" \
      --output-md "$PREFLIGHT_BASE-report.md"
  done
  cmp "$PREFLIGHT_OUT/$PREFLIGHT_CASE-1-report.json" \
      "$PREFLIGHT_OUT/$PREFLIGHT_CASE-2-report.json"
  cmp "$PREFLIGHT_OUT/$PREFLIGHT_CASE-1-report.json" \
      "$PREFLIGHT_OUT/$PREFLIGHT_CASE-3-report.json"
done
```

Expected at the recorded revisions: four findings in each report, with
identical reports across the three attempts for each unchanged source path.
`--fail-on-findings` is intentionally omitted: findings remain in the report
while the diagnostic command returns zero. Technical execution errors still
require investigation.

Reproduce the separate synthetic probe without modifying either source:

```bash
PREFLIGHT_PROBE="$PREFLIGHT_OUT/approved-defaults-probe"
mkdir -p "$PREFLIGHT_PROBE/.governance/devsecops" \
         "$PREFLIGHT_PROBE/.github/workflows"
printf '{"status":"approved"}\n' \
  > "$PREFLIGHT_PROBE/.governance/devsecops/release-evidence.json"
printf 'name: synthetic-path-probe\n' \
  > "$PREFLIGHT_PROBE/.github/workflows/ci.yml"
.venv-validation/bin/python scripts/collect_devsecops_release_input.py \
  --repo "$PREFLIGHT_PROBE" \
  --release-id synthetic-approved-defaults \
  --output "$PREFLIGHT_OUT/probe-input.json"
.venv-validation/bin/python scripts/generate_devsecops_governance_report.py \
  --input "$PREFLIGHT_OUT/probe-input.json" \
  --output-json "$PREFLIGHT_OUT/probe-report.json" \
  --output-md "$PREFLIGHT_OUT/probe-report.md"
```

Expected: the four derived flags above are true and the report has zero
findings, despite absent SBOM, scan execution, and computed artifact digest.

## Separate Local Build And Core Test Results

Both source working trees were clean at the exact pins above before and after
these executions. Build and test outputs were placed outside the source trees.
The child processes received explicitly limited environments without GitHub
or governance credentials. Environment minimisation is not an operating-system
sandbox, and these results are local execution records, not CI attestations.

| Project | Executed profile | Observed outcome |
|---|---|---|
| cJSON | GCC 13.3.0; CMake/CTest 3.31.6; Ninja Python distribution 1.11.1.4; Release with tests/utilities enabled | Configure/build/test exit 0; 22 CTest cases passed, none failed or skipped |
| go-httpbin | Checksum-verified Go 1.26.8 linux/amd64; root-module race/coverage tests; vet; direct static binary build | Tests/vet/build exit 0; 83 top-level tests passed, one skipped; 86.3% statement coverage |

The cJSON Ninja binary identified itself as
`1.11.1.git.kitware.jobserver-1`. Fuzzing, Valgrind, sanitizers and SafeStack were
disabled. CMake emitted the upstream legacy-policy compatibility warning;
no build or test failures occurred. Review of the selected CMake profile
identified no external download or fetched-code project steps.

The Go test stream contains 1,441 passing terminal test events when parent
tests and named subtests are both counted. They are not 1,441 independent test
functions. Its one skipped top-level test is the optional Docker-based
Autobahn WebSocket suite. Root-module tests do not include separate example
modules. The compiler archive was checked against the SHA-256 published by
the official [Go download metadata](https://go.dev/dl/?mode=json&include=all):
`d0f743b33e8d8945e6b1f432edd15785c70507121d6e2a723b21285eddf8b57b`.

The Go build used `CGO_ENABLED=0`, `-trimpath`, `-buildvcs=true` and these exact
linker flags:

```text
-s -w -X main.commit=34888fd21d6667e9f0c842db483ba595b9c8c094 -X main.buildDate=2026-09-18T20:35:07Z
```

The embedded date is the source commit date, not the actual execution time.
Execution times were captured separately. Embedded VCS metadata identifies
the selected commit with `vcs.modified=false`. Only one application build was
performed per profile; bit-for-bit reproducibility was not tested.

| Actual artifact | Bytes | SHA-256 |
|---|---:|---|
| `libcjson.so.1.7.19` | 49008 | `47f46217adc5d9303362cf2078e764749f603b277891b8d71983d11f0ceb39bf` |
| `libcjson_utils.so.1.7.19` | 34664 | `4680fdb39744e38243888da743d93e0e910945777873e0d3dc0a17d978048a6c` |
| `go-httpbin` | 8868002 | `a0b195878631832be8583ec96343437ea01c40741d54af432677d4f4449850f4` |

The maintainer evidence bundle retains the JSON execution records, exact
commands, tool identities, JUnit/Go test streams, coverage and build logs.
It is named `External_Consumer_Preflight_Evidence_2026-10-04.zip`, contains 56
entries including an internal digest manifest, and has archive SHA-256
`afae0d216bde7758748e4d83b62e0dbfe4d0a4603d53fe3c436f73d0fd966968`.
It contains logs and metadata, not toolchains, caches or application binaries.
These observations establish working native and Go build/test profiles for
onboarding. SBOM completeness, vulnerability coverage, container execution,
governance intake, independently verified provenance and closed-loop behavior
remain untested by these application runs.

## Consequence For The Next Live Step

Proceed with dedicated consumer repositories, real artifacts, generated SBOMs,
and normalized scanner outputs. Keep every trigger explicitly `report-only`,
including `main`; the released wrapper's default is blocking. A pipeline-only
start can omit the richer governance input until its required claims are
measured. It needs no central intake credential in the producer: central
collection can be initiated separately using the matching artifact name.

Use a disposable governance checkout for any local intake/index exercise,
because the existing intake scripts bind their output roots to their own
repository location. This preflight supports those next integration steps;
it does not establish live usability, sustained stability, provenance trust,
or approval to activate blocking enforcement.
