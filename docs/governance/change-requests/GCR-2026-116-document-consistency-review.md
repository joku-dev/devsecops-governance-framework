# GCR-2026-116: Phase 0 — Inventar und Design für Document Consistency Review

## Anfrage und Einordnung

Phase 0 des Workpackages WP-DCR-001 abschließen. Die Entscheidung umfasst
Quelleninventar, Register-/Datei-Snapshot, Quellenumfang, Review-Routing und die
Grenzen für Vertraulichkeit, semantische Verarbeitung und Viewer. Technische
Implementierung wird separat als Phase 1 vorgelegt.

| Feld | Wert |
|---|---|
| Artefakte | WP-DCR-001, ADR-DCR-001 und Phase-0-Quellenmanifest |
| Artefakttyp | Planung, dokumentierte menschliche Scope-Entscheidung, Metadaten-/Hash-Snapshot |
| Repository-Basis der Entscheidung | `a8fc36f3de7f33cd2a26dff94f9a28985e78d64f` |
| Aktuelle Quellenidentitätsprüfung | `f7e0304421b20e2a5df1d138d84ec14bae88489c`; Register- und Quellhashes der zwei Pilotquellen unverändert |
| Angenommener Pilotumfang | `DSCB-STD-REQ-001`, `PRA-STD-REQ-001`, synthetische Fixtures |
| Quellpromotion oder Derivation | Keine |
| Semantischer Review / Provider | Aufgeschoben; kein Aufruf |
| Viewer / Veröffentlichung | Aufgeschoben; keine Änderung |
| Release- oder Baseline-Auswirkung | Keine |
| Entscheidung | Phase 0 durch ausdrückliche Maintainer-Erklärung am 2026-10-07 angenommen |

## Festgehaltene Entscheidungen

- `model/documents/source-document-register.yaml` bleibt das einzige
  Quellenregister.
- Das Manifest enthält nur die zwei freigegebenen Pilot-IDs, Metadaten und
  SHA-256-Dateihashes zum aktuellen main-Commit `f7e0304421b20e2a5df1d138d84ec14bae88489c`. Ein erneuter Vergleich bestätigte, dass Register und
  zwei Pilotquellen seit der angenommenen Entscheidungsbasis unverändert sind.
  Es enthält keine Quelltextauszüge.
- Fünf zusätzlich bereitgestellte Dateien bleiben unregistriert, lokal und
  außerhalb des Piloten. Sie erscheinen weder im Manifest noch in den
  öffentlichen Phase-0-Artefakten mit Dateinamen oder Inhalten.
- Owner-Angaben sind Review-Routing und bestätigen keine Quellenautorität.
- Phase 1 wird als eigener Änderungssatz mit Schema, Generator,
  deterministischen Prüfungen und Tests vorgelegt.
- Semantischer Review und Viewer bleiben aufgeschoben. Weitere Phasen erfordern
  ihre jeweiligen Scope- und Freigabeentscheidungen.

## Auswirkung und Grenzen

| Bereich | Auswirkung |
|---|---|
| Quellenregister | Unverändert; keine neuen Quellen oder Statusänderungen |
| Controls, Architektur, OPA und Baselines | Keine Änderungen oder Derivation |
| Workflow und Enforcement | Keine Änderungen |
| Ergebnis-/Evidence-Verträge | Keine Änderungen |
| Viewer und Statusindizes | Keine Änderungen |
| Vertraulichkeit | Nur registrierte Metadaten und Hashes im Manifest; lokale Zusatzdateien ausgeschlossen |

Die Annahme bestätigt nur die Planung und den begrenzten Phase-0-Umfang. Sie
bestätigt keine Autorität oder Veröffentlichung der lokalen Dateien und keine
semantische Konsistenz, Compliance oder Implementierungsabdeckung.

## Abnahmebeleg

Der Maintainer erklärte am 2026-10-07 ausdrücklich die Annahme von Phase 0 mit
dem oben angegebenen Repository-Stand und Pilotumfang. Diese Textfassung hält
die Entscheidung fest; sie ist selbst kein Commit, Merge oder Release.
