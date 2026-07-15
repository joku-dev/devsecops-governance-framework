# Architecture Findings Reference Run - 2026-07-06

## Purpose

This reference run documents a controlled architecture-governance run that intentionally produces findings.

The existing `ha-CPsWMS` mainline architecture result is green. This run does not change that status.

Instead, it adds a dedicated fixture that demonstrates how Architecture Runtime Governance behaves when release-candidate evidence is incomplete.

## Safety Boundary

This run is safe because it changes only:

```text
policies/example-input.architecture-release-candidate-findings.json
tests/test_architecture_governance_report.py
docs/operations/reference-runs/2026-07-06-architecture-findings-reference-run.md
```

It does not change:

- released architecture baseline packages
- architecture OPA policies
- architecture schemas
- status indexes
- viewer output
- `ha-CPsWMS` mainline status
- report-only versus blocking behavior

## Fixture

Input:

```text
policies/example-input.architecture-release-candidate-findings.json
```

The fixture represents a release candidate with:

- architecture readiness evidence present
- deployment evidence missing
- runtime evidence missing
- feedback evidence missing
- security evidence missing
- release compatibility declaration present but not approved
- selected security and operation markers below required release thresholds
- no approved exceptions

## Command

```bash
tmpdir=$(mktemp -d)

python3 scripts/generate_architecture_governance_report.py \
  --input policies/example-input.architecture-release-candidate-findings.json \
  --output-json "$tmpdir/architecture-governance-report.json" \
  --output-md "$tmpdir/architecture-governance-report.md"
```

## Observed Summary

```text
Generated .../architecture-governance-report.json
Generated .../architecture-governance-report.md
- gates: 4
- findings: 12
```

Gate summary:

```text
Architecture Readiness: PASS, 0 findings
Integration Readiness: FINDINGS, 2 findings
Operation Readiness: FINDINGS, 4 findings
Release Readiness: FINDINGS, 6 findings
```

## Findings

### Integration Readiness

```text
RG-INTEGRATION-READY: Integration readiness requires deployment evidence.
RG-INTEGRATION-READY: Integration-readiness marker S5 requires score 3 or a valid exception; current score is 2.
```

Recommended remediation:

```text
Verify solution security evidence
```

### Operation Readiness

```text
RG-OPERATION-READY: Operation readiness requires feedback evidence.
RG-OPERATION-READY: Operation readiness requires runtime evidence.
RG-OPERATION-READY: Operation-readiness marker B5 requires score 4 or a valid exception; current score is 3.
RG-OPERATION-READY: Operation-readiness marker P11 is missing and has no valid exception.
```

Recommended remediations:

```text
Strengthen architecture feedback loop
Verify observability evidence
```

### Release Readiness

```text
RG-RELEASE-READY: Release candidate requires deployment evidence.
RG-RELEASE-READY: Release candidate requires security evidence.
RG-RELEASE-READY: Release compatibility declaration must be approved.
RG-RELEASE-READY: Release-critical architecture marker E6 requires score 4 or a valid exception; current score is 2.
RG-RELEASE-READY: Release-critical architecture marker P8 requires score 4 or a valid exception; current score is 2.
RG-RELEASE-READY: Release-critical architecture marker S5 requires score 4 or a valid exception; current score is 2.
```

Recommended remediations:

```text
Create release compatibility declaration
Verify enterprise security guardrail evidence
Verify product security implementation
Verify solution security evidence
```

## Interpretation

This run proves the architecture governance path can do more than produce a green demo result.

It can identify missing or insufficient evidence across separate gates:

- integration readiness
- operation readiness
- release readiness

It also proves that remediation actions are attached to matching findings when `architecture/remediation-actions.yaml` contains a matching rule.

## Report-Only Versus Blocking

The fixture does not change enforcement behavior.

If the architecture workflow runs with:

```yaml
fail_on_findings: false
```

then these findings are reported but do not fail the workflow.

If the workflow runs with:

```yaml
fail_on_findings: true
```

then the same findings can fail the workflow during the enforcement step.

The governance model is the same in both modes. Only enforcement behavior changes.

## Validation

The fixture is protected by:

```bash
python3 -m unittest tests/test_architecture_governance_report.py
```

The test verifies:

- 4 gates are evaluated
- 1 gate passes
- 3 gates have findings
- 12 findings are produced
- expected finding text appears in the generated Markdown
- expected remediation text appears in the generated Markdown

## Next Architecture Uses

This fixture can be reused when changing:

- architecture OPA policies
- architecture remediation mappings
- architecture report rendering
- architecture workflow enforcement behavior
- Bamboo architecture governance templates
- Mistral architecture agent prompts
