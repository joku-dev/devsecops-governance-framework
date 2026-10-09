# OPA-DSCB-2026-001: Requirement-to-Policy Equivalence Review

## Decision brief

This review compares the 14 proposed OPA links with the exact active canonical requirement revisions. It authorizes no runtime or enforcement change and creates no effective artifact-register entry.

| Result | Count | Proposed decision |
|---|---:|---|
| Equivalent | 8 | Approve existing-policy adoption |
| Partial | 4 | Remediate before adoption |
| Not equivalent | 2 | Reject current mapping or correct the requirement first |

## Recommended approvals

| Requirement | Control | Policy | Assessment | Reason |
|---|---|---|---|---|
| `GRQ-000003@rev1` | `DSCB-L1-REQ-003` | `branch_protection.rego` | equivalent | Denies direct pushes to protected branches and also requires review. |
| `GRQ-000006@rev1` | `DSCB-L1-REQ-006` | `sbom_required.rego` | equivalent | Requires an SBOM for release candidates and links it to the artifact. |
| `GRQ-000020@rev1` | `DSCB-L2-REQ-004` | `access_control.rego` | equivalent | Denies privileged access without MFA. |
| `GRQ-000022@rev1` | `DSCB-L2-REQ-006` | `dependency_source_control.rego` | equivalent | Denies detected direct downloads from external sources. |
| `GRQ-000023@rev1` | `DSCB-L2-REQ-007` | `artifact_signing.rego` | equivalent | Requires signatures for PRA-Level 2 release candidates. |
| `GRQ-000025@rev1` | `DSCB-L2-REQ-009` | `iac_required.rego` | equivalent | Requires an IaC repository where deployment is required. |
| `GRQ-000026@rev1` | `DSCB-L2-REQ-010` | `iac_required.rego` | equivalent | Requires the IaC repository to be version controlled. |
| `GRQ-000027@rev1` | `DSCB-L2-REQ-011` | `pipeline_security_gates.rego` | equivalent | Requires enforced security gates for release candidates. |

Approval of these eight mappings would create eight adoption entries in the requirement-to-artifact register. The entries would pin the exact GRQ revision and current Rego SHA-256. They would record `enforcement: none`, matching the current GRQ revisions, and would not change current consumer behavior.

## Remediation before adoption

| Requirement | Policy | Missing coverage |
|---|---|---|
| `GRQ-000009@rev1` | `vulnerability_gate.rego` | Evidence existence does not prove execution during build or test and does not validate evidence provenance or freshness. |
| `GRQ-000010@rev1` | `vulnerability_gate.rego` | Only critical vulnerabilities are evaluated; the requirement covers every identified vulnerability. |
| `GRQ-000011@rev1` | `artifact_integrity.rego` | Approved repository controls and validation/linkage of a present signature are not checked. |
| `GRQ-000028@rev1` | `pipeline_security_gates.rego` | Waiver existence is checked, but approval, scope, and expiry are not validated by this policy. |

These mappings must not receive an effective register entry with `equivalence: equivalent` in their current state.

## Reject or correct

### `GRQ-000044@rev1` / `DSCB-GOV-REQ-003`

The requirement says that non-compliance requires an approved waiver. `waiver_validity.rego` only validates records already marked approved. It receives no non-compliance record and cannot detect a missing waiver or validate the required non-compliance-to-waiver link. The current mapping is not equivalent.

### `GRQ-000046@rev1` / `DSCB-GOV-REQ-005`

The active canonical statement is incomplete: `[DSCB-GOV-REQ-005]All deviations SHALL:`. A semantic equivalence decision is impossible until the complete normative list is restored through a new requirement revision. The current policy also evaluates only records already marked approved.

## Test evidence

- OPA syntax validation passes with OPA 1.18.2.
- The complete repository suite passed 764 regression tests before this review.
- A direct positive-path test exists for `branch_protection.rego`.
- No dedicated positive-and-negative unit-test pair was found for the other nine reviewed policy files.

Before any remediation is adopted, each policy should receive representative allow and deny tests for every mapped GRQ predicate. Test coverage alone does not establish semantic equivalence; it verifies the reviewed behavior after the expected predicate is agreed.

## Hashes

| Policy | SHA-256 |
|---|---|
| `branch_protection.rego` | `220789bb1ccce8ac9dd0a1fa51501ce9cd82085052f34754b6b96557d9172c04` |
| `sbom_required.rego` | `b5c2865d9fc3a99b799898f01ac81e3abb5176fdcae3a2860733634412faa484` |
| `vulnerability_gate.rego` | `f25504187acd7b8cfe6c3632bcfc4d13edc5d6d6824e551278a39f3915e3a809` |
| `artifact_integrity.rego` | `36052a619e7c3b8a4e60f32ff6f039776dad3bed35f45e3613b9586e6cdeea50` |
| `access_control.rego` | `ddca4015919b0ca3115d2d7a6510947398a68fb13215094eec5784be8420da38` |
| `dependency_source_control.rego` | `2371c0d9ea978659399c5210550b6a142d3736b4149274082aacfec4f79ef201` |
| `artifact_signing.rego` | `1c0d59a4587d9ed21f81f1b27318de66b24db55b30f4cfaa20cb52b85ab3013c` |
| `iac_required.rego` | `fbed44d90463e190da05083d0652f048efa124ae10fbd333cedb82ea91f0ee15` |
| `pipeline_security_gates.rego` | `b28553b35fff00ec527e6e099395cf9011a295da6e2effd8ea256414f1db5b43` |
| `waiver_validity.rego` | `ac0a8fe0982a9b97bf845a6e21673b9482776ea467d0e2c310fa494e56b7ace5` |

## Human decision requested

The recommended decision is:

1. approve the eight equivalent mappings listed above;
2. withhold adoption of the four partial mappings pending remediation;
3. reject the `GRQ-000044@rev1` mapping in its current form;
4. correct `GRQ-000046` through a new revision before reviewing any OPA mapping.
