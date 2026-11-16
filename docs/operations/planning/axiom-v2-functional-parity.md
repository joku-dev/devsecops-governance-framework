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

## Complete typed image verification and private intake

The `typed` command adds the existing V1 complete ha-CPsWMS image profile. It
verifies every selected ZIP, the complete Docker archive configuration and
uncompressed layers, scanner/SBOM byte and image bindings, explicit execution
records, immutable baseline references, freshness, custody and per-type replay.
It runs no image, application code or scanner. Native facts and provenance labels
stay in adapters; shared Trust logic requires explicit model context and custody
steps. The old `evidence_trust.py` remains V1 source but is physically excluded
from the active V2 installation and import closure.

```sh
python scripts/axiom_v2.py --instance /private/operator/v2-instance typed verify-local \
  --provider github-actions --bundle /private/operator/typed-bundle \
  --sha256 EXACT_CAPTURE_MANIFEST_SHA256 --at 2026-11-15T12:00:00Z
python scripts/axiom_v2.py --instance /private/operator/v2-instance typed capture \
  --provider github-actions --repository joku-dev/ha-CPsWMS \
  --run-id EXACT_SUCCESSFUL_MAIN_PUSH_RUN --credential typed-reader.json
python scripts/axiom_v2.py --instance /private/operator/v2-instance typed inspect \
  --id STORED_TYPED_ASSESSMENT_ID
python scripts/axiom_v2.py --instance /private/operator/v2-instance typed intake \
  --id STORED_TYPED_ASSESSMENT_ID
python scripts/axiom_v2.py --instance /private/operator/v2-instance typed index \
  --limit 100 --offset 0
```

The explicit reader file uses the same exact private schema as measured capture.
Native capture keeps V1's successful Main/push/original-workflow ha-CPsWMS scope,
artifact/run/attempt binding and optional exact-commit paired baseline run. It
reads whole archives because typed integrity includes configurations and layers;
the selected-JSON measured route alone cannot prove that claim. Native API
credentials never accompany storage requests. Archive sizes/digests are checked,
the producer run is rechecked after acquisition and failures remain visible.
Native verification uses actual system UTC after acquisition; it accepts no
operator-supplied historical `--at`. A fixed historical time belongs to local
replay, whose native metadata flag remains false.

Local import snapshots exact operator bytes before verification. A retained
capture manifest binds six archives and native wire metadata. `inspect` rehashes
and recomputes the full reports from retained bytes, without refreshing native
metadata. Typed assessment records bind the node, runtime/source and raw manifest.
They remain private/report-only/unverified wrappers, without official acceptance,
authority, risk acceptance or production approval. Inner V1 Trust records retain
the original computed vocabulary; their scope remains explicit.

`intake` separately admits a verified record into a private transactional SQLite
ledger. Native repository IDs, provider and instance define the namespace; display
paths do not collapse independent identities. Operator and native histories are
separate, so a supplied bundle cannot occupy a native receipt. Original V1
within-realm per-type replay rules are retained. A display path reused by a
different native repository fails replay rather than inheriting the old identity.
First records remain immutable: identical retries retain their first timestamp,
Trust and source receipt; changed evidence for one run/attempt is quarantined.
Failed batches roll back their writes. No accepted repository status file or
public index is edited.

The paged private index exposes native and replay latest separately. Producer
time selects latest independently of Trust; local replay always projects effective
Trust as unverified even when its inner diagnostic result reports a higher V1
level. A native read can derive the model's supported level only after its actual
checks and replay pass. This is evidence assessment, not role authorization or
independent attestation. Public publication and general typed intake profiles
remain separate open Goal work.

Storage is bounded: each ZIP is at most 1 GiB, image members at most 2 GiB,
metadata at most 32 MiB, and raw plus extracted material is at most 2 GiB per
verification by default. `--storage-budget-bytes` can select up to 32 GiB while
the 8 GiB filesystem reserve remains enforced. Invalid members, links, duplicate
names/JSON and archive/configuration/layer mismatches fail closed. Retention and
per-realm replay-history limits remain explicit capacity boundaries; this new
typed profile is not a production acceptance for 2,000 live repositories.

An independent frozen V1 fixture contains complete synthetic ZIP/tar bytes and
both original typed snapshots before and after replay, plus the measured container
report. Focused tests cover full report equality, native acquisition/clock mocks,
credential stripping, private command flow, native/replay separation, idempotence,
conflicts, transaction rollback, identity/realm isolation, tampering and storage
limits. Mock acquisition is not a successful live provider acceptance. The actual
fresh consumer producer remains blocked by its original OCI-index/configuration
guard; no permission or missing evidence is invented.

The installed acceptance harness is reproducible with a fresh prefix:

```sh
python tests/acceptance/prepare_v1_parity_fixtures.py /private/operator/host-fixtures
"$V2_PREFIX/venv/bin/python" tests/acceptance/axiom_v2_typed_intake.py \
  "$V2_PREFIX" /private/operator/host-fixtures /private/operator/typed-result.json \
  --expected-source EXACT_INSTALLED_COMMIT
```

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


## DCR operating contracts, catalogue and private projection

Finite `dcr` routes now expose the nine-artifact operating-contract validation,
trigger-based `scope`, and `prepare-catalog --review-id ID`. The last command
copies the six exact synthetic provider inputs, verifies their source/register
hashes and produces the original V1 `prepared_not_run` package. No provider/model
is configured or invoked. These reference data are explicit, fingerprinted product
resources; retired source CLIs remain absent from the installed execution set.

`structural --context committed-source` reads the fixed installed product source.
It requires a clean Git root and compares all document/model/schema bytes with
committed blobs, including files hidden behind Git index skip flags. The review
records that technical revision and rechecks it on subsequent operations. The
default `candidate` context still has no Git commit and retains DCR-009. Neither
context grants human approval or changes the accepted report-only pilot.

`project --review-id ID --report FILE --manifest FILE --decision FILE
--comparison-count N` prepares a **private** redacted snapshot. Repeat `--decision`
for every finding. Original schema, exact manifest/finding hashes, duplicate and
complete decision coverage, tracked requirement population and source freshness
checks remain. Supplied reviewer identities are declarations, not authenticated
human approvals. The snapshot is stored in a candidate generation; no public
`status/` file or provider proposal is written. Public handoff remains separate.

Independent frozen V1 cases cover the complete operations result, trigger plans,
all package input hashes, committed-source manifest/structural rules and exact
redaction. Positive/negative application tests cover technical commit binding,
stale sources, skipped-index tampering, decision hashes and transactional rollback.
The installed harness `tests/acceptance/axiom_v2_dcr_operations.py` repeats the
operating flows and frozen redaction on Mac/Linux. These are synthetic DCR cases;
the real ha-CPsWMS source/evidence comparisons remain separate.

The typed archive quota override now permits 32 GiB, covering the combined
original per-archive and material limits that can exceed 16 GiB. Default quota
remains 2 GiB, the 8 GiB free-space reserve remains, and files are streamed.
A higher override is a limit, not an allocation or production capacity approval.


## General declared results and complete private indices

The finite `results` routes restore the original local CI-bundle/manual mapping
and all three index projections. `describe` computes a bundle digest;
`validate-bundle` copies and validates it without admitting a result.
`verify-bundle` and `manual` create private source-bound assessments; `intake` is
an explicit separate action. Completed report-only execution returns zero even
when a recorded result contains findings; invalid execution returns 2. No
publisher is activated and no accepted product `status/` file is overwritten.

Metadata is an explicit JSON object validated by
`schemas/axiom-v2-result-metadata.schema.json`: `schema_version: 1`,
`input_kind: bundle|manual`, domain, SCM repository descriptor, logical governance
repository identifier and the declared V1 parameters. Manual summaries are
separate explicit input files. Synthetic starting templates are
[bundle metadata](../../examples/axiom-v2-general-results/bundle-metadata.json) and
[manual metadata](../../examples/axiom-v2-general-results/manual-metadata.json). Required metadata prevents credential fields or
implicit provider identities from being interpreted as result data. Original
snapshot payloads retain their vocabulary; these are declared data and do not
prove scanner, pipeline, review or deployment execution.

```sh
"$V2_PREFIX/axiom-v2" results describe --bundle /private/operator/ci-bundle.zip
"$V2_PREFIX/axiom-v2" results validate-bundle --domain devsecops \
  --bundle /private/operator/ci-bundle.zip --sha256 EXACT_BUNDLE_SHA256
"$V2_PREFIX/axiom-v2" results verify-bundle \
  --bundle /private/operator/ci-bundle.zip --sha256 EXACT_BUNDLE_SHA256 \
  --metadata /private/operator/result-metadata.json --at 2026-11-15T12:00:00Z
"$V2_PREFIX/axiom-v2" results manual \
  --metadata /private/operator/manual-metadata.json \
  --summary /private/operator/control-summary.json --at 2026-11-15T12:00:00Z
"$V2_PREFIX/axiom-v2" results inspect --id ASSESSMENT_SHA256
"$V2_PREFIX/axiom-v2" results intake --id ASSESSMENT_SHA256
"$V2_PREFIX/axiom-v2" results records --domain devsecops \
  --origin operator_bundle --limit 100 --offset 0
"$V2_PREFIX/axiom-v2" results project --domain devsecops \
  --origin operator_bundle --scm DECLARED_SCM_PROVIDER --service https://scm.example \
  --event-profile legacy-v1 --main-branch main --at 2026-11-15T12:00:00Z
"$V2_PREFIX/axiom-v2" results inspect-project --id PROJECTION_SHA256
```

Directory digests bind exact relative file names and bytes; ZIP digests bind
original archive bytes. Copies reject links, special files, traversal, ambiguous
required names and case aliases. Original Windows ZIP separators are normalized
as in V1. Limits are 4,096 members, 256 MiB/member and 1 GiB material; raw ZIP is
bounded at 2 GiB. The combined input/material quota defaults to 2 GiB, explicitly
up to 32 GiB. Derived metadata/assessments are separately bounded. Writes preserve
an 8 GiB free-space reserve; quota overrides allocate no storage automatically.

The private ledger uses opaque provider/instance/native-ID namespaces, separate
operator/native histories and complete identity/replay rules. Retry retains the
first payload, verification time and assessment reference. Changed target
identity is quarantined; execution failure rolls back the whole transaction.
Display-name reuse by another native ID is visible rather than merged. Renaming
retains old descriptors. These technical records grant no governance authority.

Projection contains the original complete `reported_index` and an
`effective_index`; operator Trust stays unverified in the latter. Findings and
historical freshness/replay fields remain visible independently. Typed results
use the existing private typed ledger and its original byte-bound assessments.
Missing or foreign-node sources and re-sealed outcomes fail reconstruction.
`legacy-v1` preserves the original raw event classification; `portable-v1` uses
normalized manual events. Main-branch choice is explicit. A historical projection
pins membership and file hashes and remains unchanged when later records arrive.
Offline inspection never claims a new native metadata read.

The independent frozen V1 fixture covers four complete local bundle snapshots,
two manual snapshots, and fifteen synthetic source records with all three full
index outputs. Tests cover context selection, Trust/outcome separation, indexed
replay equivalence, identity conflict, rollback, archive/node tamper and private
source-backed views. A 2,000-small-repository fixture verifies local ledger
storage and paging only; it is not live collection or production capacity
acceptance. The installed harness is `tests/acceptance/axiom_v2_general_results.py`.

Full native general intake preserves additional original API/job/artifact and
physical-evidence facts; it is not replaced by the simpler local bundle mapper.
Those native counterparts and public proposal handoff remain required Goal work.

The separate disposable-host CI deployment protocol retained all twelve
transitions and expected failure checks but exhausted its 60-minute job budget
after ten expected outcomes. The job budget is now 90 minutes; no validation,
service isolation, rollback, schema-recovery or backup test is removed.

## Native general result reader increment

`results capture-native` supplies the previously separate native general-intake
path. It requires an explicit provider, exact repository/run/attempt, artifact
name, governance-repository label and private reader file. No ambient login,
command-line token or inherited environment token is used. The initial adapter
supports GitHub Actions; other live target profiles remain open.

```sh
"$V2_PREFIX/axiom-v2" results capture-native --provider github-actions \
  --repository owner/application --run-id 12345 --attempt 1 --domain devsecops \
  --artifact-name devsecops-pipeline-evidence \
  --governance-repository owner/governance --baseline-ref l1-baseline-v1.1.3 \
  --credential-file /private/operator/result-reader.json
"$V2_PREFIX/axiom-v2" results inspect-native --id CAPTURE_ASSESSMENT_ID
"$V2_PREFIX/axiom-v2" results intake-native --id CAPTURE_ASSESSMENT_ID
```

The reader JSON has exactly `schema_version: 1`, `provider: github-actions`,
`instance: https://api.github.com`, `repository: owner/application` and a `token`.
Store it privately with mode `0600`. Only the explicit repository API receives
its credential. Allowlisted HTTPS artifact-storage redirects receive none; no
credentials, signed download locations or ambient tokens enter retained captures.
Use a repository-scoped read token; this route requests no writes or authority.

The adapter preserves the full native V1 snapshots, rather than substituting the
local declared-bundle mapping. It reads the completed run and attempt-specific
jobs, lists artifacts, downloads exact primary ZIP bytes and, when required, the
separate governance-input ZIP. Physical SBOM/scan presence, application digest,
gate-vs-job status, evidence context, baseline observations, archive/report/input
hashes and nullable protection lookup remain in the original wire report.
Architecture report/release-input subjects have their own original mapping.
Failed runs/findings remain visible; they are not filtered out to improve status.

Run, jobs and artifact metadata are rechecked after acquisition. Foreign
repository/native-ID/commit/attempt bindings, changed metadata, duplicate native
IDs, ambiguous required members, unsafe paths, malformed JSON and archive/digest
changes fail closed. Native verification uses system UTC, not an operator-chosen
freshness time. Original ZIPs and credential-free API observations stay under
`state/results-native/`; subsequent inspect/projection is exact offline replay,
not a new native metadata lookup. It retains the original verification time.

The request limit defaults to 100 (maximum 2,000); pagination is bounded to 25
pages per listing. Each original ZIP is limited to 1 GiB, extracted material to
1 GiB and each member to 256 MiB/4,096 members. Metadata is bounded to 16 MiB.
Combined raw/metadata/material defaults to 2 GiB and accepts an explicit override
up to 32 GiB. The 8 GiB free-space reserve remains in effect. Quotas bound actual
bytes; setting a quota does not allocate that space.

Capture creates a private source/node/runtime-bound assessment. Separate explicit
intake writes the existing native-origin ledger; operator bundles remain in their
own origin and cannot claim native provenance. All three source-backed index
routes can consume their corresponding native records. Inner Trust keeps the
original verified wire semantics, while the outer candidate grants no source,
risk, compliance, deployment or personal operating approval. Public accepted
status and proposal handoff are still separate, unfinished Goal work.

Five synthetic fixtures were generated by executing the actual frozen V1 CLI
orchestration against fixed API/download bytes, including a separate companion
input. Complete snapshots and Trust match V2. These are technical regression
cases; fresh native live acceptance and installed evidence are recorded separately
when actually observed. No new scanner/application run follows from capturing
an existing run.

## Committed-data reporting increment

The finite `reports` route returns the original control-coverage JSON/Markdown,
control traceability CSV, architecture runtime traceability CSV, Policy/Directive
traceability CSV and governance graph JSON. Source lineage and change impact each
add their original JSON/Markdown pair. Five source-intake report families add
ten more files; four model report families add six files. `--kind all` produces
all twenty-six files.
The computations use explicit data roots; V2 imports or dispatches no retained
source CLI and writes no generated files in its installed source.

```sh
"$V2_PREFIX/axiom-v2" reports build --kind all --at 2026-11-15T12:00:00Z
"$V2_PREFIX/axiom-v2" reports inspect --id REPORT_ASSESSMENT_ID
```

The build receipt supplies a private artifact directory and each file's size and
SHA-256. The source profile `committed-governance-data-v2` records complete committed Git
file membership and snapshots only exact required data blobs: `model/`,
`architecture/`, retained `governance/` data, `status/`, the historical lineage
report, the frozen architecture release metadata/model YAML, registered source
extracts and requirement source documents. The process-status profile also reads
its original committed intake-status and requirement-delta JSON inputs. Membership
retains mode, object and size without copying retired executable source. Ordinary
working-file edits are excluded. All
copied files bind their Git object, size and SHA-256 to the exact product commit
and tree. Schema/resource/runtime/node/time bindings surround the derived output.
Git reads use local objects and disable lazy fetching and all transport protocols;
a missing promised blob fails locally without invoking repository remote helpers.
CSV column order and CRLF bytes match V1; graph timestamps retain their original
derivation from input documents. The outer assessment time records the diagnostic
operation rather than making historical evidence fresh.

Inspect verifies the committed Git inventory, original copied bytes, report
metadata and all output bytes, then repeats the full computation. Resealed source
hashes still have to match actual committed Git blobs; resealed report metadata
still has to match the original computation. Missing or extra files, links,
traversal, foreign nodes, altered authority flags, unsupported report kinds and
quota failures are rejected. Repeated builds at the same explicit time are
idempotent. Source snapshots are cached privately per exact revision.

The bounded profile admits up to 10,000 committed members and copied data files,
128 MiB total/16 MiB per copied file; its manifest is limited to 4 MiB. Output is
bounded to sixty-four files, 64 MiB per file
and 128 MiB total. The existing 8 GiB free-space reserve is preserved.

These are read-only projections of committed governed data and historical
results. Candidate authoring workspaces and live private collection state retain
their separate contexts. Reports confer no compliance, source approval, risk
acceptance or personal operating authority. Public report/Viewer publication,
remaining report families and complete authoring/operating parity remain part of
the ongoing Goal.

The independently executed frozen V1 writers/computation produced all six expected
files from 285 exact committed governance input files. Tests compare complete
output bytes, including CSV endings, and exercise corruption, foreign scope,
source-membership and quota failures. Installed evidence is recorded separately
for the exact committed package once its execution has actually been observed.


### Source lineage and change impact

`--kind source-lineage` and `--kind change-impact` preserve the original register,
source status, artifact roles, review lanes, release considerations, suggested
validations and Markdown rendering. Their clock is explicit UTC, truncated to
seconds as in V1. Change impact calls the pure lineage computation directly; it
does not dispatch a source CLI or trust an old generated lineage payload.

File presence and policy enumeration use the full committed tree, including
paths absent from the installed sparse working tree. The private input copy
contains only admitted data. Historical derivation labels remain historical:
a retired path is reported absent even when a new application route supplies
its functional counterpart. This report does not approve or rewrite lineage.
Candidate source status remains intact and no controls are derived or activated.

Original frozen V1 functions and renderers were executed at the same UTC against
two exact memberships: the frozen V1 tree and the later V2 reporting tree. Their
lineage dependency invokes the original lineage writer directly in the private
oracle directory. All four output files match without normalized fields. The
existing six report files remain byte-identical. The expanded installed harness
checks thirty-three complete files, immutable replay and tamper rejection; installed
acceptance is recorded only after the new committed package actually runs.

This source-profile change requires a fresh candidate instance; existing private
report snapshots are not silently migrated or reinterpreted. General update and
workspace migration remain separate full-Goal work.


### Existing source-intake report families

The same finite report application now exposes `source-replacement`,
`source-intake`, `source-review-briefs`, `requirement-delta` and `source-process`.
Each produces its original JSON/Markdown pair. Their pure functions retain the
existing replacement/advisory classification, source status, review options,
explicit requirement identifiers, provenance and lifecycle/baseline blockers.
They make no source, architecture, requirement or release decisions.

The first four families recompute their original dependencies directly from
committed data, without executing a source generator or trusting stale generated
outputs. Process status preserves its distinct original input contract: it joins
the committed intake-status/delta reports, source register, lifecycle cases,
authority ledger, DCR projection and requirement/artifact links. It does not
silently substitute newly generated or candidate-workspace records. A later
composed current-state/private-workspace view requires its own explicit scope.

Registered source/requirement document bytes are copied with the existing Git
object/SHA-256 and resource bindings. Format extraction follows the original
Markdown/DOCX/PDF parser, with original warnings/error semantics, after member,
link and raw-file size checks. Candidate intake records whose text is withheld
remain unscanned; unlabelled prose and reference mentions create no requirements.
Identifier presence remains separate from author-provided identifier provenance
and source approval. Historical lifecycle proposals remain historical counts.

The process report retains the original UTF-8 JSON writer; the other report
writers keep their original JSON escaping. Complete byte comparisons use the
actual frozen V1 functions/renderers in two exact committed input contexts.
Original dependency writers execute only in the private V1 oracle; V2 uses
direct pure function calls. The corresponding installed acceptance compares all
thirty-three files, and records only actually observed host execution. Existing generic
Workbench imports remain unchanged until their candidate/workspace context has
its own migration and interface tests.


### Model follow-up reports and explicit data-layout repair

`automation`, `document-controls`, `open-gaps` and `pipeline-baseline` return six
original Markdown/CSV files. The admitted data adds only the existing pipeline
control-placement YAML and waiver schema JSON. CSV column order and CRLF bytes
remain unchanged; explicit original headers also allow legitimate zero-row gap
or mapping reports, which previously failed while reading `rows[0]`. An empty
automation population remains an execution failure, not a coverage result.

The old automation writer is broken against the frozen repository's data layout:
its `controls/` path is absent, and moving the current model files there alone
still lacks classification fields on 41 controls. The current pipeline baseline
already declares a unique placement for each of the same 46 control IDs. The V2
read-only view uses `model/controls/`, retains provided control classifications,
and copies only absent `automation.type`, `maturity` and `check_type` fields from
that same control's explicit `gate_type`, `maturity` and `check_type` placement.
If that lookup is needed, its existing verification text can fill the absent
optional verification text. Complete legacy inputs do not acquire an unnecessary
placement dependency. Missing, ambiguous or differently levelled placements fail
instead of inferring a classification. Models, source status and OPA are unchanged.

These values describe declared automation and pipeline placement, not newly
implemented controls, measured coverage or enabled blocking. The portable gate
still evaluates five controls; the separate full assessment retains all 46 V1
records. Rendering a declared blocking-gate classification activates no gate.

The independent V1 oracle records both original failures separately. It runs the
original writer on its declared legacy layout using exact approved model bytes
and an openly recorded, per-control field projection from the existing placement
records. All six valid output files match original bytes in two contexts; this
does not claim that an unadapted failed V1 run produced successful output. Tests
also cover direct-value priority, absent/ambiguous inputs, unchanged source bytes,
zero-row CSV repair and complete legacy input compatibility. No old CLI executes
in the product.


## Original domain files and separate release-readiness gate

`evaluate --domain devsecops-release` evaluates the existing
`data.devsecops.release_readiness.deny` query with the pinned product OPA. It is a
separate legacy gate and wire format; it does not replace the 46-row `controls`
report or add new control or enforcement semantics. `collect-source --domain
controls` already preserves its original V1 source input, including declared
approval defaults and CI-layout observations supplied through the explicit port.
Those declarations are not independently verified evidence.

```sh
"$V2_PREFIX/axiom-v2" evaluate --domain devsecops-release \
  --input /private/operator/release-input.json --at 2026-11-15T12:00:00Z
"$V2_PREFIX/axiom-v2" reports domain --id RELEASE_ASSESSMENT_ID \
  --at 2026-11-15T12:00:00Z
"$V2_PREFIX/axiom-v2" reports combine \
  --architecture-id ARCHITECTURE_ASSESSMENT_ID --devsecops-id RELEASE_ASSESSMENT_ID \
  --at 2026-11-15T12:00:00Z
"$V2_PREFIX/axiom-v2" reports inspect-domain --id DOMAIN_REPORT_ID
```

`reports domain` accepts architecture, the 46-row controls report, or the separate
DevSecOps release gate. It writes their original JSON and Markdown files under
private `state/domain-reports`. `reports combine` accepts exactly one architecture
and one release-gate assessment. IDs, runtime, product revision, approved OPA,
complete execution and exact explicit assessment time are checked before
rendering. Repository path, displayed commit and release ID must all be explicit
and equal. Architecture may retain its additional service-count field. These are
**matching declared labels**, not independent proof of the consumer revision.
Missing gates or empty objects cannot fall through to the original empty-input
PASS. Other malformed or mismatched inputs fail with exit 2.

The full diagnostic assessment now retains `report_json` alongside its parsed
object. Private atomic envelope storage sorts object keys; retaining the original
wire string preserves nested input key order and exact V1 JSON bytes through
persistence. Parsed report, wire string, gate status and complete finding counts
are checked for consistency. Full assessment records are bounded to 16 MiB.
The changed runtime/schema require a fresh instance; no previous records are
silently migrated. An inspection rechecks the immutable input records and
rebuilds all output bytes. It explicitly does **not** claim to reverify original
operator input files or perform a fresh native metadata lookup.

JSON/Markdown reference labels retain original defaults and can be set with
`--architecture-md-ref` and `--devsecops-md-ref`; these strings are never opened,
fetched or executed. The legacy combined Markdown interpretation remains byte
compatible. Its historical evidence-acceptance wording does not grant authority:
the outer record remains operator supplied, unverified, report-only, private and
without official, production, risk or operating acceptance.

Evaluation defaults to exit 0 after complete execution, including findings. An
explicit local `--fail-on-findings` returns 1 when findings exist; incomplete or
invalid execution returns 2. This restores an operator exit-code option without
enabling any consuming workflow or changing approved blocking scope. Existing
controls and architecture evaluations can use the same explicit option.

The frozen original V1 CLI produced twelve complete domain/combined file wires
for two synthetic input pairs, including its original opt-in finding exit codes.
The installed acceptance harness is `tests/acceptance/axiom_v2_domain_reports.py`.
Arbitrary legacy report-pair import, public publication and remaining report and
operating flows retain open acceptance in the full matrix. No entrypoint or flow
is excluded from the Goal.


## Candidate maturity and historical intake/replay views

Three additional finite report kinds use the exact committed data profile:

```sh
"$V2_PREFIX/axiom-v2" reports build --kind candidate-maturity --at 2026-11-15T12:00:00Z
"$V2_PREFIX/axiom-v2" reports build --kind intake-health --at 2026-11-15T12:00:00Z --window-days 7
"$V2_PREFIX/axiom-v2" reports build --kind replay-triage --at 2026-11-15T12:00:00Z
```

`candidate-maturity` preserves the existing harmonized model and explicit candidate
maturity assignments. It creates the original JSON/Markdown decision support,
still candidate, non-normative, without enforcement and requiring human review.
It derives no new requirement or control and changes no normative source or model.

`intake-health` restores the original event metrics, latest-result ages and
collection-attempt lifecycle. The explicit window defaults to 30 days; any positive
integer is accepted if the selected timestamp supports the subtraction. Time
underflow or overflow is an invalid execution, not an empty success. The window
is inclusive and excludes future events. Attempts and resolving snapshots retain
their original complete-history scope independently of the event window. Empty
events remain `no_data`, with original zero rates and null duration percentiles;
latest-result ages retain the original nonnegative clamp. These are historical
committed records, not current queue or liveness observations of the installed V2
node. The current private queue retains its separate collector/status profile.

`--window-days` is meaningful for `intake-health` and `all`. A nondefault window
with another kind is rejected. The window is stored in the immutable report
assessment, affects its identity and is used again during inspection. The `all`
selection applies it only to health; all other output bytes remain unchanged.
The required schema field and changed runtime require a fresh candidate instance.
The logical `status/intake-health.json` output lives beneath the private artifact
directory returned by the command; the accepted repository status file is untouched.

`replay-triage` restores the original historical replay classification, related
artifact comparisons and recorded-versus-recalculated distinctions. References
to `official_latest` describe the committed input index. This view neither selects
new accepted latest results nor changes Trust, snapshots or enforcement. Empty
history retains its explicit zero count and original epoch timestamp. The original
malformed JSON/unreadable-history skip is preserved; strict duplicate/nonfinite,
link and input-budget errors are rejected rather than silently hidden.

All histories are selected from bounded committed membership and read through the
same strict data port. No application checkout code, legacy report CLI or native
API is executed. The existing pure collection-attempt lifecycle helper is selected
and fingerprinted explicitly. All 33 committed-data output files fit the current
64-file cap described below; per-file, aggregate, manifest and free-space limits remain unchanged.
Original V1 writers produced five complete output files in each of two exact
source/membership contexts; no output bytes were normalized. The oracle relocated
only its health output destination to preserve the input snapshot.

The tests also cover empty history, inclusive/future-event windows, attempt
resolution, malformed versus duplicate JSON, time/overflow failures and resealed
window parameters. Candidate decisions, attestation actions, current private
health, public reporting and the remaining full Goal continue to require their
own implementation and acceptance. No catalogue area or entrypoint is excluded.


## Informational portfolio projection

```sh
"$V2_PREFIX/axiom-v2" reports build --kind portfolio --at 2026-11-15T12:00:00Z
```

This kind restores the original registry-based onboarding JSON and Markdown from
committed consumer integrations, accepted-domain indexes and the optional committed
previous portfolio projection. It reads one additional inert source file,
`generated/reports/portfolio-onboarding-status.json`, which is already distributed
as data. The admitted report data scope now has 366 files in the comparison
contexts. Output lives under the private artifact directory; the previous source
file and actual accepted status remain unchanged.

The original timestamp rule is retained: if summary and repository rows are
unchanged, keep the previous `generated_at`; otherwise use the explicit assessment
time. Freshness retains its original 30-day threshold and missing/future declaration
semantics. Registry `active`/`pilot` labels describe the committed source record,
not activation or acceptance of the installed node. The report is informational
and approves no waiver, baseline, enforcement mode or consumer integration.

Adding the two portfolio files brings the finite `all` profile to 33 unique files.
Its count cap is deliberately increased from 32 to **64** in both the application
and schema; 65 small files are rejected. The **64 MiB per-file**, **128 MiB aggregate**,
**4 MiB record**, source/manifest bounds and **8 GiB free-space reserve** remain.
Greater file count does not bypass aggregate-byte checks. This change supports the
full report scope without removing previous families or accepting an unbounded list.
Domain/combined reports remain their separate finite profile. Changed source and
runtime fingerprints require a fresh instance, with no silent history or authority
migration.

Actual original V1 writers at an explicit frozen UTC consumed their original
previous projection in two exact input/member contexts. Both complete output files
match without normalization. The private oracle restored its previous input after
capturing output and checked every source checksum. Tests cover timestamp retention,
changed rows/staleness, threshold/missing/future declarations, empty registry,
private artifact separation and finite/aggregate capacity. Multi-consumer configuration
readiness, provider-native configuration facts and remaining reporting/operating
capabilities retain their open scope; no full Goal acceptance is claimed.
