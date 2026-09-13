# CLG-04 Governance Lifecycle Pilot Runbook

13 September 2026. This runbook demonstrates the **synthetic, report-only**
closure/reopening runtime. It does not activate live intake or supply human
operational acceptance. Contracts and limits are documented in the
[closure guide](../operations/evidence/governance-lifecycle-closure.md).

## Reproduce the full synthetic sequence

Use a fresh output directory. Existing accepted history is never reset:

```bash
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/run_governance_lifecycle_closure_demo.py \
  --ledger /tmp/clg04-demo/ledger \
  --output /tmp/clg04-demo/index.json --report /tmp/clg04-demo/report.md
.venv-validation/bin/python scripts/generate_governance_lifecycle_pilot.py \
  --ledger /tmp/clg04-demo/ledger --as-of 2026-09-13T14:20:00Z \
  --output /tmp/clg04-demo/rebuilt.json --report /tmp/clg04-demo/rebuilt.md
cmp /tmp/clg04-demo/index.json /tmp/clg04-demo/rebuilt.json
cmp /tmp/clg04-demo/report.md /tmp/clg04-demo/rebuilt.md
```

| Synthetic UTC time | Input | Result |
|---|---|---|
| 13:00 | GRS-002 FAIL | One open finding, revision 1 |
| 13:10 | Bound test remediation approval | Active decision, revision 2 |
| 13:20–13:40 | Planned → in progress → completed work | Revision 5; finding remains open |
| 13:50 | New accepted criterion PASS | Revision 6; finding still open |
| 14:00 | Bound test closure approval | Closed, revision 7; complete evidence chain |
| 14:10 | Delayed FAIL observed at 13:05 | Closed, revision 8; occurrence retained |
| 14:20 | New FAIL observed at 14:20 | Same finding reopened, revision 9; historical closure retained |
| Retry | Original closure packet | No transaction and no reclosure |

The final index contains nine transactions, four accepted observations, nine
events, one decision, three remediation revisions, one closure, no conflicts
and one reopened finding with three occurrences. To inspect the closed state,
regenerate a separate historical projection with `--as-of 2026-09-13T14:10:00Z`.
The current checked-in index must cover the entire stored history.

`intake_governance_lifecycle_action.py --synthetic` also accepts a supplied
closure 0.2.0 packet with `--record`, `--resources`, `--ledger` and
`--expected-revision`. Its resource directory contains only the referenced
fixture consent file. Accepted observation/work resources are resolved from
history, not resubmitted by the closure proposer.

## Negative cases and reproducibility

Run the pinned repository validation:

```bash
./scripts/validate_all.sh
.venv-validation/bin/python scripts/validate_governance_lifecycle_ledger.py \
  --base-ref <full-accepted-base-commit-sha>
.venv-docs/bin/mkdocs build --strict
```

Tests demonstrate missing/wrong consent, wrong role, changed content, stale
revision/time, expired evidence, revoked remediation approval, nonlatest work,
newer FAIL, conflicting/incompatible evidence, unsupported live/rejected/revoked
closure packets, two closure cycles and deterministic historical replay. They
also race closure against a new failure in two real processes and merge two
competing Git proposals to verify semantic rejection.

Publisher tests exercise the narrow synthetic scope against a local remote,
including stale/forged projections, accepted-history changes and out-of-scope
profile or consumer changes. They verify that only a review branch is pushed
and no approval/merge endpoint is called.

## Separately recorded live observation

The [dated live observation](../operations/reference-runs/2026-09-13-clg04-live-observation.md)
records the actual repository's GRS-002 result after the authorized #78 merge
exception was restored. GRS-002 is PASS with one required approving review.
This is a read-only observation outside the synthetic ledger. It does not
establish a live finding or attest a human decision. The full self-security
report has additional findings; criterion PASS is not overall repository PASS.

No real branch protection was disabled to manufacture a pilot failure. The
existing ha-CPsWMS demo, released baselines, consumer enforcement and official
viewer remain governed by their existing runbooks.

## Accountable acceptance still required

The technical pilot can be reviewed now. Before any live acceptance, responsible
humans must record LD-01–05 and LD-07 in the
[pilot decision sheet](../operations/evidence/governance-lifecycle-pilot-decisions.md):
actual role assignments, authenticated deliberate consent, registry control,
accepted producers and Trust checks, freshness/replay limits, and operational
acceptance including correction/withdrawal handling. This document does not fill
those slots or infer authority from a GitHub account or PR merge.

After the technical PR is merged, record the accountable acceptance and explicit
release decision before marking the full CLG-04 milestone complete. CLG-05 then
adds scoped, expiring exceptions under the existing waiver authority contracts.
