# GCR-2026-123: Beobachtung des begrenzten semantischen Pilotlaufs

## Entscheidung und Umfang

Der Maintainer genehmigte am 7. Oktober 2026 einen einmaligen manuellen,
report-only Modelllauf über die bestehende ChatGPT-Pro-Anmeldung. Der Scope war
auf `DSCB-STD-REQ-001`, `PRA-STD-REQ-001` und die versionierten synthetischen
Fixtures begrenzt. Die fünf lokalen unregistrierten Dokumente, Secrets,
Consumer-Repositories und alle anderen Repositoryinhalte blieben
ausgeschlossen.

Modelltraining war in den sichtbaren Kontodatenkontrollen deaktiviert. Zero
Data Retention war nicht bestätigt; der Maintainer akzeptierte die geltende
ChatGPT-Aufbewahrung ausdrücklich für diesen begrenzten Lauf.

## Ergebnis

Der tatsächliche Lauf mit `gpt-6-luna` wurde technisch abgeschlossen und
lieferte einen Finding-Kandidaten. Die unveränderte Antwort scheiterte jedoch
an der maßgeblichen Repositoryschemaprüfung, weil
`findings[0].applicability.status` den unzulässigen Wert `context_missing`
enthielt. Es entstand kein validierter Pilotreport und kein Finding für die
menschliche fachliche Bewertung.

Die Rohantwort wurde nicht committed. Nach Erfassung von Größe, SHA-256,
Laufparametern und Validierungsfehler wurde sie entsprechend der Genehmigung
gelöscht. Der vollständige technische Nachweis steht in
`docs/operations/reference-runs/2026-10-07-document-consistency-semantic-pilot.md`.

## Governance-Auswirkung

- Der Validator verhielt sich fail-closed.
- Findings bleiben unbestätigt; es existiert kein angenommener Finding-Datensatz.
- Quellenstatus und Quellenautorität bleiben unverändert.
- Keine Controls, Architekturmarker, OPA-Regeln, Releases oder Baselines ändern sich.
- Keine Veröffentlichung und keine Consumer-Auswirkung.
- Die Rolloutentscheidung bleibt `pending`.
- Ein weiterer Providerlauf benötigt eine neue ausdrückliche Freigabe.

## Folgearbeit

Vor einem weiteren Live-Lauf sind ein providerkompatibles Projektionsschema,
ein normalisierender Adapter, eine immutable aktive Laufkonfiguration und
Regressionstests für Enum-Verwechslungen erforderlich. Diese Folgearbeit darf
providerneutral vorbereitet werden; dieser GCR autorisiert keinen weiteren
Modellaufruf.
