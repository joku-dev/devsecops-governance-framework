# Synthetic lifecycle reporting candidate

`axiom-v2 synthetic-lifecycle generate/inspect/replay` exposes the complete five
original synthetic lifecycle generators. The retained profile is
`legacy-synthetic-lifecycle-reporting-v1`. The original 367 source lines and all
19 functions remain represented: index, closure pilot, exceptions, overview,
viewer, report rendering and direct overview/viewer validation.

This is an engineering candidate in the V2 parity stack. The complete Goal still
covers 22 areas, 135 entrypoints, 37 CI definitions and 16 operating workflows.
The five mappings remain `in_progress`; the full signed source, installation,
consumer comparison and review requirements below still apply to this increment.

## Explicit schema resources

Locally registered lifecycle schemas resolve from the retained selected data.
Additional references require an explicit `--schema-resource URI FILE` before
`--`. This selects local bytes for that URI, including HTTP or file URI labels;
it never authorizes fetching the URI. Up to 128 distinct resources are admitted.
Their ordinary owned files are read lazily through the same bounded capture
ports, and URI/path selections are bound into the closed request. Replay uses
those retained bytes even after the selected files disappear. Neither capture
nor replay uses implicit HTTP or file URI resolution.

For example, add `--schema-resource https://example.invalid/schema.json
/path/to/selected-schema.json` to the V2 options before the original arguments.
An unresolved reference without a selected resource makes capture incomplete
with no original verdict. Resource bytes and a successful validation are
technical observations, without producer authentication or approval authority.

## Choose the original generator

| `--generator` | Original entrypoint | Original options after `--` |
| --- | --- | --- |
| `index` | `generate_governance_lifecycle_index.py` | required `--as-of`; optional `--ledger`, `--output` |
| `pilot` | `generate_governance_lifecycle_pilot.py` | required `--as-of`; optional `--ledger`, `--output`, `--report` |
| `exceptions` | `generate_governance_lifecycle_exceptions.py` | required `--as-of`; optional `--ledger`, `--output`, `--report` |
| `overview` | `generate_governance_lifecycle_overview.py` | required `--as-of`; optional `--output`, `--report` |
| `viewer` | `generate_governance_lifecycle_viewer.py` | optional `--output`; reads the already verified overview |

The selected data directory supplies the original models, schemas, synthetic
ledgers, overview inputs and viewer template. No program from that directory is
loaded. `--working-directory` explicitly selects the interpretation of relative
original arguments; its default is `--source-worktree`. Original root defaults
refer to that selected data directory. The V2 instance is separate from it;
lexically overlapping instance/source directories are rejected before a journal
is created. Aliased source paths are additionally checked when data are read.

```bash
/path/to/axiom-v2 synthetic-lifecycle generate \
  --profile legacy-synthetic-lifecycle-reporting-v1 \
  --generator overview --source-worktree /path/to/governance-data \
  -- --as-of 2026-11-15T12:00:00Z
```

The example evaluation instant is explicit. It does not select current time or
certify that a later dataset has been evaluated. Missing ledgers retain the
original empty-projection behavior. Complete transaction history is checked
before the evaluation cutoff is applied. Current overview/viewer validation also
rejects a projection that hides later accepted history.

Original immutable-ledger, model, distinct-output and official-viewer guards are
preserved for the generators that declare them. In particular, viewer output
cannot overwrite its inputs or `generated/viewer/status-viewer.html`.

## Private candidates and actual files

The default is `private-candidate`. Source preimages, raw observations, candidate
bytes and the original result are stored in a fresh private record under
`INSTANCE/state/synthetic-lifecycle/records/RECORD_ID`. The receipt prints its
`record_root`. Source files and directories are unchanged by the projection.

The logical candidate supports creating directories, overwriting files,
reading the resulting bytes, querying their existence and listing the combined
source/candidate directory view. Direct `generate`, `validate_overview` and
`validate_viewer` calls use the same view, so a changed candidate report or viewer
fails the original validation. The original implicit text-read codec is retained
and supplied explicitly during replay.

`private_projected_changes` describes this logical view. New candidate objects
use an explicit private creation mask `077` and a separate identity namespace.
Existing modes and preimages remain visible. This is a declared candidate model;
it does not predict future filesystem ACLs, disk failures or a native host umask.
`source_output_paths_observed` stays empty in private mode. Candidate bytes are
addressed by their hashes in the private record, rather than copied into the
selected output paths.

To execute the original selected output paths, create a new run with
`--write-selected-reports`:

```bash
/path/to/axiom-v2 synthetic-lifecycle generate \
  --profile legacy-synthetic-lifecycle-reporting-v1 \
  --generator pilot --source-worktree /path/to/governance-data \
  --write-selected-reports \
  -- --as-of 2026-11-15T12:00:00Z \
     --output /path/to/exports/pilot.json --report /path/to/exports/pilot.md
```

This executes a new source evaluation. Ordinary owned files and held export
directories are admitted; raw preimages, file identity/mode, truncation and
partial byte progress are retained. The installed product and private instance
state cannot be selected native exports. Original relative, nested and
outside-data-directory targets remain supported within these explicit admission
boundaries. Original partial results remain visible, including a completed first
index when the second export is a directory, and a text encoding failure after
the target file has been truncated.

## Inspect and reconstruct

```bash
/path/to/axiom-v2 synthetic-lifecycle inspect --record /private/record/path
/path/to/axiom-v2 synthetic-lifecycle replay --record /private/record/path
```

Inspection binds the record to the calling instance. Portable `replay` also works
without an instance through `python3 scripts/axiom_v2.py synthetic-lifecycle
replay --record ...`; it still requires exactly compatible registered product
bytes and the captured product generation. It reconstructs the whole generator
from retained raw bytes and ordered observations. Selected sources may have been
removed. No selected source read, native program or selected export is repeated.

Request, original generator, code fingerprints, node context, complete result,
source effects, logical candidate changes, event chain and the closed blob set
are checked together. Foreign-instance inspection, changed code, authority
claims, missing metadata, unused blobs and coherent protocol tampering fail.
Consistency is declared evidence: it does not authenticate the producer or an
independent reviewer.

## Exit and interruption semantics

An original success, help exit `0`, parser exit `2` or captured original exception
exit `1` is a `complete` program outcome. `--format legacy` emits original stdout
and stderr; a caught original exception is displayed as structured exception
metadata rather than an invented traceback. The receipt format remains default.

Additional alias/private-path/ownership, stability, stream and capture limits
produce `incomplete` with technical exit `2` and no original verdict. An
interrupted terminal journal is indicated by `journal_terminal_written: false`;
inspection rejects an unfinished record. There is no automatic retry or resume.
For an incomplete native run, observed paths may be partial; inspect the actual
selected files before intentionally starting a new run.

The scoped journal admits at most 16,384 events and 32 MiB of event bytes; shared
older profile limits are unchanged. Native output operations are capped at 256.
The private candidate additionally bounds its logical namespace to 2,048 nodes
and 1 MiB of path names. The underlying ordinary-file, aggregate-read, blob,
directory-member and stream limits remain explicit technical admission limits.

## Scope, history and delivery

The whole original generators remain available through source-only compatibility
facades backed by complete explicit legacy adapters. Both the five facades and
their five complete legacy adapters are excluded from the active V2 installation
and its runtime fingerprint. The installed neutral application uses only its
registered native input, selected-output, private-projection and storage ports. Existing frozen original fixtures are reused for
comparisons, so no Git history is needed to execute the reference tests. Neither
the source facades nor historical lifecycle validation imply that V2 imports
operating consent, live action authority or a V1 accepted runtime.

The three synthetic scenarios remain separate histories. Displayed decision,
exception, coverage and closure labels preserve original semantics. They do not
approve live waivers, close real findings, activate intake, publish results,
change enforcement or transfer source, compliance or operating authority. The
remaining live/personal lifecycle reporters stay in the full Goal.

Delivery requires the full pinned bootstrap/validation, current revision-bound
declared coordinator reviews, a signed coherent source and fresh matching Mac
and Linux installations. Current whole V1 positive/negative comparisons, private
and native CLI runs, source-deletion replay, foreign-node rejection and complete
fixed `ha-CPsWMS` reports must be checked against that exact candidate. Earlier
development snapshots and the preceding renderer's delivered evidence do not
certify a newer package automatically.
