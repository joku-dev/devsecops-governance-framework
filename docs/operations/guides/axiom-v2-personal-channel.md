# Personal-channel programs in AXIOM V2

`personal-channel generate/inspect/replay` restores the three complete original
statement, channel-check and evidence-report programs. Their nine named functions,
two additional main guards and unchanged history validators remain separate from
personal consent and operating authority. The selected transport profile is
`legacy-personal-github-get-v1`; the program profile is
`legacy-personal-channel-v1`.

This is a development candidate. Full pinned regression, revision-bound review,
signature and fresh installed Mac/Linux/peer/consumer acceptance remain required.
The three subjects are in progress; this increment does not establish full parity.

## Choose the original operation

- `--program statement` renders the original personal statement template.
- `--program check` preserves the original `--replay`, `--previous-capture` and
  `--output` options after `--`. A new capture performs explicit provider reads.
- `--program evidence` renders the original retained-capture report. With the
  separate V2 option `--verify-base-ref REF`, it instead executes the complete
  original `verify_new_captures` function: local Git selects already accepted
  files, and new captures are checked against freshly read provider state. Its
  integer return value is retained separately from the command exit code. This
  option is a V2 invocation of an original function, not an original CLI flag.

For example, preview a new diagnostic capture using an existing private instance:

```sh
/path/to/axiom-v2 --instance /private/node personal-channel generate \
  --profile legacy-personal-channel-v1 \
  --transport-profile legacy-personal-github-get-v1 \
  --program check --source-worktree /private/selected-repository \
  -- --output /private/selected-repository/generated/reports/lifecycle-personal-channel/new.json
```

The default creates a private candidate and leaves the selected repository
unchanged. `--write-selected-files` requests actual local file effects. Original
exclusive creation prevents replacement of an existing capture. Original
directory creation, output sequence, errors and possible partial native writes
remain visible. Private creation mask `077` is a bounded projection model; it
does not attest native buffering or durability.

Provider access is restricted to the original GET issue/comment endpoints,
including at most ten pages before and after capture. The adapter uses the
operator's existing provider client credentials; credentials are not put in the
record. An explicit `--provider-executable` selects that client. No operation
posts a statement, changes a role, closes a finding or activates a service.
Retained historical statements do not become current consent for this node.
The original GET timeout starts after process creation. Local Git has an
additional finite 90-second observation budget; reaching it is a technical
incomplete capture, since the original Git call has no timeout.

## Inspect or replay

```sh
/path/to/axiom-v2 --instance /private/node personal-channel inspect --record /private/record
/path/to/axiom-v2 personal-channel replay --record /private/record
```

Inspection binds the record to its product generation and originating node.
Portable replay needs neither the selected repository nor its provider program,
credentials, terminal or current clock. It reconstructs the original execution
from closed file/process/clock observations and rejects changed result, event,
source, authority, stream and orphan-blob data. It repeats no native effects.
This consistency check does not authenticate a producer or an execution claim.

Raw provider stderr remains ordered binary data, including invalid UTF-8 and
CRLF; original Git text stdout retains its original text decoding/newline rules.
The original check parser's complete producer profile is captured explicitly.
Capture/resource/journal failures are incomplete and obtain no original verdict;
separate resource cleanup may flush an owned buffer without certifying it as a
completed original output. Original program errors remain complete errors.

`--format legacy` emits original kernel streams. Thrown exceptions retain their
original type/message with a structured diagnostic; exact external Python
interpreter traceback equality remains an open full-Goal boundary. All 22 areas,
135 entrypoints, 37 CI definitions and 16 operating flows remain in scope.
