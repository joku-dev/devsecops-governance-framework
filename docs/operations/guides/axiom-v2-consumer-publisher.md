# AXIOM V2 Consumer-Publisher

Der separate Einstieg `consumer-publisher publish/inspect/replay` erhält den
vollständigen bisherigen Ablauf aus `publish_consumer_lifecycle.py`. Er ist ein
lokaler Entwicklungsstand der Funktionsparität. Aktuelle vollständige Regression,
gebundener Review, Signatur, installierte Mac-/Linux-Abnahme, Peer-Nachrechnung
und fester ha-CPsWMS-Vergleich müssen vor einer abgeschlossenen Produktabnahme
noch nachgewiesen werden.

## Umfang und Freigabeprüfung

Der einzige Scope ist `consumer-lifecycle`; der ursprüngliche Parser verwendet
ihn weiterhin als Standard. Er umfasst neue Consumer-Observations-, Aktions- und
Acceptance-Dateien sowie die beiden ursprünglichen Projektionen. Historische
Consumer-Evidenz bleibt append-only. Andere Source-Änderungen werden abgelehnt;
unbeteiligte erzeugte Berichte werden wie zuvor nicht ausgewählt.

Nach Fetch und Vorfahrenprüfung läuft immer die vollständige
`ConsumerAcceptance.validate_publication`: akzeptierte Source-/Modellpräfixe,
Projektion, neue Receipts, neue Aktionen, neue Acceptance-Captures, persönliche
Provider-Erklärungen und Required-Guard sowie die ursprünglichen Grenzen für
inaktive Consumer. Dafür werden dieselben vollständigen Consumer-Modelle und
Ports einschließlich unabhängiger gepinnter OPA verwendet. Persönliche und
zentrale Guard-Zugriffe behalten ihre bisherigen Zugangsdaten; nur Consumer-
Evidenz kann den gesonderten Lesetoken verwenden. Historische Source-Annahme
verleiht der V2-Instanz keine Betriebsautorität.

Erst danach folgen der neue Automation-Branch, gezieltes Staging, Commit, Push,
PR, beide Pipeline-Ausgaben und die vier Dispatches: Governance CI, CodeQL,
Repository Security und Consumer Lifecycle Guard. Provider-Endpunkte, Akteur,
Umfeldschlüssel und genaue PR-Texte liegen im ausgewählten Adapter. Kern und
Adapter rekonstruieren alle sechs vollständigen Originalfunktionen; der
Consumer-Publisher verwendet seinen eigenen Scope und sein eigenes Protokoll.

## Expliziter nativer Aufruf

Der folgende Aufruf kann Git- und Provider-Schreibzugriffe ausführen. Er setzt
passenden Zugang und eine tatsächlich autorisierte Operation voraus. Eine
Instanz im Modus `paused` aktiviert dadurch keinen dauerhaften Publisher-Dienst.
Das angegebene Workflow-Ref ist ein deklarierter Eingang und kein Nachweis eines
geschützten Workflow-Laufs.

```bash
axiom-v2 --instance /path/to/instance consumer-publisher publish \
  --profile legacy-consumer-publisher-v1 \
  --transport-profile legacy-consumer-publisher-native-v1 \
  --source-worktree /path/to/standalone-consumer-clone \
  --repository owner/repository --run-id 123 --attempt 1 \
  --workflow-ref refs/heads/main
```

Der Schreibadapter verlangt einen eigenen gewöhnlichen Clone mit eindeutigem
Pull-/Push-Ziel. Geteilte Git-Verzeichnisse, externe Filter/Include-Konfiguration,
Source-/Instanzprogramme und umgeleitete Git-Schreibpfade werden nicht implizit
zugelassen. `legacy-consumer-publisher-local-test-v1` erlaubt ausschließlich das
explizit gebundene lokale Test-Remote unter `--local-origin-root`.

`--original-arguments` übernimmt die ursprünglichen Parserargumente als letzten
Abschnitt. Ohne diese Option gelten die ursprünglichen Standardargumente.
`--output-file` und `--summary-file` wählen die ursprünglichen Append-Ziele;
Produkt-, Instanz- und Source-Dateien sind dafür gesperrt. Native Dateimodi,
UTF-8-Schreibschritte, Rückgaben, Prozessstreams und Teilfehler bleiben erhalten.
`--native-temporaries` betrifft die temporären Prüfschritte. Der private
Standardmodus dieser Dateien ist keine Simulation der Git-/Provider-Publikation.

## Nachweise und Nachrechnung

```bash
axiom-v2 --instance /path/to/instance consumer-publisher inspect --record /path/from/record_root
axiom-v2 consumer-publisher replay --record /path/from/record_root
```

Der persistierte Nachweis hält Absicht vor Außenwirkung, ursprüngliche Argumente,
Remote-/Programm-/Node-/Produktbindungen, Rohstreams, Returncodes, ursprüngliche
Fehler und Append-Beobachtungen fest. Er verwendet das begrenzte Consumer-
Journalprofil. `inspect` prüft dieselbe Instanz; `replay` rechnet den gesamten
beobachteten Ablauf ohne gewählten Source-Clone, Client, aktuelle Uhr, erneute
Programme oder Exporte nach. Private Nachweisdateien werden dabei gelesen.

Ein späterer Fehler kann einen bereits erzeugten Commit, Push oder PR
hinterlassen. Technisch unvollständige Aufnahmen liefern `2` und behaupten weder
ursprünglichen Erfolg noch automatische Wiederholung oder Rollback. Ein
konsistenter Nachweis authentifiziert keinen Producer und beweist keinen
unabhängigen externen Abschluss. `official_acceptance`, `production_approval`
und `authority_transferred` bleiben separate Aussagen; der aufgezeichnete
native Prozess darf nicht mit einer neu erteilten Betriebsfreigabe verwechselt
werden. Source-Aliase und vollständige äußere V1-Diagnostik bleiben Teil der
noch offenen Gesamtparität.
