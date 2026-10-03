# GCR-2026-109: Bind ha-CPsWMS evidence to its same-commit baseline run

The first fresh intake after GCR-2026-108 verified artifact identity, commit,
custody and replay, but did not promote the evidence. GitHub reports no
`referenced_workflows` for the local `L1 Measured Evidence` workflow. The
producer report declares `l1-baseline-v1.1.3`, while the successful
`DevSecOps Baseline` workflow is a separate push run for the same protected
main commit and carries the tagged reusable-workflow reference and immutable
workflow SHA.

This change permits that independently reported baseline run to supply the
baseline provenance only when the pairing is unambiguous and all of these
conditions hold: same repository, exact producer commit, `push` event, `main`
branch, completed successful conclusion, and the expected baseline workflow
path. The report's baseline must still match exactly one pinned
`devsecops-baseline-l1-*` entry with a tagged reference and 40-character
workflow SHA. Missing or ambiguous run metadata, a failed or manual run, or any
repository, branch, event, commit, or baseline mismatch fails the existing
report-only Trust check. When the producer run itself contains the pinned
reference, that same-run evidence remains preferred.

| Classification | Decision |
|---|---|
| Governance intent | Normative Evidence Trust provenance resolution for the fixed ha-CPsWMS container profile |
| Source-document intake | None: refine application of the active report-only Evidence Trust model |
| Affected artifacts | Central typed-evidence intake, verifier tests, Trust observations, evidence-trust documentation |
| Contract impact | Additive paired baseline run identity in observations; no snapshot fields are removed |
| Release impact | No released baseline, package, or tag changes |
| Enforcement | Report-only; no workflow gate or policy enforcement changes |
| Scope | `joku-dev/ha-CPsWMS` five-image vulnerability and SBOM evidence |
| Limits | Does not establish producer attestation, compliance, risk acceptance, deployment approval, or release approval |
| Historical data | Existing snapshots remain unchanged; only newly captured evidence uses the paired-run rule |
| Validation | Focused negative and positive tests, full pinned repository validation, then a fresh mainline consumer run and central intake |

The same-commit pairing follows the repository's existing workflow topology:
the measured-evidence workflow creates the five image archives, while the
separate baseline workflow evaluates the released DevSecOps baseline. The
verifier requires both successful runs to refer to the exact same protected
main commit; it does not infer provenance from a baseline name in the report
alone.
