# V2: Governance-Dokumente vollständig rendern

Der Entwicklungskandidat übernimmt den ganzen bisherigen
`render_governance_documents.py`: Katalog, Renderprofile, Filter,
Frontmatter, Markdown-/HTML-Darstellung und den optionalen Pandoc-Aufruf.
Die Paritätsmatrix bleibt `in_progress`; die vollständige signierte
Mac-/Linux-Abnahme dieses Bausteins steht noch aus.

## Privat vorbereiten

In einer initialisierten, pausierten V2-Instanz:

```sh
./axiom-v2 document-rendering generate \
  --profile legacy-governance-documents-v1 \
  --source-worktree /privater/pfad/governance-daten
```

Der Datenarbeitsbaum benötigt `model/documents/governance-documents.yaml`,
`model/documents/governance-document-rendering.yaml` und die ausgewählten
Quelldokumente. Seine Programme werden nicht geladen. Wie bisher werden
`policy` und `directive` berücksichtigt. Wiederholte Filter sind möglich:

```sh
./axiom-v2 document-rendering generate \
  --profile legacy-governance-documents-v1 \
  --source-worktree /privater/pfad/governance-daten \
  -- --document-id DEVSECOPS-POL-001
```

Die Vorgabe `private-candidate` schreibt die vollständigen Ausgaben und
Beobachtungen in einen privaten Nachweis. Die Antwort nennt `record_root`.
Markdown und HTML werden vollständig berechnet; ein verfügbares Pandoc arbeitet
auf einer privaten Kopie. Der Datenarbeitsbaum erhält dabei keine Exporte.

## Ursprüngliche Dateien und Pandoc

`--write-selected-reports` wählt ausdrücklich die ursprünglichen Dateiausgaben
unter `generated/documents/` des Datenarbeitsbaums: pro Dokument zunächst
`<id>.rendered.md`, dann `<id>.html`, anschließend optional `<id>.docx`.
Verzeichnisse, wiederholte Ziele, Reihenfolge und ursprüngliche Teilfehler
bleiben erfasst. Eigene Produktdateien und privater Instanzzustand sind als
native Ausgabeziele gesperrt.

Pandoc wird wie bisher über `PATH` gefunden. `--tool-path` legt für diesen Lauf
einen ausdrücklichen Suchpfad fest; `--working-directory` bestimmt dessen
Arbeitsverzeichnis. Ohne diese Optionen gilt der aktuelle Prozesskontext.
`--source-date-epoch` übernimmt den gleichnamigen reproduzierbaren Pandoc-Kontext
`SOURCE_DATE_EPOCH`. Für einen bytegenauen Hostvergleich sind dieselbe
Pandoc-Version und derselbe Zeitwert erforderlich. Die Anwendung installiert
Pandoc nicht. Fehlt es, bleiben Markdown/HTML und die ursprüngliche Meldung
zum ausgelassenen DOCX erhalten.

Der Nachweis erfasst Programmpfad, Binärhash, ursprüngliche und tatsächlich
verwendete Argumente, Rohstreams, Prozessende und beobachteten Dateizustand.
Ein Exit null ohne DOCX wird nicht als vorhandene Datei ausgegeben.
Ein Nichtnull-Exit kann trotzdem eine Teil-Datei hinterlassen. Die bisherigen
Erfolg-/Überspringen-Meldungen bleiben erhalten; sie belegen allein keinen
Dateiexport. `observed_tool_outputs` und die geordneten Datei-Beobachtungen
beschreiben den erfassten Zustand. Es wird keine Netzwerk- oder vollständige
Prozessbaum-Isolation des externen Tools behauptet.

## Nachrechnen und Grenzen

```sh
./axiom-v2 document-rendering inspect --record /privater/pfad/nachweis
./axiom-v2 document-rendering replay --record /privater/pfad/nachweis
```

Die ganze Ausführung wird aus aufbewahrten Rohbytes und geordneten
Beobachtungen rekonstruiert. Dabei werden weder beobachtete Quellen erneut
gelesen noch Pandoc gestartet oder Exporte wiederholt. Eigene Produktbytes
bleiben Teil der Codebindung. `inspect` prüft zusätzlich die eigene Instanz.
Portables Replay benötigt dieselbe Produktversion und keine fremde Instanz:

```sh
python /pfad/zur/produktquelle/scripts/axiom_v2.py \
  document-rendering replay --record /privater/pfad/nachweis
```

`--format legacy` gibt ursprüngliche Streams aus, einschließlich Hilfe und
Parserfehlern. Ursprüngliche unbehandelte Fehler erscheinen mit Typ und Meldung;
ein ursprünglicher Traceback wird nicht erfunden. Ein vollständiger
ursprünglicher Parser-Exit zwei bleibt von unvollständiger technischer Erfassung
mit Exit zwei und `original_exit_code: null` unterscheidbar.

Gewöhnliche eigene Dateien, stabile Deskriptoren/Eltern, Ablehnung von
Alias-/Symlink-/Privatpfaden, begrenzte Datei-/YAML-/Stream-/Ereignismengen und
ein endlicher Tool-Lauf sind zusätzliche Aufnahmegrenzen. Das Tool-Limit beträgt
standardmäßig 120 Sekunden und höchstens 600 Sekunden, pro Rohstream 256 KiB.
Ein solcher Abbruch bleibt `incomplete`, auch wenn zuvor Dateien entstanden.

Nachrechnung bestätigt Konsistenz deklarierter Daten. Sie authentifiziert
keinen Produzenten. Gerenderte Angaben zu Freigabe, Zuständigkeit oder Status
übertragen keine Quell-, Governance-, Compliance- oder Betriebsfreigabe.

## Explicit producer parser inputs

The current correction candidate requires complete producer parser context in
capture/replay requests: admitted module profile/version, observed width and
English translations. Pure replay uses those inputs without consumer terminal
or gettext defaults. Missing context has no native fallback; old records remain
historical without relabeling. Whole original bodies, argument/IO/error behavior
and any selected tool observations remain in scope. See the
[producer parser contract](axiom-v2-producer-parser-context.md); fresh full and
signed installed proof is still required for this correction.
