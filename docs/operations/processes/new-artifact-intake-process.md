# New Artifact Intake Process

## Purpose

This process defines how new artifacts are introduced into the DevSecOps
governance repository without bypassing source-document intake, evidence
contracts, release governance or documentation structure rules.

It is the first classification step before a new file is added, moved, derived
or consumed by automation.

The process is intentionally report-only. It does not approve source documents,
enable stricter gates, change schemas, update releases or promote runtime
governance behavior by itself.

## When To Use This Process

Use this process whenever a new artifact enters the repository or an existing
artifact is moved into a new governed area.

Examples:

- upstream source documents
- ADO architecture documents
- policy or directive material
- machine-readable evidence examples
- downstream pipeline result snapshots
- CI/CD adapter artifacts
- generated reports or viewer outputs
- new schemas, OPA policies, model files or release package content
- publishing, guide, process, architecture or onboarding documentation

## Intake Principle

Every new artifact must be classified before it is used.

Classification answers:

- Is this artifact authoritative source material?
- Is it runtime evidence from a downstream repository?
- Is it an example, documentation page, generated output or release artifact?
- Which folder owns it?
- Which validation proves it is safe?
- Does it change governance behavior, downstream contracts or baseline
  releases?

## Artifact Classification Matrix

| Artifact type | Target location | Required process | Typical validation |
|---|---|---|---|
| Authoritative governance source | `docs/governance/source-documents/` | Full Source Document Intake and register update | Source lineage, intake status, repo validation |
| Candidate source or possible replacement | `docs/governance/source-documents/` | Candidate registration, similarity and replacement review | Intake review briefs, requirement delta, architecture replacement assessment |
| Downstream governance result snapshot | `status/results/` | Result intake script and viewer regeneration | Results index, viewer, repo validation |
| Pipeline evidence bundle | Application run artifact or intake bundle | Evidence/result intake, not source-document intake | Bundle validation, intake script, spot check |
| Evidence contract example | `docs/examples/` | Example update plus schema validation | Schema validation and repo validation |
| Evidence schema or contract | `schemas/`, `docs/operations/evidence/`, `model/evidence/` | Evidence contract review | Schema validation, examples, tests |
| OPA policy or executable governance logic | `policies/opa/`, scripts, workflows | Governance behavior review | OPA check, tests, repo validation |
| Architecture governance model | `architecture/` | Architecture governance review | Runtime governance validation |
| CI/CD adapter guidance or templates | `docs/operations/adapters/`, `pipeline-baseline/templates/` | Adapter review | Platform-specific examples and repo validation |
| Practical operations guide | `docs/operations/guides/` | Documentation-only guide review | MkDocs strict build |
| Governance operation process | `docs/operations/processes/` | Process documentation review | MkDocs strict build and repo validation |
| Publishing communication artifact | `docs/publishing/` | Publishing documentation review | MkDocs strict build |
| Generated report or viewer artifact | `generated/` | Script-generated only | Generator plus validation |
| Release package content | `releases/`, `docs/releases/` | Explicit release decision | Release validation and baseline review |

## Intake Decision Steps

1. Identify the artifact owner and intended use.
2. Classify the artifact using the matrix above.
3. Choose the target path before adding or moving the file.
4. Create or update a governance change request.
5. Record whether full Source Document Intake is required.
6. Record whether the artifact changes evidence contracts, runtime governance,
   schemas, viewer behavior, release packages or downstream migration needs.
7. Run the validation commands required for the chosen classification.
8. Commit only the intended artifact and its required index, navigation,
   generated or validation updates.

## Source Document Boundary

An artifact becomes source material only when it is intentionally introduced
under `docs/governance/source-documents/` or registered in
`model/documents/source-document-register.yaml`.

If the artifact may define policy, directive, architecture guardrails,
controls, mandatory evidence, baseline requirements or review gates, use the
full Source Document Intake process:

```text
docs/operations/processes/source-document-intake-process.md
docs/operations/processes/source-document-intake-review-operating-model.md
model/documents/source-document-register.yaml
```

Do not derive controls, architecture markers, policies, schemas or baseline
release content from an unreviewed candidate source.

## Evidence And Result Boundary

Runtime evidence from downstream repositories is not a source document.

Use the evidence and result intake flow when the artifact is a pipeline output,
control evaluation result, architecture result, governance run input or
downloaded CI artifact bundle:

```text
docs/operations/evidence/governance-evidence-contract.md
docs/operations/evidence/governance-result-intake-and-viewer-usage.md
docs/operations/processes/spot-check-governance-intake.md
```

Use scripts instead of hand-editing status indexes:

```bash
python3 scripts/intake_governance_result.py
python3 scripts/intake_github_actions_run.py
python3 scripts/intake_ci_artifact_bundle.py
python3 scripts/generate_repository_results_index.py
python3 scripts/generate_status_viewer.py
```

## Documentation Boundary

Documentation artifacts should enter the folder that matches their purpose:

| Purpose | Folder |
|---|---|
| Official entrypoint | `docs/` root |
| Governance architecture explanation | `docs/governance/architecture/` |
| Practical operation guide | `docs/operations/guides/` |
| Governance process description | `docs/operations/processes/` |
| Evidence operation guidance | `docs/operations/evidence/` |
| Platform adapter guidance | `docs/operations/adapters/` |
| Agent operation guidance | `docs/operations/agents/` |
| Publishing or Confluence article | `docs/publishing/` |
| Schema-backed example | `docs/examples/` |
| Demo or walkthrough | `docs/demos/` |
| Release documentation | `docs/releases/` |

Avoid adding new documents directly under `docs/operations/` unless they are
temporary and a follow-up structure decision is recorded.

## Generated Artifact Boundary

Generated artifacts should be produced by scripts whenever possible.

Do not hand-edit these areas unless the repository instructions explicitly
allow a narrow metadata cleanup:

```text
generated/
status/
releases/
```

If validation only changes `generated_at` fields, revert those timestamp-only
changes before committing unless the task explicitly requires refreshed
generated outputs.

## Change Request Fields

Every artifact intake change request should include an artifact classification
record:

| Field | Value |
|---|---|
| Artifact name |  |
| Artifact type | source/evidence/example/schema/policy/model/workflow/documentation/generated/release |
| Target path |  |
| Owner |  |
| Source Document Intake required? | yes/no |
| Evidence contract impact | none/additive/breaking |
| Runtime governance impact | none/report-only/blocking |
| Release impact | none/patch/minor/major |
| Validation required |  |

## Validation Baseline

For documentation-only artifact intake:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
.venv-docs/bin/mkdocs build --strict
```

For source, schema, policy, evidence, generated result or release artifacts,
add the specific validators or generator scripts named by the owning process.

## Non-Goals

- no automatic source-document promotion
- no automatic release creation
- no new blocking behavior
- no uncontrolled artifact drop zone
- no manual edits to generated status indexes when an intake script exists
