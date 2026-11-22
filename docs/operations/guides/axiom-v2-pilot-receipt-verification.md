# AXIOM V2: neue Pilot-Receipts frisch gegenprüfen

`pilot-receipt-verification generate/inspect/replay` führt den vollständigen
ursprünglichen API-Helfer `verify_new_receipts(repo, base_ref)` aus. Im gewählten
Git-Basisbaum bereits enthaltene Receipts werden übersprungen. Für jede neue
Receipt-Datei werden die Provider-Fakten erneut gelesen und das vollständige
Original-Preflight geprüft: Run, Artefakt, rohe ZIP-Bytes, gebundene Producer-Dateien,
Schema, Kriterien und zeitliche Zuordnung. Origin und Producer-Fingerprint müssen
zum gespeicherten Receipt passen; Frische und zukünftige Receipt-Zeitpunkte bleiben
ursprüngliche Prüfungen.

Die reguläre strukturelle Ledger-/Schema-/History-Prüfung gehört weiterhin zum
übergeordneten Validierungsablauf. Dieser Befehl liefert dessen vollständigen
frischen Prüfhelfer. Ausgabe und Nachrechnung tragen ausdrücklich
`verification_scope: whole_original_verify_new_receipts_helper` und
`structural_ledger_validation_included: false`. Der vollständige ursprüngliche
Validator-Main- und Publikationsablauf ist damit noch nicht abgeschlossen.

## Aufruf

```console
axiom-v2 --instance /path/node pilot-receipt-verification generate \
  --profile legacy-pilot-receipt-verification-v1 \
  --transport-profile legacy-preflight-receipt-git-v1 \
  --source-worktree /path/governance-source \
  --base-ref IMMUTABLE_BASE_COMMIT
```

Die Basis muss im lokalen Git-Bestand vorhanden sein. Der lokale Git-Adapter
führt ausschließlich die ursprüngliche lesende `ls-tree`-Abfrage für das
Pilot-Validation-Ledger aus. Netzwerkprotokolle, optionale Locks, Ersetzungen,
implizites Nachladen und externe Git-Konfiguration werden beim technischen
Aufruf begrenzt. Der Legacy-Provider-Adapter verwendet festes Host/GET und den
ursprünglichen Raw-Header; Zugangsdaten verbleiben beim Provider-Werkzeug.
`--provider-executable` wählt dessen ausdrücklich benannten ausführbaren Adapter.

Der Standard verwendet ein privates Modell für temporäre Erfassungsdateien.
`--native-capture` wählt tatsächliche eigene temporäre Verzeichnisse und deren
ursprüngliche Bereinigung. `--temporary-parent` wählt einen eigenen kanonischen
Anker; der private Standard beobachtet den Home-Anker, der native Standard den
System-Temp-Anker. Der Prüfhelfer veröffentlicht kein Receipt im Ledger.
Aufnahmebedingungen und native/partielle Bereinigungsgrenzen entsprechen dem
[Run-Intake](axiom-v2-pilot-run-intake.md).

## Ergebnis und Nachrechnung

Ein vollständiger technischer Nachweis enthält ursprünglichen Exit-Code,
Rückgabewert und Rohbeobachtungen. Der Rückgabewert zählt frisch geprüfte neue
Receipts; null neue Receipts erfordern keine neuen Provider-Aufrufe. Ein
ursprünglicher Fingerprint-/Frischefehler bleibt ein ursprünglicher Fehler.
Nicht beobachtbare Eingaben oder Journalverlust ergeben einen unvollständigen
technischen Nachweis mit unbekanntem ursprünglichem Ergebnis.

`inspect --record PATH` bindet die Nachrechnung an die erzeugende Instanz.
`replay --record PATH` verwendet passende Produktbytes und die gespeicherten
Git-, GET-, Uhren-, Datei- und temporären Beobachtungen. Es liest die gewählte
Quelle nicht erneut und startet keine Programme oder nativen Bereinigungen.
Produkt-, Request-, Node-, Ergebnis-, Journal-, Blob- und Authority-Abschluss
werden vollständig nachgerechnet. Technische Konsistenz authentifiziert weder
Provider noch persönliche Zustimmung und überträgt keine Source-, Compliance-
oder Betriebsautorität.

Die vollständige ursprüngliche Helfer-AST, Rückgaben, reale lokale Git-Abfrage,
GET-Reihenfolge, unveränderte Quelle und reine Nachrechnung werden an isolierten
V1-Vergleichsquellen geprüft. Gefälschte Provider-Daten sind ausdrücklich
Testeingaben. Aktuelle vollständige Repo-Prüfung und signierte installierte
Mac/VM-, Peer- und feste Consumer-Nachweise bleiben eigene Lieferbedingungen.
Das gesamte V2-Goal bleibt offen.
