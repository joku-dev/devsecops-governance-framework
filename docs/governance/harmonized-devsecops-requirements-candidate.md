# Harmonized DevSecOps Requirements Candidate

## Purpose

The candidate model converts a private standards-requirements workbook into a
public-neutral review model without publishing source requirement text or
Office metadata.

The authoritative candidate artifacts are:

- `model/requirements/harmonized-devsecops-requirements.yaml`
- `model/traceability/standards-to-harmonized-requirements.yaml`
- `model/traceability/harmonized-requirements-to-maturity-levels.yaml`
- `generated/reports/harmonized-requirements-coverage.json`
- `generated/reports/harmonized-requirements-coverage.md`
- `generated/reports/harmonized-requirements-maturity.json`
- `generated/reports/harmonized-requirements-maturity.md`

## Model Boundary

The model is deliberately:

```text
status: candidate
normative: false
enforcement: none
derivation_policy: review_only
```

It does not change existing controls, architecture markers, OPA behavior,
evidence contracts, workflows, released baselines, or consumer compliance
status.

## Harmonization Method

The import process:

1. reads only visible workbook cell values needed for analysis;
2. normalizes eleven source labels to public-neutral identifiers;
3. collapses identical source descriptions while retaining every distinct
   standard requirement reference and occurrence count;
4. assigns missing identifiers to neutral `UNASSIGNED-*` review identifiers;
5. maps each unique source requirement to one or more paraphrased harmonized
   requirements;
6. publishes source identifiers and mappings, but no source requirement text;
7. marks every mapping `human_review_required`;
8. calculates preliminary design coverage without making an operational
   compliance claim.

The committed mapping records 264 raw rows, 233 unique source requirements, 29
duplicate identifier pairs, and 10 missing source identifiers. All 233 unique
source requirements have a candidate mapping.

## Coverage Interpretation

`covered` means an existing control or architecture marker substantially
addresses the harmonized intent. `partial` means related governance exists but
detail or evidence is missing. `gap` means no adequate current requirement was
identified.

The weighted design-coverage percentage counts `covered` as 1.0, `partial` as
0.5, and `gap` as 0.0. It is decision support only and must not be presented as
audited or operational compliance.

## Candidate Maturity Assignment

Every harmonized requirement has a proposed minimum maturity level. The model
is cumulative: L1 requirements remain active at L2 and L3, and L2 requirements
remain active at L3. GOV is a separate cross-level overlay for lifecycle,
applicability, roles, and controlled documentation.

| Minimum level | Candidate requirements | Cumulative active |
|---|---:|---:|
| `L1` | 22 | 22 |
| `L2` | 17 | 39 |
| `L3` | 1 | 40 |
| `GOV` | 4 | 4 |

Maturity does not replace applicability. Risk-based, capability-based, and
product-context conditions are evaluated independently. All 44 assignments are
`human_review_required` and do not modify the released L1, L2, L3, or GOV
control models.

## Public Hygiene

The private workbook is not committed. Public outputs contain no workbook
properties, embedded table definitions, authors, company fields, or source
requirement text.

Run the generic hygiene scanner with locally supplied forbidden terms:

```bash
PUBLIC_ARTIFACT_FORBIDDEN_TERMS="private-term-1,private-term-2" \
python3 scripts/check_public_artifact_hygiene.py \
  model/requirements/harmonized-devsecops-requirements.yaml \
  model/traceability/standards-to-harmonized-requirements.yaml \
  generated/reports/harmonized-requirements-coverage.json \
  generated/reports/harmonized-requirements-coverage.md
```

The scanner also opens Office ZIP containers when Office files are explicitly
included in the scan, so hidden XML metadata is checked as well as visible
cell text.

## Required Human Decisions

- CISO/Governance Owner: authority, enterprise strength, and applicability
- DevSecOps Baseline Owner: proposed minimum maturity levels, control-baseline
  mapping, and gaps
- Enterprise Architect: architecture and product-security routing
- Platform Owner: platform capability implications
- Legal or License Compliance: retained standard identifiers and publication
  rights
- Release Manager: no release, release candidate, or future minor baseline

Only an approved governance change request may authorize promotion or
derivation into runtime governance.
