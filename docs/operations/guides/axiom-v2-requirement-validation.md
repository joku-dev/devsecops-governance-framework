# V2: vollständige Prüfung des Anforderungs-Lifecycles

Der Entwicklungskandidat überführt den gesamten bisherigen
`validate_requirement_lifecycle.py` in einen neutralen Prüfkern mit ausdrücklich
gewählten Daten- und Historienadaptern. Er prüft vorhandene Entscheidungen und
Aktivierungen; er trifft keine neuen Entscheidungen und überträgt keine Autorität.
Der Eintrag der Paritätsmatrix bleibt `in_progress`.

## Daten prüfen

In einer initialisierten V2-Instanz:

```sh
./axiom-v2 requirement-validation check \
  --profile legacy-requirement-validation-v1 \
  --source-worktree /privater/pfad/governance-daten
```

Die Quelle ist ein ausdrücklich gewählter Datenarbeitsbaum. Ohne Basisreferenz
benötigt sie keine Git-Historie. Der Prüfer liest Konfigurationen, Schemata,
Katalog, Ledger, Lifecycle-Fälle, referenzierte Quellen und Entscheidungsdateien,
Artefakte sowie OPA- und Plattform-Review-Pakete. Programme aus dieser Quelle
werden nicht geladen oder ausgeführt. Schemata im Datenarbeitsbaum gehören zu den
beobachteten Eingaben; ein gültiges Ergebnis authentifiziert diese Quelle nicht.

Die vollständige bisherige Reihenfolge bleibt erhalten: Schema-Prüfungen,
Policy-/Plattform-Reviews, Katalog und Autoritätsledger, alle Vorschläge und
Aktivierungen, gegebenenfalls Historie, Artefaktregister und Publikationsmanifest.
Das betrifft unter anderem ID-Vergabe, Revisionen, Herkunftshashes,
Entscheidungsreferenzen, Duplikatziele, erlaubte Ableitungen, Äquivalenz und
Schutz veröffentlichter Artefakte. Die bisherige Ablehnung einer Aktivierung
blockierender Durchsetzung bleibt bestehen.

## Änderungen gegenüber einer Basis prüfen

```sh
./axiom-v2 requirement-validation check \
  --profile legacy-requirement-validation-v1 \
  --source-worktree /privater/pfad/governance-daten \
  --base-ref REFERENZ
```

Damit werden die vollständigen bisherigen Vergleiche aktiviert: alte
Katalogrevisionen, unveränderlicher Intake, Vorschlagsfelder, getroffene
Entscheidungen, Analysen nach einer Entscheidung und Aktivierungen. Die Auswahl
geänderter Pfade versucht wie bisher zuerst den Vergleich über die gemeinsame
Historie und bei dessen Fehler den direkten Vergleich einschließlich Arbeitsbaum.
Die Semantik fehlgeschlagener Git-Lektüre bleibt sichtbar unverändert: frühere
Werte können fehlen, Pfadexistenz kann falsch und die Änderungsmenge leer sein.
Das ist keine Bestätigung einer vorhandenen oder vollständigen Historie.
Referenzen werden bei den jeweiligen Lektüren ausgewertet; dies ist keine
historische Attestation einer unveränderlichen benannten Referenz.

Der explizite lokale Adapter startet ausschließlich feste lesende Git-Aufrufe.
Er übernimmt keine Git-Umgebungsüberschreibungen und erlaubt keine Netzwerk-
Nachladung, Hooks oder externen Diff-/Textkonvertierungsprogramme. Native
Objektformate SHA-1 und SHA-256 werden unterstützt. Argumente mit führendem
Bindestrich, Leer-/Steuerzeichen oder mehr als 2.048 Zeichen werden als zusätzliche
Auswahlgrenze abgelehnt.

## Externe Schemaverweise ausdrücklich versorgen

Externe Verweise werden über ausgewählte lokale Dateien aufgelöst:

```sh
./axiom-v2 requirement-validation check \
  --profile legacy-requirement-validation-v1 \
  --source-worktree /privater/pfad/governance-daten \
  --schema-resource https://example.invalid/schemas/regel.json /privater/pfad/regel.json
```

Die Option ist wiederholbar. Auch relative Verweise innerhalb ausgewählter
Ressourcen werden mit deren URI-Kontext aufgelöst; die benötigten externen
Ressourcen müssen jeweils ausgewählt sein. Dateien werden erst gelesen, wenn
der Prüfer ihre URI tatsächlich benötigt. Nicht verwendete Zuordnungen lesen
keine Datei. Die gespeicherten Rohbytes reichen für die spätere vollständige
Nachprüfung aus, auch wenn die Dateien danach entfernt wurden.

Der ursprüngliche Prüfer kann Schemaverweise implizit nachladen. V2 übernimmt
keine automatische HTTP- oder Datei-URI-Lektüre: ein nicht ausgewählter externer
Verweis bleibt ein sichtbarer Auflösungsfehler. Mit gleichen Ressourcenbytes
bleiben die vollständigen ursprünglichen Schemaentscheidungen erhalten. Die
Zuordnung verleiht den ausgewählten Schemata keine Governance-Autorität.

## Ausgabe und gespeicherter Ablauf

Die Standardausgabe nennt den privaten Nachweispfad, Erfassungszustand und Exitcode.
`--format legacy` liefert die gesamte ursprüngliche erfolgreiche oder fehlgeschlagene
Prüfausgabe. Fachliche Prüffehler liefern wie bisher eins; ein erfolgreicher Lauf
liefert null. Unbehandelte ursprüngliche Fehler werden mit Typ und begrenzter Meldung
erfasst. Die Legacy-Ausgabe ergänzt den Fehlertyp als technische Diagnose und erfindet
keinen ursprünglichen Traceback. Unvollständige technische Erfassung liefert zwei.

```sh
./axiom-v2 requirement-validation inspect --record /privater/pfad/nachweis
./axiom-v2 requirement-validation replay --record /privater/pfad/nachweis
```

`inspect` bindet zusätzlich die aktuelle Instanz. Das ausdrücklich portable
`replay` benötigt keine Instanz und prüft dieselben registrierten Produktbytes.
Es rekonstruiert alle Entscheidungen, Ausgaben und ursprünglichen Fehler aus der
vollständigen geordneten Daten-/Historienlektüre. Dabei wird weder die beobachtete
Quelle erneut gelesen noch Git gestartet. Eigene Produktdateien werden weiterhin
für die Prüfung der Codebindung gelesen.

Quelldateien werden begrenzt über gehaltene Deskriptoren gelesen. Aliasse,
Symlinks, Spezialdateien, private Credential-Pfade, ausbrechende Referenzen und
Überlappung mit dem privaten Nachweiszustand sind zusätzliche Aufnahmegrenzen.
Wiederholte Lektüren müssen dieselben Daten beobachten; YAML-Komposition und
Quell-/Protokollmengen sind begrenzt. Die private Erfassung speichert verwendete
Rohbytes, geordnete Metadaten, erfolgreiche lokale Git-Ausgaben und tatsächliche
Fehler. Sie ändert keine Quelldateien oder öffentlichen Ergebnisindizes.

Die Nachprüfung belegt Konsistenz gespeicherter Angaben. Sie authentifiziert
keinen Produzenten und bestätigt keine menschliche Freigabe, aktive Governance-
Entscheidung, Compliance oder Betriebsannahme. Ein Quellenhash oder übernommener
Entscheidungsdatensatz verleiht der neuen Instanz keine Autorität.

## Aktueller Nachweisumfang

Die lokalen fokussierten Prüfungen vergleichen den vollständigen unveränderten
V1-Prüfer, seine Entscheidungsmethoden und den gesamten Hauptablauf einschließlich
Ausgaben und Fehlerreihenfolge. Native Tests verwenden tatsächliche private
Git-Datenarbeitsbäume beider Objektformate, erfolgreiche und fehlgeschlagene
Historienvergleiche, entfernte Quelldaten sowie manipulierte und konsistent neu
gehashte Nachweise. Quellweite gepinnte Validierung und frische identische
Mac-/Linux-Installationskandidaten bleiben vor der Lieferung erforderlich.
