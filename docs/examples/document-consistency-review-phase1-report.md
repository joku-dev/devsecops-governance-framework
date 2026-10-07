# Document Consistency Review — Structural Report

- Overall structural status: `partial`
- Semantic review: `not_run`
- Reviewed commit: `3be081f9e424d3ad5c298a27e4a4a75a544609c2`
- Sources: DSCB-STD-REQ-001, PRA-STD-REQ-001

| Rule | Status | Details |
|---|---|---|
| DCR-001 | `pass` | — |
| DCR-002 | `pass` | — |
| DCR-003 | `not_in_scope` | model contains no role references |
| DCR-004 | `pass` | 102 mandatory requirement(s) have an explicit scope gap for owner/verification mapping. |
| DCR-005 | `not_in_scope` | no structured gate records supplied |
| DCR-006 | `not_in_scope` | no structured evidence links supplied |
| DCR-007 | `pass` | — |
| DCR-008 | `not_in_scope` | no topic-authority map supplied |
| DCR-009 | `pass` | repository HEAD is newer than the recorded source snapshot; freshness is checked against register and source bytes |

## Limits

- Structural checks do not prove semantic consistency, completeness, implementation, or compliance.
- not_in_scope rules remain open for a later structured governance model.
- Owner metadata is review routing and does not confirm source authority.
