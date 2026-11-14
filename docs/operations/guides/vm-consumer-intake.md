# Consumer-Ergebnisse auf der VM sammeln

## Was der Pilot macht

Der Collector fragt alle 15 Minuten den Mainline-Push-Workflow
`.github/workflows/devsecops-baseline.yml` von `joku-dev/ha-CPsWMS` ab. Er verwendet
`l1-baseline-v1.1.3` und das primäre Artefakt `devsecops-pipeline-evidence`.
Auch fehlgeschlagene abgeschlossene Läufe werden gesammelt. Ein fehlgeschlagenes
Governance-Ergebnis kann gültige Evidence sein; fehlende, abgelaufene oder nicht
verifizierbare Evidence bleibt zur manuellen Klärung stehen.

Der erste Start übernimmt nur den neuesten passenden abgeschlossenen Lauf und
aktive Läufe. Anschließend werden alle Seiten seit dem letzten vollständigen
Abruf mit einer Stunde Überlappung verarbeitet. Zeitfenster mit mehr als 1.000
Treffern werden geteilt. Bereits bekannte Lauf-IDs werden zusätzlich abgefragt,
damit spätere Wiederholungsversuche erkannt werden. Vor dem ersten Start liegende
unbekannte historische Läufe werden nicht automatisch nachgeladen.

Die Warteschlange unterscheidet Repository, Domäne, Lauf-ID und Versuch. Ein
Worker verarbeitet höchstens 25 Einträge pro Durchlauf. Discovery und Worker
haben getrennte Sperren; lange Validierungen halten die Discovery nicht auf.
Anfangs läuft alles im Schattenbetrieb ohne eigene Veröffentlichungen.

## Installation und private GitHub Apps

Zuerst die abhängigen Workbench-/IaC-Änderungen und diesen Branch prüfen und in
Main übernehmen. Dann die [Linux-VM-Installation](linux-vm-installation.md) auf
den vollständigen freigegebenen Commit aktualisieren. Die vorhandene URL, der
SSH-Tunnel, Port 8766 und der Workbench-Zugangsschlüssel bleiben nutzbar.

Der Maintainer richtet zwei GitHub Apps ein und bestätigt deren Installationsrechte:

| App | Auswahl | Minimale Rechte |
|---|---|---|
| Reader | Zentralrepository und `ha-CPsWMS` | Metadata, Contents, Actions, Pull Requests: read |
| Publisher | Ausschließlich Zentralrepository | Metadata: read; Contents, Pull Requests: write |

Keine App erhält Administration, Workflow-Schreibrechte, Actions-Schreibrechte
oder einen Branch-Protection-Bypass. Die Apps authentifizieren mit kurzlebigen
Installationstokens; eine Erneuerung erfolgt vor Ablauf. Die Tokens werden nicht
in URLs, Kommandoargumente, Git oder Logs geschrieben. Details zu den Rechten
stehen in der [GitHub-Dokumentation zu Installationstokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app).

Root legt ausschließlich auf der VM diese Dateien mit Modus 0600 an:

```text
/etc/axiom/consumer-reader.pem
/etc/axiom/consumer-publisher.pem       # erst für die spätere Veröffentlichung nötig
/etc/axiom/consumer-intake.json
```

Die JSON-Vorlage liegt in `infra/ansible/consumer-intake.example.json`. App-IDs
und Installation-IDs ersetzen; `mode` bleibt zunächst `shadow`. Schlüsselwerte
gehören weder in Chat noch in das Repository. Danach dasselbe freigegebene
IaC-Update erneut ausführen, damit die Units vorhandene Schlüssel als systemd
Credentials referenzieren. Die Konfiguration wird ebenfalls als Credential
eingelesen. Ohne Reader-Schlüssel und Konfiguration überspringt systemd die
Dienste. IaC erzeugt keine App, vergibt keine Rechte und speichert keine Tokens.

Die Units `axiom-consumer-poll.timer` und `axiom-consumer-work.timer` sind
getrennt. Der erste fragt alle 15 Minuten ab, der zweite startet nach Abschluss
eines Workers nach einer Minute erneut. Ein laufender Worker wird nicht parallel
gestartet. Bei HTTP 429 und Rate-Limit-403 werden `Retry-After` beziehungsweise
Reset-Zeit beachtet. Bedingte GETs verwenden persistierte ETags. Transiente
Fehler erhalten drei Wiederholungen; Zugriffsfehler und ausgeschöpfte Versuche
benötigen nach Behebung einen expliziten Operator-Neustart der Verarbeitung.

## Workbench und offizielle Ergebnisse

Unter **Consumer-Repos** werden getrennt angezeigt:

- offiziell aus zentralem Main übernommene Ergebnisse mit Quell-Commit;
- gesammelte und verifizierte Kandidaten;
- vorbereitete oder offene Übernahme-PRs;
- Fehler und blockierter Abgleich.

Governance-Ergebnis und Evidence Trust sind eigenständige Angaben. Erzeugungszeit,
letzte Abfrage, letzte erfolgreiche Sammlung und Main-Abgleich haben verschiedene
Bedeutungen. Eine frische Abfrage setzt das Alter alter Evidence nicht zurück.
Die Ansicht zeigt bis zu 100 letzte Queue-Einträge, die vollständige Queue bleibt
privat erhalten. Der HTTP-Endpunkt `/api/consumers` benötigt dieselbe Sitzung wie
die Dokumentenarbeit und bietet keine Schreibaktionen.

Der Dienstbenutzer `axiom-intake` besitzt `/var/lib/axiom/consumers` (0700).
Die Workbench liest nur `consumer-view/consumers.json` (0640 in einem Verzeichnis
mit gesetzter Gruppenvererbung). App-Schlüssel, Rohartefakte und SQLite-Datenbank
bleiben unzugänglich. Der Collector schreibt weder per Intake noch per `git pull`
in den aktiven Checkout `/srv/axiom/repository`.

Main wird in einer separaten Arbeitskopie auf einen vollständigen Commit
festgelegt. Skripte, Schemas, Modelle, Policies, Pakete und gesperrte Abhängigkeiten
müssen exakt zur installierten Anwendung passen. Bei Änderungen erscheint
**Anwendungsupdate erforderlich**; nach einem geprüften IaC-Update kann der
Operator fortsetzen. Das bisherige akzeptierte Ergebnis bleibt mit seinem alten
Quell-Commit sichtbar. Ein akzeptierter Stand wird erst nach Validierung atomar
als eine vollständige Projektion veröffentlicht.

## Schattenvergleich und kontrollierte Umschaltung

1. Mindestens 24 Stunden im Modus `shadow` sammeln. Der bestehende GitHub-Intake
   bleibt währenddessen Eigentümer. Mindestens ein nach dem Collector-Start
   erzeugter realer Mainline-Lauf muss in beiden Wegen vorliegen. Identität,
   Commit, Baseline, Verdict, Checks und Artefakt-Digests müssen übereinstimmen;
   unterschiedliche Erfassungszeiten sind zulässig. Ohne neuen Lauf bleibt
   die Umschaltung gesperrt.
2. Collector pausieren. Aktive zentrale Intake-Läufe und bestehende operative
   PRs abwarten oder ausdrücklich abgleichen. Keine verdeckte Parallelübernahme.
3. In einem eigenen geprüften zentralen PR den Eintrag für `ha-CPsWMS/devsecops`
   in `config/consumer-intake-routing.json` auf `owner: vm` setzen. Erst nach
   dessen Merge überspringt der bestehende zentrale Workflow neue Intake-Jobs
   für dieses Paar. Andere Consumer und Domänen bleiben bei GitHub Actions.
4. Publisher-Schlüssel bereitstellen, Units über IaC erneuern, private
   Konfiguration auf `mode: publish` setzen und die Verarbeitung fortsetzen.
   Der Collector prüft Route und Schattennachweis erneut. Offene alte
   `automation/devsecops/`-PRs verhindern eigene neue VM-Batches.
5. Höchstens 25 verifizierte Ergebnisse werden auf einen eingefrorenen Batch
   gebunden. Ein serialisierter Publisher erzeugt höchstens einen offenen VM-PR.
   Seine Beschreibung nennt VM-Batch, Basis-Commit, Manifest und echte
   Producer-Läufe. Es gibt keine erfundene zentrale Actions-Lauf-ID.
   CI, menschlicher Review und Merge bleiben erforderlich.

Weitere Ergebnisse warten bis zum Abschluss des offenen PRs. Ein geschlossenes,
nicht gemergtes PR wird als `not_accepted` beendet und nicht automatisch neu
eröffnet. Bereits erzeugte Branches/PRs werden nach einem Neustart anhand der
deterministischen Batch-ID wiedergefunden. Historische Snapshots sind unveränderlich.
Wenn Main vor Fertigstellung eines vorbereiteten Batches fortgeschritten ist,
pausiert dieser zur manuellen Abstimmung; kein Force-Push repariert ihn automatisch.
Nach Prüfung eventuell schon erzeugter Remote-Branches/PRs kann der Operator im
Modus `paused` mit `reconcile-batch --batch-id BATCH_ID` den vorbereiteten Batch
historisch als aufgegeben markieren und seine Kandidaten für einen neuen Batch
auf dem bereits akzeptierten neueren Main vormerken. Das schließt keine PRs.
Ein noch offener fremder oder nach Restore nicht zugeordneter VM-PR blockiert
weiterhin jede neue Veröffentlichung und muss zuerst ausdrücklich geklärt werden.

Rollback: Publisher pausieren, offene Batches ausdrücklich abgleichen, Route in
einem geprüften PR auf `github-actions` zurücksetzen. Es gibt keinen automatischen
Failover. Beim Anwendungs-Downgrade auf eine Version ohne Collector-Unterstützung
verwendet IaC vor dem Umschalten das noch installierte Backup-Werkzeug und
deaktiviert die Collector-Timer. Queue und Rohdaten bleiben erhalten. Fehlt ein
geeignetes Backup-Werkzeug, wird die Umschaltung angehalten.

## Operator-Befehle und Sicherungen

`status` liest ohne App-Schlüssel. Für Wiederaufnahme und manuelle Wiederholung
benötigt der Prozess Zugriff auf die private Konfiguration. Auf der VM:

```bash
sudo -u axiom-intake /usr/bin/python3 \
  /srv/axiom/repository/scripts/consumer_intake.py status
sudo systemd-run --wait --pipe --collect --uid=axiom-intake \
  --property=LoadCredential=operator-config:/etc/axiom/consumer-intake.json \
  /usr/bin/python3 /srv/axiom/repository/scripts/consumer_intake.py resume \
  --config %d/operator-config
```

Für eine manuelle Wiederholung im zweiten Befehl `resume` durch
`retry --run-id RUN_ID --attempt ATTEMPT` ersetzen. Die schreibenden Befehle
laufen als Eigentümer der Operations-Dateien; nicht als Root oder Workbench-
Benutzer direkt in diese Queue schreiben. Ein Service-Neustart allein hebt eine
dauerhafte Fehlerpause nicht auf.

Der Rohcache ist auf 1 GiB begrenzt. Vor Downloads werden Cachebudget und freier
Speicher mit 8 GiB Reserve zuzüglich Downloadbudget geprüft. Bei Platzmangel
bleibt die Metadatenabfrage nutzbar. Staging und Sicherungen verbrauchen ebenfalls
freien Speicher. Historische Evidence und Backups werden nicht automatisch
gelöscht. Die zweite VM-Platte wird nicht eigenmächtig formatiert oder eingebunden.

IaC stoppt die Collector-Dienste vor einer Aktivierung und sichert SQLite über
die Backup-API. Rohcache, verifizierte Kandidaten und akzeptierte Generationen
werden separat kopiert und mit einem SHA-256-Manifest geprüft. Diese Dateien
werden zusätzlich zum Controller übertragen und dort erneut geprüft. Die
512-MiB-Grenze des Workbench-ZIP wird dafür nicht vergrößert. Credentials gehören
nicht in diesen Backup-Satz und benötigen eine getrennte private Wiederherstellung.

```bash
python scripts/consumer_intake.py backup --destination /PRIVATE/NEW-BACKUP
python scripts/consumer_intake.py verify-backup --destination /PRIVATE/NEW-BACKUP
python scripts/consumer_intake.py restore --destination /PRIVATE/NEW-BACKUP \
  --root /PRIVATE/NEW-EMPTY-OPERATIONS-ROOT
```

Backup hält beide Operations-Sperren. Restore erfordert gestoppte Dienste und
einen noch nicht vorhandenen Zielpfad; vor dem Wiederanlauf Dateieigentümer,
Credentials und Projektion prüfen. Die Workbench-Drafts sind ein eigener Backup-Satz.

Die synthetischen Queue-/API-Tests mit 1.000 und 2.000 Repositories prüfen
Algorithmik und Persistenz. Sie sind keine Lastzusage für einen produktiven
Fleet-Betrieb. Externe Queue, Objektspeicher, Worker-Pool und Lastmessungen bleiben
Folgeschritte.
