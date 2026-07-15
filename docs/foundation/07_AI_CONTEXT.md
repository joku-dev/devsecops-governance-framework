# AI Context for Repository Work

## Mandatory Reading

Before proposing or implementing material changes, read:

1. `AGENTS.md`
2. `docs/ai-index.md`
3. `docs/foundation/01_VISION.md`
4. `docs/foundation/02_CONSTITUTION.md`
5. `docs/foundation/03_ARCHITECTURE_PRINCIPLES.md`
6. `docs/foundation/04_REFERENCE_ARCHITECTURE.md`
7. `docs/foundation/05_CURRENT_DIRECTION.md`

## Mental Model

This repository is a technology-agnostic reference implementation of an Engineering Governance Runtime.

## Required AI Behaviour

1. Prefer capability-oriented designs over product-specific designs.
2. Keep core governance models separate from platform adapters.
3. Preserve traceability.
4. Do not automate ambiguous governance decisions.
5. Preserve human accountability.
6. Use released and identifiable baselines.
7. Add schemas, tests, validation, and documentation for new structured artifacts.
8. Avoid uncontrolled refactoring.
9. Do not silently change normative meaning.
10. Record material architectural decisions through ADRs.
11. Keep AI Factory topics out of the current milestone unless explicitly requested.

## Decision Priority

1. Repository operating instructions in `AGENTS.md`
2. Constitution
3. Architecture principles
4. Approved governance documents and released baselines
5. Reference architecture
6. Current direction
7. Implementation convenience

Foundation documents guide architecture and strategy. They do not replace approved policy, directive, standards, released baselines, source-document registers, or recorded governance decisions.
