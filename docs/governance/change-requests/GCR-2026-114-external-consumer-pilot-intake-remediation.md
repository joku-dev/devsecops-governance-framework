# GCR-2026-114: External Consumer Pilot Intake and Evidence Reconciliation

## Intent

Correct the central evidence intake defects observed during the WP-ECV-001 Wave 1 pilot. The change makes the GitHub Actions intake consume the reusable workflow's actual evidence artifact, verifies producer-declared files against downloaded bytes, preserves archive custody on the authenticated CLI fallback, and distinguishes a report-only governance failure from a successful workflow job.

The evidence and run records for the pilot are documented in [the 2026-10-05 pilot results](../../operations/status/external-consumer-validation-pilot-2026-10-05.md). The pilot remains exploratory: its private evaluation repositories are not official consumers and no pilot result is added to the official status indexes.

## Artifact Intake Classification

| Field | Decision |
|---|---|
| Artifact | Governance change request for result intake, evidence attribution, and documentation |
| Type | Additive governance-platform behavior and evidence-contract clarification |
| Source document intake | Not required; no new source document is introduced |
| Primary implementation | `scripts/intake_github_actions_run.py`, reusable workflow evidence generation, typed Evidence Trust artifact fallback |
| Schema impact | Additive optional `security_gates.blocks_merge` field and clarified meaning for `security_gates.enforced` |
| Policy impact | None; no OPA policy behavior changes |
| Control baseline impact | None; released DevSecOps L1.1.3 package is unchanged |
| Architecture governance impact | None |
| Viewer/index impact | Existing status snapshots gain additive `evidence_context` and a distinct workflow-job check. No generated official index or viewer data is edited in this change. |
| Release impact | No policy, control-model, or OPA change. The additive evidence fields require a new minor L1 v1.2.0 package and versioned wrapper; existing `l1-baseline-v1.1.3` remains unchanged. |
| Enforcement impact | None; report-only remains report-only, and gate `blocks_merge` follows the configured mode |
| Consumer impact | Additive snapshot fields; standard intake now uses `devsecops-pipeline-evidence` by default. Older report artifacts remain selectable explicitly. |

## Observed Problems

The pilot exposed five issues in the central result-intake path:

1. The intake default selected `governance-control-evaluation`, while the released reusable workflow places `pipeline-evidence.json`, `baseline-gate-result.json`, SBOM, scan, and build output in `devsecops-pipeline-evidence`.
2. The result snapshot derived SBOM, scan, and build-digest flags from run-input assertions instead of checking the downloaded evidence artifact and its files.
3. `devsecops-governance-run-input` may be a separate artifact. The previous intake did not download it, leaving its digest absent even when the artifact existed.
4. The `gh run download` fallback extracts files but does not retain the original archive bytes, preventing an archive digest/custody subject from being recorded.
5. A report-only gate could correctly write `status: fail` and `blocks_merge: false` while its GitHub Actions job concluded successfully. The snapshot labeled the baseline gate from the job conclusion, creating an apparent pass/fail contradiction.

The pilot also found a naming ambiguity: `security_gates.enforced` was treated as both “gate evaluated” and “findings block merge.” The reusable workflow already records gate mode and `blocks_merge` separately.

## Change

1. Default direct and workflow intake to `devsecops-pipeline-evidence`; retain explicit artifact-name override for historical runs.
2. Read `pipeline-evidence.json` from the downloaded archive. Resolve the declared SBOM, scan, and build paths only when each resolves to a unique file inside that archive. For the build digest, require SHA-256 and compare the declared digest with the actual file bytes.
3. Download the separate `devsecops-governance-run-input` artifact when it is not embedded in the primary archive. Record its content digest and artifact identity. Keep producer-declared run-input values beside pipeline-evidence values, with clear source attribution; the central intake does not claim to independently observe consumer network traffic.
4. Use the GitHub Actions artifact API through authenticated `gh api` as the fallback download path. Retain the raw ZIP and hash it before safe extraction. Reuse this helper in typed Evidence Trust intake so a successful fallback preserves archive custody.
5. Set `checks.baseline_gate` from the downloaded governance report and store the technical job outcome separately as `checks.baseline_gate_workflow_job`.
6. Define `security_gates.enforced` as the gate executing and evaluating the run. Record merge blocking separately in `security_gates.blocks_merge` and `baseline-gate-result.json`. This preserves successful evaluation in report-only mode without implying that merge is blocked.

## Evidence and Validation

The pilot result is the motivating observation, not a passing result for this remediation. It recorded the original failure modes, including the fact that two consumer integrations produced real builds, source-tree SBOMs, and Trivy reports but the central projection marked these items absent. The full local repository validation passed in a temporary clone: OPA, runtime governance, repository checks, evidence-agent provenance, and 656 unit tests. A final small intake refactor then passed the focused 14-test GitHub Actions intake suite in the workspace. A local replay of both original pipeline and run-input artifacts against the updated evidence-resolution helpers confirmed that the SBOM, scan, build digest, and separate run input are now detected for both runs. The report-only governance failures remain failures, and the two producer declarations still disagree on gate enforcement and direct downloads. The downloaded artifact archive digests and replay findings are recorded in the linked pilot result. This replay did not run the complete live intake or create snapshots; a fresh consumer rerun is still required to demonstrate that:

- SBOM, scan, and artifact digest flags derive from files actually present in the intake archive;
- modifying a build artifact without updating its digest makes the digest evidence flag false;
- a separate run-input artifact is downloaded and its digest/identity is represented with producer attribution;
- a report-only governance failure is shown as `checks.baseline_gate: failure` alongside `checks.baseline_gate_workflow_job: success`;
- an authenticated `gh api` fallback leaves a raw ZIP whose digest is available and whose content is safely extracted;
- typed Evidence Trust intake continues to verify subject content and retains the archive digest on fallback.

Repository-required validation is `./scripts/bootstrap_validation_env.sh` followed by `./scripts/validate_all.sh`. The pilot consumers currently call `l1-baseline-v1.1.3`, whose wrapper pins the reusable workflow to immutable commit `33d5aa35479b4230525731911757afa4a24d8af2`. This change on `main` will not alter those existing runs. After this change is reviewed and merged, a new versioned reusable-workflow entry and tag must pin the reviewed implementation; the pilot workflows can then opt into that version and run again. A fresh consumer rerun is required before ECV-01 can pass. No consumer admission or official status update follows automatically from this code change.

## Boundaries and Remaining Decisions

- The central intake records consumer-declared `external_direct_downloads_detected`; it does not measure consumer egress. The consumer workflow must set that declaration from a defined observation method before the claim can be treated as meaningful.
- The current pilot's `security_gates.enforced: false` run-input value was produced by the pilot integration. This change clarifies the contract and emits a separate `blocks_merge` value; existing consumer producer code must adopt the semantics and rerun to reconcile those producer-side facts.
- The standard reusable collector's `external_direct_downloads_detected` remains false unless its configured observation input is set. It is not inferred from downloaded toolchains.
- The go-httpbin Trivy finding, its independent upstream CI failures, the cJSON archive byte-level variation, ECV-12 independent usability, and ECV-13 closure authority remain open and are outside this central intake change.
- No official consumer registry, status indexes, viewer data, Trust results, source application repositories, branch protection, or published baseline is changed by this proposal.

## Release Decision

- [x] No policy, control-model, or OPA behavior change; prepare the additive L1 v1.2.0 evidence package as a minor release
- [x] No released package or tag mutation
- [x] No change to blocking mode or lifecycle acceptance
- [x] Prepared versioned L1 v1.2.0 workflow and package in this follow-up PR; publish only after review and merge, and keep `l1-baseline-v1.1.3` unchanged
- [ ] Re-run the pilot and close ECV-01 after reviewed implementation is available
- [ ] Keep ECV-12 and ECV-13 blocked until their independent reviewer and closure authority criteria are met

## Post-Merge Verification

PR #212 merged to `main` on 2026-10-05 as `df15833e0dea51b6415a0ce416243698c656f6ca`. After the merge, the full central `intake_github_actions_run.py` path was executed in a disposable checkout against the retained attempt-3 artifacts for both private pilot consumers. The resulting snapshots remained local under `/private/tmp/ecv-stability-governance/status/results/`.

For both cJSON (`37266266970`) and go-httpbin (`37266263787`), the central intake found the SBOM, vulnerability scan, build artifact and separate run-input artifact; verified the build digest; retained digests for the primary and run-input archives; and recorded `checks.baseline_gate: failure` separately from `checks.baseline_gate_workflow_job: success`. The report-only governance outcome remained `fail`, and Trust for each captured governance-result artifact reached `provenance_verified`.

This replay confirms central processing of the retained historical artifacts. It is not a fresh consumer run or producer adoption test. Both consumers still reference `l1-baseline-v1.1.3`, so their artifacts lack the updated `blocks_merge` declaration and continue to disagree between pipeline evidence and run input about gate evaluation and direct downloads. No pilot snapshot, index, viewer, consumer registry or Trust result was published. A new immutable workflow reference and fresh consumer runs remain necessary to verify producer semantics and close ECV-01; ECV-12 and ECV-13 remain blocked.
