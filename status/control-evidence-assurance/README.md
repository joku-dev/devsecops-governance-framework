# Control Evidence Assurance

This append-only store links every measured L1 assessment to a conservative
evidence-quality statement for all 16 controls. Each control records coverage,
effective Trust, content integrity, provenance, Freshness, replay, custody,
attestation, decision context and subject binding for its required evidence
groups.

Missing required evidence keeps the aggregate control Trust at `unverified`,
even when another group such as an SBOM or vulnerability scan is
`integrity_verified`. Assurance is report-only and does not change the control
result, released baseline, blocking mode, production approval or risk decision.
