# Diagnostic pilot projections in V2

`pilot-projections generate/inspect/replay` exposes the complete original
`generate_lifecycle_pilot_actions.py` and `generate_lifecycle_pilot_validation.py`
programs. Their five named functions and complete action-script main guard use
explicit lifecycle context and IO. The existing retained report methods and
historical receipt/action checks remain unchanged.

## Scope and explicit captured-evidence profile

```bash
/path/to/axiom-v2 pilot-projections generate \
  --profile legacy-pilot-projection-v1 \
  --capture-profile legacy-lifecycle-capture-v1 \
  --program actions --source-worktree /private/operator/source-data
```

Select `validation` for the durable receipt projection. The capture profile is
required; its adapter retains the original GitHub identity, URL, archive and
personal-comment field checks over supplied bytes. It performs no provider
fetch, authenticates no producer and verifies no current personal statement.
The product core does not select a provider implicitly.

The original programs have no argument parser: any original arguments after
`--` are retained and ignored, including `--help`. The selected data is still
read and the whole original program runs. There is no producer parser context
or consumer terminal/gettext dependency for these two original programs.
The outer V2 command has its own explicit options.

## Original outputs, private candidates and selected files

The actions program writes `status/governance-lifecycle-pilot-actions.json`
then `generated/reports/governance-lifecycle-pilot-actions.md`. The validation
program writes `status/governance-lifecycle-live-validation.json` then
`generated/reports/governance-lifecycle-live-validation.md`. Both retain the
original print output, default text encoding, write order and errors. Parent
directories are not invented. A missing report directory can leave the first
index write complete before the original error.

The default produces a private candidate retaining all output bytes and modes;
selected source files remain unchanged. Add `--write-selected-files` to request
actual original file operations on the selected ordinary owned files. There is
no automatic rollback or retry. A complete original exit1 can retain partial
native effects, indicated by `source_effects_may_be_partial: true`. Capture or
terminal-storage failure instead yields incomplete state and no original
verdict. `--format legacy` emits original streams; captured exceptions additionally
use structured type/message diagnostics, not an identical Python traceback.
Stable ordinary files, bounded metadata/blobs/journals, owned paths and closed
schema resources are technical admission conditions. Unsupported observations
are not represented as original successes or accepted findings.

## Own inspection and portable closed replay

```bash
/path/to/axiom-v2 pilot-projections inspect --record /private/record
/path/to/axiom-v2 pilot-projections replay --record /private/record
```

Inspection checks the own node and current product generation. Portable replay
retains producer context without adopting its identity and works without an
instance. All historical receipt bytes, schemas, captured provider fields and
personal statements are replayed from the closed record. It does not read the
selected source, execute an original program, call a provider or repeat writes.
Requests, whole results, strict false authority flags, source/node bindings,
event order and complete blob membership are checked, even after resealing.

The immutable V1 reference fixture has two receipts and no actions; its action
projection is `no_finding`. It is not silently replaced by later historical
closed states. The 73 exact original program/dependency/data fixture files are
hash and Git-blob checked and require no historical Git objects in an installed
runtime. This development has focused source comparisons; full current source,
three pinned runtimes, revision-bound review and signed installed/peer/consumer
proofs remain separate delivery conditions.

No generated index accepts a live finding, transfers consent or operating
acceptance, activates roles/services, publishes official consumer state or
changes immutable ledgers. All 22 areas, 135 entrypoints, 37 CI definitions and
16 operating flows remain in the full Goal. This counterpart is in progress.
