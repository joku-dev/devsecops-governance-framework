# V2 functional parity: scope, evidence and implementation record

The maintainer requested full technical parity with the last V1 on 15 November
2026. [GCR-2026-186](../../governance/change-requests/GCR-2026-186-axiom-v2-functional-parity.md)
records the technical scope. The Goal remains **in progress** until the complete
product, installed capabilities and operating workflows have matching evidence.

## Frozen comparison scope

| Binding | Value |
| --- | --- |
| V1 reference | `6b557fefe295b58272d2271326576ca3a3687197` |
| V2 starting source | `b6e3b64951456b5878a98810d50ba17cbe89dfe0` |
| New implementation branch | `feat/axiom-v2-functional-parity` |
| Machine-readable scope | `config/axiom-v2-functional-parity.json` |
| Coverage to deliver | All 22 catalogue areas, 135 original script entrypoints, 37 native CI/workflow definitions and 16 named operating workflows |
| Scope exceptions | None; retaining a source file is not an installed counterpart |
| Real consumer reference | `joku-dev/ha-CPsWMS`, pinned Main `5c3b5cb50d2260bfbde736c9ac80667271406d99` |

The matrix retains each original source blob/SHA/mode, top-level declarations
and statically declared CLI options/actions. Native workflow definitions are
also pinned. The catalogue remains the functional source of scope; source-file
counts alone neither define functional equivalence nor prove execution.

`pending`, `in_progress` and `verified` are different states. Verified claims
require installed counterpart/evidence bindings, including positive and negative
outcomes. The audit can compare the matrix with the original immutable Git
snapshot, and rejects removed subjects, changed source hashes, duplicate/missing
areas and unapproved scope exceptions. Declared evidence is technical evidence,
not independent human approval, a new operating acceptance or compliance.

```sh
python scripts/axiom_v2.py parity --reference /private/operator/v1-reference
python scripts/axiom_v2.py parity --reference /private/operator/v1-reference \
  --evidence-directory /private/operator/parity-receipts --require-complete
```

The second command currently returns nonzero: full functional parity is not
complete. Normal audit output names the outstanding subjects instead of silently
reducing the product to the already portable subset.

## First executable increment

The product now has an explicit, instance-bound `evaluate` command for the full
existing control report and four architecture gates. The common control evaluator
keeps its legacy report semantics and accepts an explicit pinned OPA for V2.
Architecture assessment is extracted into a neutral application module with V1
source lineage; the retired V1 CLI is not imported or dispatched by V2.

```sh
python scripts/axiom_v2.py --instance /private/operator/v2-instance evaluate \
  --domain controls --input /private/operator/run-input.json \
  --at 2026-11-15T12:00:00Z
python scripts/axiom_v2.py --instance /private/operator/v2-instance evaluate \
  --domain architecture --input /private/operator/architecture-input.json \
  --at 2026-11-15T12:00:00Z
```

All queries use the same frozen physical input bytes. Duplicate JSON keys,
unapproved OPA, incorrect source revision, changed/tampered report summaries and
approval flags are rejected. A typed diagnostic assessment is stored privately
under the node's `state/assessments/`; source/model/accepted indexes are not
rewritten. Its runtime/input/OPA digest, source revision, worktree-clean flag and
explicit evaluation time remain visible.

The report preserves all 46 V1 control records, including applicable,
not-applicable and not-tested outcomes. This is the V1-compatible report scope,
not a claim that every record has measured proof or that the five-control
portable CI gate has suddenly expanded. Source declarations and physical/native
measured evidence remain different inputs and assurance scopes.

The new command is diagnostic/report-only: findings remain in the stored report,
while completed assessment execution returns zero. An incomplete execution
returns 2. The retained V1 control-report CLI's finding exit 1 is a different
CLI contract; existing legacy blocking integrations are not changed or silently
activated in V2. Complete operating/enforcement parity still requires its own
explicit profile and tests.

## Evidence captured so far

- Four independently executed frozen V1 golden cases: control pass/finding and
  architecture pass/finding. The V2 raw reports match their complete V1 reports,
  not only headline counts. These fixtures are explicitly synthetic and are
  separate from real consumer evidence.
- A first real `ha-CPsWMS` source/declaration replay at pinned Main `5c3b5cb` uses
  the exact same generated physical inputs for both versions. Raw reports match:
  46 control records, 16 applicable (10 pass, 6 fail), 30 not applicable; four
  architecture gates pass. The six controls concern missing structured linkage,
  source-control/review, static-analysis review, release-approval/artifact-only
  and operational-record fields in this collector input. They are not newly
  measured vulnerabilities or V2-only regressions.
- The real replay is not a fresh application CI/scanner run, independent
  provenance acceptance, installed V2 proof or an official result-index update.
  Private raw inputs, hashes and receipts remain outside Git. Existing accepted
  results and other producer contexts keep their original findings and Trust.

## Candidate requirement and DCR authoring increment

The same Goal now adds private `requirements` and `dcr` application routes.
`requirements` exposes source import, native source preparation, decisions,
whole/partial activation, reanalysis, next-decision/report, migration completion
and publication preparation. It shares the existing requirement business rules
and extracts orchestration into an explicit workspace context. The V1 CLI is
neither imported nor dispatched. A frozen V1 native flow produces exactly the
same eight data/publication files in V2 at the same synthetic time.

```sh
python scripts/axiom_v2.py --instance /private/operator/v2-instance requirements \
  --workspace authoring init
python scripts/axiom_v2.py --instance /private/operator/v2-instance requirements \
  --workspace authoring report
python scripts/axiom_v2.py --instance /private/operator/v2-instance requirements \
  --workspace authoring put-native --file /private/operator/requirement.md --name requirement.md
python scripts/axiom_v2.py --instance /private/operator/v2-instance requirements \
  --workspace authoring start-native --case-id RLC-NEW \
  --source-path docs/governance/requirements/native-sources/requirement.md
python scripts/axiom_v2.py --instance /private/operator/v2-instance dcr \
  --workspace authoring structural --review-id review-001 --source-id DSCB-STD-REQ-001
```

Each workspace seeds committed `docs/` and `model/` data into a fresh private
node-owned store. A writer takes an exclusive lock, works on a separate staging
copy and publishes a hash-bound immutable data generation only after success.
Exceptions leave the previous generation visible. Invalid paths, symlinks,
tampered generations, different nodes/runtimes and concurrent writers fail
closed. Historical generations stay available; existing workspaces are never
reset by `init`. Runtime updates will require explicit workspace migration.

All workspace results declare `authority_scope: candidate_only` and
`official_acceptance: false`. Historical approval vocabulary inside copied
payloads is preserved for faithful authoring; it does not confer authority on
the new node. Explicit decision/activation commands prepare candidate changes.
They do not approve a real source, transfer personal consent, publish a baseline,
update accepted result indexes or activate blocking. Registered candidate sources
remain unavailable for requirement derivation.

`dcr` exposes structural review, normalization of a supplied provider projection,
validation of a supplied semantic response and comparison with either existing
synthetic evaluation catalogue. It invokes no provider/model. Valid semantic
findings remain unconfirmed; fabricated quotes are quarantined. Responses bind
the review ID and exact stored manifest digest, and existing review evidence is
not overwritten. Frozen V1 structure, positive/negative semantic cases and
adapter outputs match the neutral domain modules exactly.

A candidate data generation is not a reviewed Git working tree. Its generated
manifest therefore records a null `reviewed_commit`; the resulting `DCR-009`
freshness finding remains visible. Candidate structure/semantic checking is
implemented, while reviewed Git publication, full DCR operation/catalogue-run
preparation and installed authoring acceptance remain open matrix work. These
routes do not yet constitute full document-workflow parity or a production DCR
rollout. Existing schema/report versions and human decision boundaries remain.

## V2 source collection and installed comparisons

`collect-source` now prepares either full report input directly from a local
repository at an explicit immutable commit. It snapshots committed blobs into a
private data-only directory; inspected application code is never executed.
Uncommitted/untracked changes are ignored, Git replacement refs cannot reinterpret
the pin, symlink/submodule entries and oversized snapshots fail explicitly.
Provider adapters observe the selected CI source layout. Shared collectors retain
the V1 declaration semantics without embedding native CI paths in the core.

```sh
python scripts/axiom_v2.py --instance /private/operator/v2-instance collect-source \
  --domain controls --repo /private/operator/ha-CPsWMS \
  --revision 5c3b5cb50d2260bfbde736c9ac80667271406d99 --ci-profile github-actions
```

The receipt supplies a private `input_path` for `evaluate`, its physical SHA-256
and canonical input digest. Source declarations, including historical `approved`
fields, remain unverified; source file presence proves no actual CI execution or
independent approval. The reviewed default source-layout profiles are GitHub
Actions (`.github/workflows/ci.yml`), GitLab CI (`.gitlab-ci.yml`) and Bamboo YAML
Specs (`bamboo-specs/bamboo.yml` or `.yaml`). Live target acceptance remains separate.
Both collectors' synthetic full inputs match independent frozen V1 outputs;
collection from real pinned Main `5c3b5cb` matches the existing V1 input objects.

The first two increments at `6dd4581` have also been installed and exercised on
both hosts. Their pinned identities, separate source replay and fresh consumer
measurement limitations are recorded in the
[partial-parity progress receipt](../status/axiom-v2-parity-progress-2026-11-15.md).
This is evidence for those implemented capabilities, not for the rest of the
matrix. The later `7f74a85` collection and measured replay increment now has its
own separately pinned Mac/Linux proof in that same progress receipt.

The installed functional test is repeatable from a trusted development checkout:

```sh
python tests/acceptance/prepare_v1_parity_fixtures.py /private/operator/host-fixtures
"$V2_PREFIX/venv/bin/python" tests/acceptance/axiom_v2_functional_parity.py \
  "$V2_PREFIX" /private/operator/host-fixtures /private/operator/host-result.json \
  --expected-source 6dd4581b2398e9162c395c743ea9a4c1b6140984
```

Use a fresh prefix/workspace for a full repeat. The script checks four complete
V1 report goldens, private native-requirement preparation/decision/activation and
publication, rollback before decisions, retained DCR missing-snapshot findings
and explicit semantic-not-run behavior. It reports partial parity and no provider
or human acceptance. The fixture transport is private and all bytes are checked.

## Full measured L1 and container wire profile

The product now exposes `measured verify-local` and `measured capture` for the
existing ha-CPsWMS measured wire profile. The sixteen-control decision function
is extracted once into neutral `measurement_logic.py`; service lists and native
provenance/tool labels come from explicit adapters. GitHub run/artifact/ruleset,
scan, SBOM, dependency-lock, source-content and ephemeral-runtime bindings stay
inside native adapters. Neither original intake CLI is imported or dispatched.

```sh
python scripts/axiom_v2.py --instance /private/operator/v2-instance measured verify-local \
  --provider github-actions --kind l1 --bundle /private/operator/measured-bundle \
  --sha256 EXACT_CAPTURE_MANIFEST_SHA256 --at 2026-11-15T12:00:00Z
python scripts/axiom_v2.py --instance /private/operator/v2-instance measured capture \
  --provider github-actions --kind l1 --repository joku-dev/ha-CPsWMS \
  --run-id EXACT_SUCCESSFUL_MAIN_PUSH_RUN --credential measured-reader.json \
  --at 2026-11-15T12:00:00Z
```

`--kind containers` selects the original separate five-image container report.
The supported native profile retains V1's successful Main/push/original-workflow
scope, exact run attempt/commit/artifact binding, producer byte hashes, JUnit/SAST
recomputation, dependency/SBOM/scan identity checks and ephemeral runtime transport
binding. A failed diagnostic branch is rejected before artifact acquisition. This
native profile remains explicitly ha-CPsWMS/GitHub-specific; other providers need
separate reviewed bindings. The common control decision function has no native
SDK, API, hostname or provider command.

Live acquisition requires an explicit private file under the instance's
`credentials/` directory. The filename is passed as `--credential`; never pass a
token on the command line. Its exact JSON fields are `schema_version: 1`,
`provider: github-actions`, `instance: https://api.github.com`, the selected
`repository` and `token`. The native adapter requires matching realm/repository
and safe file permissions. No ambient `gh` login, environment token or inspected
application credential is used. The existing Actions secret is not a local/VM
credential and is not copied out of Actions.

The reader charges one shared bounded request budget for native metadata and
credential-free storage requests. Selected ZIP member reads use strict HTTPS
storage hosts, exact byte ranges, size/CRC/manifest checks and bounded aggregate
bytes; full multi-gigabyte image archives need not be downloaded. Authorization
is sent only to the configured native API and is absent from storage requests.
Truncated artifact lists, duplicate members/JSON, changed source bytes, wrong
image/run identities and XML entities cannot become valid measurements.

Captured selected bytes and a hash-bound `capture.json` are stored privately for
replay. Local verification records `native_metadata_rechecked: false`; a live
reader call records its actual acquisition separately. Replaying that same bundle
does not inherit the live-reader claim. The outer typed assessment always remains
report-only, unverified, without official acceptance, risk/production approval or
transferred authority. V1 report fields inside it describe only the retained wire
assessment. They do not promote a private V2 candidate into accepted indexes.

Complete independently executed frozen V1 raw groups and reports match both new
normalizers: all sixteen control records and the separate container details, not
only headline counts. Synthetic capture/redirect/range tests also verify private
credentials, metadata/source binding, no credential forwarding, budgets, tamper
rejection and replay boundaries. These are technical fixtures, not a fresh
successful consumer measurement. Source collection and synthetic measured replay
have separately pinned installed Mac/Linux evidence at `7f74a85`. Official
accepted-result publication and the remaining intake flows are still open under
the same Goal.

## Private assurance and staging supplements

`supplement assurance`, `staging`, `consolidate` and `inspect` expose the existing
V1 per-control assurance, seven-day staging-bundle validation and exact-subject
consolidation with explicit product data context. The core has no provider API or
legacy intake CLI dependency. Native composition retains the original supported
ha-CPsWMS successful Main/push profile; this is not a new deployment mechanism.

```sh
python scripts/axiom_v2.py --instance /private/operator/v2-instance supplement assurance \
  --measured STORED_L1_ASSESSMENT_ID --at 2026-11-15T12:00:00Z
python scripts/axiom_v2.py --instance /private/operator/v2-instance supplement staging \
  --measured STORED_L1_ASSESSMENT_ID --bundle /private/operator/staging-evidence \
  --evidence-repository-commit EXACT_COMMIT --at 2026-11-15T12:00:00Z
python scripts/axiom_v2.py --instance /private/operator/v2-instance supplement consolidate \
  --measured STORED_L1_ASSESSMENT_ID --staging STORED_STAGING_SUPPLEMENT_ID \
  --at 2026-11-15T12:00:00Z
python scripts/axiom_v2.py --instance /private/operator/v2-instance supplement inspect \
  --id STORED_SUPPLEMENT_ID
```

Assurance optionally takes `--typed-bundle FILE --sha256 EXACT_FILE_SHA256`. The
bundle is an explicit JSON object with `schema_version: 1` and `snapshots`, each
containing a schema-valid `snapshot` and its logical `source_file` label beneath
`status/typed-evidence-results/`. Exact original bytes are retained. Without it,
typed snapshots are empty; missing scope remains missing. Duplicate matching
typed snapshots are rejected. Supplied Trust is **reported input**, not a newly
verified attestation. All outer receipts remain `evidence_trust: unverified` and
`reported_trust_only: true`, without official acceptance or deployment authority.

Staging imports bounded regular files, rejects links/nested directories and
duplicate decision-bearing JSON keys, and checks every checksum, approval target,
image/risk acknowledgement, exact measured commit/run/attempt, security boundary
and time window. It retains a private hash-bound raw bundle. Consolidation joins
only a staging receipt tied to the exact stored measured source, and supplements
only L1-013/014/016. `inspect` reloads the source IDs and raw bytes and recomputes
the complete report; a changed report, different node/runtime, wrong dependency
domain or stale/tampered bundle fails closed. Historic inner Trust and approval
vocabulary does not become approval on the new node. No accepted index is edited.

The independently executed frozen V1 synthetic fixture compares all three full
reports. Negative tests cover checksum and resealed-subject changes, stale or
wrong-target approvals, typed ambiguity, links/size limits, foreign nodes and
resealed report tampering. The installed counterpart is reproducible from a
trusted development checkout with a fresh prefix:

```sh
python tests/acceptance/prepare_v1_parity_fixtures.py /private/operator/host-fixtures
"$V2_PREFIX/venv/bin/python" tests/acceptance/axiom_v2_measured_supplements.py \
  "$V2_PREFIX" /private/operator/host-fixtures /private/operator/supplement-result.json \
  --expected-source EXACT_INSTALLED_COMMIT
```

This test is explicitly synthetic, invokes no provider and asserts no full Goal
completion. Private supplement preparation is implemented; official acceptance,
typed-evidence native verification and publication remain separate open work.

A separate real historical replay uses the committed ha-CPsWMS staging bundle
for run `35428987714`, attempt 1, as present at Main `5c3b5cb`, evaluated at
`2026-09-19T09:00:00Z`. Frozen V1 and the new domain modules produce identical
complete assurance, staging and consolidated reports: 19 recorded staging checks;
consolidated 11 measured, 4 partial, 1 finding and zero gaps. Its comparable report
digest is `e9945cb126f8891c80fd307d006c5b6cba634b5952f646490f9f31da50651b8f`.
This is a historical source-level replay with the original measured snapshot,
separate from synthetic installed acceptance and the failed fresh producer. It
does not refresh evidence, exercise deployment or grant new operating approval.

## Remaining work in the same Goal

The full matrix stays authoritative for completion. Continue with neutral
collection and measured evidence, document/requirement/DCR workflows, accepted
intake and projections, lifecycle functions and explicit provider authority,
publication/release tooling, and service/update/backup/restore operation.
Rebuild and admit complete per-host packages, exercise installed counterparts
and repeat the real consumer comparison at the final source/evidence pins.
Unknown native target versions or human authority remain separate external
limits; they do not justify declaring missing technical capabilities complete.

No existing installation, released baseline or accepted personal pilot is
replaced by this increment. Source authoring and V1 are preserved while V2
capabilities are implemented and proven.
