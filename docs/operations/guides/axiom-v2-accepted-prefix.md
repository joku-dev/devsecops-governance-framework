# AXIOM V2: gespeicherten Governance-Bestand vergleichen

`accepted-prefix` führt den vollständigen ursprünglichen Helfer
`check_accepted_prefix` aus. Er vergleicht den gewählten lokalen Quellbestand mit
einer festen Git-Revision. Veröffentlichte Transaktionen, Profile und die im
ursprünglichen Helfer genannten Vorbereitungspfade dürfen dabei nicht still
ersetzt werden. Das Ergebnis zählt die Ledger-Einträge der Basisrevision; es
ist keine Anzahl erfüllter Controls und keine neue Freigabe.

Der Helfer gehört zur Umsetzung der V2-Funktionsparität. Der [vollständige ursprüngliche Validator](axiom-v2-lifecycle-validator.md)
verbindet diesen Helfer mit seinen übrigen Prüfungen. Die gemeinsame signierte
Lieferabnahme und der Publikationsablauf bleiben eigene offene Schritte. Den Gesamtstand zeigt der
[Goal-Fortschritt](../status/axiom-v2-goal-progress.md).

## Vergleich ausführen

Verwende eine getrennte, bereits initialisierte V2-Testinstanz und die bewusst
gewählte feste Git-Revision des zu prüfenden Governance-Quellbestands:

```bash
axiom-v2 --instance /path/to/instance accepted-prefix generate \
  --profile legacy-accepted-prefix-v1 \
  --transport-profile legacy-accepted-prefix-git-v1 \
  --source-worktree /path/to/governance-source \
  --base-ref 0123456789abcdef0123456789abcdef01234567
```

Die Beispielrevision ist durch eine tatsächlich vorhandene Revision zu ersetzen.
Der ursprüngliche Helfer verlangt eine unveränderliche, von null verschiedene
SHA-1-Commitkennung. Ein Branchname ist keine Ersatzbasis.

Die Antwort enthält `record_root`, den Zustand und bei vollständiger Aufnahme
den ursprünglichen Exitcode und Rückgabewert. Der Quellbestand wird nicht
geändert. Temporäre Git-Metadaten liegen getrennt im Zustand der Testinstanz;
ein Publisher oder ein KI-Provider wird nicht gestartet.

| Exitcode von `generate` | Bedeutung |
| --- | --- |
| `0` | Vollständig aufgezeichnet; der ursprüngliche Helfer besteht. |
| `1` | Vollständig aufgezeichnet; der ursprüngliche Helfer meldet einen Fehler, etwa eine geänderte Transaktion oder eine ungültige Basis. |
| `2` | Technisch unvollständige Aufnahme; ein ursprüngliches Prüfergebnis wird nicht behauptet. |

Ein technisch konsistenter Vergleich überträgt keine ursprüngliche persönliche,
Producer-, Source- oder Betriebsautorität auf die V2-Instanz.

## Ergebnis prüfen und wiedergeben

`inspect` bindet das Ergebnis an die eigene Instanz:

```bash
axiom-v2 --instance /path/to/instance accepted-prefix inspect \
  --record /path/from/record_root
```

`replay` prüft die aufgezeichneten Beobachtungen auch ohne die ursprüngliche
Quelle und ohne eine aktive Instanz:

```bash
axiom-v2 accepted-prefix replay --record /path/from/record_root
```

Die Wiedergabe startet weder Git noch einen Provider und erzeugt keine neuen
Hilfsverzeichnisse. `inspect` und `replay` geben für einen konsistenten
vollständigen Datensatz `0` zurück, auch wenn dessen ursprünglicher Helfer einen
fachlichen Fehler gemeldet hatte. Der ursprüngliche Exitcode steht separat in
`original_exit_code`. Ein fremder Node oder eine andere Produktgeneration darf
das Ergebnis nicht als eigene Aufnahme ausgeben.

## Erhaltene Prüfungen und Aufnahmegrenzen

Der vollständige ursprüngliche Algorithmus enthält die Prüfung des Commits,
der erlaubten verfolgten Transaktionsnamen, akzeptierter Git-Modi und Blobwerte,
der gelöschten oder durch Symlinks ersetzten Transaktionen, der Default- und
Exception-Profile sowie aller sieben ursprünglichen Vorbereitungsbereiche.
Optionale fehlende Exception-Profile behalten das ursprüngliche binäre
`subprocess.run`-Verhalten. Ursprüngliche `check_output`-Fehler und rohe Git-
Diagnostik bleiben davon unterschieden.

Git kann Dateinamen als C-zitierte Zeichenfolge ausgeben, etwa bei Umlauten,
Tabulatoren, Zeilenumbrüchen, Anführungszeichen oder Backslashes. Der ursprüngliche
Helfer verbindet diese Zeichenfolge wörtlich mit dem Quellpfad. V2 erhält genau
diese Auswahl: Es dekodiert die Zeichenfolge nicht in einen anderen Dateinamen.
Fehlt dieser wörtliche Pfad, bleibt der ursprüngliche Fehler „Accepted preparation
deleted or replaced“ erhalten. Existiert zufällig ein entsprechender wörtlicher
Pfad, verwendet auch dessen Hash-Prüfung diese ursprüngliche Auswahl. Die
Zulassung bleibt auf dieselben Quellbereiche und eine geschlossene Grammatik
beschränkt; fremde, fehlerhafte und traversierende Pfade werden abgewiesen.
`core.quotePath=false` behält das ursprüngliche Verhalten für unzitierte
Unicode-Namen. Die Prüfung der veröffentlichten Transaktionsnamen wird dadurch
nicht erweitert.

Hash-Konvertierungen berücksichtigen die beobachteten Git-Attribute,
Konvertierungseinstellungen und Indexdaten. Eingebaute Umwandlungen wie CRLF,
`ident` und `working-tree-encoding` werden erhalten; `--no-filters` wäre dafür
kein gleichwertiger Ersatz. Standardrepos, Split-Index und verknüpfte Worktrees
haben eigene Tests. Die Aufnahme verlangt stabile, gebundene Quelldaten und
Indexdateien. Änderungen während der Aufnahme führen zu `incomplete`.

Ein für den gewählten Hash-Pfad konfiguriertes externes `clean`- oder `process`-
Programm wird nicht ausgeführt. Seine Schlüsselnamen werden abgefragt; seine
Programmbefehle werden nicht in den Datensatz übernommen. Dieser Fall ist eine
technisch unvollständige Aufnahme und kein erfundener ursprünglicher Befund.
Unbeteiligte Filterkonfiguration ist kein Ablehnungsgrund.

Die temporären Git-Metadaten verwenden eine eigene geschlossene Dateiauswahl.
Unerwartete Kinder, geänderte Dateien und Protokollverlust lassen das betreffende
Verzeichnis zur Diagnose bestehen. Es gibt keinen automatischen Wiederanlauf
und kein pauschales Löschen unbekannter Inhalte.

Die Tests vergleichen vollständige ursprüngliche Helferaufrufe, Rückgabewerte,
Fehlertyp und Meldung sowie rohe Git-Diagnostik. Die vollständige äußere Python-
Traceback-Darstellung, alle übrigen Validator-/Publikationsschritte und die
signierte gemeinsame Mac-/Linux-Lieferabnahme bleiben gesonderte Goal-Nachweise.
