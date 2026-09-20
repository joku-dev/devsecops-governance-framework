# Vertraulicher Funktionsprototyp: zustandsgebundene Autorisierung

Dieser Prototyp untersucht einen einzelnen lokalen Autorisierungskontext für
eine mögliche spätere Patentanmeldung. Er erzeugt reproduzierbare technische
Nachweise. Patentfähigkeit, Erfinderschaft und persönliche Zustimmung sind
keine automatisch abgeleiteten Testergebnisse.

## Einstieg

* [Versuchsvertrag](DESIGN.md): genaue Roots, Schreibgrenze und Vertrauensannahmen.
* [Technisches Dossier](DOSSIER.md): Hypothese, Mechanismus, Vergleich und Grenzen.
* [Vertraulichkeit und Herkunft](DISCLOSURE.md): geprüfter Veröffentlichungsstatus
  und noch zu klärende frühere Offenlegungen/menschliche Beiträge.
* [Ergebnisverzeichnis](evidence/README.md): aufbewahrte Versuchspakete und Prüfsummen.
* [Unterlagen für die Patentberatung](counsel-package/README.md): Problemstellung,
  Lösungsansatz, Architektur, Anwendungsfelder und feste Implementierungsreferenzen
  als PDF und vertrauliches Weitergabepaket.

Der Code liegt vollständig in diesem Versuchsbereich. Die Tests werden über
`tests/test_state_binding_prototype.py` von der normalen Testsuite entdeckt.
Die bestehenden abgenommenen Pilotdateien werden lediglich importiert/gelesen.
Neue Requests und Transaktionen gehören ausschließlich zum Testvertrag 1.

## Versuche wiederholen

Vom Repository-Root aus, mit einem noch nicht vorhandenen Ausgabeverzeichnis:

```bash
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python experiments/state_binding/run_experiments.py \
  --output experiments/state_binding/runs/local-reproduction
python3 experiments/state_binding/verify_evidence.py \
  experiments/state_binding/runs/local-reproduction
```

Der Runner führt 18 Dateisystemversuche aus. Dazu gehören zwei echte Prozesse,
Änderungen zwischen Freigabe und Ausführung, Widerruf, Wiederholung und explizit
gekennzeichnete Versuche mit ausgelassenen Prüfungen. Er führt zusätzlich die
unveränderten bestehenden Tests für Pilot-Aktionen und Betriebsabnahme aus.
Alle automatischen Provider-Erklärungen sind `test_fixture`.

Die erlaubte Operation veröffentlicht den Testinhalt direkt in einem neuen,
atomar geschriebenen JSON-Transaktionsartefakt. Es gibt keinen zweiten externen
Schreibvorgang, keinen Deployment-Aufruf und keine Änderung von Consumer-Repos.
Die Messzeiten betreffen einzelne lokale Versuche; sie sind kein Kapazitätsbenchmark.

`results.json` enthält Quelle, Dateifingerprints und Ergebnisse; `cases/`
bewahrt die tatsächlichen Dateien vor/nach dem Versuch, Anträge und Providerdaten
auf. `REPORT.md` erläutert die Resultate. `MANIFEST.json` bindet alle Paketdateien.
Der eigenständige Prüfer importiert den Prototyp nicht und berechnet Ketten,
Zustandsprojektion, Roots, Zulässigkeit und tatsächlichen Schreibeffekt erneut.

Mit einem außerhalb des Pakets aufbewahrten Digest wird zusätzlich geprüft,
ob das Manifest ausgetauscht wurde:

```bash
python3 experiments/state_binding/verify_evidence.py PFAD_ZUM_PAKET.zip \
  --expect-manifest-sha256 DIGEST_AUS_DEM_ERGEBNISVERZEICHNIS
```

Prüfsummen beweisen Integrität relativ zu einem vertrauenswürdigen Bezugspunkt.
Sie sind keine amtliche Zeitbestätigung oder ein Nachweis des Anmeldetags.

## Persönlicher Demonstrationslauf

Der erste persönliche Lauf wurde am 20. September 2026 erfolgreich ausgeführt.
[Ergebnis und Rohdaten](evidence/PERSONAL-DEMO.md) dokumentieren die von `joku-dev`
abgegebene GitHub-Erklärung und genau eine lokale Testpublikation. Die folgenden
Befehle bereiten einen neuen Lauf vor; dessen Antrag benötigt eine eigene Erklärung.

Der automatische Versuchsrunner gibt keine persönliche Erklärung ab. Für einen
ergänzenden Lauf kann die vorhandene GitHub-Kommentarprüfung verwendet werden:

```bash
.venv-validation/bin/python experiments/state_binding/human_demo.py prepare \
  --workspace experiments/state_binding/human-demo/session-2 \
  --discussion-number PRIVATE_PR_NUMMER --subject-id 81616324
```

Der Befehl prüft, dass das Repository privat und die Diskussion ein PR ist.
Er erstellt `personal-request.json`, `PERSONAL-STATEMENT.txt` und eine Anleitung.
Die benannte Person prüft den vollständigen Antrag und postet die Erklärung
selbst in diesem privaten PR. Der Antrag bindet ausdrücklich nur einen lokalen
Demonstrationsschreibvorgang. Danach:

```bash
.venv-validation/bin/python experiments/state_binding/human_demo.py execute \
  --workspace experiments/state_binding/human-demo/session-2
```

Die Ausführung fragt die Kommentare direkt bei GitHub ab, prüft die tatsächliche
Kontoidentität und Inhaltsbindung und behält dabei die lokale Schreibsperre.
Die vorhandene Bibliothek liest die Kommentare zweimal, um Änderungen während
der Erfassung zu erkennen. Eine fehlende, bearbeitete, widerrufene oder ungültige
Erklärung verhindert den Schreibvorgang. Die komplette Erfassung wird in der
Testtransaktion aufbewahrt. Offline-Replay beweist deren Konsistenz; eine frische
Providerabfrage ist für eine neue Aktion weiterhin erforderlich.

Die Körperlichkeit einer Person bleibt selbst erklärt. Die benannte Rolle ist
eine reine Versuchsrolle und verleiht keine Produktionsbefugnis. Ein echter
persönlicher Lauf ist erst nach tatsächlich erfasster Erklärung nachgewiesen.

## Vertraulichkeit

Das Repository bleibt privat. Dieser Ordner wird nicht in MkDocs, Viewer oder
Release-Pakete aufgenommen. `runs/` und `human-demo/` sind lokal ignoriert;
gezielt ausgewählte Evidence-Pakete unter `evidence/` dürfen ausschließlich in
das private Repository gelangen. `CONFIDENTIAL` sperrt den Docs-Publisher auch
bei einer später versehentlich öffentlichen Repository-Einstellung. Der
Workflow selbst wurde während der Arbeit zusätzlich serverseitig deaktiviert.

## Validierung

```bash
.venv-validation/bin/python -m unittest discover -s tests -p test_state_binding_prototype.py -v
./scripts/validate_all.sh
```

Wenn die globale Git-Konfiguration alle Commits signiert, benötigt ein
bestehender Repository-Test eine prozesslokale Ausnahme für seine temporären
Fixture-Repositories. Der reproduzierbare Validierungsbefehl lautet dann:

```bash
GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign GIT_CONFIG_VALUE_0=false \
  ./scripts/validate_all.sh
```

Das ändert keine gespeicherte Git-Konfiguration und gilt nicht für die späteren
Entwicklungscommits. Die expliziten Signaturtests für Release-Tags bleiben aktiv.

Reale persönliche Freigabe, frühere öffentliche Offenlegungen und anwaltliche
Bewertung bleiben getrennte, ausdrücklich ausgewiesene Nachweise.
