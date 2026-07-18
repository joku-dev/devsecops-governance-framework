# Security Policy

## Reporting A Vulnerability

Do not disclose suspected credentials, workflow bypasses, policy manipulation,
release-integrity problems, or other security vulnerabilities in a public
issue.

Use the repository's private vulnerability reporting channel:

```text
https://github.com/joku-dev/devsecops-governance-framework/security/advisories/new
```

Include the affected path or release, reproduction information, likely impact,
and any evidence needed to validate the report. Avoid including live secrets;
revoke or rotate exposed credentials before sharing diagnostic material.

## Security-Sensitive Areas

Changes to the following areas can affect every downstream consumer and require
governance-owner review:

- `.github/workflows/`
- `model/controls/`, `model/evidence/`, `model/platform/`, and `model/traceability/`
- `policies/opa/`
- `schemas/`
- `scripts/`
- `releases/`
- release tags and reusable workflow references

## Supported Versions

The current supported public baselines are:

- DevSecOps L1: `l1-baseline-v1.1.3`
- Architecture L1: `architecture-baseline-l1-v0.1.0`

Historical packages remain available for audit and migration but do not receive
new security behavior unless a dedicated maintenance decision is recorded.
