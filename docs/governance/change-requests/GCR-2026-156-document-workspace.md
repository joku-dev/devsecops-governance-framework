# GCR-2026-156 — Benutzerfreundlicher Dokument-Arbeitsplatz

## Anlass und Ziel

Der Maintainer beauftragt einen zusammenhängenden AXIOM-Arbeitsablauf: Dokumente
aufnehmen, explizite Anforderungen prüfen, unterbrechen, wiederfinden und als
Vorbereitung weitergeben. Nutzer müssen gespeicherte Vorschläge und formale
Entscheidungen jederzeit unterscheiden können. Die Serverinstallation bleibt
zurückgestellt.

## Artifact Intake Classification

| Feld | Einordnung |
|---|---|
| Typ und Owner | Operative Workbench-Implementierung, Tests, CI und Bedienungsdokumentation; Governance Platform Maintainers |
| Neue Artefakte | Navigationshelfer, Node-DOM-Regressionen, gesperrte Entwicklungsabhängigkeiten, UI-Testworkflow und dieser GCR |
| Source Document Intake | no; keine normative Quelldatei oder Registeränderung |
| Governance-Effekt | Lokale Entscheidungsvorbereitung; ausschließlich explizite Extraktion und `proposal_only` bleiben verbindlich |
| Release-Klassifikation | no baseline release; additive Draft-Antwort und Entwicklungs-CI, Release-Manager-Review wegen Workflow |
| Evidenzvertrag | Private lokale Vorbereitungen; keine Änderung akzeptierter Consumer-Evidenz oder öffentlicher Projektionen |

## Umsetzung und Akzeptanz

1. Dokumente und Entwürfe besitzen vollständige Seiten mit ID-basierten Hash-Routen.
   Anforderungsliste, Bearbeitung und Original stehen auf breiten Bildschirmen
   nebeneinander; schmale Ansichten nutzen zugängliche Lesereiter mit Pfeiltasten.
   Direktlinks, Browser-Zurück/Vorwärts und Filter behalten die Sitzungsarbeit.
2. Ungespeicherte Eingaben bleiben nur im Arbeitsspeicher. Navigation schreibt
   keine Notiz. Vor Reload/Verlassen warnt der Browser; nach Reload gilt der
   gespeicherte Stand. URLs und dauerhafter Browser-Speicher enthalten keine
   Dokumenttexte oder Prüfnotizen. Speicher-/Ladezustände und Fehler sind sichtbar.
3. Start und Dokumentliste zeigen den nächsten sinnvollen Schritt: ohne Notiz,
   danach Klärung, danach Weitergabe. Unvollständige Pakete bleiben exportierbar.
   Veröffentlichte Entwürfe verweisen auf ihren vorhandenen PR. Fehlende explizite
   Anforderungen führen zur Originalprüfung und einer möglichen Dokumentfrage.
4. Quellenstatus, Vorbereitungsfortschritt, Klärungsbedarf und formale Historie
   erscheinen getrennt. Fortschritt zählt Anforderungen mit Prüfnotiz; historische
   Vorschläge werden weder neu extrahiert noch als lokale Freigaben gewertet.
   Formale Zähler erfordern die genaue gespeicherte Quellenbindung ID/Pfad/Hash.
5. Additive `stale_details` erklären Änderungen an HEAD, Register, Quelldateien
   und fehlende Dateien. Alte Vorbereitungen bleiben lesbar; Mutationen/Export
   bleiben gesperrt. Wiederanlauf legt eine frische Vorbereitung ohne alte Notizen
   oder Entscheidungen an. Diagnosen und `formal_status` ändern weder gespeicherte
   Draft-Bytes noch Paket-/Draft-Schemas.
6. Die Oberfläche heißt nun „Dokumentvergleich vorbereiten“ und
   „Freigabevoraussetzungen“ entsprechend ihrer tatsächlichen Funktionen.

## Grenzen und Migration

Öffentlicher Viewer, Quellenfreigaben, kanonische Anforderungen, akzeptierte
Resultate, Pilot-Fingerprints, Baselines, OPA und Enforcement bleiben unverändert.
Kein SSO, Team-Rechtesystem, VM-Installer oder GitLab-/Bitbucket-Publisher wird
implementiert. Die vorhandene optionale GitHub-Veröffentlichung bleibt eine
explizite Draft-PR-Aktion. Vorhandene private Drafts bleiben lesbar. Bei geänderter
Quelle werden sie nicht automatisch neu gebunden. Node/jsdom sind reine
Entwicklungsabhängigkeiten; die lokale Workbench benötigt keinen Frontend-Build.

## Prüfung und Lieferung

Regressionen prüfen Navigation, Filter, private Sitzungseingaben, verzögerte
Speichervorgänge, Veröffentlichungsabschluss nach Navigation, Stale-/Missing-Fälle,
leere Extraktion, unvollständige Weitergabe, Historie und vorhandene PRs.
Ein isolierter Chrome-Durchlauf nutzt ausschließlich synthetische Dokumente:
Upload → Prüfung → Klärungsnotiz → Unterbrechen/Fortsetzen mit ungespeicherter
zweiter Notiz → Reload-Warnung → unvollständiges Review-ZIP. Schmale Darstellung
bei 400 CSS-Pixeln und Lesereiter per Pfeiltaste sind eingeschlossen.
Gepinnter Bootstrap, vollständige Repository-Validierung, DOM-Tests, MkDocs strict
und revisionsgebundene Rollen-Perspektiven mit abschließender Steward-Synthese
werden vor signiertem Commit und PR ausgeführt. Der PR braucht erfolgreiche CI
und unabhängige menschliche Freigabe; lokale Rollen-Perspektiven ersetzen sie nicht.

## Lokale Prüfergebnisse

Gepinnter Bootstrap und vollständiges `validate_all.sh` bestanden mit **841 Tests**,
darunter **29 Workbench-Tests**. Reproduzierbares `npm ci --ignore-scripts` und
**16 Node-Testfälle** einschließlich tatsächlicher DOM-Navigation bestanden;
MkDocs strict und die Viewer-/Indexgeneratoren wurden geprüft. Der synthetische
Browser-Download enthält zwei explizite Anforderungen, eine gespeicherte
Klärungsnotiz mit `proposal_only` und byte-identisches Original; die zweite
ungespeicherte Notiz wurde nicht exportiert. Die Reload-Warnung, Wiederaufnahme
und Pfeiltastenbedienung bei 400 CSS-Pixeln wurden im Browser bestätigt.
Kein geänderter Pfad liegt im Operating-Acceptance-Manifest. Validierungsbedingte
Berichte/Indexänderungen sind ausgeschlossen. Signatur, CI und revisionsgebundene
Review-Ergebnisse werden im PR dokumentiert.
