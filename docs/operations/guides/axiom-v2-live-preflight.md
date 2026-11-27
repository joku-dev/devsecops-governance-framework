# Diagnostic live-evidence preflight in AXIOM V2

`live-preflight generate/inspect/replay` retains the entire original
`preflight_lifecycle_live_evidence` main and `collect_preflight` operation.
The explicit legacy adapter keeps the complete original capture verifier and
saved-bundle replay. The selected source programs are never imported or run.
This is diagnostic, report-only work; it submits no lifecycle observation,
appends no receipt and grants no operating acceptance.

The implementation is under development. Passing focused source comparisons
are separate from pinned full validation, review and a matching signed
Mac/Linux installation, peer exchange and fixed-consumer comparison. The
original Goal scope remains 22 areas, 135 entrypoints, 37 CI definitions and
16 operating flows. The subject remains in progress.

## Capture or verify a bundle

```sh
/path/to/axiom-v2 --instance /private/node live-preflight generate \
  --profile legacy-lifecycle-preflight-v1 \
  --transport-profile legacy-preflight-github-get-v1 \
  --provider-executable /path/to/gh \
  --source-worktree /private/selected-repository \
  -- --run-id 12345 --output-dir /private/selected-repository/generated/reports/lifecycle-live-preflight/new
```

The original repository/run/workflow/artifact queries, paginated artifact
listing, pinned raw producer files and before/after race checks remain in the
adapter. Requests use the fixed original GET method and official host; raw
producer requests retain their original Accept header and full commit ref.
Credentials remain in the explicitly selected `gh` environment. Provider
stderr is captured in ordered opaque bytes. The original clock sample occurs
after all fetches and metadata comparisons, before full capture verification.
No original profile, assignment, archive, schema, digest, timeline, criterion or
report-summary check is bypassed.

The default creates a finite private output candidate. Provider reads still
occur. `--write-selected-files` selects actual original POSIX file effects.
Inside the selected source root, output must use the dedicated original
`generated/reports/lifecycle-live-preflight` subtree. A destination outside that
root retains the original selection behavior, subject to the owned-path,
product/private-state separation and finite observation guards.

Directory creation is exclusive and every file uses the original buffered
`xb` operation. A competing ordinary file or directory is observed separately
and never claimed as an owned write. The original `FileExistsError` is retained,
including appearance during GETs or at the final mkdir. Existing snapshots are
not replaced. `preflight.json` is written last; an interrupted directory without
that completion manifest cannot be replayed as a complete capture. No fsync or
crash-durability guarantee is added to the original buffered-write behavior.

To exercise the complete original saved-bundle verifier instead of collection:

```sh
/path/to/axiom-v2 --instance /private/node live-preflight generate \
  --profile legacy-lifecycle-preflight-v1 \
  --transport-profile legacy-preflight-github-get-v1 \
  --source-worktree /private/selected-repository \
  -- --verify-bundle /private/capture
```

Original bundle inventory, per-file digest, before/after metadata, producer
revision and full projection comparisons remain mandatory. This branch makes
no provider request or clock sample. `--output-dir` is not a replay output.

## Inspect and reconstruct

```sh
/path/to/axiom-v2 --instance /private/node live-preflight inspect --record /private/record
/path/to/axiom-v2 live-preflight replay --record /private/record
```

Inspection binds the originating node and exact product generation. Portable
replay reconstructs the original complete program from the closed request,
producer parser context, input bytes, GET observations, sampled clock,
exclusive-directory/file progress and completion-manifest sequence. It repeats
no selected-source access, program, provider query, write or clock sampling.
External path observations are distinct from owned outputs.

The original artifact limit stays **10 MiB**. This transport explicitly permits
up to **16 MiB** of stdout per GET; a valid archive at the complete original
10-MiB boundary is tested. The existing personal-channel transport keeps its
8-MiB default. Other limits include 256 KiB of stderr per process, the original
90-second GET timeout, 16 MiB per admitted file, 128 MiB of logical file data,
finite directory depth/membership and the existing closed journal/blob budgets.
Exceeding added observation limits or encountering an unsafe alias/nonordinary
entry is technical incompleteness and receives no invented original verdict.

Observed original errors retain their kernel streams, type/message and file
bytes/modes. A seven-byte partial exclusive write retains exactly those bytes,
its original error and the possible partial-effects indication. Lost journal,
clock or input observations receive no original verdict; owned host streams
are released separately without certifying unobserved flushing. `--format
legacy` emits retained streams and a structured exception diagnostic. Full
byte equality of the outer Python interpreter traceback remains open.

Tests use immutable original programs and explicit fake-provider bytes; a
legacy capture-method marker or a consistent replay does not authenticate a
producer. CLI tests can supply a distant expiry in synthetic provider metadata
to exercise the real clock, then compare the unchanged V1 program at that exact
sample. This does not assert real evidence freshness, personal consent,
Source/compliance authority or live activation. Receipt intake and
`intake_lifecycle_pilot_run` remain separate unfinished Goal entrypoints.
