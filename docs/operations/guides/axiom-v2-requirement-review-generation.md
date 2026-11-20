# V2: Vorschläge zur Anforderungsumsetzung erzeugen

Der Entwicklungskandidat übernimmt die beiden vollständigen bisherigen Generatoren
für die Zuordnung implementierter Artefakte und das PRA-Plattform-Review.
Die Ergebnisse bleiben Vorschläge für menschliche Prüfung. Textähnlichkeit,
Herkunft und bestehende Modellangaben erteilen weder eine neue Entscheidung noch
eine Aktivierung. Beide Einträge der Paritätsmatrix bleiben `in_progress`.

## Private Berichte vorbereiten

In einer initialisierten, pausierten V2-Instanz:

```sh
./axiom-v2 requirement-review generate \
  --kind implemented-migration \
  --profile legacy-requirement-review-v1 \
  --source-worktree /privater/pfad/governance-daten

./axiom-v2 requirement-review generate \
  --kind pra-platform \
  --profile legacy-requirement-review-v1 \
  --source-worktree /privater/pfad/governance-daten
```

Der ausdrücklich gewählte Datenarbeitsbaum benötigt keine Git-Historie. Der
erste Generator liest Lifecycle-Fälle, Artefaktregister und das vollständige
bisherige Artefaktinventar. Das explizite Legacy-Profil wählt dabei auch die
bisherigen Workflow-Dateien unter `.github/workflows`; dieser Pfad steht im
Adapterprofil. Der Produktkern erhält Inventarwurzeln als Eingaben und startet
keinen Provider. Der zweite Generator liest das vorhandene Migrationsergebnis,
den PRA-Lifecycle-Fall, Plattformmodelle und die registrierte Quelle.

Die bisherige Reihenfolge, Schwellenwerte, maximal acht Zuordnungskandidaten,
Herkunftskennzeichnung, Klassifikation und Entscheidungsgrenzen bleiben erhalten.
Beide ursprünglichen JSON-/Markdown-Ausgaben werden vollständig privat gespeichert.
Der Standardmodus `private-candidate` schreibt keine Berichte in die Quelle.
Ein privater Entwurf bestätigt deshalb keinen erfolgreichen nativen Dateiexport.
Der PRA-Generator liest den bereits vorhandenen Migrationsbericht; er verwendet
nicht automatisch den zuvor privat erzeugten Entwurf.

## Ursprüngliche Berichtspfade ausdrücklich schreiben

```sh
./axiom-v2 requirement-review generate \
  --kind implemented-migration \
  --profile legacy-requirement-review-v1 \
  --source-worktree /privater/pfad/governance-daten \
  --write-source-reports
```

Die zusätzliche Option wählt den nativen Modus `source-worktree`. Je Generator
sind genau zwei ursprüngliche Dateipfade vorgesehen:

| Generator | JSON | Markdown |
| --- | --- | --- |
| `implemented-migration` | `generated/reports/implemented-requirement-migration.json` | `generated/reports/implemented-requirement-migration.md` |
| `pra-platform` | `docs/governance/review-packets/PRA-2026-001/review.json` | `docs/governance/review-packets/PRA-2026-001/review.md` |

Vorhandene Dateien werden in ursprünglicher Reihenfolge überschrieben; die
bisherigen Dateimodi bleiben erhalten. Für PRA werden wie bisher gegebenenfalls
die festen Elternverzeichnisse erzeugt. Teilweise geschriebene Dateien und
ursprüngliche Fehler werden erfasst. Scheitert die zweite Ausgabe, kann die
erste bereits vollständig geschrieben sein. Auch ein unverändertes erfolgreiches
Überschreiben wird als berührter Pfad protokolliert. Eine Veröffentlichung,
Freigabe oder Übernahme in einen offiziellen Ergebnisindex erfolgt dadurch nicht.

## Ergebnisse und Fehler nachprüfen

```sh
./axiom-v2 requirement-review inspect --record /privater/pfad/nachweis
./axiom-v2 requirement-review replay --record /privater/pfad/nachweis
```

Der Nachweis enthält die verwendeten Rohbytes, geordnete Lektüren, Ausgabeabsichten,
Ergebnisse und im nativen Modus Vorher-/Nachher-Zustände sowie Schreibfortschritt.
Die Nachprüfung berechnet alle ursprünglichen Entscheidungen, Berichtsbytes,
Ausgaben und Fehler erneut. Sie liest die beobachtete Quelle nicht nochmals,
startet kein Quellprogramm und wiederholt keine Dateiexporte. Eigene registrierte
Produktdateien bleiben Bestandteil der Codebindungsprüfung. `inspect` prüft
zusätzlich die eigene Instanz; das ausdrücklich portable `replay` benötigt keine
Instanz, aber denselben Produktstand. Ursprüngliche hostabhängige Fehlermeldungen
bleiben Angaben des erzeugenden Hosts.

Die Standardausgabe nennt Zustand, Nachweispfad, Exportmodus, berührte Quellpfade
und Exitcode. `--format legacy` gibt die vollständigen bisherigen Streams aus;
bei einem abgefangenen ursprünglichen Fehler ergänzt es dessen Typ als Diagnose,
ohne einen ursprünglichen Traceback zu erfinden. Erfolg liefert null, ein
vollständig erfasster ursprünglicher Fehler eins. Zusätzliche Aufnahmegrenzen
oder unvollständige Erfassung liefern zwei und keinen ursprünglichen Exitcode.

Quell- und Ausgabedateien müssen gewöhnliche eigene Dateien sein. Begrenzte
Lektüren über gehaltene Deskriptoren, Wiederholungsprüfungen, YAML- und
Protokollbudgets, Alias-/Symlink-Ablehnung und getrennte Quell-/Nachweisverzeichnisse
sind zusätzliche Aufnahmegrenzen. Sie werden auch im Anforderungsprüfer als
unvollständige Aufnahme ausgewiesen und nicht als ursprünglicher Fachbefund.

Die Nachprüfung belegt Konsistenz gespeicherter Angaben. Sie authentifiziert
keinen Produzenten und bestätigt keine menschliche Freigabe, wirksame Governance,
Compliance oder Betriebsannahme. Die vollständigen unveränderten V1-Originale
dienen positiven und negativen Vergleichen einschließlich tatsächlicher
Dateifehler. Quellweite gepinnte Validierung, revisionsgebundene Reviews und
passende installierte Mac-/Linux-Kandidaten bleiben vor der Lieferung erforderlich.
