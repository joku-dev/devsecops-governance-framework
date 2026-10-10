# GCR-2026-146: DSCB OPA adoption decision

## Decision

The governance owner accepted the recommendation in `OPA-DSCB-2026-001` on 9 October 2026.

### Approved existing-policy adoptions

- `GRQ-000003@rev1` → `policies/opa/branch_protection.rego`
- `GRQ-000006@rev1` → `policies/opa/sbom_required.rego`
- `GRQ-000020@rev1` → `policies/opa/access_control.rego`
- `GRQ-000022@rev1` → `policies/opa/dependency_source_control.rego`
- `GRQ-000023@rev1` → `policies/opa/artifact_signing.rego`
- `GRQ-000025@rev1` → `policies/opa/iac_required.rego`
- `GRQ-000026@rev1` → `policies/opa/iac_required.rego`
- `GRQ-000027@rev1` → `policies/opa/pipeline_security_gates.rego`

### Withheld pending remediation

- `GRQ-000009@rev1`
- `GRQ-000010@rev1`
- `GRQ-000011@rev1`
- `GRQ-000028@rev1`

### Rejected or correction required

- The proposed `GRQ-000044@rev1` mapping is rejected because the policy cannot detect non-compliance without a waiver.
- `GRQ-000046@rev1` requires a new, complete requirement revision before an OPA adoption can be reviewed.

## Runtime effect

This decision adopts existing artifacts for traceability. It authorizes no OPA source change, new blocking behavior, enforcement-mode change, or released-baseline change.
