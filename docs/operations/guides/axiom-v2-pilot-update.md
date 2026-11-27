# AXIOM V2: Pilot-Update vorbereiten

`pilot-update` führt den vollständigen ursprünglichen Ablauf von
`run_lifecycle_pilot_update.py` aus. Die Operationen `acceptance`, `observe`,
`action` und `refresh` behalten ihre Reihenfolge und Prüfungen. Auch die
ursprünglichen Betriebsfunktionen `capture()` und `generate()` sind aufrufbar.
Der Baustein gehört zur noch offenen [V2-Funktionsparität](../status/axiom-v2-goal-progress.md);
die aktuelle gemeinsame signierte Quell- und Mac-/Linux-Lieferabnahme steht aus.

## Privaten Kandidaten erstellen

Verwende eine getrennte, initialisierte und pausierte V2-Testinstanz sowie einen
gewählten lokalen Governance-Quellbestand:

```bash
axiom-v2 --instance /path/to/instance pilot-update generate \
  --profile legacy-pilot-update-v1 \
  --transport-profile legacy-pilot-update-readonly-v1 \
  --source-worktree /path/to/governance-source \
  --provider-executable /path/to/gh \
  -- --operation refresh
```

Alle ursprünglichen Optionen stehen nach `--`. Ersetze den letzten Teil für die
anderen Operationen durch:

```text
--operation acceptance
--operation observe --source-run-id 123456789
--operation action --request-path model/governance/lifecycle/action-requests/example.json
```

`observe` verlangt wie V1 eine positive numerische Run-ID. `action` verlangt
einen bereits in Git erfassten Antrag unter dem ursprünglichen eigenen
Antragsverzeichnis. Der lesende Adapter prüft dies mit `git ls-files`. Er
veröffentlicht und committet keinen Antrag. Die Operation erhält den ursprünglichen
Append über beide Ledgers. `acceptance` erfasst vorhandene persönliche Aussagen
und erzeugt die anschließenden Berichte; sie überträgt keine Zustimmung auf die
V2-Instanz. Fehlende persönliche Aussagen bleiben ein ursprünglicher Fehler.

Standardmäßig entstehen private Dateiprojektionen in der eigenen Aufnahme;
der Quellbestand bleibt unverändert. `--write-selected-files` vor `--` wählt
ausdrücklich die ursprünglichen Dateischreiboperationen im Quellbestand und
native temporäre Arbeiten. `--temporary-parent /path/to/private-temporaries`
legt deren eigenes Verzeichnis fest. Nach einem späteren Fehler können wie im
Original bereits ausgewählte Dateien geschrieben sein; die Antwort kennzeichnet
diesen Fall. Der Aufruf veröffentlicht keine Ergebnisse und aktiviert keinen
Dienst. Zugangsdaten gehören in den lokal eingerichteten Client, nicht in Optionen.
Das Legacy-Profil verwendet dessen bestehendes GitHub-Datenformat; ein anderer
Provider benötigt ein eigenes kompatibles Profil.

Die einzelnen ursprünglichen Betriebsfunktionen ohne Runner sind über
`--helper capture` beziehungsweise `--helper generate` vor `--` verfügbar.
Dabei werden keine ursprünglichen Runner-Argumente angehängt.

## Aufzeichnung prüfen und wiedergeben

Die Antwort nennt `record_root`, Zustand, ursprünglichen Exitcode und
Exportmodus. Eine vollständige Aufnahme kann einen ursprünglichen Fehler
enthalten. Technische Unvollständigkeit liefert `2` und behauptet keinen
ursprünglichen Exitcode. Parserfehler behalten gesondert ihr ursprüngliches
`SystemExit`-Ergebnis. `--format legacy` gibt die gespeicherten ursprünglichen
Ausgabeströme aus; vollständige äußere Python-Tracebacks und der technische
Launcher-Fehlerdraht sind noch eigene offene Paritätsarbeit.

```bash
axiom-v2 --instance /path/to/instance pilot-update inspect \
  --record /path/from/record_root

axiom-v2 pilot-update replay --record /path/from/record_root
```

`inspect` verlangt dieselbe Instanzidentität. `replay` benötigt keine Instanz und
keine ursprünglichen Quelldateien. Die Wiedergabe startet weder Git noch Provider,
liest keine neue Uhr und wiederholt keine nativen Schreiboperationen. Beide
prüfen Produktgeneration, Anfrage, Reihenfolge, Ergebnisse und die vollständige
Blob-Menge. Konsistente vollständige Aufnahmen liefern dabei `0`; der
ursprüngliche Exitcode bleibt getrennt lesbar. Manipulierte oder fremde
Aufnahmen werden abgewiesen. Fehlende Beobachtungen und Protokollverlust
begründen keinen erfundenen Erfolg oder automatischen Wiederanlauf.

Die Aufnahme ist technische Engineering-Evidenz. Sie aktualisiert keinen
offiziellen Latest-Index, erteilt keine Freigabe und überträgt weder Source-,
persönliche, Producer-, Compliance- noch Betriebsautorität. Der ursprüngliche
Publikationsablauf, Consumer-Runner und übrige Betriebsabläufe bleiben eigene
offene Schritte im Goal.
