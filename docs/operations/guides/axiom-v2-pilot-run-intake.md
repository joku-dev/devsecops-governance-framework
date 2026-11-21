# AXIOM V2: frischer Pilot-Run-Intake

Entwicklungsstand: Der vollständige frische Ablauf und die geschlossene
Anwendung sind im Arbeitszweig registriert. Kernel-/Quellvergleiche und
Anwendungsprüfungen bleiben von der vollständigen Repo-Prüfung sowie einer
signierten installierten Mac-/VM-Lieferung getrennt. Das Gesamt-Goal ist offen.

Der Baustein führt den vollständigen ursprünglichen `intake_lifecycle_pilot_run.py`
aus: Betriebsprofil prüfen, frische Rohdaten über den ausdrücklich gewählten
Legacy-GET-Adapter sammeln, das vollständige Bundle prüfen, einen zweiten
Zeitpunkt erfassen und unter dem ursprünglichen Writer-Lock ein Receipt atomar
anhängen. Die temporäre Erfassung wird vor der abschließenden Ausgabe bereinigt.
Exakte erneute Zustellung wird vor der veralteten Sequenz erkannt. Profil,
Vorbereitungs-/Rollenreferenzen und ursprüngliche Producer-Prüfungen bleiben
maßgeblich; ein fremdes Consumer-Profil wird nicht automatisch abgeleitet.

## Bedienung

```console
axiom-v2 --instance /path/node pilot-run-intake generate \
  --profile legacy-pilot-run-intake-v1 \
  --transport-profile legacy-preflight-github-get-v1 \
  --source-worktree /path/governance-source \
  -- --run-id RUN_ID --expected-sequence SEQUENCE
```

Standardmäßig entsteht ein privater Kandidat. Neue Verzeichnisse, temporäre
Dateien, Receipt-Locks, `fsync` und Veröffentlichung sind dabei Modellschritte.
Die gewählte Quelle wird gelesen, aber nicht beschrieben. Der temporäre
Modell-Anker muss eine gewöhnliche eigene Directory-Preimage besitzen; der gespeicherte kanonische Home-Anker ist der Standard. `--temporary-parent`
wählt einen anderen eigenen Anker. Das ist keine Behauptung über den tatsächlichen
System-Temp-Pfad oder künftige native ACL-/Datenträgerverhältnisse.

`--write-selected-files` wählt tatsächliche temporäre Erfassung und Receipt-
Veröffentlichung im `governance/lifecycle/live-validation`-Ledger der gewählten
Quelle. Der native Standard verwendet den gespeicherten kanonischen System-
Temp-Anker. Die ursprünglichen Datei-Modi werden beobachtet. Eigene gewöhnliche,
unveränderte und nicht gemeinsam beschreibbare Pfade sind Aufnahmebedingungen;
der kontrollierte Dienst-/Testkontext verwendet Erzeugungsmaske `077`.

## Nachweise und Fehler

`inspect --record PATH` ist an die eigene V2-Instanz gebunden. `replay --record
PATH` berechnet den gespeicherten Ablauf mit den aktuellen passenden Produktbytes
nach. Eingaben, GETs, Exporte, Uhren und temporäre native Effekte werden dabei
nicht wiederholt. Produkt-, Request-, Node-, Authority-, Ergebnis-, Journal- und
Blob-Abschluss müssen vollständig zusammenpassen; eine neue Instanz erhält
keine ursprüngliche Betriebsautorität.

Capture-Zeit und Receipt-Zeit bleiben getrennte gespeicherte Eingaben. Ein Fehler
beim Verzeichnis-`fsync` kann ein bereits veröffentlichtes Receipt hinterlassen.
Eine anschließende Bereinigungsstörung kann zusätzlich eine teilweise temporäre
Erfassung hinterlassen und unterdrückt die spätere ursprüngliche Ausgabe. Solche
ursprünglichen Fehler unterscheiden sich von technischer Unvollständigkeit.
Ersetzte temporäre Wurzeln oder unbekannte Kinder werden nicht gelöscht;
Finalizer werden auf diesem technischen Abbruchpfad deaktiviert. Nach erfolgtem
ursprünglichem Cleanup-Versuch wird er nicht automatisch wiederholt.

Das ursprüngliche 25-MiB-Capture-Limit bleibt bestehen. Die Base64-Darstellung
kann ein Receipt über 16 MiB erzeugen. Nur dieser Run-Intake wählt deshalb das
feste 64-MiB-Transaktionsdatei-/2-GiB-Wiederholungslesebudget. Andere Ledger-
Profile behalten 16/128 MiB. Große Dateien außerhalb der gewählten
Transaktionsdirectory, zusätzliche/ungebundene Hardlinks, unvollständige
Beobachtungen und implizite Schema-URI-Zugriffe bleiben abgewiesen.

Die ursprünglichen Producer-Fakten sind im Konsistenznachweis gespeichert und
werden durch Offline-Replay nicht unabhängig authentifiziert. Ein technisch
`eligible_for_pilot` bewertetes Receipt erteilt keine persönliche Zustimmung,
Compliance-Freigabe, Source-Autorität, produktive Aktivierung oder Publisher-
Berechtigung. Die Nachprüfung neuer Receipts gegen unabhängige frische Fakten
bleibt ein eigener Einstiegspunkt; sie wird nicht durch diesen Intake ersetzt.

Die vollständige äußere Python-Traceback-Darstellung bleibt ein eigenes offenes
Paritätsthema. Ein erfolgreicher Kernel-/Quelltest ersetzt weder die vollständige
Repo-Prüfung noch signierte installierte Mac/VM-, Peer- und Consumer-Nachweise.
Die zwei Writer-Tests prüfen ein initialisiertes Ledger; konkurrierende erstmalige
Ledger-Provisionierung ist damit nicht nachgewiesen.
