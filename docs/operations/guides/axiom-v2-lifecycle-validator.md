# AXIOM V2: vollständigen Lifecycle-Validator ausführen

`lifecycle-validator` führt den vollständigen ursprünglichen Ablauf von
`validate_governance_lifecycle_ledger.py` aus. Strukturelle Ledger-, Modell-,
Profil-, Berichts- und Viewer-Prüfungen bleiben in ihrer ursprünglichen
Reihenfolge erhalten. Die beiden ursprünglichen Optionen `--base-ref` und
`--verify-new-provider` werden nach `--` übergeben.

Der Baustein gehört zur laufenden [V2-Funktionsparität](../status/axiom-v2-goal-progress.md).
Die gemeinsame signierte Quell- und Mac-/Linux-Lieferabnahme, der
Publikations-/Runner-Ablauf und die vollständige äußere Python-Traceback-
Darstellung haben eigene noch offene Nachweise. Ein gespeicherter historischer
Zustimmungsnachweis aktiviert keine V2-Instanz.

## Lokal prüfen

Verwende eine getrennte, initialisierte V2-Testinstanz und den gewählten lokalen
Governance-Quellbestand:

```bash
axiom-v2 --instance /path/to/instance lifecycle-validator generate \
  --profile legacy-lifecycle-ledger-validation-v1 \
  --transport-profile legacy-lifecycle-ledger-readonly-v1 \
  --source-worktree /path/to/governance-source
```

Ohne ursprüngliche Optionen prüft der Ablauf den lokalen Bestand ohne neue
Provider-Abfragen. Eine feste akzeptierte Basis ergänzt die ursprüngliche
[Prefix-Prüfung](axiom-v2-accepted-prefix.md). Für frische Provider-Prüfungen:

```bash
axiom-v2 --instance /path/to/instance lifecycle-validator generate \
  --profile legacy-lifecycle-ledger-validation-v1 \
  --transport-profile legacy-lifecycle-ledger-readonly-v1 \
  --source-worktree /path/to/governance-source \
  --provider-executable /path/to/gh \
  -- --base-ref 0123456789abcdef0123456789abcdef01234567 --verify-new-provider
```

Ersetze die Beispielrevision durch den tatsächlich vorhandenen akzeptierten
Commit. `--verify-new-provider` verlangt wie im Original eine Basis. Die
zusätzlichen Prüfungen stehen zwischen ursprünglicher Betriebsvalidierung und
abschließender Index-, Pilot-, Exception-, Overview- und Viewer-Prüfung. Sie
prüfen neue Receipts, persönliche Aufnahmen, Aktionen und Betriebsaufnahmen.
Eine geänderte aktive Indexprojektion löst die ursprüngliche erneute
Betriebsprüfung auch ohne neue Betriebsaufnahme aus. Bei inaktiver Projektion
bleibt die ursprüngliche Bedingung erhalten.

Das ausdrücklich gewählte Legacy-Transportprofil verwendet den bestehenden
lesenden Provider-Adapter und dessen GitHub-Datenformat. Es benötigt passende
Leserechte des lokal eingerichteten Clients. Zugangsdaten werden nicht als
Kommandooption übergeben. Andere Provider benötigen ihr eigenes kompatibles
Profil; persönliche oder betriebliche Autorität wird nicht abgeleitet.

Der Quellbestand bleibt unverändert. Standardmäßig werden temporäre
Receipt-Arbeiten privat projiziert. `--native-temporaries` erlaubt die
ursprünglichen temporären Dateioperationen unter einem ausdrücklich gewählten
`--temporary-parent /path/to/temporary-directory`. Auch dieser Modus exportiert
keine Dateien in den Quellbestand und veröffentlicht keine Ergebnisse.

## Aufzeichnung lesen und wiedergeben

Die Antwort enthält `record_root`, den Aufnahmezustand und den ursprünglichen
Exitcode. `generate` liefert bei vollständiger Aufnahme den ursprünglichen
Exitcode, einschließlich ursprünglicher Parser- und Validierungsfehler.
Technisch unvollständige Aufnahmen liefern `2` und behaupten keinen
ursprünglichen Exitcode. Der Zustand und die Felder `original_exit_code` und
`original_exit_signal` unterscheiden einen ursprünglichen Parserfehler von
technischer Unvollständigkeit.

```bash
axiom-v2 --instance /path/to/instance lifecycle-validator inspect \
  --record /path/from/record_root

axiom-v2 lifecycle-validator replay --record /path/from/record_root
```

`inspect` verlangt die eigene Instanzidentität. `replay` benötigt keine aktive
Instanz und keine ursprüngliche Quelle. Es startet weder Git noch den Provider,
liest keine neue Uhr und erzeugt keine neuen temporären Verzeichnisse.
Beide prüfen die gespeicherte Anfrage, Produktgeneration, Beobachtungsreihenfolge,
Ergebnisse und sämtliche Blob-Inhalte. Ein konsistenter vollständiger Datensatz
liefert dabei `0`, auch wenn sein ursprüngliches Prüfergebnis fehlerhaft war;
der ursprüngliche Exitcode bleibt gesondert lesbar.

Fehlende Beobachtungen, Quellenänderungen oder Protokollverlust ergeben eine
technisch unvollständige Aufnahme. Es gibt keinen automatischen Wiederanlauf
mit erfundenen ursprünglichen Ergebnissen. Die Aufnahmegrenzen des
Prefix-Adapters, einschließlich ausgewählter externer Git-Filter, bleiben
sichtbar. Diese Prüfung ist weder eine neue Freigabe noch eine Übertragung von
Source-, persönlicher, Producer-, Compliance- oder Betriebsautorität.
