# Synthetic ledger candidate

`axiom-v2 synthetic-ledger generate/inspect/replay` exposes the six complete
original synthetic ledger programs through profile `legacy-synthetic-ledger-v1`.
This is an engineering candidate. Full pinned validation, declared reviews,
signed delivery and fresh matching installed Mac/Linux comparisons are required
before the increment is delivered. The broader V2 parity Goal remains open.

## Retained behavior and explicit context

| Program | Whole original entrypoint |
| --- | --- |
| `synthetic` | `run_governance_lifecycle_synthetic_demo.py` |
| `action` | `run_governance_lifecycle_action_demo.py` |
| `closure` | `run_governance_lifecycle_closure_demo.py` |
| `exception` | `run_governance_lifecycle_exception_demo.py` |
| `observation` | `intake_governance_lifecycle_observation.py` |
| `record` | `intake_governance_lifecycle_action.py` |

All 24 original functions across ten modules, 587 original source lines, remain
in scope. This includes the seven ledger-store functions and three synthetic
packet modules, all four action record types, duplicate/stale delivery decisions,
quarantine, consent withdrawal, closure and exception projection. Six source-only
facades preserve the complete original APIs through complete legacy adapters;
these twelve compatibility files are excluded from the V2 installation and
runtime fingerprint. Selected source programs are never executed by V2.

`--source-worktree` selects data, schemas and fixtures. It does not select product
code or approval authority. `--working-directory` defaults to that worktree and
controls relative original paths. Original arguments follow `--`; the original
parser handles required fields, abbreviations, `--ledger=...`, repeated options,
help and parser errors. Ledger ports bind only after successful parsing. Help
and parser exits need no selected source or ledger access.

## Producer parser context and portability

A complete request retains `parser_context`: CPython implementation/version,
explicit `cpython-3.11-argparse-v1`, `cpython-3.12-argparse-v1` or
`cpython-3.13-argparse-v1` profile, observed formatter width and
`stdlib-en-v1` translations. Native composition admits the exact complete
stdlib module identities observed in the pinned 3.11.18 CI, 3.12.3 Linux and
3.13.18 Mac runtimes. It also checks the original formatter defaults and English
singular/plural translations. Other or modified module identities and translated
native parsers require a new explicit profile; capture refuses them before
selected source access or record creation. A minor-version label alone does not
admit an arbitrary Python distribution. Missing or malformed retained context
has no consumer-native fallback.

Pure replay selects the complete retained producer parser, including its groups,
actions, help and usage formatter. Its terminal width and English translations
are explicit inputs. It does not consult the consumer's terminal, environment or
gettext functions, copy retained final stdout, or normalize wrapping differences.
The original six programs still decide their own parser exits before ledger ports
bind. Retained modules have their complete PSF licenses and provenance notices
under `scripts/lib/argparse_profiles/`; source fixtures verify the complete module
AST except the three documented composition changes. Argument-file expansion is
not an admitted source-data channel for these fixed original parsers.

The earlier signed development candidate `a5ea574` passed 25 of 28 complete
Linux-to-Mac record replays; three help/parser records differed because CPython
3.12 and 3.13 wrap usage differently. That comparison did not establish full
installed parity, and its records lack the new required context. They remain
historical records, without relabeling or silent migration. The corrected
candidate requires fresh source validation, signed packages and complete
Mac/Linux peer comparisons before delivery. Synthetic and operating authority
remain separate from this technical parser context.

## Default private preparation

```bash
/path/to/axiom-v2 synthetic-ledger generate \
  --profile legacy-synthetic-ledger-v1 --program closure \
  --source-worktree /path/to/data-worktree \
  -- --ledger /path/to/disposable-history \
     --output /path/to/candidate-index.json \
     --report /path/to/candidate-report.md
```

Without `--write-selected-files`, selected source files stay unchanged. The
separate record under `INSTANCE/state/synthetic-ledger/records/RECORD_ID` retains
owned source preimages, candidate bytes, directory membership and ordered domain
operations. The record path is printed in the receipt. Each invocation constructs
its own candidate over the observed source; an earlier private invocation does
not silently become the next invocation's source ledger.

The finite private model tracks inode aliases, descriptors, buffered writes,
locks, temporary publication, fsync order and finally cleanup. Reads and probes
see earlier candidate effects. Its creation mask `077`, identity namespace and
modeled permissions describe that candidate, without asserting native disk
persistence, ACL behavior or concurrent-writer certification. It permits at most
128 model descriptors and 8,192 model operations. Original guards, original
exceptions and partial candidate history remain visible.

## Explicit native effects

Add `--write-selected-files` before `--` to request actual selected ledger and
output file effects. Use a disposable selected ledger and output paths when
comparing candidates. There is no automatic retry, rollback or history reset.
A failure after publication can retain a transaction; unlink failure can retain
both its canonical and pending hardlink. A subsequent explicit original duplicate
retry preserves that history.

The POSIX adapter retains actual opened file identity, owner, mode, link count,
directory members, descriptor binding, buffered prefixes and before/after images.
It performs the original file fsync, exclusive hardlink publication, directory
fsync and finally unlink/unlock/close sequence. Observed platform metadata remains
host context. The permitted two-link case is exactly one owned canonical
transaction and one pending alias in the selected transaction directory, with
matching transaction identity and stable metadata. External, extra, substituted,
two-canonical and two-pending aliases are rejected. Private source preimages
admit the same exact pair without changing it.

Installed product/private-state exports and overlapping selected source/instance
roots are rejected. Stable ordinary-file, ownership, alias, path, input and
capture budgets are additional technical admission requirements. A contended
native lock reaches a finite observation boundary instead of inventing an
original governance verdict. Original I/O errors can be fully captured; failed
observation or journal storage is incomplete capture and may follow real native
partial effects.

Native descriptor teardown is a separate host boundary after the original
kernel ends. The receipt's `host_resource_release` reports actual release counts
and errors. It can release an owned lock even when journal exhaustion prevents
the original finally calls. It never resets history or retries the original
program. End-of-kernel resource facts remain in the record and in pure replay;
replay performs no host teardown. Remaining/replaced descriptors, cleanup errors
or buffered streams needing unobserved flushing make capture incomplete, with no
complete original verdict. Teardown checks descriptor identity and never closes
a replacement file descriptor as if it belonged to the original operation.

## Receipts and original streams

Default output is a JSON capture receipt. A complete receipt preserves the
original exit code, including original parser exit 2 and original exception exit
1. Incomplete capture has exit 2 and `original_exit_code: null`; it must not be
read as a complete original finding or success. For complete captures,
`--format legacy` emits original stdout/stderr. Captured exceptions additionally
have structured type/message diagnostics rather than an identical Python stack.

Local lifecycle schemas and explicitly selected external resources form a closed
registry. Use repeatable `--schema-resource URI FILE` selections before `--` for
required external schema bytes. Unselected references produce incomplete capture.
Neither capture nor replay performs implicit HTTP/file-URI schema retrieval.

```bash
/path/to/axiom-v2 synthetic-ledger inspect --record /private/record/path
/path/to/axiom-v2 synthetic-ledger replay --record /private/record/path
```

Inspection checks the current own node and product generation. Portable replay
uses the same product generation without adopting the producer's node identity;
it is also available without an instance through
`python3 scripts/axiom_v2.py synthetic-ledger replay --record /private/record/path`.
Replay reconstructs the complete original execution, candidate/native effect maps,
streams, errors and end-of-kernel descriptor state from closed retained bytes.
It does not repeat selected data reads, native file effects, external programs
or provider calls. Raw blobs, event chain, request, source, binding, authority
flags, observations and the entire reconstructed result are checked. Resealing
an inconsistent observation chain does not make it a valid execution.

Consistency is declared technical evidence. It does not authenticate an external
producer, activate a service, approve a governance result, transfer personal
consent or operating acceptance, or authorize a live waiver/action. Synthetic
closure and exception labels remain bounded scenario data. The separate
[reporting commands](axiom-v2-synthetic-lifecycle-reporting.md) consume retained
synthetic history; live/personal reporters and full operating parity remain in
the [complete Goal](../planning/axiom-v2-functional-parity.md).
