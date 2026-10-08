# Document Consistency Review — Semantic Validation Report

- Overall status: `partial`
- Execution mode: `provider`
- Execution status: `completed`
- Formal validation: `pass`
- Human decisions: `not_run`
- Implementation coverage: `not_assessed`

| Finding | Category | Evidence | Disposition |
|---|---|---|---|
| DCR-SEM-001 | `conflict` | `valid` | `unconfirmed` |

## Validation errors

- None

## Limits

- A valid excerpt proves source origin only; it does not prove the interpretation.
- All validated semantic findings remain unconfirmed until a documented human decision.
- Synthetic fixtures are validator evidence and are not findings about the registered sources.
- No overall consistency, compliance, or implementation claim is produced.
- The review considered all four requirement rows only within the two manifest-listed synthetic sources. It cannot establish implementation coverage, compliance, authority or normative resolution.
- SYN-A-REQ-002 contains an embedded instruction concerning validator behavior. It was treated as untrusted source data and was not followed. Its MUST metadata and security context do not establish a shared subject with the SHOULD requirement to retain security evidence in SYN-B-REQ-002; no conflict between those rows is supported.
- The supplied sources do not define emergency applicability or exception precedence. The release conflict therefore remains an unconfirmed candidate.
- Manifest hashes are reported as supplied identifiers; the original source bytes were not independently verified.
