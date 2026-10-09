# Dokumentationsabgleich nach Merge

Auslöser: PR #244: feat(intake): register source candidates and remove public placeholders (`430550f00aa9`)

## Ergebnis

- Lokale Markdown-Linkprüfung: 1 fehlende lokale Markdown-Zielpfade.
- `mkdocs build --strict`: passed.
- Der PR-Inhalt stammt aus der PR-Zusammenfassung und den geänderten Pfaden; fachliche Bedeutung und Querverweise benötigen menschliche Prüfung.

## Betroffene Implementierungspfade

- `architecture/arch-gov.yaml`
- `architecture/arch-l1.yaml`
- `architecture/arch-l2.yaml`
- `architecture/arch-l3.yaml`
- `architecture/guardrails.yaml`
- `architecture/quality-markers.yaml`
- `architecture/remediation-actions.yaml`
- `architecture/review-gates.yaml`
- `model/controls/governance-repository-security.yaml`
- `model/documents/governance-documents.yaml`
- `model/documents/source-document-register.yaml`
- `model/evidence/evidence-collector-contract.yaml`
- `model/evidence/evidence-freshness-policies.yaml`
- `model/evidence/evidence-trust-model.yaml`
- `scripts/generate_architecture_source_replacement_assessment.py`
- `scripts/generate_source_document_intake_status.py`
- `scripts/generate_source_document_requirement_delta.py`
- `scripts/generate_source_lineage_report.py`

## Fehlende lokale Markdown-Ziele

- `README.md` → `/picture`

## Redaktionelle Prüfpunkte

- README-Einstieg und Funktionsumfang aktualisieren.
- Funktion fachlich im Katalog dem passenden Bereich zuordnen und Eingaben, Ablauf, Ergebnisse sowie Grenzen beschreiben.
- Technische Inventareinträge und Navigations-/Querverweise ergänzen.
- Prüfen, ob Foundation, Governance-, Demo-, Release- oder Consumer-Dokumentation betroffen ist.
