# Portable evidence intake v2 candidate

This is the first M2 increment after the [portable runtime](../adapters/portable-governance-runtime.md). It implements shared evidence verification and a private state/migration foundation. It does not complete M2, install a VM version, update accepted indexes or enable publication. See [GCR-2026-174](../../governance/change-requests/GCR-2026-174-portable-evidence-intake.md).

## Verification contract

`scripts/intake_portable_evidence.py` exports a fresh directory and ZIP containing context, normalized input, result and the three real evidence files. The manifest retains original subject paths, byte sizes, SHA-256 digests, repository identity and full execution identity. No provider credential or operator policy belongs in the bundle. The v2 bundle/policy/receipt schemas are under `schemas/portable-intake-*-v2.schema.json`.

The same `verify_bundle` function serves local import and native collection. It checks the exact member set, safe paths, file digests, subject associations, provider/instance/repository/run/job/attempt identity, trusted baseline/runtime pins and context consistency. It reconstructs critical input facts from the files and calls the same M1 evaluator with real pinned OPA. A re-signed manifest cannot conceal a forged decision or normalized scan. Findings remain eligible evidence when execution is complete; this does not mean the finding passed.

The caller supplies an explicit timezone-aware evaluation time and replay history. Freshness uses policy bounds; native provenance also requires the result time inside the independently resolved job window and a sufficiently recent job completion. Replay distinguishes `new`, `duplicate` and `conflict`. Every accepted import records its first verification receipt transactionally, including integrity-only imports. Subsequent processing does not renew the old receipt's time or Trust. A different payload for the same execution conflicts. Use separate state roots for experiments and operational native collection.

Local imports can reach `integrity_verified`. `provenance_verified` additionally requires collector-owned native run/job/commit/artifact/configuration/custody assertions, fresh evidence and a new replay key according to the existing trust model. A JSON field inside the bundle cannot supply these assertions. The observation is bound to the exact downloaded manifest; an observation from another bundle cannot qualify it. `attested` is not implemented. Native Trust describes evidence provenance and does not grant governance authority or trusted runner administration.

The original result remains `unverified`; verification is a separate source-bound receipt. Every receipt says `official_acceptance: false`, `blocks_merge: null`. Eligible candidates are not official latest results, full-baseline assessments, releases, waivers or blocking approvals. The five-control `pipeline-l1` scope remains explicit.

## Native transports and proof limits

Native collection also reacquires effective protection/review facts through the SCM adapter and compares their values with the producer context. Missing facts or changed protection keep the receipt below native candidate eligibility. A genuine native artifact cannot make consumer-declared protection facts authoritative. CI and SCM readers may use separate private credentials through `transport` and `scm_transport`; same-platform profiles can reuse their read-only API client. This comparison describes the observed intake-time facts; it does not invent historical branch-protection data.

| Profile | Implemented acquisition | Local evidence | Open boundary |
| --- | --- | --- | --- |
| GitHub Actions + GitHub | Exact run attempt, unique configured completed job, successful upload step, artifact metadata and SHA-256 ZIP digest, configuration bytes at the run commit | Synthetic API responses, actual ZIP/files, real OPA, instance/revision/configuration/manifest/time negatives | Real versions/edition and target workflow execution; reviewed transitive workflow/action/runner closure; PR head/merge checkout provenance remains unsupported here |
| GitLab CI + GitLab | Exact project, pipeline, job, native tested SHA, job artifact ZIP, configuration bytes at that SHA; failed jobs are collectible | Subgroup/native-ID fixture, same verifier and real OPA; native job ID separates retries | Real edition/version, protected configuration and transitive includes/runner closure; target lint/import and actual failure artifacts |
| Bamboo + configured SCM | Exact completed build key, native revision and one configured artifact file link, same-origin bounded download | Synthetic result/artifact response and real bundle integrity | Installed Bamboo/Bitbucket versions, plan/job/attempt and Specs/SCM provenance closure; this profile stays integrity-only |

Configuration hashes must come from independently reviewed producer configuration, never from the downloaded evidence. Review must cover transitive includes, actions/runtime pins, profile ownership, credentials and runner administration. A matching top-level file is one provenance check, not a proof of that entire security review. GitHub branch events are the supported native provenance context; a workflow-run head SHA is not silently treated as a PR merge SHA. GitLab captures the exact tested native job SHA. No last-successful-branch artifact lookup substitutes for a requested execution.

The adapters use configurable HTTPS endpoints, read-only credentials, finite request/page/byte budgets and redacted errors. API JSON does not follow redirects. Downloads start at the configured instance; cross-origin HTTPS redirects lose authorization. Rate-limit and retry diagnoses retain codes and delays, not response bodies or tokens. Native responses are private audit evidence under the operations root.

Acquisition reserves the full archive/unpacked/copy budget first. The default retained raw budget is 2 GiB with an 8 GiB free-space reserve; private policy may raise `storage_budget_bytes` and `storage_reserve_bytes`. Exhaustion halts collection without deleting historical evidence. This conservative pilot budget is not a storage/retention plan for 1,000–2,000 repositories.

Official contracts checked for this candidate: [GitHub workflow runs](https://docs.github.com/en/rest/actions/workflow-runs), [jobs](https://docs.github.com/en/rest/actions/workflow-jobs), [artifacts](https://docs.github.com/en/rest/actions/artifacts), [GitLab jobs](https://docs.gitlab.com/api/jobs/), [job artifacts](https://docs.gitlab.com/api/job_artifacts/) and [Bamboo REST](https://developer.atlassian.com/server/bamboo/rest/). Installed version/edition compatibility remains open; these references do not certify a live installation.

## Explicit local use

The operator's maximum age may tighten the existing central `freshness-governance-result-24h` policy; it cannot extend that policy's maximum. `future_skew_seconds` must be zero, preserving the central rejection of future timestamps. The central policy file is included in the verifier source digest. Separate typed scanner freshness and attestation claims remain outside this five-control governance-result candidate.

Prepare the pinned validation environment and OPA as described in the runtime guide. First run `governance_runtime.py run` to produce an assessment from real application/scanner output. Then:

```bash
python scripts/intake_portable_evidence.py bundle \
  --assessment portable-evidence --checkout application --destination portable-bundle
python scripts/intake_portable_evidence.py verify-local \
  --bundle portable-bundle.zip --policy /private/path/intake-policy.json \
  --root /private/path/mac-intake --opa .venv-validation/bin/opa \
  --at 2026-11-15T12:10:00Z
```

The policy must be a private operator-owned file. It pins `schema_version: "2.0.0"`, SCM identity (`provider`, canonical HTTPS `instance`, `native_id`, `path`, `url`), CI provider/instance, `baseline_id`, `baseline_digest`, `runtime_source_digest`, `max_age_seconds`, `future_skew_seconds` and `max_severity`. The baseline/runtime pins must match the prepared runtime, not values accepted from the bundle. Obtain them with the existing runtime's `baseline()`/`source_digest()` helpers. Choose the evaluation time for the actual evidence; the example time is a reproducible test input, not a freshness bypass.

Native `collect` uses `--context`, `--policy`, `--root`, `--opa` and `--at`. The policy additionally configures `transport.instance`, `api_url`, `token_env` and provider-specific selectors. For GitHub these are `workflow_path`, the exact native `job_name`, M1's `logical_job_id`, `upload_step_name` and `artifact_name`. For GitLab use the exact `job_name`, `configuration_path` and `bundle_prefix: "portable-bundle"`. Bamboo requires one downloadable bundle ZIP artifact name. A trusted `producer_config_sha256` is required for supported native provenance. The token value is supplied outside Git and outside the bundle; only the environment variable name is configured.

The templates archive diagnostics even when the runtime cannot create a complete bundle. Missing bundles or failed export/upload cannot produce a native candidate. GitLab `after_script` export failures may leave the job's earlier result unchanged; the collector still rejects missing native evidence. Bamboo exports a concrete ZIP artifact, since its ordinary directory artifact link is not a ZIP transport contract.

## State version and migration

The existing VM store is explicitly schema **1** (`PRAGMA user_version`). Existing version-0 legacy databases remain readable through the v1 operator. Schema **2** adds separate execution/receipt/batch/mapping tables with opaque provider/instance identities and transactionally claimed queue entries. Legacy jobs, metadata/cache/watermarks, frozen batch IDs, original PR numbers/URLs and snapshot bytes remain present. Old and new scopes are distinguished: a legacy workflow aggregate is not fabricated into a proven native job.

Stop the affected timers/services and acquire both operation locks before migrating. `migrate-legacy` creates a **fresh candidate destination** through SQLite's backup API and verifies the raw/verified/accepted file manifest. It requires a private mapping with `schema_version: 2` and `repositories`, keyed by the exact legacy repository path. Each mapping supplies complete SCM identity, `ci_provider: "github-actions"`, canonical `ci_instance` and `legacy_scope: "workflow-aggregate"`. Missing or ambiguous mappings and unclassified state halt the operation. No credentials are copied.

```bash
python scripts/intake_portable_evidence.py migrate-legacy \
  --root /private/path/stopped-legacy-state \
  --destination /private/path/new-v2-candidate \
  --legacy-mapping /private/path/legacy-mapping.json
```

Migration never changes the source data root or activates the candidate. Version-2 operators reject incomplete migration candidates. After an interrupted candidate, retain it for diagnosis and rerun from the unchanged source into another fresh destination. Legacy frozen/open/partially published batches are explicitly held for reconciliation through their original publication identity. They are not silently rebatched or sent to a new provider. Neither imported legacy Trust nor authority is upgraded.

The v2 `backup`, `verify-backup` and `restore` operations preserve SQLite, immutable evidence and migration metadata. Restore requires a fresh data root and verifies content hashes/database integrity before opening it. Migration also retains the exact original SQLite backup as `legacy-database.sqlite3`; it is not overwritten by the v2 transformation. `restore-legacy --root FRESH_ROOT --destination VERIFIED_V2_BACKUP` reconstructs exactly the original legacy manifest from that retained database and its original files. Later v2 evidence remains in the v2 backup for reconciliation. Keep evidence created after a backup separately and reconcile it before switching roots. A legacy code pin is not a supported rollback on a v2 root; use a compatible v2 operator or an independently verified legacy restore and publication reconciliation. No automatic downgrade is provided.

## Current work-package status

| Work | State |
| --- | --- |
| WP0–WP4 / M1 | Implemented candidate in preceding PR; local and GitHub Ubuntu validation, separate live acceptance open |
| WP5 shared bundle/verification/identity/replay | Implemented in this increment; local/native fixtures and real OPA |
| WP5 legacy persistent migration | Backup-first candidate and immutable mappings implemented; real legacy identity mapping and open batch reconciliation remain operator-specific |
| WP6 central SCM/CI operations, lifecycle/self-security profiles | Subsequent implementation required; legacy accepted paths unchanged |
| WP7 VM wiring, deployment/update/drift/recovery integration | Subsequent implementation required; new schema is not selected by existing VM services |
| WP7 1,000/2,000-repository capacity | No end-to-end capacity claim in this increment |
| WP8 | Revision-bound local review/CI for this increment; full M2 acceptance remains open |

The Mac and VM must use separate private operations roots, credentials and sessions. This CLI requires an explicit `--root`; it does not synchronize drafts or select a publisher. The VM was last read at `edf16239e9274dbc33f38f204ef80f58c989f969`, with the Workbench active. Poll/work timers were active; the last oneshot executions were condition-skipped. This observation does not prove collection or publication. No VM change was made for this increment.
