# AXIOM V2: private Intake-Datenhaltung

Dieser interne Baustein erhält die ganze ursprüngliche `Store`-Klasse aus
`consumer_intake_store.py` am V1-Stand
`6b557fefe295b58272d2271326576ca3a3687197`. Alle zwölf Methoden, SQL-Anweisungen,
Transaktionsgrenzen, Retry-Schritte und ursprünglichen Fehler bleiben erhalten.
Nur Pfad-, SQLite- und Zeit-Zugriffe werden explizit übergeben.

Es gibt hierfür noch keinen neuen öffentlichen Operator-Befehl. Der vollständige
Operator mit `poll`, `work`, `status`, `retry`, `resume`, `reconcile-batch`,
`backup`, `verify-backup`, `restore` und `route` sowie Sperren, Backup und Restore
bleibt weitere Goal-Arbeit. Der Baustein aktiviert keinen Collector oder Dienst
und migriert keine bestehende Instanz.

## Kern und native Zugriffe

`private_intake_store.py` enthält den vollständigen fachlichen Algorithmus.
`private_intake_sql.py` bietet die gemeinsame DB-API-Fassade und die reine
Nachrechnung. SQL-Profil und Datentypen sowie vollständige Dateiaufnahmen stehen
in den benachbarten neutralen Modulen. Der Adapter
`providers/private_intake_sql.py` besitzt die tatsächlichen SQLite-Verbindungen,
Cursor, Zeitabfragen und privaten Dateizugriffe.

Das native Profil führt die ursprünglichen Python-SQLite-Aufrufe aus,
einschließlich impliziter Transaktionen und tatsächlicher Fehler. Ein
Connection-Kontextmanager schließt die Verbindung nicht automatisch; eine vom
Original nicht geschlossene Verbindung wird als solche aufgezeichnet und
anschließend getrennt freigegeben. Diese Freigabe wird nicht als ursprünglicher
Programmschritt oder als zusätzlicher erfolgreicher Commit bezeichnet.
Siehe die [Python-SQLite-Dokumentation](https://docs.python.org/3.13/library/sqlite3.html).

Der Adapter verlangt einen expliziten privaten Datenpfad außerhalb von Produkt
und Journal. Er bindet ein gehaltenes Verzeichnis an seine beobachtete Identität
und prüft die vier SQLite-Dateinamen vor und nach Aufrufen auf gewöhnliche,
private Dateien ohne zusätzliche Hardlinks. Diese Prüfungen sind keine
VFS-Isolation gegen konkurrierende Prozesse desselben Benutzers. Der Adapter
behauptet auch nicht, Python aktiviere das C-Flag
[`SQLITE_OPEN_NOFOLLOW`](https://www.sqlite.org/c3ref/open.html).

## Aufzeichnung und Nachrechnung

Vor jedem SQLite-Aufruf wird die Absicht dauerhaft im privaten Journal
festgehalten. Danach folgen das tatsächliche Ergebnis oder der ursprüngliche
Fehler. Die Aufnahme erhält einzelne Verbindungs-, Cursor-, SQL-, Transaktions-
und Zeitaufrufe. Vor dem ersten Verbindungsaufbau und nach dem ursprünglichen
Ablauf samt getrennter Ressourcenfreigabe werden `queue.sqlite3`, WAL, SHM und
Rollback-Journal vollständig aufgenommen, soweit vorhanden. Zwischenstände
werden nicht als zusätzliche vollständige Dateiaufnahmen ausgegeben.

Die Nachrechnung führt die ganze Store-Klasse erneut aus und verbraucht die
aufgezeichneten primitiven Ergebnisse in derselben Reihenfolge. Sie greift weder
auf SQLite noch auf den ursprünglichen Datenpfad oder eine neue Uhrzeit zu.
Sie validiert Anfragen, Typen, Referenzen, vollständige Datei-Bytes und
Ressourcenfreigaben. Sie authentifiziert den Produzenten nicht unabhängig und
berechnet die SQL-Engine-Ergebnisse nicht selbst neu. Eine konsistent erfundene
Produzenten-Aufzeichnung erhält dadurch keine Governance-Autorität.

Geht nach einem tatsächlichen Commit die Ergebnisaufzeichnung verloren, bleibt
die Aufnahme unvollständig. Weitere native Zugriffe werden gesperrt; eigene
Handles werden getrennt freigegeben. Der bereits erfolgte Commit wird weder
als zurückgerollt dargestellt noch automatisch wiederholt.

Das fest ausgewählte Profil begrenzt skalare Werte auf 32 MiB, jede ausgewählte
Datenbankdatei auf 128 MiB und gelesene Zeilen auf 32.768. Zusätzlich gelten die
unveränderten Journal- und Blob-Grenzen des vollständigen Consumer-Profils.
Grenzverletzungen sind technische Unvollständigkeit und kein fachliches Urteil.

## Nachweis und verbleibender Umfang

Differenzielle Tests vergleichen alle zwölf ganzen Methoden mit der vollständigen
unveränderten V1-Quelldatei. Sie prüfen Ergebnisse, native SQL-Folgen und komplette
Datenbank-Bytes bei denselben expliziten Uhrzeiteingaben. Weitere Tests prüfen
Aufzeichnung und Nachrechnung, echte SQLite-Fehler und Rollbacks, die ursprüngliche
Ablehnung eines Version-2-Namensraums, Symlinks, beschädigte Aufnahmen und verlorene
Commit-Ergebnisaufzeichnungen. Deterministische Uhrzeiteingaben in einem solchen
Vergleich sind keine Performance-Messung.

Gezielte grüne Tests ersetzen keine vollständige gepinnte Regression, keinen
gebundenen Review und keine frische signierte Mac-/VM-/Peer-Abnahme dieses neuen
Bausteins. Die Paritätsmatrix behält ihren vollständigen Umfang von 22 Bereichen,
135 Einstiegspunkten, 37 CI-Definitionen und 16 Betriebsabläufen. Betriebsfreigabe,
offizielle Ergebnisannahme und äußere V1-Traceback-Parität bleiben getrennt offen.
