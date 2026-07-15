# Current Design Direction

## Current Position

The repository originally focused on DevSecOps Governance as Code.

Its current direction is broader:

> A technology-agnostic reference implementation of an Engineering Governance Runtime for continuously trustworthy software engineering.

## Current Narrative

```text
Engineering
    ↓
Software Industrialisation
    ↓
DevSecOps
    ↓
Continuous Security
    ↓
Continuous Compliance
    ↓
Executable Engineering Governance
    ↓
Trust
```

## Current Scope

- DevSecOps governance
- Security controls
- Secure software supply-chain evidence
- Policy and control evaluation
- Evidence contracts
- Architecture runtime governance
- Versioned governance baselines
- Application repository integration
- Result intake
- Traceability
- Governance reporting
- Multi-platform adapter patterns

## Explicit Non-Goal

The AI Factory is intentionally out of scope for the current milestone.

## Technology Position

The repository is not a GitHub architecture, an OPA product, a Jenkins solution, a GitLab-only baseline, or a vendor-specific DevSecOps platform.

GitHub Actions and OPA are current reference implementations for selected capabilities.

## Repository Position

The repository implements the executable governance layer of the engineering lifecycle. It does not implement the complete software development process.

## Key Decisions

1. Use structured governance data as controlled machine-readable sources where feasible.
2. Retain Word and PDF as important review and audit outputs.
3. Automate only objectively verifiable requirements.
4. Preserve human governance authority.
5. Separate reusable governance logic from application-owned evidence.
6. Use versioned release baselines.
7. Keep adapters additive and replaceable.
8. Maintain source-to-result traceability.
9. Treat governance artifacts as engineering assets.
10. Use report-only adoption before broad enforcement.
