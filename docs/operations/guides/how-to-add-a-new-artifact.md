# How To Add A New Artifact

## Purpose

This guide explains how to add a new artifact to the DevSecOps governance
repository without bypassing intake, validation, source lineage or release
governance.

Use it when you want to add, move or start consuming a new file such as a source
document, evidence result, schema, example, adapter template, generated report,
release artifact or documentation page.

## Before You Add The File

Start with classification, not with the target folder.

Read:

```text
docs/operations/processes/new-artifact-intake-process.md
docs/examples/artifact-intake-checklist.template.md
docs/examples/artifact-intake-classification.example.md
```

Then answer:

- What is the artifact?
- Who owns it?
- Is it source material?
- Is it runtime evidence?
- Is it generated output?
- Does it change schemas, policies, workflows, releases or downstream behavior?
- Which validation proves the change is safe?

## Step 1: Classify The Artifact

Use the artifact intake checklist:

```text
docs/examples/artifact-intake-checklist.template.md
```

Record the classification in the governance change request.

Typical classifications:

| If the artifact is | Usually use |
|---|---|
| A policy, directive, ADO source or architecture source | Full Source Document Intake |
| A downstream run result or CI evidence bundle | Evidence/result intake |
| A schema-backed example | `docs/examples/` plus schema validation |
| A new evidence contract or schema | Evidence contract review |
| An OPA policy, workflow or evaluator change | Governance behavior review |
| A Bamboo, Bitbucket, GitHub, GitLab or Jenkins adapter artifact | Platform adapter review |
| A practical how-to document | `docs/operations/guides/` |
| A governance process document | `docs/operations/processes/` |
| A Confluence or stakeholder article | `docs/publishing/` |
| A release package update | Explicit release decision |

## Step 2: Choose The Target Path

Only choose the path after classification.

Common target paths:

| Target | Use for |
|---|---|
| `docs/governance/source-documents/` | Candidate, draft or approved source documents |
| `status/results/` | Normalized downstream result snapshots |
| `docs/examples/` | Example payloads and reusable templates |
| `schemas/` | JSON schemas |
| `policies/opa/` | OPA/Rego policy rules |
| `architecture/` | Machine-readable architecture governance models |
| `pipeline-baseline/templates/` | CI/CD adapter templates |
| `docs/operations/guides/` | Practical repository guides |
| `docs/operations/processes/` | Governance operation processes |
| `docs/operations/evidence/` | Evidence and result handling documentation |
| `docs/operations/adapters/` | CI/CD platform adapter documentation |
| `docs/publishing/` | Publication-oriented communication artifacts |
| `releases/` | Versioned baseline release packages |

Avoid adding new files directly under `docs/operations/` unless the target is
temporary and a follow-up migration decision is recorded.

## Step 3: Create The Change Request

Create a GCR from:

```text
docs/governance/change-requests/TEMPLATE.md
```

Fill in:

- `Artifact Intake Classification`
- `Source Document Intake`
- `Impact Analysis`
- `Governance Behavior`
- `Release Decision`
- `Validation Plan`

Use full Source Document Intake only when the artifact is introduced under
`docs/governance/source-documents/` or changes
`model/documents/source-document-register.yaml`.

## Step 4: Add Or Generate The Artifact

Use the owning process:

| Artifact class | Add it how |
|---|---|
| Source document | Add under `docs/governance/source-documents/` and update the source document register |
| Downstream result | Use `scripts/intake_governance_result.py` or a platform-specific intake script |
| CI artifact bundle | Use `scripts/intake_ci_artifact_bundle.py` |
| Generated report or viewer | Run the generator script |
| Schema | Edit schema and matching examples together |
| Documentation | Add the page and update MkDocs navigation or the relevant index |
| Release package | Follow the release and migration model |

Do not hand-edit status indexes when an intake or generator script exists.

## Step 5: Validate

For documentation-only artifact intake, run:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
.venv-docs/bin/mkdocs build --strict
```

For other artifact types, add the relevant extra checks:

| Artifact type | Additional checks |
|---|---|
| Source document | Source lineage and source-document intake reports |
| Candidate replacement | Requirement delta and architecture replacement assessment |
| Evidence bundle | Bundle validation and spot-check process |
| Schema | Schema validation against examples |
| OPA policy | `opa check policies/opa` and relevant policy tests |
| Viewer or status result | Results index and viewer regeneration |
| Release package | Release checklist and package review |

If validation only changes `generated_at` timestamps, revert those timestamp-only
changes unless refreshed generated artifacts are explicitly in scope.

## Step 6: Review The Diff

Before committing, check:

```bash
git status --short
git diff --check
git diff --stat
```

Confirm:

- only intended files changed
- generated files are present only when required
- source documents are registered when applicable
- MkDocs navigation or index files are updated when needed
- the GCR validation checklist is complete

## Step 7: Commit And Push

Use one focused commit.

The commit should include:

- the new artifact
- the GCR
- required index or navigation updates
- required generated artifacts if they are truly in scope
- required validation or example updates

Do not mix unrelated cleanup or generated timestamp noise into the same commit.

## Quick Decision Rule

If you are unsure where an artifact belongs, do not add it yet.

First classify it with:

```text
docs/operations/processes/new-artifact-intake-process.md
```

Then decide whether it belongs to Source Document Intake, Evidence/Result
Intake, Examples, Documentation, Generated Outputs or Release Governance.
