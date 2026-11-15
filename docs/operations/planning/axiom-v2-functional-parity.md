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
