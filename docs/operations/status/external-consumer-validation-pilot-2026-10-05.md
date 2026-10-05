# WP-ECV-001 External Consumer Validation Pilot — Results

**Execution date:** 2026-10-05 (UTC)
**Disposition:** Continue and remediate Wave 1; do not admit these consumers or propose Wave 2 yet.
**Scope:** Two pinned upstream source states in newly created private repositories. Report-only integration. All local intake outputs remained in the disposable governance checkout under `/private/tmp/ecv-pilot-f6EssS/governance`.

## Executive result

Both consumer workflows built, tested, generated source-tree CycloneDX SBOMs, ran Trivy, and completed the released L1.1.3 report-only workflow. The initial run and two repeated attempts succeeded for each consumer. The governance decision was **not a pass**: each baseline report recorded a failed control while report-only kept the GitHub workflow green. The central result intake verified the governance report, but it did not project the consumer SBOM, scan, or artifact digest into the result snapshot. A separate typed-evidence intake could not proceed because neither consumer artifact contained `governance/vulnerability-scan-trust.json`.

The isolated central Trust verifier classified the **governance-result artifact** for cJSON as `provenance_verified`; go-httpbin reached `integrity_verified` because the private-artifact fallback path did not preserve an archive digest/custody subject. These are local pilot measurements, not official consumer Trust results, and they do not mean the application binary or source is trusted at those levels.

## Consumers and runs

| Consumer | Pinned upstream source | Private pilot repository / integration commit | Hosted pilot run (attempt 3) | Build and tests | Produced application artifact |
|---|---|---|---|---|---|
| cJSON | `DaveGamble/cJSON` `c859b25da02955fef659d658b8f324b5cde87be3` (`v1.7.19`) | [`governance-eval-cjson`](https://github.com/joku-dev/governance-eval-cjson), `d6340fc34b4a35d4ee2db4aa53826d959ece6034` | [run 37266266970](https://github.com/joku-dev/governance-eval-cjson/actions/runs/37266266970) | CMake 3.31.6, Ninja 1.13.2, GCC 13.3.0; CTest **22/22 passed** | `dist/application-source.tar.gz`, SHA-256 `78b4330eaf28e0345cbd38bfe9bb994a203c03e6cfe9469d28f9960d7c2a1789` |
| go-httpbin | `mccutchen/go-httpbin` `34888fd21d6667e9f0c842db483ba595b9c8c094` | [`governance-eval-go-httpbin`](https://github.com/joku-dev/governance-eval-go-httpbin), `86118ea5f641f4217f005ab039a6714d557cd3f7` | [run 37266263787](https://github.com/joku-dev/governance-eval-go-httpbin/actions/runs/37266263787) | Go 1.25.0, race detector; 84 top-level test functions, 1,441 passing test/subtest events, 1 skipped, 0 failed | `dist/go-httpbin`, SHA-256 `9e93a8293846baffb6a8ddf98e5d0af76e3007261f671fec8aa811e60dc64289` |

Both repositories remain **private**. The source diff from each verified upstream pin contains only the five pilot integration/configuration files; upstream application source and license files were not edited. No PRs were opened. Both `main` branches were measured as unprotected, with direct pushes allowed and no review requirement.

Both pilot workflows used `actions/checkout` and `actions/upload-artifact` pinned to full commit SHAs, Syft 1.54.0 through the pinned SBOM action, and Trivy 0.70.0. SBOM scope is explicitly **source tree**, not the compiled library/binary or a container. Runner OS/image and compiler/tool versions are recorded; the hosted runner image itself is not immutable.

## Governance outcome and evidence findings

The consumer and central artifacts disagree on two governance fields:

- Consumer `governance-run-input.json` truthfully records `external_direct_downloads_detected: true` and `security_gates.enforced: false`.
- The central `pipeline-evidence.json` records `external_direct_downloads_detected: false` and `security_gates.enforced: true`.

The consumers download build/scanner/toolchain dependencies, and their gate mode is report-only. The central collector currently does not preserve those measured values consistently.

The baseline-gate artifacts reported:

- **cJSON:** `fail`, `blocks_merge: false`; direct pushes are allowed on `main`.
- **go-httpbin:** `fail`, `blocks_merge: false`; direct pushes are allowed, and the scan severity threshold is exceeded because Trivy classified `CVE-2026-39824` in `golang.org/x/sys` v0.41.0 as `unknown` (Trivy's fixed version field says v0.44.0). The finding must remain visible; `unknown` is not evidence of no vulnerability.

The downloaded raw Trivy report locates this dependency in
`examples/custom-instrumentation/go.mod`. The Go Vulnerability Database scopes
the issue to `golang.org/x/sys/windows.NewNTUnicodeString` before v0.44.0; the
Go Security Team's announcement says v0.45.0 was tagged to address it. The
pilot build evidence records the application binary as Linux/amd64 with CGO
disabled. This makes the finding specific to a Windows API dependency in an
example, and does not show that the Linux application binary reaches that
function. Keep the finding visible and the governance result failed until the
upstream owner confirms the affected-version mapping, updates the example to a
fixed module version (v0.45.0 is the conservative published target), and a new
scan is reviewed. Do not treat the platform scope as a waiver or as proof that
the dependency is safe for consumers of the Windows example. Sources:
[Go Vulnerability Database GO-2026-5024](https://pkg.go.dev/vuln/GO-2026-5024),
[Go Security Team announcement](https://groups.google.com/g/golang-announce/c/6MMI8Lj-Atg).

Both jobs were green because report-only records findings without failing the workflow. The intake snapshot also showed `baseline_gate: success` while its normalized control summary was `fail` (one applicable control, one failed). That wording can be misread as a governance pass.

The local DevSecOps intake correctly bound each downloaded governance report to repository, commit, run, artifact, and the immutable L1.1.3 workflow tag/SHA. However, its snapshot marked SBOM, scan, and artifact digest as absent: the consumer governance-run input and application evidence are separate artifacts and the intake was run against only `devsecops-pipeline-evidence`. The typed-evidence intake stopped for both consumers because the expected `governance/vulnerability-scan-trust.json` file was absent. The result snapshots stayed in the temporary checkout and were never registered or published.

### Repeatability

Attempt 2 and attempt 3 used the same commit, event, tool versions, Trivy database evidence, normalized findings, and governance input facts. The go-httpbin binary digest was identical. For cJSON, the gzip archive digest changed, but all four unpacked archive members had identical content hashes. SBOM timestamps/serial identifiers and scanner production timestamps varied; the normalized component sets/findings stayed the same. This supports semantic decision repeatability, not byte-for-byte reproducible packaging for cJSON.

### Existing go-httpbin CI

The upstream go-httpbin workflow also ran on the pilot commit in [run 37266263227](https://github.com/joku-dev/governance-eval-go-httpbin/actions/runs/37266263227) and failed independently of the pilot workflow:

- `test (stable)` hit a timing failure in `TestDrip/handle_cancelation_during_drip` (`context deadline exceeded`).
- `lint-github-actions` failed while trying to fetch the private evaluation repository (`repository ... not found` in that job).
- The oldstable test and general lint jobs passed.

The dedicated pilot build/test job passed on all three attempts. This does not erase the separate upstream CI failure; it should be resolved or classified before claiming the whole repository CI is green.

## ECV case matrix

| Case | Status | Observed result |
|---|---|---|
| ECV-01 Measured evidence | **FAIL** | Real build/SBOM/scan evidence exists and the central verifier binds governance report identity. Central intake does not bring the consumer SBOM, scan, or artifact digest into its result projection; typed Trust intake is unavailable without the trust record. The baseline decisions are failures in report-only mode. |
| ECV-02 Repeatability | **PASS, semantic** | Attempts 2 and 3 preserve inputs, findings, tools, and decision semantics. cJSON archive bytes vary despite identical unpacked contents; see byte-for-byte limit above. |
| ECV-03 Missing evidence | **PASS, report-only** | A disposable run with the SBOM path missing generated an explicit `SBOM not found` failure with `blocks_merge: false`; no positive evidence was fabricated. |
| ECV-04 Tampering | **PASS** | Altering a digested report after capture fails `content_digest_verified`. |
| ECV-05 Misattribution | **PASS** | Supplying another consumer/commit causes identity binding checks to fail. |
| ECV-06 Replay | **PASS** | Exact replay is idempotent; conflicting context/digest is surfaced by replay assessment. |
| ECV-07 Reordering | **PASS** | Delivering an older record after a newer one retains both history entries and leaves the newer result current. |
| ECV-08 Freshness | **PASS** | Expired evidence is explicitly marked failed under the provisional report-only freshness policy. |
| ECV-09 Recovery | **PASS** | Retrying the same event with a new generated timestamp returns the existing append-only record without overwriting history. |
| ECV-10 Concurrency | **PASS, fixture scope** | Parallel intake writes for two consumer identities remain separated in distinct paths. |
| ECV-11 Unsupported input | **PASS** | Unsupported event values fail schema validation. |
| ECV-12 Independent usability | **BLOCKED** | No independent engineer performed the onboarding/usability tasks. The maintainer’s walkthrough would not meet the independence criterion. |
| ECV-13 Controlled closed loop | **BLOCKED** | No closure authority was established for this pilot. Prior authority delegated for the GRS-002 waiver is scoped to that waiver and was not reused. |

ECV-04 through ECV-11 were executed as disposable local fixtures against the isolated governance revision; they do not claim live cross-organization review or production intake. The focused evidence-trust, freshness, result-ledger, concurrency, and typed-intake test groups also passed (41 tests total).

## Governance integrity and current situation

- The official governance repository is at `main` commit `df15833e0dea51b6415a0ce416243698c656f6ca`, which merged the central intake remediation in PR #212. The official indexes still cover **three registered consumers**. The most recent committed ha-CPsWMS result indexes are dated 2 October and were not refreshed by this pilot.
- In those indexes, ha-CPsWMS DevSecOps run `36997125273` is `pass` (16/16 applicable controls) with Trust `integrity_verified`; Architecture run `36997124090` is `pass` (4/4 gates) with Trust `integrity_verified`. The separate typed vulnerability scan run `36997124065` is `provenance_verified` (9 checks pass, 0 fail, 3 not evaluated), but records **3,269 findings** and maximum severity **critical**, including one critical finding in the `neo4j` image. Provenance verification confirms evidence identity/custody; it is not a clean-security result. The pilot did not refresh or change any of these official records.
- Governance baseline, policies, schemas, waivers, official result history, viewer, and official consumer registry were not changed by this pilot.
- The official portfolio remains at **three registered consumers**. Neither private evaluation repository is an official consumer.
- No pilot artifact or snapshot was pushed to the governance repository; the original working checkout and local-only material were not used by the pilot.
- The isolated governance baseline validation passed after using a temporary test-only Git identity and disabling signing for the suite’s throwaway fixture commit. No signing key was used by the test. The first unmodified validation invocation failed only at that signing-dependent fixture because the sandbox could not reach the signing agent.

## Recommended next actions

1. Publish a new immutable, versioned reusable-workflow reference that includes the merged #212 implementation. Keep `l1-baseline-v1.1.3` unchanged; new release tags require the registered SSH signer.
2. Update both private pilot consumers to that version while keeping them report-only, then run fresh workflows and normal central intake. Confirm producer `blocks_merge` semantics and re-check evidence, archive custody, source attribution, governance outcome, and Trust.
3. Resolve the go-httpbin finding at `examples/custom-instrumentation/go.mod` through source-owner review and a fixed-version rescan; also classify the upstream flaky test/private lint failure.
4. Decide the repository protection posture before any official admission. Current pilot repositories permit direct pushes; any review-independence exception must remain an explicit, separately scoped decision.
5. Keep ECV-12 and ECV-13 blocked until an independent engineer and a properly authorized closure role are available. Decide admission and Wave 2 separately after Wave 1 evidence is complete.

## Follow-up remediation record

**Recorded:** 2026-10-05
**Change request:** [GCR-2026-114](../../governance/change-requests/GCR-2026-114-external-consumer-pilot-intake-remediation.md)
**Implementation state:** PR #212 was merged as `df15833e0dea51b6415a0ce416243698c656f6ca`; a fresh consumer rerun remains outstanding until a new versioned reusable-workflow reference is published and adopted.

Both pilot repositories still call the immutable `l1-baseline-v1.1.3` wrapper.
Merging PR #212 onto `main` did not alter that tag; do not move or rewrite it.
The next release step is to publish a new versioned reusable-workflow reference
with a directly signed tag, then update the private pilot workflows to use it
before starting fresh runs.

### Historical artifact replay against the remediation

After preparing the intake changes, the original attempt-3 pipeline and run-input
archives were downloaded again from the two private GitHub Actions runs and
replayed locally through the updated evidence-resolution and gate-normalization
functions. The downloaded archives were retained in a disposable directory;
their SHA-256 values are recorded here:

| Consumer / run | Pipeline artifact ZIP SHA-256 | Run-input artifact ZIP SHA-256 | Resolved evidence |
|---|---|---|---|
| cJSON / `37266266970` | `5b63e6b6c246e5140ccbc9d665c8b8ef40ed8d24f303e16318dffcfabcab0e3a` | `d1f0a8b4a4ad0247553577c4086105f7b62cbec0f3ef40422621b483c662cf9d` | SBOM present, scan present, build bytes match declared SHA-256, separate run input present |
| go-httpbin / `37266263787` | `ee5cb3c2a019da1c1282c0fb3781c822d29f7b53748c7b8dbf30e486ed1cbea6` | `c0ecd717d26aedbd3d1d2026887e9bcfe452e80aa8195e18673b2327156635be` | SBOM present, scan present, build bytes match declared SHA-256, separate run input present |

The normalized gate result remains `fail` with `blocks_merge: false` for both
runs. cJSON fails the direct-push protection check. go-httpbin has the same
finding plus the `unknown` Trivy severity threshold finding and the unapproved
security-threshold finding. The workflow job being green therefore remains
distinct from the governance result.

The replay also confirms that two producer declarations still disagree:
`pipeline-evidence.json` says `security_gates.enforced: true` and
`external_direct_downloads_detected: false`; the separate governance run input
declares `security_gates.enforced: false` and
`external_direct_downloads_detected: true`. The intake preserves these sources
separately and does not treat consumer-declared egress as centrally measured.

This was a local replay of the original artifacts against the remediation
helpers, not a new consumer workflow run and not a complete live central intake.
It created no result snapshot, Trust record, official index entry, viewer
update, consumer registration, or PR in either pilot repository. A new workflow
run using an updated producer, followed by normal central intake, is still
required to verify the full round trip and close ECV-01.

Validation ran in a fresh temporary clone so pre-existing generated changes in
the maintainer workspace remained untouched. OPA, runtime governance,
repository validation, evidence-agent provenance, and all 656 unit tests
passed with an isolated Git identity/signing configuration for temporary test
fixtures. The final workspace code also passed all 14 focused GitHub Actions
intake tests, including path containment and source-attribution cases.

The follow-up implementation addresses these central repository defects:

1. The GitHub Actions result intake now defaults to the standard `devsecops-pipeline-evidence` artifact, where the reusable workflow uploads `pipeline-evidence.json`, `baseline-gate-result.json`, SBOM, scan, and build output. Legacy report artifacts remain selectable explicitly.
2. The intake reads `pipeline-evidence.json`, resolves declared SBOM, scan, and artifact paths against the downloaded archive, and only reports those evidence flags when the files are present. For the build artifact it also recomputes SHA-256 and compares the actual file bytes with the declared digest.
3. When `devsecops-governance-run-input` is a separate artifact, the intake downloads it and records its content digest and artifact identity. The snapshot keeps its facts labelled as producer-declared values beside the central pipeline evidence values; it does not assert that the central service independently observed consumer network traffic.
4. The Python-download fallback now obtains the raw artifact ZIP through `gh api`, keeps the archive bytes, and safely extracts that exact archive. The typed Evidence Trust intake uses the same fallback so archive hashing and custody are retained.
5. The snapshot separates the governance decision in `checks.baseline_gate` from the Actions job conclusion in `checks.baseline_gate_workflow_job`. A report-only failure is no longer rendered as a governance pass just because the workflow job succeeded.
6. Evidence documentation defines `security_gates.enforced` as “gate ran and evaluated”; merge blocking is recorded separately by `blocks_merge`. The reusable evidence generator now emits that separate field.

The cJSON and go-httpbin pilot repositories have not yet been updated or rerun against these changes. No pilot snapshot was added to official status, no consumer was registered, and ECV-12/13 remain blocked. The official portfolio and ha-CPsWMS status cited above therefore remain unchanged.

### Post-merge full central intake replay

**Recorded:** 2026-10-05, after PR #212 merged. Using a fresh disposable checkout at the merged `main` revision, the complete central `intake_github_actions_run.py` command was run against the retained attempt-3 artifacts for both consumers. The resulting snapshots stayed under `/private/tmp/ecv-stability-governance/status/results/`; they were not copied into the official checkout or published.

| Consumer / run | Resolved evidence | Governance / job outcome | Governance-result Trust |
|---|---|---|---|
| cJSON / `37266266970` | SBOM, scan, build digest, and separate run input all present and verified; both primary and run-input archive digests recorded | `checks.baseline_gate: failure`; `checks.baseline_gate_workflow_job: success`; overall `fail` | `provenance_verified` |
| go-httpbin / `37266263787` | SBOM, scan, build digest, and separate run input all present and verified; both primary and run-input archive digests recorded | `checks.baseline_gate: failure`; `checks.baseline_gate_workflow_job: success`; overall `fail` | `provenance_verified` |

Trust applies to the captured governance-result artifact and its provenance/custody; it does not establish trust in the application source or binary. Both runs still reference the old `l1-baseline-v1.1.3` workflow. Accordingly, `blocks_merge` is absent from the producer declarations, and the consumer run input still disagrees with `pipeline-evidence.json` on gate evaluation and direct downloads. The central snapshot preserves those source-labelled values rather than resolving them by assumption.

This confirms the full **central intake path** against retained historical artifacts after #212. It is not a fresh consumer run, does not verify producer adoption of the new evidence semantics, and does not close ECV-01. No official index, viewer, Trust result, consumer registry, or `main` state changed. ECV-12 and ECV-13 remain blocked.
