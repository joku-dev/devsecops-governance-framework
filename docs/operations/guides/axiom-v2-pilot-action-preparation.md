# Pilot action request preparation in AXIOM V2

`pilot-action-requests generate/inspect/replay` retains the complete original
`prepare_lifecycle_pilot_action.prepare` function and main guard. It loads and
validates the recorded operating profile, role binding, receipts and actions,
selects the original required role, binds both ledger heads and revision, and
validates the complete request before producing its original statement text.

This is a source-development candidate. Full pinned validation, accountable
review and fresh signed installed Mac/Linux/peer/consumer evidence remain
required. The subject is in progress; no full-Goal completion is claimed.

## Prepare a request

```sh
/path/to/axiom-v2 --instance /private/node pilot-action-requests generate \
  --profile legacy-pilot-action-preparation-v1 \
  --capture-profile legacy-lifecycle-capture-v1 \
  --source-worktree /private/selected-repository \
  -- --body /private/input-body.json --discussion-number 900001 \
  --output /private/prepared-action.json
```

The default creates a private candidate in the diagnostic record. It leaves
the selected repository and requested output path unchanged. Add
`--write-selected-files` to request actual local output. The original command
checks output existence after preparation, then creates it with `xb` and prints
the complete request-bound statement. An existing output cannot be replaced;
the output parent must already exist. No parent directory is created implicitly.

The original body kinds remain `decision`, `progress`, `closure`, `withdrawal`
and `role_withdrawal`, with their original schemas and validation. A PASS does
not manufacture a finding. Quarantine, inactive roles, stale evidence, missing
records and invalid progress/closure chains retain their original errors.
The creation clock is sampled after context loading; the internal original
`created_at` argument retains its supplied-value/default semantics.

The capture profile selects checks over retained provider fields. This command
performs no fresh provider query, posts no personal statement and appends no
action or operating acceptance. A generated request and printable declaration
are preparation artifacts; they are not proof that a person issued them or that
an action, remediation, closure or live activation was authorized.

## Inspect or replay

```sh
/path/to/axiom-v2 --instance /private/node pilot-action-requests inspect --record /private/record
/path/to/axiom-v2 pilot-action-requests replay --record /private/record
```

Inspection checks the originating node and product generation. Portable replay
reconstructs the original result after the selected source has been removed,
without another native read, output, process or clock sample. The complete
request, source, node, result, event chain, raw bytes and authority fields remain
bound. This is declared consistency evidence, not producer authentication or
personal/operating approval.

Private mask077 projection is a finite candidate model; native buffered
creation/write/close is observed separately. Original partial native errors
remain complete errors and expose possible partial effects. An actual seven-byte
write failure is compared with the unchanged original. Unobserved resource,
clock or journal failures are incomplete and obtain no original verdict; cleanup
does not certify an output that was never fully observed.

`--format legacy` emits the retained original kernel streams. Complete original
parser profiles preserve producer width/language/version during replay. Thrown
exceptions use their original type/message in a structured diagnostic; exact
external interpreter traceback equality remains an open full-Goal boundary.
All22/135/37/16 remain in the unchanged Goal scope.
