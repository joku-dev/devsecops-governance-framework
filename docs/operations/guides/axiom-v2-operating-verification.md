# AXIOM V2: gespeicherte Betriebsabnahme frisch gegenprüfen

`operating-verification generate/inspect/replay` stellt die drei vollständigen
ursprünglichen API-Helfer `collect`, `verify_provider` und `verify_new_captures`
über ausdrücklich gebundene Datei-, Git-, Provider- und Uhrenports bereit.
Die gewählte Quelle bleibt schreibgeschützt. Persönliche Erklärungen werden
nicht veröffentlicht; der ausführenden V2-Instanz wird keine Betriebsfreigabe
übertragen.

## Operationen

```console
axiom-v2 --instance /path/node operating-verification generate \
  --profile legacy-operating-verification-v1 \
  --transport-profile legacy-personal-operating-git-v1 \
  --source-worktree /path/governance-source \
  --operation verify-new-captures \
  --base-ref IMMUTABLE_BASE_COMMIT
```

`verify-new-captures` unterscheidet die im Git-Basisbaum bereits enthaltenen
Aufnahmen von neuen Aufnahmen. Für jede neue Aufnahme bleiben die ursprüngliche
frische Nachweisprüfung, zukünftige Aufnahmezeit und gegebenenfalls der exakte
Implementierungsmanifest-Vergleich erhalten. Bei einer neuen wirksamen
Indexprojektion wird der Provider auch ohne neue Aufnahme erneut geprüft.

`--operation verify-provider` vergleicht den frischen persönlichen Nachweis mit
der letzten gespeicherten Aufnahme und prüft die ursprüngliche Wirksamkeit in
der gewählten Quelle. `--operation collect` liefert den ursprünglichen frischen
Snapshot als Rückgabewert im privaten technischen Nachweis. Das gesonderte
Anhängen einer Aufnahme durch `capture` ist ein weiterer Betriebsablauf.
Für `collect` und `verify-provider` wird keine Git-Basis angegeben.

`--checked-at` erhält den ursprünglichen optionalen Zeitparameter von `collect`
und `verify-new-captures`. `verify-provider` verwendet seine ursprüngliche
beobachtete Uhr. Auch eine von `verify-new-captures` zusätzlich aufgerufene
Provider-Prüfung behält diese eigene Uhr. Leere Zeitangaben erhalten die
ursprüngliche Rückfalllogik. Gespeicherte Testzeitpunkte authentifizieren keine
frischen Live-Fakten.

## Git- und Ergebnistreue

Der Legacy-Adapter erlaubt die ursprüngliche lesende `ls-tree`-Abfrage für die
Betriebsabnahme-Aufnahmen und die binäre `git show BASE:INDEX`-Abfrage für den
festen Live-Index. Letztere erhält die Semantik von `subprocess.run` mit
aufgenommenen Standardstreams: Auch ein nicht erfolgreicher oder negativer
Rückgabecode ist ein Ergebnis. Aufgenommenes Git-stderr wird dabei nicht als
geerbtes stderr ausgegeben. Ein fehlender Basis-Index kann deshalb wie im
Original eine erneute Provider-Prüfung auslösen.

Das bisherige `check_output` für die Pfadauswahl behält seine eigene Semantik:
Textdekodierung, geerbte rohe Fehlerausgabe und ursprüngliche Ausnahme bei einem
Fehlerstatus. Die zusätzliche technische Zeitgrenze einer lokalen Git-Erfassung
ergibt bei Überschreitung einen unvollständigen Nachweis. Sie wird nicht als
ursprünglicher Timeout oder Governance-Befund ausgegeben.

Vollständige technische Aufnahmen enthalten ursprünglichen Rückgabewert,
Ausnahmen, rohe Streams, geordnete Beobachtungen und alle referenzierten Blobs.
`inspect --record PATH` bindet die Nachrechnung an die erzeugende Instanz.
`replay --record PATH` rekonstruiert die gewählte vollständige Originaloperation
ohne erneute Quell-, Git-, Provider- oder Uhrenzugriffe. Nicht beobachtbare
Eingaben oder Journalverlust liefern keinen erfundenen ursprünglichen Befund.

## Aussagegrenze

Die Ausgabe nennt den gewählten vollständigen Helfer als `verification_scope`
und kennzeichnet die übergeordnete strukturelle Gesamtprüfung mit
`structural_ledger_validation_included: false`. Die ursprünglichen
Kontext-, Historien-, Projektions- und Manifestprüfungen innerhalb des Helfers
bleiben erhalten. Vollständiger Validator-Main, akzeptierter Git-Prefix,
Publikationsorchestrierung und übrige Betriebsabläufe sind weitere offene
Umfänge des Gesamt-Goals.

Ein ursprünglicher Snapshot kann eine Betriebsabnahme seiner ursprünglichen
Quelle beschreiben. Dieser gespeicherte Wert aktiviert die V2-Instanz nicht.
Die Tests verwenden isolierte private Kopien unveränderter V1-Dateien. Nur in
solchen Testkopien wird ein Implementierungsmanifest passend zur simulierten
Erklärung erzeugt. Das ist keine Änderung oder Freigabe der akzeptierten
Repository-Betriebsabnahme. Vollständige Repo-Prüfung, revisionsgebundenes Review,
Signierung und aktuelle Mac-/VM-/Peer-/Consumer-Liefernachweise bleiben
gesonderte Bedingungen.
