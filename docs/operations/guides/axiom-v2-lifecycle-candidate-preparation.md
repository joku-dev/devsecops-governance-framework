# Diagnostic lifecycle candidate preparation

`axiom-v2 lifecycle-candidates generate/inspect/replay` exposes both complete
original preparation programs through profile
`legacy-lifecycle-candidate-preparation-v1`. The development candidate retains
all seven original functions and all161 source lines from the two CLIs, shared
writer, complete candidate normalization and both report adapters. Full pinned
validation, declared revision-bound review and matching signed installed
Mac/Linux comparisons remain required before delivery. The full V2 Goal is open.
The complete original reference modules, schemas and example bytes are frozen as
checked fixtures. Source and installed tests need no historical Git objects and
never load their oracle code into the product process.

## Inputs and original decisions

| Program | Original entrypoint | Preserved granularity |
| --- | --- | --- |
| `devsecops` | `prepare_lifecycle_devsecops_candidates.py` | Explicit control rows |
| `architecture` | `prepare_lifecycle_architecture_candidates.py` | Exactly four supported gates |

The original schema, raw report digest, producer/context, observation-time,
summary and duplicate guards are preserved. Demo control reports require a
synthetic declaration. Architecture report messages remain gate messages;
marker names or remediation text do not create extra outcomes. Whole original
candidate IDs, counts, context classifications, age and source messages are
retained. Declared repository/run/baseline/policy context does not authenticate
its producer or earn accepted trust. Outputs remain diagnostic, `report_only`,
`unverified`, `not_evaluated` and `official_state: false`, with all original
acceptance gaps. Nothing is inserted into an accepted lifecycle ledger or index.

## Private preparation

```bash
/path/to/axiom-v2 lifecycle-candidates generate \
  --profile legacy-lifecycle-candidate-preparation-v1 --program devsecops \
  --source-worktree /path/to/data-checkout \
  -- --report /path/to/control-report.json \
     --context /path/to/context.json \
     --output /path/to/data-checkout/generated/reports/lifecycle-candidates/candidate.json \
     --evaluated-at 2026-09-13T12:01:00Z
```

Without `--write-selected-files`, the original program runs over a finite private
candidate filesystem, leaving selected data unchanged. Its mask077 describes a
model, not native persistence or concurrency. The receipt identifies a separate
record under `INSTANCE/state/lifecycle-candidates/records/RECORD_ID`, retaining
source preimages, ordered operations and whole candidate bytes. An earlier
private output does not silently become a later invocation's selected input.

`--source-worktree` selects data and schemas, never product code or authority.
`--working-directory` controls relative original arguments. Arguments after `--`
reach the complete original parser, retaining abbreviations, repetitions, help,
required fields and original exits. The request retains the explicit complete
producer CPython parser profile, version, width and English translations; see
the shared [parser contract](axiom-v2-synthetic-ledger.md#producer-parser-context-and-portability).
Help/parser exits require no selected data reads, schema loading or output writes.
Unsupported native profiles fail before record creation; replay has no consumer
terminal/gettext fallback or stdout normalization.

## Explicit native outputs and failures

Add `--write-selected-files` before `--` to request the original directory and
file operations. Original input-overwrite guards and dedicated diagnostic output
paths inside the selected root remain intact. Outside-root paths retain the
original ordinary selected-output semantics, subject to technical admission.
Installed product/private-state exports and overlapping source/instance roots
are rejected. Owned stable ordinary files, bounded input/output/record sizes and
non-group/world-writable input files are additional technical boundaries; no unsupported path or
capture failure is reported as an original success or accepted finding.
Symbolic or multiply linked paths require separate admission; they are not
silently resolved into an original execution.

Native effects are not rolled back or retried. Original read/write errors and
partial outputs can be captured as complete original exit1 outcomes. In selected
mode, `source_effects_may_be_partial` is true for these failed original executions
as well as for incomplete captures; a successful complete native exit0 reports false. Failed
observation or terminal storage instead yields incomplete capture, exit2 and
`original_exit_code: null`; native effects may already have occurred. A complete
receipt with `--format legacy` emits the original stdout/stderr; exceptions also
have structured type/message diagnostics rather than an identical Python stack.

Local lifecycle schema resources form a closed registry. Repeat
`--schema-resource URI FILE` before `--` to retain explicitly supplied external
resources. Unselected references yield incomplete capture; no implicit HTTP or
file-URI retrieval occurs. Schema sources are selected data, not executable code.

## Inspection and portable replay

```bash
/path/to/axiom-v2 lifecycle-candidates inspect --record /private/record/path
/path/to/axiom-v2 lifecycle-candidates replay --record /private/record/path
```

Inspection verifies the own node and product generation. Portable replay verifies
the complete current product generation while retaining the producer's node
identity; it never adopts that identity. It is also available without an instance
through `python3 scripts/axiom_v2.py lifecycle-candidates replay --record PATH`.
Replay reconstructs the complete original execution, streams/errors, successful
writes, touched paths and private/native effects from closed retained bytes.
It repeats no selected reads, effects, external programs or provider calls.
Requests, product/node context, authority flags, event order, raw blob closure and
the whole reconstructed result are checked, including after a chain is resealed.

Consistency is declared technical evidence. It does not authenticate a producer,
approve requirements, accept findings, activate services or inherit personal
consent, live waivers or operating acceptance. The separate
[candidate-index command](axiom-v2-candidate-index.md) has a different input
contract; diagnostic lifecycle candidates are not silently converted into that
index or an accepted result.
