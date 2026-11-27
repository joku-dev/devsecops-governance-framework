# AXIOM V2: Prüfung vor einem Veröffentlichungsvorschlag

`publication-validation` führt die vollständige ursprüngliche Funktion
`operating_acceptance.validate_publication(repo, base_ref)` aus V1 aus.
Sie prüft einen ausgewählten Quellbestand. Sie erzeugt weder einen Git-Commit
noch einen Branch, Pull Request, Workflow-Dispatch oder Merge.

```sh
/path/to/installation/axiom-v2 publication-validation generate \
  --profile legacy-operating-publication-validation-v1 \
  --transport-profile legacy-operating-publication-readonly-v1 \
  --source-worktree /operator/selected-source \
  --base-ref ACCEPTED_LOCAL_GIT_REFERENCE \
  --provider-executable /operator/tools/gh
```

Die Referenz muss im ausgewählten lokalen Git-Bestand vorhanden sein. Dieser
Befehl ermittelt oder aktualisiert keinen entfernten Main-Branch. Der vollständige
ursprüngliche Publisher benötigt zusätzlich dessen Abruf, den Abstammungsnachweis,
die genaue Dateiauswahl, Commit, Push und PR-/CI-Schritte. Diese Funktionen bleiben
Teil des offenen Gesamt-Goals; die Vorprüfung ersetzt sie nicht.

Die ursprüngliche Reihenfolge bleibt erhalten:

1. Akzeptierte historische Inhalte mit der Basis vergleichen.
2. Nachweis-, Aktions- und Betriebsprojektionen vollständig validieren.
3. Neue Nachweise, Aktionen und Betriebserklärungen unabhängig nachprüfen.
4. Bei wirksamer Betriebsfreigabe den Provider erneut prüfen. Andernfalls neue
   Beobachtungen und neue positive Aktionsfreigaben zurückweisen; ausdrücklich
   berechtigungsreduzierende Korrekturen bleiben wie im Original zulässig.

Der explizite Legacy-Adapter verwendet die vorhandenen fest begrenzten Git- und
Provider-Leseprofile. Der zusätzliche Git-Port erlaubt genau den ursprünglichen
Baumvergleich der beiden Ledger in ihrer ursprünglichen Reihenfolge. Er nimmt
weder allgemeine Git-Befehle noch Provider-Schreibaufrufe an. Ein Provider muss
für die vom Original verlangten frischen Fakten erreichbar sein; fehlende
Eingaben oder Berechtigungen werden nicht als erfolgreiche Prüfung ausgegeben.

Standardmäßig liegen benötigte temporäre Nachweisdateien im privaten
Kandidatenmodell. `--native-temporaries --temporary-parent /operator/private-tmp`
wählt tatsächliche temporäre Verzeichnisse. Bereits ausgeführte Teilschritte und
ursprüngliche Fehler bleiben im Nachweis sichtbar. Technisch unvollständige
Aufnahmen erhalten keinen erfundenen ursprünglichen Prüfentscheid und starten
keinen automatischen Wiederholungsversuch.

```sh
/path/to/installation/axiom-v2 publication-validation inspect --record /path/to/record
/path/to/installation/axiom-v2 publication-validation replay --record /path/to/record
```

`inspect` bindet den Nachweis an die gewählte Instanz. `replay` benötigt die
passende Produktgeneration und gespeicherte Rohdaten, aber weder die ausgewählte
Quelle noch Provider, Git, Uhren oder native temporäre Verzeichnisse. Rückgabe,
ursprüngliche Ausnahme, Streams, Beobachtungsreihenfolge und verwendete Blobs
werden erneut verglichen. Ein vollständig nachrechenbarer Datensatz kann ein
ursprüngliches Fehlerergebnis enthalten.

Ein zurückgegebener Quellindex kann seine historische
`live_activation_approved`-Angabe enthalten. Diese ist Dateninhalt des geprüften
Quellbestands. Sie überträgt weder persönliche Zustimmung, Betriebsfreigabe,
Compliance noch Veröffentlichungsrecht auf die ausführende V2-Instanz. Die
äußeren Autoritätsangaben bleiben ausdrücklich falsch.

Die Gegenprüfung umfasst den vollständigen ursprünglichen Funktionskörper,
echte vollständige Modell-/Provider-Fixtures, beide temporären Modi und
manipulierte Nachweise. Isolierte Tests einzelner Freigabezweige verwenden
kenntlich gemachte Stand-ins und ersetzen diese vollständigen Vergleiche nicht.
Die signierte Quell- und gemeinsame installierte Mac-/Linux-Abnahme des neuen
Kandidaten bleiben eigenständige Schritte. Der
[aktuelle Goal-Stand](../status/axiom-v2-goal-progress.md) bleibt maßgeblich.
