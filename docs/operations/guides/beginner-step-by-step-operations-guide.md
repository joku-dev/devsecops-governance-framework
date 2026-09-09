# Beginner Step-By-Step Operations Guide

## Choose Your Task

For daily observation, start with the
[operations handbook](governance-repository-operations-handbook.md) and
[daily report](../status/daily-governance-operations.md).
For adding an application, use the [consumer quickstart](../../onboarding/public-repo-quickstart.md).
This page explains a reviewed change to the central governance repository.

## Step 1: Prepare The Checkout And Tools

In a clone of `joku-dev/devsecops-governance-framework`, inspect the worktree
before changing branches. Keep unrelated local work separate.

```bash
git status --short
git switch main
git pull --ff-only origin main
git switch -c docs/example-governance-change
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh --check-tools
```

Use an unused branch name for the actual change. The bootstrap installs pinned
Python dependencies and OPA into `.venv-validation`; no global pip installation
is needed. See [local validation](local-validation-toolchain.md) for prerequisites,
custom paths and checksum failures. The commands below assume the default path.

## Step 2: Classify And Edit The Source

Follow the [artifact intake process](../processes/new-artifact-intake-process.md)
and record governance intent before deriving behavior from a new source.

| Change | Primary paths |
|---|---|
| Control requirements | `model/controls/` |
| Policy/directive rendering inputs | `docs/governance/`, `model/documents/` |
| Platform and traceability | `model/platform/`, `model/traceability/` |
| OPA behavior | `policies/opa/` plus representative tests |
| Evidence contract | `schemas/`, `model/evidence/` plus existing examples/tests |
| Operational documentation | `docs/operations/` and navigation |

Edit the relevant source, not generated reports or historical result snapshots.
Released packages/tags require an explicit release flow; a candidate source
cannot authorize control or policy changes before its review decision.

## Step 3: Validate And Regenerate Relevant Outputs

Run full validation:

```bash
./scripts/validate_all.sh
```

This includes schema/model checks, runtime governance, OPA syntax and unit tests.
Missing dependencies are a setup failure, not permission to skip validation.

Regenerate only outputs affected by your change. Examples:

```bash
.venv-validation/bin/python scripts/generate_traceability_csv.py
.venv-validation/bin/python scripts/generate_document_control_matrix.py
.venv-validation/bin/python scripts/generate_open_gap_report.py
.venv-validation/bin/python scripts/render_governance_documents.py
.venv-validation/bin/python scripts/generate_governance_graph.py
.venv-validation/bin/python scripts/generate_status_viewer.py
```

These produce traceability CSV, document/control and gap reports, Policy and
Directive renderings, the graph and viewer. The intake workflows regenerate
scope-specific result projections automatically before proposing their PRs;
see the [intake guide](../evidence/governance-result-intake-and-viewer-usage.md).

If source changes after validation, rerun the affected checks and the full
required validation before committing. Pure generated timestamp noise does not
belong in a source-change commit; inspect the diff before omitting it.

## Step 4: Build And Inspect Documentation

```bash
python3 -m venv .venv-docs
.venv-docs/bin/python -m pip install -r requirements-docs.txt
.venv-docs/bin/mkdocs build --strict
```

Inspect the changed prose, navigation and relevant generated reports. A passing
MkDocs build checks buildability and configured links; it does not prove that
instructions or paths displayed as code are semantically correct.

For an optional local demonstration, use the pinned tools:

```bash
PATH="$PWD/.venv-validation/bin:$PATH" .venv-validation/bin/python scripts/run_demo.py
```

Generated demo results demonstrate representative cases; they do not replace
real consumer evidence. Review and exclude unrelated demo output from the commit.

## Step 5: Commit A Focused Change And Open A PR

```bash
git status --short
git diff --check
git diff --stat
```

Stage the intended files explicitly. For example, for an actual change to the
existing docs landing page:

```bash
git add -- docs/index.md
git diff --cached
git commit -m "Clarify documentation entry points"
git push -u origin HEAD
gh pr create --base main
```

Replace the example file/message with the real scope. Include meaningful
generated changes when required, not unrelated timestamps, `.DS_Store` files
or editor artifacts. If commit signing is configured, use the configured valid
key; resolve a signing failure deliberately rather than silently changing the
repository's signing setup.

The PR should explain behavior, validation, release impact and known limits.
PRs are required even when the source change is only documentation.

## Step 6: Review, Merge And Verify

Check the PR's **Checks** and **Files changed** tabs. Main currently requires
`validate-and-report`, `Analyze Python`, and `Governance Repository Security`,
a current branch, resolved conversations, and one approval.

The approval must come from another authorized account when you authored the
PR. For a bot-authored operational PR, the maintainer can review it. Approving
workflow execution is separate from approving the PR. Do not treat a prior
one-off administrative exception as a standing review bypass.

After approval and successful checks, merge using GitHub. Then:

```bash
git switch main
git pull --ff-only origin main
gh run list --branch main --limit 10
```

Confirm the relevant main workflows and Pages publication succeed. The viewer
reflects accepted evidence; the daily report is a separate Actions artifact.
See [documentation publishing](mkdocs-and-github-pages-step-by-step.md) for
publication paths and troubleshooting.
