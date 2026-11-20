# Complete documentation reconciliation candidate

The `documentation-reconciliation` command preserves all seven functions and
165 lines of the original `reconcile_documentation_after_merge.py` at immutable
V1 revision `6b557fefe295b58272d2271326576ca3a3687197`. Its complete function
bodies use explicit data paths, local Git, text streams and parser context.
Selected repository programs are never loaded. The source-only facade, unchanged
original adapter and constant-binding helper remain outside the active product
and its runtime fingerprint.

This is an engineering candidate in its own branch. Full pinned regression,
declared revision-bound review, signed source, fresh installed Mac/Linux packages
and the fixed whole ha-CPsWMS comparison remain delivery conditions. The complete
Goal remains open; this entrypoint is in progress, with no parity receipt or
operating acceptance inferred from development tests.

## Run and reconstruct

```sh
axiom-v2 --instance /path/to/instance documentation-reconciliation generate \
  --profile legacy-documentation-reconciliation-v1 \
  --source-worktree /path/to/selected-repository -- \
  --base BASE_COMMIT --merge MERGE_COMMIT --pr 42 --title 'Example change' \
  --body-file /path/to/selected-body.txt --docs-build-status 'caller declaration'
```

The default creates a private candidate. Add `--write-selected-files` before
`--` to choose actual writes to the selected ordinary owned files. Four outputs
are preserved: README, function catalog, technical inventory and the generated
documentation-refresh audit. Functional-path classification, summary cleanup,
replacement-regex behavior and the complete tracked-Markdown link audit remain
the original algorithms. Subsequent audit reads see earlier candidate writes.

Original `--github-output FILE` selects an ordinary append file. It invokes no
GitHub API. Existing opaque bytes remain intact, including invalid UTF-8 and an
unterminated last line. No separator, parent directory creation, truncation or
fsync is added. Original missing-parent, directory, permission, short-write and
close failures retain preceding document/file effects. An append may overlap a
previous document output, after the original link audit has completed.

```sh
axiom-v2 --instance /path/to/instance documentation-reconciliation inspect \
  --record /path/to/private/record
axiom-v2 documentation-reconciliation replay --record /path/to/private/record
```

`inspect` checks the selected local node. `replay` admits a portable record with
the same complete registered product generation; it reconstructs the whole
original result from closed raw blobs and observations. It repeats no selected
source reads, Git processes, native writes or provider calls. Entire streams,
original exit/exception, successful outputs, candidate transitions and observed
native partial effects remain bound. This consistency check authenticates no
producer. Relabeled local nodes are rejected by local inspection; portable
replay does not prove the claimed node's identity.

## Effect and capture boundaries

Only the original local `git diff --name-only --diff-filter=ACDMR BASE..MERGE`
and `git ls-files '*.md'` requests are admitted. The native provider selects an
ordinary bounded system Git executable, records its identity and raw process
outcome, and prevents implicit hooks, external diff/text conversion, inherited
Git environment overrides and network transport. Both SHA-1 and SHA-256 data
repositories are covered. This finite read environment is an additional capture
condition; it is not permission to execute selected repository tools.

Git processes terminated by a signal retain the producer CPython/OS context.
Closed reconstruction derives the entire original signal diagnostic from the
finite Linux/macOS signal profile, including unnamed Linux signals. Current
profiles are compared against each host's complete native signal enumeration;
whole original runs also test actual SIGTERM, SIGUSR1 and SIGKILL termination.
A review probe found the earlier prefix-only diagnostic check too broad. Its
controlled interrupted full run is archived, with all 19 classified effects
exactly restored, and is not successful current-source validation.

Native append records open/write/close stages, exact preimages and byte prefixes,
file identity/mode, actual buffered-stream state and original errors. A failed
observation yields incomplete capture without an original verdict. Owned host
streams are released separately after capture abort; an unobserved close may
flush bytes and cannot certify a successful original execution. A replacement
descriptor is not closed. No automatic original retry or rollback occurs.

Private append uses the same finite candidate filesystem as document writes,
with explicit mask `077`, logical identities, raw preimages and ordered close.
This model certifies no native ACL, umask, durability or concurrent-writer
behavior. Ordinary stable owned paths, bounded files, names, processes, streams,
blobs and journals are admission conditions. Rejected or incomplete capture is
separate from an original program error captured completely.

`--docs-build-status` is a caller declaration. It does not run MkDocs. Prepared
documentation still requires human editorial review. Report-only evaluation,
source history, released baselines, personal consent and operating authority
are unaffected by a reconciliation record.

## Evidence scope

The separate frozen prototype passed 23 complete original/capture/error tests
on CPython 3.13/macOS and 3.12/Linux, then ten complete records in each direction
with native source/file/Git/network ports forbidden. These prototype proofs do
not certify the later registered application or a future installation.

On the earlier frozen whole data tree, the original link audit and captured
reconstruction agree over all 707 tracked Markdown files (5,043,650 bytes and
1,781 initial link matches). Its three broken local targets are documentation
audit results, separate from consumer governance findings. All 2,869 source
files remain unchanged and closed replay succeeds after source/Git removal.
This dated development scope remains separate from current delivery gates.

## Explicit producer parser profile

Every application request retains the original producer's complete CPython
argparse profile, Python version, observed formatter width and admitted English
translations. Capture verifies the exact complete native stdlib module identity
before selected data access or record creation. The shared
[ledger parser contract](axiom-v2-synthetic-ledger.md#producer-parser-context-and-portability)
admits the retained 3.11.18 CI, 3.12.3 Linux and 3.13.18 Mac module identities;
a minor-version label alone is insufficient. Complete PSF licenses and provenance
notices travel with all retained parser modules. Unsupported/modified modules or
translations require a new explicit profile, rather than a native fallback.

Replay reconstructs the producer's entire parser, help/usage and original exits
using those explicit inputs. It consults no consumer terminal, gettext function,
selected source data or Git command for parser exits. It compares the whole
reconstructed result; it does not normalize wrapping or copy retained stdout.
Missing, malformed or inconsistent parser context cannot be accepted as a new
application request. Earlier development records remain dated and are not
silently converted to this contract. The seven original functions/165 lines,
Git signal handling and append semantics remain in scope. Current focused source
tests are separate from full regression, signed installation and whole-peer
acceptance, which are still required before delivery.

A complete failed original selected-files execution can retain earlier writes.
`source_effects_may_be_partial` is true for these outcomes as well as for
incomplete selected-files captures. This receipt indication does not retry,
roll back, alter the retained original error or repeat any effects during replay.
