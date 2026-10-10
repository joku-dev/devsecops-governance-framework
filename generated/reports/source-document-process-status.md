# Source Document Process Status

- Authorized-source baseline readiness: `blocked`
- Registered sources: `15`
- Authorized sources: `6`
- Confirmed source-author IDs (P1): `0`
- Unverified extraction row IDs in approved sources: `867`
- Unverified extraction row IDs across all registered sources: `2138`
- Inferred candidates (P2): `237`

## Process Phases

| Phase | Status | Counts | Next action |
|---|---|---|---|
| Source Documents aufnehmen und registrieren | `complete` | registered: 15, approved: 6, missing_files: 0, unregistered_files: 0 | Eingaben sind registriert; Quellenstatus separat prüfen. |
| Dokumente extrahieren und Anforderungen klassifizieren | `partial` | scanned: 14, withheld: 1, extraction_blocked: 0 | Extraktionslücken oder zurückgehaltene Quellen bearbeiten. |
| P1: gekennzeichnete Anforderungen und Status prüfen | `blocked` | confirmed_author_ids: 0, unverified_extraction_ids: 867, decided: 84, undecided: 783, activated: 54 | Kennungsherkunft belegen und offene Requirement-Entscheidungen bearbeiten. |
| P2: Inferred Candidates prüfen | `review_required` | inferred_candidates: 237 | Kandidaten gegen die Quelldokumente und P1-Anforderungen prüfen. |
| Quellen auf Widersprüche und Konsistenz prüfen | `partial` | review_scope_sources: 10, proposed_or_unresolved_findings: 3, semantically_assessed_requirements: None | Vollständigen, frischen Review über exakt die autorisierte Quellenmenge durchführen. |
| Entscheidungsvorlagen bearbeiten | `decision_required` | consistency_findings_open: 3, requirements_undecided: 783 | Befunde und Requirement-Vorschläge durch die zuständigen Rollen entscheiden lassen. |
| Widerspruchsfreie Quellenbaseline freigeben | `blocked` | authorized_sources: 6, blocking_reasons: 5 | requirement identifier origin remains unverified for extracted row IDs |
| Freigegebene Anforderungen auf Governance-Artefakte abbilden | `in_progress` | effective_requirement_artifact_links: 19, all_links: 19 | Nur durch menschliche Entscheidung autorisierte Anforderungen in Controls, Plattformmodelle und OPA ableiten. |

## Baseline Blocking Reasons

- requirement identifier origin remains unverified for extracted row IDs
- approved-source requirement lifecycle decisions remain open
- Document Consistency Review scope does not expose an exact approved-source set
- semantic consistency review is not exhaustive for the approved source set
- proposed or unresolved consistency findings remain

## Limits

- This report joins existing governed records and does not make human source, requirement, conflict or release decisions.
- A report-only consistency result is not proof that no semantic contradiction exists.
- The authorized-source baseline remains blocked until source provenance, requirement lifecycle, exhaustive consistency review and human decision conditions are met.
