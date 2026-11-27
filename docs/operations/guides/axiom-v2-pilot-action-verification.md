# AXIOM V2: neue persönliche Pilot-Aktionen frisch gegenprüfen

`pilot-action-verification generate/inspect/replay` überführt den vollständigen
ursprünglichen Helfer `verify_new_actions(repo, base_ref, fetch=None,
checked_at=None)`. Der lokale Git-Basisbaum bestimmt, welche Aktionen bereits
aufgenommen waren. Das vollständige ursprüngliche Kontextmodell prüft die
Receipt- und Aktionshistorie. Jede neu hinzugekommene Aktion wird anschließend
frisch mit dem persönlichen Provider-Nachweis verglichen.

Der Helfer erhält die ursprünglichen Prüfungen für Capture-Methode,
Nachweisprojektion, zukünftige Aufnahmezeit, aktuellen Evidence-Head und gültigen
Aktionskontext. Bei einer neuen positiven Aktion werden auch aktive Entscheidung
und Fortschritt erneut beim Provider geprüft. Widerruf und Rollenrückzug behalten
ihre ursprünglichen gesonderten Bedingungen. Der Befehl schreibt weder Aktionen
noch Kommentare und aktiviert keinen Betrieb.

## Aufruf

```console
axiom-v2 --instance /path/node pilot-action-verification generate \
  --profile legacy-pilot-action-verification-v1 \
  --transport-profile legacy-personal-action-git-v1 \
  --source-worktree /path/governance-source \
  --base-ref IMMUTABLE_BASE_COMMIT
```

Die technische Aufnahme verwendet den expliziten Legacy-Adapter für das
ursprüngliche lesende Git-`ls-tree` und feste persönliche GET-Abfragen. Die
Provider-Abfragen lesen Diskussion und Kommentarfolgen zweimal, sodass eine
Änderung während der Aufnahme ein ursprünglicher Fehler bleibt. Zugangsdaten
verbleiben beim ausdrücklich gewählten Provider-Werkzeug. Der Produktkern führt
keine Programme aus der gewählten Quelle aus.

`--checked-at` erhält den expliziten Zeitparameter der ursprünglichen API.
Ohne diesen Parameter werden die tatsächlich beobachteten Uhrzeiten gespeichert.
`--native-capture` wählt den nativen Erfassungsmodus; der Standard verwendet das
private Dateisystemmodell. In beiden Modi bleibt die Quelle schreibgeschützt.
Es werden keine temporären Erfassungsverzeichnisse oder Ledger-Writer benötigt.

## Ergebnis und Grenzen

Der ursprüngliche Rückgabewert zählt frisch geprüfte neue Aktionen. Bereits im
Basisbaum enthaltene Aktionen lösen keine neue persönliche GET-Prüfung aus.
Ursprüngliche Fehler bleiben von technischer Unvollständigkeit getrennt.
Fehlende Eingabebeobachtungen oder Journalverlust liefern keinen erfundenen
ursprünglichen Rückgabewert und starten keinen automatischen Wiederholungsversuch.

`inspect --record PATH` bindet den Nachweis an seine erzeugende Instanz.
`replay --record PATH` rekonstruiert den vollständigen Helfer aus passenden
Produktbytes, gespeicherten Datei-, Git-, GET- und Uhrenbeobachtungen. Dabei werden
weder die gewählte Quelle noch Provider oder Git erneut aufgerufen. Request,
Produktgeneration, Node, Rückgabe, rohe Provider-Streams, Journal und Blob-Abschluss
bleiben Bestandteil der Prüfung.

Die Ausgabe enthält `verification_scope: whole_original_verify_new_actions_helper`
und `structural_ledger_validation_included: false`. Letzteres bezeichnet den
vollständigen übergeordneten Validator einschließlich seiner weiteren Ledger,
Indizes und Viewer; die ursprüngliche Aktions-Kontextprüfung selbst bleibt
Bestandteil dieses Helfers. Die vollständige Validator-Main-, Prefix- und
Publikationsorchestrierung sowie die frische Betriebsabnahme-Prüfung sind weitere
offene Umfänge des Gesamt-Goals.

Die technischen Tests verwenden isolierte vollständige Originalhistorien und
ausdrücklich simulierte Provider-Antworten. Ein Testfeld mit behaupteter ursprünglicher
Capture-Methode ist keine authentifizierte Provider-Provenienz. Technische
Konsistenz überträgt weder persönliche Zustimmung noch Source-, Compliance- oder
Betriebsautorität. Vollständige Repo-Prüfung, revisionsgebundenes Review,
Signierung und aktuelle installierte Mac-/VM-/Peer-/Consumer-Nachweise bleiben
gesonderte Lieferbedingungen.
