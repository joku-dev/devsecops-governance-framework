# Pilot action intake in AXIOM V2

`pilot-action-intake generate/inspect/replay` retains the entire original
`intake_lifecycle_pilot_action` program and its `collect_action` and
`append_action_snapshot` dependencies. It collects a request-bound personal
statement, validates the complete original history, and prepares the original
append result. No personal statement is posted or executed.

This is a source-development increment. Original comparisons and a real
competing-process test are separate from full pinned validation, review and
matching signed installed Mac/Linux/peer/consumer acceptance. The subject
remains in progress; complete Goal parity is not asserted.

## Collect and prepare

```sh
/path/to/axiom-v2 --instance /private/node pilot-action-intake generate \
  --profile legacy-pilot-action-intake-v1 \
  --transport-profile legacy-personal-github-get-v1 \
  --provider-executable /path/to/gh \
  --source-worktree /private/selected-repository \
  -- --request /private/selected-repository/action-request.json \
  --expected-sequence 0
```

The explicit transport profile retains the original GitHub GET contract. The
adapter performs the original issue and paginated before/after comment queries,
then samples the capture time. The separate ledger `recorded_at` clock is sampled
only after collection and its original context validation succeed. The required
fresh-capture marker and all role, schema, head, revision, statement, chronology
and freshness checks remain in force. Provider stderr stays ordered opaque
bytes, including bytes that cannot be decoded as UTF-8.

The default creates a private candidate. Provider reads still occur; ledger
writes and lock/fsync steps are finite private projections, not native locks or
durability claims. `--write-selected-files` selects actual local POSIX effects.
Both ledger roots must be inside the selected owned source scope. The original
receipt-ledger lock precedes the action-ledger lock; context is reloaded while
both are held. The transaction is written and flushed to a pending file,
hard-linked without replacement, directory-synced and cleaned up using the
complete original store sequence. No historical transaction is overwritten.

The original duplicate check precedes stale-sequence rejection. A competing
writer therefore cannot share a sequence with a distinct request, while an
identical observation can retain its original duplicate result. A test with two
real processes holds the first actual receipt lock, observes the second process
attempting it, then verifies the changed state and original stale-sequence
rejection after the wait. Original validation functions are not patched.

## Inspect or replay

```sh
/path/to/axiom-v2 --instance /private/node pilot-action-intake inspect --record /private/record
/path/to/axiom-v2 pilot-action-intake replay --record /private/record
```

Inspection checks the originating node and product generation. Portable replay
reconstructs the complete request, parser profile, provider responses, both
sampled times, two-ledger effect sequence, native after-images and logical
end-of-kernel descriptors from a closed event/blob record. It needs no selected
source, provider executable, native effect, process or clock sample.

Complete original failures retain their emitted streams, type/message and file
effects. A directory-fsync error after publication can leave a visible action;
the original error and possible partial-effects indication remain visible.
Unobserved input, clock, resource or journal failures obtain no original verdict.
Adapter-owned handles are released separately when a broken journal prevents
original cleanup. This does not certify unobserved flushing or change recorded
end-of-kernel facts. Finite observation deadlines are technical incompleteness,
not invented original errors.

`--format legacy` emits retained original kernel streams. Thrown exceptions use
an additional structured type/message diagnostic; full byte equality of the
external Python interpreter traceback remains an open full-Goal boundary.
Complete parser profiles retain the producer's Python version, width and
language during cross-host replay.

Synthetic test statements, legacy provider-field markers, private candidates and
consistent replays do not authenticate a producer, establish physical human
presence, grant personal consent or transfer Source/compliance/live/operating
authority. Publication and acceptance remain separate governed operations. All
22 areas, 135 entrypoints, 37 CI definitions and 16 operating flows remain in the
Goal scope.
