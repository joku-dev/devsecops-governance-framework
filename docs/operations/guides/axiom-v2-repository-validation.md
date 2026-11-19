# V2: vollständige Repository-Prüfung und privates Replay

Der veröffentlichte Repository-Kandidat `cc32bcb` liegt in
[PR #417](https://github.com/joku-dev/devsecops-governance-framework/pull/417).
Er besteht auf dem Mac 19 und auf der VM 18 Prüfgruppen. Der zusätzliche
Linux-Referenztest benötigt die reine Testkorrektur aus
[PR #418](https://github.com/joku-dev/devsecops-governance-framework/pull/418).
Der begrenzte Replay-Worker ist als `cff5fcc` in
[PR #419](https://github.com/joku-dev/devsecops-governance-framework/pull/419)
veröffentlicht. Seine sieben CI-Familien sind grün. Die frische Mac-Installation
besteht 19 Gruppen; der Linux-Treiber ist erfolgreich mit Exit 0 beendet.
Linux-Dateiaudit und der abschließende Hostvergleich benötigen den erneuerten
SSH-Zugang. Diese Nachweise werden ihren jeweiligen Quellen zugeordnet.
Der [Goal-Fortschritt](../status/axiom-v2-goal-progress.md) trennt diese Stände.

## Eine Prüfung ausführen

`validation repository` prüft die Governance-Produktdaten am exakten Commit der
laufenden V2-Installation. Es führt die vollständige ursprüngliche
Repository-Prüflogik mit ihren Generatoren, Unterprüfern, Snapshot-Familien und
Release-Integritätsentscheidungen aus. Consumer-Auswertungen wie ha-CPsWMS
verwenden weiterhin die vorhandenen Consumer-Einstiegspunkte.

Nach Installation eines entsprechend geprüften neuen Kandidaten:

```bash
./axiom-v2 validation repository \
  --profile legacy-repository-validator-v1 \
  --at 2026-11-15T12:00:00Z
```

Der benannte Interoperabilitätsadapter liest auch die ursprünglichen
GitHub-Capture-Formate und Konfigurationsangaben. Er ruft keine GitHub-API auf.
Die Zeit wird explizit gesetzt und bei jedem ursprünglichen Generator-Aufruf
aufgezeichnet. Die Ausgabe enthält eine `assessment_id`, den Zustand und den
vollständigen Ergebnistext. `--output legacy` gibt stdout/stderr unmittelbar aus.
Die Rückgabe ist 0 bei bestandener Prüfung, 1 bei Befunden und 2 bei einer
unvollständigen Ausführung. Ein unvollständiger Lauf kann Teilberichte besitzen.

Standardmäßig werden sämtliche zugelassenen Dateien aus den Git-Blobs des
Produkt-Commits gelesen. Dadurch bleiben Daten verfügbar, die in der sparsamen
Installation physisch fehlen. Für Änderungen in einer separaten Arbeitskopie:

```bash
./axiom-v2 validation repository \
  --profile legacy-repository-validator-v1 \
  --source-worktree /absoluter/pfad/zur/produkt-arbeitskopie \
  --at 2026-11-15T12:00:00Z
```

Diese Arbeitskopie muss denselben HEAD und Git-Baum wie das installierte Produkt
haben. Ihre aktuellen Daten dürfen abweichen; aufgenommen werden begrenzte,
gewöhnliche Dateien und die tatsächliche Verzeichnisreihenfolge. Programme der
geprüften Arbeitskopie werden als Daten aufbewahrt. Ausgeführt werden die
registrierten Funktionen der laufenden Produktruntime und ihre endlichen
Git-/SSH-/OPA-/Krypto-Ports. Private Dateien, Links, Spezialdateien, überschrittene
Budgets oder ein benötigter Pfad außerhalb des geschlossenen Eingabebereichs
verhindern eine vollständige Ausführung.

## Ergebnis prüfen

```bash
./axiom-v2 validation repository-inspect --assessment <assessment_id>
./axiom-v2 validation repository-status
```

`repository-inspect` prüft Node, Runtime, Revision, Git-Baum und das benannte
Profil. Für vollständige Ergebnisse rekonstruiert es alle Entscheidungen aus
den aufbewahrten Bytes und tatsächlichen nativen Beobachtungen. Es vergleicht
die gesamte Ereignisreihenfolge, stdout/stderr/Rückgabe sowie sämtliche
Ausgabedateien. Dabei startet es keine nativen Prozesse zur erneuten Prüfung
der aufbewahrten Eingaben und benötigt die separate Arbeitskopie nicht mehr.
Die unveränderte installierte Produktruntime wird weiterhin für die
Instanzprüfung benötigt.

### Begrenzter Replay-Worker

Der Folgebranch ergänzt einen ausdrücklich ausgewählten Worker für das Replay:

```bash
./axiom-v2 validation repository-inspect \
  --assessment <assessment_id> --bounded-worker
```

Die Anwendung prüft zunächst die aktuelle Instanz und den gespeicherten Lauf.
Ein separater Python-Prozess rekonstruiert danach das vollständige Replay mit
der registrierten Produktruntime. Der Worker läuft unter demselben Benutzer und
liest den privaten Ergebnisdatensatz. Seine Python-Umgebung schließt das aktuelle
Arbeitsverzeichnis, Python-Umgebungsvariablen und Benutzer-Site-Packages aus.
Die Ergebnisdateien und das ursprüngliche Journal bleiben unverändert.

| Grenze | Verhalten |
|---|---|
| Laufzeit | 120 Sekunden, vom Elternprozess überwacht |
| CPU | 60 Sekunden durch das Betriebssystem begrenzt |
| Speicher | 1 GiB gemessener RSS; Kontrolle in Abständen von etwa 100 ms |
| Linux-Adressraum | Zusätzlich 2 GiB durch das Betriebssystem begrenzt |
| Ausgabe | 1 MiB stdout und 64 KiB stderr |

Die RSS-Kontrolle kann eine zwischen zwei Messungen auftretende Spitze nicht
als feste Kernel-Obergrenze garantieren. Unter macOS wird dafür keine
Adressraum-Begrenzung behauptet. Der Elternprozess prüft den eigenen Worker mit
dem festen Systemwerkzeug `ps`. Bei überschrittenem Budget, Prozessfehler oder
ungültiger Antwort beendet er die eigene Prozessgruppe und liefert einen
Fehler; daraus entsteht kein erfolgreicher Replay-Zustand.

Die zusätzliche `worker_observation` nennt Ressourcenprofil, beobachteten
Speicher und Tool-Fingerprints. Sie bleibt eine technische Deklaration.
Unvollständige gespeicherte Läufe behalten ihren bisherigen Zustand. Dieser
Schritt begrenzt das ausdrücklich angeforderte Replay; die Erstellung einer
neuen Repository-Prüfung und die übrige Worker-Orchestrierung sind weiter Teil
des offenen Gesamt-Goals.

| Zustand | Bedeutung |
|---|---|
| `pending_incomplete` | Ein Journal existiert ohne abgeschlossenen Ergebnisbeleg; daraus folgt keine Aussage über einen noch laufenden Prozess. |
| `recorded_incomplete_replay_unverified` | Eine unvollständige Ausführung samt Teilzustand wurde aufgezeichnet. |
| `recorded_complete_replay_unverified` | Eingaben, Ergebnis und Ausgaben sind konsistent gespeichert; das vollständige Replay steht aus. |
| `retained_declared_replay_consistent` | Das vollständige Offline-Replay stimmt mit dem aufbewahrten Lauf überein. |
| `invalid_or_foreign_operation` | Die Statusübersicht konnte den Datensatz nicht dieser aktuellen Instanz zuordnen oder konsistent prüfen. |

Unterbrochene Operationen werden niemals automatisch fortgesetzt oder
überschrieben. Ein neuer bewusster Prüfaufruf erhält eine neue Identität.
`repository-status` prüft abgeschlossene Datensätze einschließlich Replay und
kann bei vielen gespeicherten Läufen entsprechend Zeit benötigen.

## Speicherung und Betriebsgrenzen

Die privaten Datensätze liegen unter
`<instance>/state/repository-validation/operations/<assessment_id>/`.
Verzeichnisse sind nur für den Besitzer zugänglich; Dateien sind privat und
werden exklusiv angelegt. Eingaben und Ausgaben liegen als unveränderliche
Inhaltsblobs vor. Ein dauerhaft geschriebenes Hashketten-Journal bindet Header,
Erfassung, native Einzelaufrufe, Uhren, Generatorwirkungen und Abschluss.
Jeder Schreibabbruch erhält den unvollständigen Zustand.

Generatorwirkungen betreffen ausschließlich den privaten Ausgabedatensatz unter
`generated/`. Die geprüfte Arbeitskopie, Baselines, Statusindizes und historischen
Zustimmungen werden dadurch nicht aktualisiert. Der Vergleich historischer
Ledger macht deren damalige Betriebsautorität nicht zur Autorität dieser Node.
Der Lauf bleibt report-only und aktiviert keinen Publisher oder Dienst.

Ein übereinstimmendes Replay ist deklarierte technische Konsistenz. Es liefert
keine unabhängige Ausführungsattestierung oder persönliche Freigabe. Ursprüngliche
ungefangene Fehler mit einem abweichenden Child-Prozess-Traceback werden als
unvollständig dokumentiert. Die vollständige originale Betriebssystem-Prozess-
Semantik sowie weitere Provider-/Signaturprofile und die gesamte Bootstrap-/Test-
Orchestrierung gehören weiterhin zum offenen Gesamt-Goal.

## Vollständiger Compliance-Lauf: neuer Kandidat

Der veröffentlichte Vorgänger `59c3112` in
[PR #427](https://github.com/joku-dev/devsecops-governance-framework/pull/427)
besteht die vollständige Mac-Paketprüfung mit 2.547 Tests und einer bekannten
Deployment-Auslassung. Die neue Anwendung verbindet die Unterprüfer; ihre
vollständige Paketabnahme ist ein eigener noch offener Nachweis.

In einer passenden installierten Testinstanz mit vorbereiteten Werkzeugen:

```bash
./axiom-v2 validation compliance \
  --profile legacy-extended-compliance-v1 \
  --package /absoluter/pfad/zum/passenden-produktpaket.zip \
  --sha256 <paket-sha256> \
  --at 2026-11-15T12:00:00Z \
  --target-repo /absoluter/pfad/zu/ha-CPsWMS \
  --input-file /absoluter/pfad/zum/pruefeingang.json \
  --output-file /absoluter/pfad/zu/expliziten-exporten/compliance.json
./axiom-v2 validation compliance-inspect --assessment <assessment_id>
./axiom-v2 validation compliance-status
```

Das Paket muss zum exakten aktuellen eigenen Commit, Git-Baum und Host passen.
Der Exportordner muss bereits existieren. Relative Pfade beziehen sich auf das
ursprüngliche Aufrufverzeichnis. Ohne `--target-repo` wird die vollständige
private eigene Quelle geprüft; ohne `--input-file` deren ursprünglicher
Release-Candidate-Beispieleingang. Die Consumer-Quelle wird als Daten gelesen;
ihre Programme und Tests werden nicht gestartet.

Der ursprüngliche Bericht stellt die gewählte Zeit als UTC mit ganzen Sekunden
dar; die angegebene Zeitzone und Genauigkeit bleiben im Erfassungsbeleg erhalten.
Die Inspektion bindet diese Berichtsuhr, die ursprüngliche Textausgabe und alle
Artefakt-Präsenzangaben an den Header und den aufbewahrten Zustand.

Standardmäßig laufen die vollständigen eigenen Unit-Tests. Nur ein bewusster
Aufruf mit `--skip-unit-tests` zeichnet tatsächlich `not_run` auf. Das originale
JSON zeigt dafür weiterhin `pass` und `skipped in nested/test context`.
Die drei ursprünglichen Exporte werden in Originalreihenfolge geschrieben:
Kontroll-JSON, Kontroll-Markdown und Gesamtbericht. Aliase, Überschreiben und
Teilfolgen vor einem Schreibfehler bleiben erhalten. Die Prüfdaten behalten
alle chronologischen Vorher-/Nachherbytes unabhängig von späteren Exporten.

| Rückgabe / Zustand | Bedeutung |
|---|---|
| JSON-Modus, Exit 0 | Vollständige Erfassung und eigene Prüfbereitschaft; Consumer-Befunde bleiben report-only sichtbar. |
| JSON-Modus, Exit 1 | Eigener Repository-Validator oder eigene Tests fehlgeschlagen; außerdem bei ausdrücklich gewähltem `--fail-on-findings`. |
| JSON-Modus, Exit 2 | Unvollständige Erfassung, Abbruch oder ursprüngliche Ausnahme; keine erfolgreiche Gesamtprüfung. |
| `--output legacy` | Ursprüngliche stdout-Ausgabe und ursprünglicher Befundcode 0/1, wenn die Originalentscheidung zurückkehrt. Auch ihr bekannter leerer Integrations-Randfall bleibt sichtbar; Ausnahmen erhalten Exit 2. |
| `pending_incomplete` | Kein vollständiger Workerabschluss; keine Aussage über einen noch lebenden Prozess, keine automatische Fortsetzung. |
| `retained_declared_complete_compliance_consistent` | Vollständige aufbewahrte Unterprüfungen, Quellen, Rohdaten, Reihenfolge und Exporte stimmen überein; keine unabhängige Ausführungsattestierung. |

Private Daten liegen unter `<instance>/state/compliance/operations/<assessment_id>`.
Der feste Elternprozess überwacht den eigenen Worker bis 4.200 Sekunden und
64 KiB je Ausgabestrom; der vollständige innere Testlauf bis 3.600 Sekunden und
8 MiB je Strom. Das ist eine Ausführung unter demselben Benutzer mit begrenzten
bekannten Programmen, keine Kernel-Isolation von Netzwerk, Speicher oder allen
Nachfahren. Vorbereitete gepinnte OPA-/Python-Abhängigkeiten sowie Node, Git und
ein OpenSSL mit den benötigten Signaturfunktionen sind erforderlich.

Export-Symlinks, mehrfach verlinkte Exportdateien, Spezialdateien, Exporte in Produkt/Instanz und überschrittene
Dateibudgets sind sichtbare Zulassungsfehler. Ursprüngliche ungefangene Fehler
werden typisiert festgehalten; ein historischer Prozess-Traceback wird nicht
nachgebaut. Unvollständige Datensätze prüfen die erhaltene Entscheidung und
Teil-Exportbytes, behaupten aber keine vollständige native Gesamtverifikation.
Alle Baselines, Trust- und Betriebsfreigaben bleiben getrennt. Die passende
neue Mac-Paketabnahme und ganzen Originalvergleiche stehen aus; Linux wird auf
Wunsch später geprüft.
