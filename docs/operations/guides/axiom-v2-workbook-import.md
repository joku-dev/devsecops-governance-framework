# V2: Workbook-Zuordnungen als Kandidaten vorbereiten

Der Entwicklungskandidat übernimmt den vollständigen bisherigen
`import_harmonized_requirements_workbook.py`: Tabellenlektüre, Klassifikation,
Zuordnungen, Abdeckungsbericht, ursprüngliche Dateiausgaben und Fehler.
Die Ergebnisse bleiben nicht normative Vorschläge zur menschlichen Prüfung.
Der Eintrag der Paritätsmatrix bleibt `in_progress`.

## Privat erzeugen

In einer initialisierten, pausierten V2-Instanz:

```sh
./axiom-v2 workbook-import generate \
  --profile legacy-harmonized-workbook-v1 \
  --source-worktree /privater/pfad/governance-daten \
  --working-directory /privater/pfad/governance-daten \
  -- --input-xlsx /privater/pfad/eingang.xlsx
```

Hinter `--` stehen die vollständigen ursprünglichen Argumente. Dazu gehören
`--input-xlsx`, das optionale `--requirements-model` und die drei ursprünglichen
Ausgabeoptionen. Ohne `--working-directory` gilt der gewählte Datenarbeitsbaum
als Arbeitsverzeichnis für relative Pfade. Die Quelle benötigt keine Git-Historie.
Programme im Datenarbeitsbaum werden nicht geladen oder ausgeführt.

Der Standardmodus `private-candidate` speichert die vollständigen vorgeschlagenen
Ausgaben im privaten Nachweis. Er erzeugt keine Dateien im Datenarbeitsbaum.
Die Antwort nennt `record_root`. Die dortige `result.json` enthält die geordneten
`successful_writes` und `successful_outputs` mit SHA-256 und Bytezahl; die
zugehörigen unveränderten Bytes liegen jeweils unter `blobs/<sha256>`.

Das Legacy-Profil behält die ursprüngliche feste Auswahl bei: gemeinsame
Zeichenketten aus `xl/sharedStrings.xml`, das erste Arbeitsblatt unter
`xl/worksheets/sheet1.xml` und dessen Zeilen 4 bis 267. Andere Zeilen werden wie
bisher nicht übernommen. Die Modellvorgabe lautet
`model/requirements/harmonized-devsecops-requirements.yaml` im Datenarbeitsbaum.
Andere Workbook-Strukturen benötigen ein eigenes, separat geprüftes Profil.

## Die drei ursprünglichen Dateien schreiben

```sh
./axiom-v2 workbook-import generate \
  --profile legacy-harmonized-workbook-v1 \
  --source-worktree /privater/pfad/governance-daten \
  --write-selected-reports \
  -- --input-xlsx /privater/pfad/eingang.xlsx
```

Der ausdrückliche Modus `selected-files` erzeugt zunächst alle drei vorgesehenen
Elternverzeichnisse und schreibt danach in der ursprünglichen Reihenfolge:

| Ursprüngliche Option | Vorgabe im Datenarbeitsbaum |
| --- | --- |
| `--mapping-output` | `model/traceability/standards-to-harmonized-requirements.yaml` |
| `--report-json` | `generated/reports/harmonized-requirements-coverage.json` |
| `--report-md` | `generated/reports/harmonized-requirements-coverage.md` |

Die ursprünglichen Optionen wählen auch eigene relative oder absolute Ziele.
Jeder Schreibvorgang bleibt getrennt erfasst, auch wenn mehrere Optionen dieselbe
Datei auswählen. Bestehende Dateimodi bleiben erhalten. `successful_outputs`
bezeichnet die letzten erfolgreichen Ausgaben; bei einem späteren Teilfehler
beschreibt `touched_files` den erfassten tatsächlichen Endzustand. Der geordnete
Ablauf enthält auch frühere erfolgreiche Schreibvorgänge auf denselben Pfad.

Ursprüngliche Teilfehler bleiben sichtbar. Beispielsweise können bereits alle
drei Dateien geschrieben sein, wenn anschließend die Ausgabe eines Ziels
außerhalb des Datenarbeitsbaums an `relative_to` scheitert. Ein Dateifehler bei
der zweiten Ausgabe lässt die erste Ausgabe bestehen. Der Nachweis hält
Ausgabeabsichten, Vorher-/Nachher-Bytes und Schreibfortschritt fest.

Die registrierten Dateien der eigenen V2-Installation sind als Ausgabeziele
gesperrt. Für veränderbare Modelle und Berichte ist ein eigener Datenarbeitsbaum
vorgesehen. Der Kompatibilitätseinstieg im Quellrepository bleibt als expliziter
Adapter erhalten.

## Ausführung nachprüfen

```sh
./axiom-v2 workbook-import inspect --record /privater/pfad/nachweis
./axiom-v2 workbook-import replay --record /privater/pfad/nachweis
```

Die Nachprüfung rekonstruiert den vollständigen ursprünglichen Hauptablauf aus
den aufbewahrten Eingaben und geordneten Datei-Beobachtungen. Sie liest die
beobachteten Quellen nicht erneut, startet kein Quellprogramm und wiederholt
keinen Dateiexport. Eigene Produktbytes werden weiterhin für die Codebindung
gelesen. `inspect` bindet zusätzlich die eigene Instanz. Für portables Replay
ohne Instanz kann der Python-Einstieg der gleichen Produktversion verwendet werden:

```sh
python /pfad/zur/produktquelle/scripts/axiom_v2.py \
  workbook-import replay --record /privater/pfad/nachweis
```

Ein vollständig erfasster ursprünglicher Erfolg liefert null, ein ursprünglicher
Fehler gewöhnlich eins. Die ursprünglichen Parser-Exits, beispielsweise zwei bei
fehlenden Argumenten, bleiben ebenfalls erhalten. `state: complete` mit
`original_exit_code: 2` unterscheidet sich von einer unvollständigen technischen
Erfassung mit Exit zwei und `original_exit_code: null`. Eine erfolgreiche
Nachprüfung eines gespeicherten Fehlerfalls bestätigt dessen Konsistenz.

`--format legacy` gibt die ursprünglichen Streams aus, einschließlich Hilfe und
Parserfehlern. Bei einem ursprünglich unbehandelten Fehler ergänzt die Ausgabe
Typ und Meldung als strukturierte Diagnose; ein ursprünglicher Traceback wird
nicht erfunden. Im privaten Modus bleibt diese Legacy-Ausgabe eine berechnete
Sicht. Ihr Wortlaut bestätigt keinen Export in die gewählten Quelldateien.

## Grenzen und fachliche Bedeutung

Die ursprünglichen Standardnamen, Kennungszuordnungen, Inhaltsmuster, Prioritäten,
maximal fünf Zielanforderungen, Duplikat-/Leerkennungszählung, Hash-Gruppierung,
Abdeckungsrechnung und menschlichen Review-Grenzen bleiben erhalten. Das Profil
bezeichnet weiterhin die feste Quellkennung `CISO-REQ-SRC-001`. Synthetische
Gruppenkennungen wie `SRCREQ-…`, übernommene Zeilenkennungen und Dateihashes sind
keine Bestätigung ihrer Autorenschaft, Freigabe oder normativen Geltung.
Es werden bestehende Zielanforderungen zugeordnet; neue normative Anforderungen,
Kontrollen, OPA-Regeln oder Releases werden nicht abgeleitet oder aktiviert.
Die Abdeckungszahl berechnet sich aus den bereits im Modell hinterlegten
Designstatuswerten.

Zusätzliche Aufnahmegrenzen verlangen gewöhnliche eigene Dateien, gehaltene
Deskriptoren, unveränderte wiederholte Lektüren, stabile Ausgabe-Elternverzeichnisse
und getrennte private Instanzdaten. Aliasse, Symlinks, Spezialdateien, private
Credential-Pfade und ausbrechende Pfadausdrücke werden abgelehnt. Einzelne Dateien
und ZIP-Einträge sind auf 16 MiB begrenzt, Archive auf 4.096 Einträge und insgesamt
32 MiB entpackte Daten. YAML-Komposition, Argumente, ursprüngliche Fehlermeldungen
und Streams sowie das private Protokoll sind ebenfalls begrenzt. Diese Grenzen
und Erfassungsfehler liefern keinen ursprünglichen Fachbefund.

Die Nachprüfung belegt Konsistenz deklarierter Daten. Sie authentifiziert keinen
Produzenten und erteilt keine Source-, Compliance- oder Betriebsfreigabe.
Quellweite gepinnte Validierung, revisionsgebundene Reviews und passende signierte
Mac-/Linux-Installationen bleiben vor der Lieferung erforderlich.

## Explicit producer parser inputs

The current correction candidate requires complete producer parser context in
capture/replay requests: admitted module profile/version, observed width and
English translations. Pure replay uses those inputs without consumer terminal
or gettext defaults. Missing context has no native fallback; old records remain
historical without relabeling. Whole original bodies, argument/IO/error behavior
and any selected tool observations remain in scope. See the
[producer parser contract](axiom-v2-producer-parser-context.md); fresh full and
signed installed proof is still required for this correction.
