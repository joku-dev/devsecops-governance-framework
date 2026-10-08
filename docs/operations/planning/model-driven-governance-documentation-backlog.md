# WP-MDG-001 — Model-driven Governance Documentation Backlog

Status: **`deferred`**  
Abhängigkeit: formaler Abschluss von `WP-DCR-001`  
Startfreigabe: separat erforderlich

## Ziel

Governance-Modelle sollen künftig reproduzierbare, nachvollziehbare und klar
als abgeleitet gekennzeichnete Dokumente erzeugen können. Der erste geeignete
Pilot ist ein Markdown-Katalog aus bestehenden DevSecOps-Control-Modellen.

## Vorgesehener Mindestumfang

- deterministische Model-to-Markdown-Generierung;
- stabile Reihenfolge, IDs und Verweise;
- Eingabepfade, Git-Revision und SHA-256-Provenance;
- Kennzeichnung als `derived` oder `generated-report`;
- CI-Driftprüfung zwischen Modell und eingecheckter Ausgabe;
- Schutz vor manueller Änderung generierter Dateien;
- menschliche Reviewentscheidung vor normativer Verwendung;
- Rückprüfung durch den Document Consistency Review.

## Noch zu entscheidende Punkte

1. autorisierte Eingabemodelle und erster Dokumenttyp;
2. Ablageort und Publikationsstatus;
3. Trennung von Quelle, abgeleitetem Dokument und technischem Bericht;
4. Auswirkungen auf Release- und Baseline-Prozesse;
5. Update-, Review- und Freigabeverantwortung;
6. Verhalten bei Modell- oder Generatoränderungen.

## Nicht autorisiert

Dieser Backlogeintrag startet keine Implementierung. Er genehmigt keine
Dokumentveröffentlichung, Quellenpromotion, normative Ableitung oder Änderung
einer freigegebenen Baseline.

