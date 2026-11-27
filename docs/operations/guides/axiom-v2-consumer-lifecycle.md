# AXIOM V2: Consumer-Lifecycle

`consumer-lifecycle` erhält den vollständigen ursprünglichen Runner
`run_consumer_lifecycle.py` sowie seine Evidenz-, Receipt-, Aktions- und
Betriebsannahmeprüfungen. Der Baustein ist in Arbeit; die vollständige signierte
Quell-, Installations- und Host-Abnahme des aktuellen Kandidaten steht aus.

## Ablauf ausführen

Verwende eine eigene, initialisierte und pausierte V2-Instanz und einen getrennten
Governance-Quellbestand. Alle ursprünglichen Argumente stehen nach `--`:

```bash
axiom-v2 --instance /path/to/instance consumer-lifecycle generate \
  --profile legacy-consumer-lifecycle-v1 \
  --transport-profile legacy-consumer-readonly-v1 \
  --source-worktree /path/to/governance-source \
  --temporary-parent /path/to/private-temporaries \
  -- --operation validate
```

Die ursprünglichen Operationen sind `prepare-acceptance`, `preflight`,
`acceptance`, `observe`, `action`, `refresh` und `validate`. Beispiele:

```text
--operation prepare-acceptance --discussion-number 123
--operation preflight --source-run-id 123456 --output /path/to/new-capture
--operation observe --source-run-id 123456
--operation action --request-path model/governance/lifecycle/consumer-operation/action-requests/example.json
--operation validate --base-ref FULL_COMMIT --verify-provider
```

Das Legacy-Profil prüft weiterhin den einzelnen neutralen Demo-Consumer aus dem
ursprünglichen Modell. Es wird nicht automatisch auf ha-CPsWMS oder einen anderen
Consumer umgestellt. Persönliche Kommentare werden gelesen, nicht gepostet.
Aktionen benötigen ihre eigenen gebundenen Erklärungen, Rollen, Revisionen und
Evidenzen. Der Aktionsantrag muss wie bisher in Git erfasst sein. Die vollständige
unabhängige OPA-Prüfung verwendet die geprüfte OPA-Version der Instanz und die
unveränderte, im Originalprofil fixierte Policy. Source-Programme werden nicht
geladen oder ausgeführt.

Eine Symlink-Auswahl aus einer Python-Umgebung darf auf die freigegebene externe
OPA-Datei zeigen. Auswahlname, tatsächlich aufgelöste Datei, Hash und Identität
bleiben gebunden. Tatsächliche private Werkzeugziele, Programme im gewählten
Quellbestand oder in der Instanz sowie unbekannte Hashes werden weiterhin
abgewiesen. In einer VM gehört die reguläre OPA-Datei ins separate
Werkzeugverzeichnis; eine normale Binärdatei unter `venv` ist keine solche
Auswahlverknüpfung.

Eine neue Offline-Installation wählt dafür die bereits über Paket-Hash,
Manifest und Version geprüfte Datei `<prefix>/package/opa` als Instanzwerkzeug.
Sie liegt außerhalb des Produktquellbestands und des Instanzzustands. Die
zusätzliche Datei unter `<prefix>/venv/bin/opa` bleibt für die Python-Umgebung
verfügbar; sie wird nicht als Werkzeugziel des Consumer-Adapters ausgewählt.
Bereits bestehende Instanzen werden dadurch nicht nachträglich verändert.

Für Consumer-Evidenz verwendet der Adapter gegebenenfalls
`CONSUMER_EVIDENCE_TOKEN`. Persönliche Erklärungen und der zentrale Required-Guard
verwenden weiterhin die normale zentrale Client-Anmeldung. Der Publisher-Token
wird nicht im Prozessumfeld des aufrufenden Programms ersetzt. Zugangsdaten
werden nicht als Teil des Nachweises gespeichert. Ein beobachteter Client und
konsistente gespeicherte Bytes authentifizieren allein keinen Producer.

## Dateimodi und Nachrechnung

Standardmäßig entstehen private Projektionen der ursprünglichen Dateischritte.
OPA erhält dafür kurzlebige private Eingabedateien; Erzeugung, genaue Bytes,
Prozessabschluss und Entfernung werden aufgezeichnet. Der gewählte Quellbestand
wird dabei nicht exportiert. `--write-selected-files` vor `--` wählt die
ursprünglichen nativen Datei-, Lock-, Hardlink- und temporären Schritte. Ein
späterer ursprünglicher Fehler kann bereits geschriebene Dateien hinterlassen.

```bash
axiom-v2 --instance /path/to/instance consumer-lifecycle inspect --record /path/from/record_root
axiom-v2 consumer-lifecycle replay --record /path/from/record_root
```

`inspect` bindet die Aufnahme an dieselbe Instanz; `replay` benötigt keine
Instanz, Quelldateien, Client-Anmeldung, aktuelle Uhr oder ausführbaren Programme.
Beide rechnen den ganzen aufgezeichneten Ablauf nach und wiederholen keine
nativen Aktionen. `--format legacy` gibt die gespeicherten ursprünglichen
Streams aus. Technisch unvollständige Aufnahmen liefern `2` und behaupten keinen
ursprünglichen Befund oder automatischen Wiederanlauf.

Das eigene Consumer-Profil begrenzt das Journal auf 65.536 Ereignisse und
128 MiB sowie native Ausgabeoperationen auf 4.096. Datei-, Blob-, Ledger-,
Eigentums-, Identitäts- und Reihenfolgeprüfungen bleiben erforderlich. Die
kleineren bestehenden Profile behalten ihre Grenzen. Grenzüberschreitungen
sind technische Unvollständigkeit. Der private Modus ist ein Dateisystemmodell;
er verspricht keine native Sperrwirkung, ACL-Garantie oder Isolation gegenüber
anderen Prozessen desselben OS-Benutzers. Rohdiagnostik behält tatsächliche
Materialisierungspfade; vollständige äußere V1-Tracebacks, Source-Aliase und
weitere Host-Diagnostik gehören weiterhin zur offenen Paritätsarbeit.

Retained Betriebsannahmen und Source-Projektionen erteilen dieser V2-Instanz
keine persönliche Zustimmung, offizielle Annahme oder Betriebsautorität. Der
separate [Consumer-Publisher](axiom-v2-consumer-publisher.md) ist als eigener
Ablauf angebunden. Ebenso stehen vollständige Regression,
aktueller Review, Signatur, Installation und der feste ha-CPsWMS-Vergleich aus;
die Gesamtparität ist dadurch nicht abgeschlossen.
