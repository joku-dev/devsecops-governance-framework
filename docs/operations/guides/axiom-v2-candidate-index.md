# Portable candidate index in AXIOM V2

`candidate-index` builds the original separate candidate read model. Its rows
are declarations from portable intake, including GitHub Actions, GitLab CI and
Bamboo profiles. They do not prove mainline status, native verification or
official result acceptance. Branch, manual and pull-request histories retain
their original selection and equal-timestamp path tie-breaker; different PR
executions remain separate.

## Generate and inspect

Use an admitted V2 instance. The default source is the installed product's exact
committed candidate data, including data held as sparse Git objects:

```bash
axiom-v2 candidate-index generate --profile legacy-portable-candidate-index-v1
```

The response identifies a private assessment and its complete original index
artifact. To capture a separate working tree, explicitly select its root:

```bash
axiom-v2 candidate-index generate --profile legacy-portable-candidate-index-v1 \
  --source-root /path/to/producer --output /path/to/artifacts/candidate-index.json
axiom-v2 candidate-index inspect --id ASSESSMENT_ID
axiom-v2 candidate-index export --id ASSESSMENT_ID --output /path/to/artifacts/candidate-index.json
```

`--root` is an alias for `--source-root`. Supplying `--revision FULL_COMMIT`
selects committed data in that source instead of its working tree. Both Git
SHA-1 and SHA-256 object formats are supported. Source scripts, native CI
providers and network readers are never invoked by this command.

Working-tree capture is a bounded per-file observation, not an atomic snapshot
of a changing repository. Use a quiescent working tree or select an immutable
full commit with `--revision` for repeatability. New product/runtime versions
follow normal instance upgrade and admission; old assessment bindings are not
automatically rewritten or transferred.

The normal CLI response is metadata. `--format legacy` suppresses successful
stdout, as in the original script; use `--output` for its complete original
JSON file. Without an explicit output, V2 retains the artifact inside private
instance state. It does not write the installed product's generated directory.
Exports inside a separate source root are restricted to the original
`generated/portable-intake/index.json` destination. Product files, instance
files, Git metadata and unsafe output links are excluded.

## Retained evidence and output effects

Private inputs retain every selected raw candidate and its path, byte count
and SHA-256, plus the declared source origin and observed directory names.
Assessments bind these inputs and the complete index bytes to the current
node, runtime and product revision. Inspection reprojects all retained inputs
and compares the entire artifact, even after the original producer disappears.
Changed inputs, outputs, members or bindings fail. These local consistency
checks do not authenticate the original producer or establish independent
execution quality.

Explicit export preserves the original atomic file-replacement behavior.
Before replacement, private export history records the previous bytes,
observed metadata, intended output and assessment binding. Failed or interrupted
exports retain their prepared intent and do not auto-resume. An operator must
inspect the actual destination before retrying. A single operating owner is
required for each external output; the node lock is not a distributed lease.
The V2 private/export files use mode `0600` and new parents `0700`; the original
script used public artifact mode `0644`. Existing directory permissions are
not changed. No official index or consumer configuration is selected implicitly.

## Bounds and compatibility evidence

The original acquisition bounds remain 50,000 files, 64 KiB per candidate,
128 MiB total candidate bytes and `3 * file_limit + 4` visited descendants.
V2 also rejects unsafe held files, hardlinks, submodules, malformed paths and
non-finite JSON; committed tree metadata is limited to 32 MiB, retained manifests
to 64 MiB and index output to 512 MiB. These explicit product guards do not
become governance findings. They are not a kernel memory-limit guarantee.

The original strict UTF-8 text contract is retained: UTF-8 BOM and UTF-16/32
candidate files are rejected. Malformed candidate/JSON failures surface as
structured product Exit 2 diagnostics. No identity with original uncaught
traceback bytes is claimed. If several inputs fail simultaneously, failure
priority can differ because V2 acquires inputs before projecting them.

Focused tests execute the unchanged frozen V1 CLI and compare its entire JSON
file, stdout and successful exit. They cover all three declared provider
profiles, empty input, history/context/tie-breaker behavior, Unicode/timezones,
source quotas, both Git formats, tampering, source removal, default committed
data, actual development-instance CLI admission and explicit output effects.
A separate test compares 2,000 synthetic repository records against the whole
original CLI file. That is a synthetic read-model test, not a claim of 2,000
live providers or a production capacity acceptance.

The entrypoint remains in progress until exact-source validation, review,
publication and installed Mac/Linux evidence are complete. The complete V1
scope and independent governance/operating approvals remain part of the Goal.
