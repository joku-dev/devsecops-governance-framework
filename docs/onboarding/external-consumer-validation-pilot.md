# External Consumer Validation Pilot

## Purpose and state

Evaluate the existing governance integration against independently developed
software, using measured evidence, repeatable test cases and an independent
onboarding session. This plan specializes the existing
[pilot runbook](pilot-runbook.md); it defines no new governance controls.

**First pair: cJSON and go-httpbin. Second wave: Marked and Gson.** Source
selection, local application builds and a limited collector/OPA diagnostic
were completed on 4 October 2026. Hosted consumer repositories, consumer-owned CI runs, central admission
and independent-user onboarding remain outstanding. Proposed consumer names
below are plan entries, not existing or registered consumers.

The [dated preflight observation](../operations/evidence/external-consumer-preflight-2026-10-04.md)
records the actual diagnostic scope and findings. Neither the source projects
nor their upstream maintainers receive a compliance assessment from these
local experiments. Build/test observations establish only
their stated local execution profile.

## Questions and measurement

| Dimension | Question | Record |
|---|---|---|
| Transferability | Can a foreign project use the documented integration? | Changes, exceptions and onboarding effort |
| Reliability | Does evidence reach its destination correctly? | Technical outcomes, retries, identities and publication latency |
| Correctness | Does each defined case produce its expected decision? | Expected/observed outcome and reasons |
| Usability | Can an independent engineer onboard and interpret a result? | Completed tasks, elapsed time and help requests |
| Operating effort | What recurring work does a consumer create? | Review, publication and recovery time |

This small portfolio adds diverse project inputs and operating observations.
The [capacity assessment](../operations/planning/consumer-scale-capacity-assessment.md)
continues to own throughput and long-term storage questions. GitHub-only runs
do not validate the non-GitHub adapter paths.

## Selected portfolio and pins

| Wave | Project | Profile | Additional coverage |
|---|---|---|---|
| 1 | [DaveGamble/cJSON](https://github.com/DaveGamble/cJSON/tree/c859b25da02955fef659d658b8f324b5cde87be3) | C library, CMake, vendored Unity | Native artifacts and source components without package manifests |
| 1 | [mccutchen/go-httpbin](https://github.com/mccutchen/go-httpbin/tree/34888fd21d6667e9f0c842db483ba595b9c8c094) | Go HTTP service | Binary identity; later container and runtime evidence |
| 2 | [markedjs/marked](https://github.com/markedjs/marked/tree/c18a64fa5e8c97cb92a8ea709a4542ea94b1c740) | TypeScript library and CLI | npm lockfile, build dependencies, several distribution formats |
| 2 | [google/gson](https://github.com/google/gson/tree/3ff35d6269894901ab8006258395aafc4b9765cd) | Java library, Maven reactor | JAR, unit/integration reports and modular build scope |

Retain upstream licenses and notices. cJSON, go-httpbin and Marked declare MIT;
Marked includes additional notices in its license file. Gson uses Apache-2.0.
Upstream releases and CI are selection evidence, not evidence from a new
consumer. These source pins were reviewed on 4 October 2026:

```yaml
cjson:
  upstream: DaveGamble/cJSON
  source_commit: c859b25da02955fef659d658b8f324b5cde87be3
  source_label: v1.7.19
  proposed_consumer: joku-dev/governance-eval-cjson
go_httpbin:
  upstream: mccutchen/go-httpbin
  source_commit: 34888fd21d6667e9f0c842db483ba595b9c8c094
  proposed_consumer: joku-dev/governance-eval-go-httpbin
marked:
  upstream: markedjs/marked
  source_commit: c18a64fa5e8c97cb92a8ea709a4542ea94b1c740
gson:
  upstream: google/gson
  source_commit: 3ff35d6269894901ab8006258395aafc4b9765cd
  source_label: gson-parent-2.14.0
integration:
  reviewed_source_commit: 55743673bec6600c9a98dccd1d97df8953368e65
  devsecops_baseline: l1-baseline-v1.1.3
  released_reusable_commit: 2d30d851f06ceabf0504400fcd06e78e76b99372
  governance_mode: report-only
```

Keep upstream identity separate from the actual consumer repository, branch,
checked-out commit, workflow run and attempt. Record the adoption-template
revision, released baseline and collector/report revision separately. A test
copy's protection settings must be measured in that hosting context. On PRs,
the commit must identify the checked-out bytes, including the merge commit
when that is the workflow's checkout choice.

## First wave build profiles

Record exact tool/runner versions and keep complete logs and exit statuses.
The commands specify the initial scope; execution results belong in the dated
observation. A build is not a vulnerability scan or complete SBOM.

### cJSON

Use GCC, Ninja and CMake at least 3.21 but below 4. The actual
[CMakeLists.txt](https://github.com/DaveGamble/cJSON/blob/c859b25da02955fef659d658b8f324b5cde87be3/CMakeLists.txt)
uses a legacy minimum policy setting. Run from the consumer source root:

```bash
mkdir -p evidence
cmake -S . -B build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  -DENABLE_CJSON_TEST=ON -DENABLE_CJSON_UTILS=ON \
  -DENABLE_FUZZING=OFF -DENABLE_VALGRIND=OFF \
  -DENABLE_SANITIZERS=OFF -DENABLE_SAFE_STACK=OFF
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure \
  --output-junit "${PWD}/evidence/ctest.xml"
```

Retain the actual library files/digests, `CMakeCache.txt`,
`compile_commands.json` and JUnit results. The
[vendored Unity framework](https://github.com/DaveGamble/cJSON/blob/c859b25da02955fef659d658b8f324b5cde87be3/tests/unity/docs/license.txt)
is a known source/test component. An empty package-manager inventory does not
establish dependency absence. Separate source/build/test scope from delivered
library scope. Cross-compilation, RTOS, target hardware, safety and fuzz
campaigns are outside the first profile.

### go-httpbin

The [root module](https://github.com/mccutchen/go-httpbin/blob/34888fd21d6667e9f0c842db483ba595b9c8c094/go.mod)
declares Go 1.25.0 and no external Go requirements. Use a recorded Go 1.26
patch version and a C compiler for race tests:

```bash
mkdir -p evidence dist
go test -count=1 -race -covermode=atomic \
  -coverprofile=evidence/coverage.txt \
  -json ./... > evidence/go-test.json
go vet ./...
CGO_ENABLED=0 go build -trimpath -o dist/go-httpbin ./cmd/go-httpbin
go version -m dist/go-httpbin > evidence/go-build-info.txt
sha256sum dist/go-httpbin > evidence/artifact.sha256
```

This direct build avoids the dynamic timestamp in the upstream Makefile. If
commit/date linker fields are supplied, record their exact values. It is a
pilot build profile, not a bit-identical upstream-release claim. Retain test
JSON, coverage, vet outcome, binary digest and Go build information. The Go
toolchain, standard library and eventual image base remain relevant components.

Container build and HTTP smoke testing are later substeps. First record the
builder, frontend and runtime base identities from the
[Dockerfile](https://github.com/mccutchen/go-httpbin/blob/34888fd21d6667e9f0c842db483ba595b9c8c094/Dockerfile).
Its current image also contains a test binary. Binary-only results do not
establish image coverage. Optional Docker/Autobahn testing and external coverage
upload are excluded from the first core profile.

### Second wave handoff

For Marked, retain `package-lock.json`, pin Node/npm and use the existing build,
unit, specification, CJS, UMD, types and lint tasks. Distinguish distributed
library contents from development dependencies. Its first successful own
baseline remains required; the selected upstream workflow was cancelled.

For Gson, use JDK 21 and fixed Maven, starting with:

```bash
mvn --batch-mode --no-transfer-progress --projects gson --also-make clean verify
```

Record the restricted core-module scope, JAR digest and Surefire/Failsafe
reports. The root POM requires JDK at least 17 and below 22. Preserve the
project's `.mvn/jvm.config`; experimental-JDK CI exceptions are not the pilot
default.

## Evidence and integration stages

### Measured pipeline entry stage

Use the existing [quickstart](public-repo-quickstart.md) and
[evidence contract](../operations/evidence/governance-evidence-contract.md).
Replace demonstration claims with actual producer outputs:

| Artifact entry | Meaning |
|---|---|
| `dist/<chosen-artifact>` | Actual build output or explicitly declared source package |
| `security/sbom.cyclonedx.json` | Generated SBOM with a stated subject and scope |
| `security/vulnerability-scan.json` | Real scan normalized to the consumed contract |
| Additional files | Native scanner output, tool/database identities, build/test logs, digest manifest and source provenance |

The first hosted call uses the released wrapper with these explicit inputs:

```yaml
governance_mode: report-only
generate_demo_evidence: false
release_candidate: false
application_evidence_artifact_name: application-evidence
```

Supply the actual artifact/SBOM/scan paths. Omit `governance_run_input_path`
initially if complete measured claims are unavailable. Missing evidence remains
an explicit limitation. A demonstration empty SBOM, fixed `none` severity or
invented protection Boolean is not measurement.

The wrapper emits `devsecops-pipeline-evidence`. The existing intake can select
it with `--artifact-name devsecops-pipeline-evidence`; the
`baseline-gate-result.json` fallback becomes a **single-gate summary**, not
control-by-control L1 coverage.

### Full control evaluation

Validate the full governance input against its existing schema and retain a
source for every claim. Unknown protection facts cannot currently be encoded
as `null` in required Boolean fields. Record that gap and keep full evaluation
pending rather than inserting positive defaults.

Use `scripts/generate_control_evaluation_report.py` after explicit schema
validation. Upload its report and input together as
`governance-control-evaluation`. The current intake searches the selected ZIP;
it does not create a full report from a separate input artifact. Record the
report implementation revision as well as the released wrapper baseline.

Preserve the script's documented findings exit code separately from technical
exceptions. Unconditional `|| true` would hide both. Architecture evidence is
optional and must be owned/relevant; its pilot mode remains
`fail_on_findings: false`.

## Isolation and scope

Keep local diagnostic outputs outside the governed tree. Exercise intake and
index generators in a separate disposable governance checkout at a recorded
revision. Do not commit that checkout's test `status/` or `generated/` outputs.

The current index has no filter that excludes a result because a repository
name or note says `test`. Naming and provenance are not isolation controls.
Official registry/portfolio admission is a separate reviewed change after the
local evidence path has been evaluated.

Consumer builds use limited-rights isolated execution and receive no central
write/intake credential. Central collection remains a separate trusted step.
Result intake does not grant lifecycle admission, waiver, risk acceptance or
closure authority. Use the existing separately scoped lifecycle process for
any later lifecycle test.

## Test cases and exit criteria

Set expected outcomes before execution. These are proposed engineering pilot
criteria, not new controls, SLOs or policy requirements.

| Case | Stimulus | Expected result |
|---|---|---|
| ECV-01 | First measured artifact/SBOM/scan | Traceable files and explicit integration scope |
| ECV-02 | Repeated evaluation of fixed inputs | Same semantic decision and reasons |
| ECV-03 | Required evidence omitted | Explicit missing-evidence result |
| ECV-04 | Subject changed after digest capture | Mismatch detected at the verifier boundary |
| ECV-05 | Wrong consumer/commit identity | Misattribution detected |
| ECV-06 | Exact duplicate delivery | Idempotent result without contradictory duplicates |
| ECV-07 | Older result arrives after newer | Documented current-state ordering preserved |
| ECV-08 | Evidence becomes stale | Explicit freshness change at the controlled assessment time |
| ECV-09 | Interrupted delivery resumes | Traceable recovery without evidence loss/overwrite |
| ECV-10 | Concurrent consumers | Correct association and consistent publication |
| ECV-11 | Unsupported format or unavailable hosting fact | Actionable diagnostic and explicit coverage gap |
| ECV-12 | Independent engineer onboards/interprets | Task completion, time and assistance recorded |
| ECV-13 | Admitted finding corrected and later recurring | Authorized decisions, new evidence, verification and recurrence handling |

For ECV-04, a change before the first digest measurement cannot itself prove
tamper detection; an independent prior binding is required. A new CI run for
the same commit differs from duplicate delivery of one event.

Use existing fixture tests for trust, ledger and isolation behavior, and keep
their results distinct from source snapshots and live consumer runs. Each
stage requires its selected expected outcomes to match; no lost or
cross-consumer evidence; and visible limitations. No known manipulated evidence
may be accepted as valid in the defined negative cases. A correctly detected
governance gap is a successful test.

For every case record: case/consumer/run identity, full source and baseline
pins, tool/database/clock inputs, expected and observed results, technical
status, governance outcome, evidence quality, elapsed/manual effort, coverage
limitations, owner role and next disposition. Fixed-input regression and
current-data operating samples are separate: newly published vulnerability
data or a changed assessment clock may correctly alter a result.

## Execution sequence

1. Review this source selection and the bounded local observations.
2. Create the two proposed hosted consumers with retained upstream notices and
   explicit source provenance. Record their actual resulting identities.
3. Implement the core builds and genuine evidence production in consumer CI;
   keep PR/main/manual calls explicitly report-only.
4. Complete ECV-01 to ECV-03 and record onboarding effort before considering
   central admission.
5. Exercise selected identity/recovery/intake cases in the disposable
   governance environment, then review official intake separately.
6. Run ECV-12 with an explicitly selected independent engineer. This plan does
   not assign or invite a person.
7. Add Marked and Gson after a repeatable first-pair integration.
8. Record the stage decision, open findings and follow-up ownership.

The framework maintainer owns preparation, application/pipeline owners own
producer facts, and the governance reviewer assesses the pilot record.
Existing authorities retain risk, release and lifecycle decisions. Completion
does not automatically activate blocking or production use.

## Related records

- [GCR 2026 113](../governance/change-requests/GCR-2026-113-external-consumer-validation-pilot.md)
- [Dated local preflight](../operations/evidence/external-consumer-preflight-2026-10-04.md)
- [Multi-consumer readiness](../operations/status/multi-consumer-readiness.md)
