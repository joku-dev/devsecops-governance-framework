# GCR-2026-118: Phase 1 — Deterministischer Strukturkern

## Anfrage und Einordnung

Baue auf der angenommenen Phase-0-Entscheidung einen deterministischen,
read-only Strukturkern auf. Er bindet die Registereinträge des begrenzten
Pilotumfangs an Commit und Dateibytes, bildet Requirement-Tabellenzeilen anhand
ihrer stabilen IDs und Stärkekennzeichnung ab und erfasst explizite ID-Verweise
als vorläufige Beziehungen. Quellprosa wird nicht in das Modell kopiert. Die
Lieferung führt keine semantische oder fachliche Dokumentenbewertung durch.

| Feld | Wert |
|---|---|
| Artefakte | Manifest- und Strukturmodell-Schemas, Quellenmanifest- und Strukturinventar-Generator, Validator, JSON-/Markdown-Bericht und synthetische Tests |
| Pilotquellen | `DSCB-STD-REQ-001`, `PRA-STD-REQ-001`, synthetische Test-Fixtures |
| Bezugsentscheidung | Angenommene ADR-DCR-001 / GCR-2026-116 auf Basis `a8fc36f3de7f33cd2a26dff94f9a28985e78d64f` |
| Laufzeit- und Policy-Auswirkung | Keine; Werkzeug ist lokal und read-only |
| Quellenregister | Unverändert und weiterhin einzige Autorität |
| Semantik / externer Provider | `not_run`; nicht implementiert oder aufgerufen |
| Viewer / Veröffentlichung | Nicht enthalten |
| Release- oder Baseline-Auswirkung | Keine |
| Abnahme | Am 2026-10-07 als begrenzter technischer Strukturkern angenommen; Ergebnis bleibt `partial` |

## Gelieferter Umfang

- Ein Schema beschreibt Commit, Registerhash, registrierte Quellenmetadaten,
  Pfade, Quellhashes und Grenzen des Manifests.
- Der Generator nimmt explizite registrierte IDs, sortiert sie deterministisch
  und lehnt unbekannte/duplizierte IDs, unvollständige Registerdaten,
  Pfad-Traversal und fehlende Quelldateien ab.
- Bei sauberem Git-Arbeitsbaum wird der Commit gebunden. Bei Änderungen oder
  nicht verfügbarer Git-Metadaten bleibt `reviewed_commit` null; so wird kein
  Snapshot eines nicht festgeschriebenen Stands vorgetäuscht.
- Das Manifest enthält keine Quelltexte oder Auszüge und ändert weder
  Registerstatus noch Autorität.
- Der Strukturinventar-Generator bildet 111 Requirement-Zeilen anhand ihrer
  Tabellen-ID und Stärkekennzeichnung ab. Er kopiert keine Requirement-Texte,
  Kontexte oder sonstige Quellpassagen.
- 102 Zeilen sind explizit mit `MUST` oder `SHALL` gekennzeichnet. Da die
  freigegebenen requirements-only Auszüge keine Owner-/Verifikationszuordnung
  enthalten, weist das Modell diese Zuordnung mit einer Scope-Lücke aus; es
  erfindet keine Rollen oder Nachweise.
- 48 explizite ID-Verweise werden als `candidate`-Beziehungen festgehalten.
  Ihre Endpunkte lösen im Modell auf. `candidate` bedeutet technische
  Extraktion und keine fachlich bestätigte Relation.
- Der Validator implementiert DCR-001 bis DCR-009. Im aktuellen Report sind
  DCR-001, DCR-002, DCR-004, DCR-007 und DCR-009 prüfbar. Rollen-, Gate-,
  Evidenz- und Autoritätsmodelle fehlen in diesem begrenzten Quellenmodell und
  bleiben für die realen Pilotquellen `not_in_scope`.
- DCR-009 bindet Modell und Bericht an denselben aufgezeichneten
  Quellsnapshot. Neuere Repository-Commits machen den Lauf nicht allein
  veraltet; Register- und Quellbytes werden erneut geprüft und eine neuere
  Repository-Revision im Report transparent vermerkt.
- Das Strukturmodell erlaubt die vorgesehenen Relationstypen, markiert
  Beziehungen aber nur als `candidate` oder `confirmed`; eine technische
  Bestätigung behauptet keine fachliche Richtigkeit.
- Synthetische Unit-Fixtures prüfen Duplikate, ungelöste Rollen und Quellen,
  Pflichtlücken, Gate-Verantwortung, Evidenzverweise, Candidate-Derivation,
  Autoritätsmehrdeutigkeit und veraltete Hashes.

## Bewusste Grenzen und verbleibende Phase-1-Arbeit

Die reale Eingabe dieses Piloten besteht aus bereits bereinigten Markdown-
Auszügen. Eine DOCX-Konvertierung wird deshalb nicht behauptet und bleibt
außerhalb dieses Änderungssatzes. Das reale Modell enthält Tabellen-IDs,
Stärkekennzeichnungen und strukturell erkannte Kandidatenverweise. Rollen,
Gates, Evidenzzuordnungen und Themenautorität sind darin nicht enthalten. Ihre
Regelpfade sind mit synthetischen Fixtures geprüft; ihre fachlichen Daten
bleiben offen. Der Report lautet daher `partial`, nicht `pass`. Phase 1 ist am
2026-10-07 als begrenzter technischer Strukturkern angenommen. DCR-003,
DCR-005, DCR-006 und DCR-008 bleiben für den freigegebenen requirements-only
Pilot `not_in_scope`; die Annahme gilt nicht als vollständiger
End-to-End-Dokumentenreview. Zusätzliche Eingaben für diese Bereiche bedürfen
einer separaten Umfangsentscheidung.

Die fünf unregistrierten lokalen Dateien sind nicht Teil dieses GCR, des
Manifests oder der Fixtures. Es werden keine Controls, Architekturmarker,
Policies, Schemas für Laufzeit-Governance oder Baselines daraus abgeleitet.

## Validierung

Validierung auf Basis des aktuellen Phase-0-Stands:

- `tests.test_document_consistency_review_manifest`: 7 Tests bestanden.
- Die Manifestsuite und synthetischen Strukturregeln zusammen: 20 Tests bestanden.
- `./scripts/validate_all.sh`: OPA, Runtime Governance, Repository-Validierung,
  Provenance-Prüfung und 681 Unit-Tests bestanden. Für lokale Git-Fixture-
  Commits wurde `commit.gpgsign=false` ausschließlich pro Testprozess gesetzt,
  da die Sandbox den SSH-Agenten nicht erreicht; es wurde kein Repository-
  Commit erstellt.
- `mkdocs build --strict`: erfolgreich. MkDocs meldet die im bestehenden
  Projekt bereits nicht in der Navigation geführten Seiten, beendet den Build
  aber mit Exit-Code 0.
- `git diff --check`: bestanden.
- Das Beispielmanifest stimmt mit dem Generator überein; sein Commit verweist
  auf den sauberen Ausgangsstand `3be081f9e424d3ad5c298a27e4a4a75a544609c2`.

Diese Ergebnisse belegen nur die technische Quellenidentität und die
Repository-Kompatibilität dieses ersten Bausteins, keine semantische
Konsistenz, Vollständigkeit oder Compliance.
