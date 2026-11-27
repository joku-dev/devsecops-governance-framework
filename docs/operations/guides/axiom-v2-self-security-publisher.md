# AXIOM V2 Self-Security-Publisher

`self-security-publisher publish/inspect/replay` erhält alle zwölf ursprünglichen
Funktionen aus `publish_self_security_refresh.py`. Er veröffentlicht materielle
Änderungen der beiden bisherigen Self-Security-Reports als Vorschlag. Aktuelle
vollständige Regression, gebundener Review, Signatur und installierte Mac-/Linux-/
Peer-/ha-CPsWMS-Abnahme bleiben vor einer abgeschlossenen Produktabnahme nötig.

## Erhaltener Ablauf

Der ursprüngliche Main-Einstieg verlangt das deklarierte Main-Ref und prüft die
Self-Security-Projektion des Viewers gegen den JSON-Report. Änderungen außerhalb
der JSON-/Markdown-Report-Allowlist werden abgelehnt; unbeteiligte erzeugte
Dateien werden nicht gestaged. Unvollständige Beobachtungen verhindern die
Publikation. Der bisherige Legacy-Protection-404 wird nur dann ausgenommen, wenn
der Report Ruleset-Schutz ausdrücklich als bestätigt führt. Das authentifiziert
keinen Report-Produzenten.

Die materielle Vergleichsprüfung entfernt ausschließlich die beiden bisherigen
Beobachtungszeiten. Alle anderen Reportwerte bleiben vergleichsrelevant. Reine
Zeitänderungen erzeugen keinen neuen Vorschlag. Es gibt weiterhin nur den festen
Automation-Branch und höchstens einen offenen PR. Ein bestehender PR benötigt
seinen vorhandenen Remote-Branch; ein verwaister Branch verhindert den Lauf.

Erst bei materieller Änderung folgen die ursprünglichen Schritte: Reset des
gewählten Arbeitsbaums, Bereinigung ungetrackter Dateien unter `generated`,
Branchwechsel, gegebenenfalls Merge des aktuellen Main, Wiederherstellung der
zuvor gesicherten Reports, gezieltes Staging, Commit, Push und PR-Erstellung oder
PATCH. Governance CI, CodeQL, Repository Security, Dependency Review und Consumer
Lifecycle Guard werden in derselben Reihenfolge gestartet. Dependency Review
behält seine expliziten Base-/Head-Eingaben. Beide Pipeline-Appends erfolgen erst
nach den Dispatches. Main, Settings und Enforcement werden nicht automatisch
geändert; es gibt weder automatische Freigabe noch Merge des Vorschlags.

## Expliziter nativer Aufruf

```bash
axiom-v2 --instance /path/to/instance self-security-publisher publish \
  --profile legacy-self-security-publisher-v1 \
  --transport-profile legacy-self-security-publisher-native-v1 \
  --source-worktree /path/to/owned-standalone-clone \
  --repository owner/repository --run-id 123 --attempt 1 \
  --workflow-ref refs/heads/main
```

Der Aufruf verändert den angegebenen eigenen Clone und kann native Git- sowie
GitHub-Schreibzugriffe ausführen. Auch die Report-Dateien werden tatsächlich
geschrieben; es gibt für diesen Publish-Ablauf keinen privaten Dateimodus, der
nur eine scheinbare Wiederherstellung vor einem echten Git-Commit vornehmen
würde. Verwende einen dafür vorgesehenen gewöhnlichen Clone. Geteilte Git-
Verzeichnisse, implizite Source-/Instanzprogramme, externe Filter/Includes und
umgeleitete Schreibpfade gehören nicht zum zugelassenen Profil.

`legacy-self-security-publisher-local-test-v1` verlangt ein ausdrücklich unter
`--local-origin-root` gebundenes lokales Test-Remote. Das deklarierte Workflow-Ref
beweist keinen geschützten Workflow oder persönliche Zustimmung. Der Aufruf
aktiviert auch auf einer pausierten V2-Instanz keinen dauerhaften Publisher.
Provider-Endpunkte, genaue Texte, Akteur und Umweltschlüssel sind im Legacy-
Adapter gebunden. `--invocation publish` wählt die ursprüngliche Publikations-
Hilfsfunktion ohne die vorausgehende Main-/Viewer-Prüfung; Standard ist `main`.

## Beobachtete Dateizustände und Nachrechnung

Git verändert zwischen Lesen und Schreiben absichtlich den Arbeitsbaum. Die
Aufnahme hält deshalb die drei bekannten Report-/Viewer-Dateizustände vor und
nach jedem zugelassenen Reset-, Clean-, Switch- und Merge-Schritt fest. Nur diese
beobachteten Übergänge eröffnen eine neue IO-Epoche für den geschlossenen
Dateiraum. Identitäten, Modi, Rohbytes, Returncodes, Teil-Schreibvorgänge und
ursprüngliche Fehler bleiben erhalten. Die Stabilitätsregeln anderer Profile
werden nicht gelockert. Die Beobachtungen sind keine OS-Isolation oder Aussage
über unabhängigen externen Abschluss.

```bash
axiom-v2 --instance /path/to/instance self-security-publisher inspect --record /path/from/record_root
axiom-v2 self-security-publisher replay --record /path/from/record_root
```

`inspect` bindet an dieselbe Instanz; `replay` wiederholt den vollständigen
beobachteten Ablauf aus privaten Nachweisdateien. Gewählter Source-Clone, Client,
Reports und Append-Ziele können dafür bereits entfernt sein. Die Nachrechnung
startet keine Programme und schreibt weder Source noch Provider erneut. Geänderte
Epochen, Identitäten, Absichten oder unvollständige Aufnahmen werden abgelehnt.

Ein Fehler nach Commit, Push oder PR kann sichtbare Teilwirkungen hinterlassen.
Technische Unvollständigkeit liefert `2` und erfindet weder ursprünglichen Erfolg
noch Wiederanlauf oder Rollback. Konsistente Aufzeichnungen übertragen keine
persönliche Zustimmung, offizielle Annahme oder Betriebsautorität.
