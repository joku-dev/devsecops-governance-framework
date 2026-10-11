# GCR-2026-145: DSCB first-wave requirement approval

## Decision

The governance owner approved the 46 control requirements extracted from `DSCB-STD-REQ-001` for canonical activation on 9 October 2026.

The approved source range is:

- `DSCB-STD-SRC-001-REQ-010` through `DSCB-STD-SRC-001-REQ-025` for the 16 L1 controls;
- `DSCB-STD-SRC-001-REQ-026` through `DSCB-STD-SRC-001-REQ-039` for the 14 L2 controls;
- `DSCB-STD-SRC-001-REQ-040` through `DSCB-STD-SRC-001-REQ-050` for the 11 L3 controls;
- `DSCB-STD-SRC-001-REQ-051` through `DSCB-STD-SRC-001-REQ-055` for the five governance controls.

Each source requirement is classified as `new` because the canonical catalog contained no active `GRQ-*` requirements before this decision. The activated revisions authorize derivation of controls. For the 14 requirements with an existing explicit OPA rule, the revision also authorizes policy derivation.

## Separate artifact decision

This approval activates the canonical requirements. It does not by itself confirm semantic equivalence of an existing control or OPA rule. Those adoptions require separate effective entries in `model/requirements/requirement-to-artifact-register.yaml`.

## Runtime effect

The activation records `runtime_enforcement: none`. It does not modify OPA code, consumer enforcement, report-only settings, blocking behavior, or released baseline packages.
