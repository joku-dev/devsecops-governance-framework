# V2: täglicher Betriebsbericht

Der Entwicklungskandidat überführt den ganzen bisherigen Betriebsbericht in
`operations-report generate`. Er umfasst Sammlung, Warnungen, Intake-Gesundheit,
die vollständige Repository-Sicherheitsprüfung und drei Exportdateien. Die
Nachprüfung rekonstruiert denselben Ablauf aus den tatsächlich gespeicherten
Eingaben. Die Paritätsmatrix führt den Baustein als `in_progress`.

## Beobachtungsdatei auswerten

In einer installierten, initialisierten V2-Instanz:

```bash
./axiom-v2 operations-report generate \
  --profile legacy-daily-operations-v1 \
  --observation /privater/pfad/operations-observation.json \
  --as-of 2026-11-15T12:00:00Z
```

Eine normale Beobachtungsdatei wird als bereitgestellte Angabe behandelt. Sie
startet weder Provider-Aufrufe noch Quellscans oder Signaturprüfungen. Ihre
Angaben werden dadurch nicht zu unabhängig bestätigten Schutzfakten.
`--config` wählt bei Bedarf die bisherige vollständige Konfiguration; ohne
diese Option gilt `.github/operations-report.json` aus der installierten Version.
Das vollständige Schema bleibt an die Produktversion gebunden.

## Daten ausdrücklich sammeln

```bash
./axiom-v2 operations-report generate \
  --profile legacy-daily-operations-v1 \
  --source-worktree /privater/pfad/governance-quellen \
  --token-file /privater/pfad/read-token \
  --output-dir /privater/pfad/betriebsbericht
```

Das gewählte Profil enthält die bisherigen GitHub-Endpunkte, Workflow-Namen,
Indexnamen und Darstellungen. Ein GitLab- oder Atlassian-Profil ist damit noch
nicht implementiert. REST liest ausschließlich die zugelassenen Ressourcen;
die einzige GraphQL-Anfrage ist ein festes lesendes PR-Dokument. API-Anfragen
folgen keinen Weiterleitungen. Es werden keine Repository-Einstellungen,
Reviews, Freigaben oder Veröffentlichungen verändert.

Der Token ist optional und muss bei Verwendung als eigene private Datei
vorliegen. CLI-Anmeldungen und Umgebungs-Tokens werden nicht übernommen.
Der ausgewählte Bearer gelangt für die isolierten Workflow-/PR-Aufrufe nur
über stdin an den eigenen Helfer. Tokenwerte stehen weder in dessen Argumenten
noch in den gespeicherten Nachweisen. Ohne expliziten Token bleiben insbesondere
die authentifizierungspflichtigen PR-Daten sichtbar unbekannt. Verweigert die API
Schutzfakten, entstehen daraus keine angenommenen positiven Schutzwerte.

Die lokale Quelle ist ausdrücklich ein Governance-Arbeitsbaum. Der Bericht liest
Register, drei Ergebnisindizes, alle sechs Ereignis-/Versuchs-/Snapshot- und
Konfliktbereiche sowie das Sicherheitsmodell. Die Sicherheitsprüfung verbindet
die sieben bisherigen Schutzabfragen, Workflow-/CODEOWNERS-/Dependabot-Daten und
die tatsächliche Release-Signatur-/Artefaktprüfung. Deren Quellrevision muss zur
Produktrevision passen. Programme aus diesem Arbeitsbaum werden nicht ausgeführt.
API-Repository und lokale Quelle bleiben wie bisher getrennte Eingaben; der Bericht
belegt damit keine gemeinsame oder historische Herkunft beider Quellen.

Eine vorhandene Beobachtungsdatei mit JSON-Inhalt `null` führt im ursprünglichen
Programm zur Live-Sammlung. V2 behält diesen Zweig mit ausdrücklicher Auswahl bei:

```bash
./axiom-v2 operations-report generate \
  --profile legacy-daily-operations-v1 \
  --observation /privater/pfad/null-observation.json \
  --allow-live-fallback \
  --source-worktree /privater/pfad/governance-quellen
```

Ohne `--allow-live-fallback` beendet `null` die Auswertung vor der Sammlung.
Auch mit dieser Option löst ein normaler JSON-Beobachtungswert keine Sammlung
oder Credential-Lektüre aus. Die Reihenfolge bleibt: Konfiguration, Schema,
Konfigurationsprüfung, bereitgestellte Beobachtung, Zeit, gegebenenfalls Sammlung,
Checkout-SHA, kompletter Bericht und Schema-Prüfung, anschließend die Exporte.
`--as-of` geht der Beobachtungszeit vor; fehlt beides, wird wie bisher die aktuelle
UTC-Zeit ohne Mikrosekunden gelesen. Eine vorgegebene Zeit ist keine historische
Attestation der aktuell gelesenen Daten.

## Dateien und Rückgabe

Die JSON-Ausgabe nennt `record_root`, `output_directory`, Erfassungszustand und
Rückgabe. Ohne `--output-dir` liegt das Ergebnis in einem neuen privaten
Artefaktverzeichnis der Instanz. Ein ausdrückliches bestehendes Ziel wird wie
bisher in dieser Reihenfolge überschrieben:

1. `governance-operations.json`: vollständiger Bericht.
2. `operations-observation.json`: vollständige verwendete Beobachtung.
3. `governance-operations.md`: vollständiger bisheriger Markdown-Bericht.

`--format legacy` gibt die ursprüngliche erfolgreiche Konsolenausgabe direkt aus.
Ein erzeugter Bericht liefert auch bei Befunden und unbekannten Fakten Rückgabe
null. Schwellen sind operative Warnungen; der Bericht aktiviert keine Gates.
Unbehandelte ursprüngliche Auswertungs-/Schreibfehler werden mit Typ, begrenzter
Meldung und Rückgabe eins erfasst; V2 erfindet keinen ursprünglichen Traceback.
Die Legacy-Textausgabe meldet den Typ als technische Diagnose.

Ein später Schreibfehler kann wie bisher frühere vollständige Dateien und eine
teilweise geschriebene Datei hinterlassen. Der private Nachweis hält angeforderte
Bytes, ursprünglichen Inhalt und tatsächlichen nachherigen Inhalt fest. Symlinks,
Spezialdateien, Mehrfachlinks und Überlappungen mit Produkt, Quelle, Eingaben,
Credentials oder Instanzzustand werden als zusätzliche Zielschutzregeln abgelehnt.
Quelldateien werden über gehaltene Deskriptoren begrenzt gelesen; bei einem
fehlerhaften Datensatz bleibt der ursprüngliche Abbruch am ersten Fehler erhalten.

`complete` bezeichnet eine vollständig gespeicherte Ausführung, auch wenn diese
mit einem Auswertungs- oder Schreibfehler endete. Ein unterbrochener oder nicht
vollständig erfassbarer Ablauf bleibt `incomplete` und liefert technisch zwei.
Eine unvollständig erfassbare untergeordnete Sicherheitsprüfung wird nicht als
vollständiger Nachweis weitergereicht. Es gibt keine automatische Fortsetzung.

## Gespeicherten Ablauf nachprüfen

```bash
./axiom-v2 operations-report inspect --record /privater/pfad/record
./axiom-v2 operations-report replay --record /privater/pfad/record
```

`inspect` bindet zusätzlich die aktuelle Instanz. Das ausdrücklich gewählte
`replay` ist auch ohne Instanz auf einem anderen Host mit genau gleichen
registrierten Quellen verfügbar. Es verwendet die damaligen Quelldaten,
rohen HTTP-Antworten, vollständigen PR-Seiten, verschachtelten Sicherheits- und
Release-Journale, Uhren, Exportbilder und Rückgaben. Neue native Programme,
Provider-Abfragen, Uhrabfragen oder Lektüre der ursprünglichen Eingabe-/Quelldaten
und Exportschreibvorgänge werden dabei nicht gestartet. Die eigene aktuelle
Produktquelle wird zum Abgleich der Fingerprints weiterhin gelesen.

Der feste Schema-Pfad und seine Rohbytes müssen außerdem mit den Fingerprints
der Produktversion übereinstimmen; das gilt auch für die eigene Standardkonfiguration.
Eine korrekt neu berechnete Hashkette erlaubt keinen Austausch dieser Produkteingaben.

Die Prüfung umfasst den ganzen Bericht und seine Reihenfolge. Sie prüft die
damals gespeicherten Exportbilder; nachträgliche Änderungen an den heutigen
Exportdateien werden dadurch nicht neu bewertet. Die Hashkette und Nachrechnung
authentifizieren keinen Produzenten und bestätigen keine historische API-Antwort.
Trust bleibt `unverified`; offizielle Indizes, Baselines, Publisher, Abnahmen und
Betriebsautorität werden nicht verändert oder übernommen.

## Entwicklungsstand

Die vorherige Bibliotheksintegration besteht auf Mac und Linux 132 gezielte
Tests. Gespeicherte vollständige Sicherheits-/Release-Aufnahmen mit jeweils
16 tatsächlich ausgeführten privaten Git-/SSH-Aufrufen und sieben kontrollierten
API-Leseantworten lassen sich auf dem anderen Host nachrechnen. Das sind
Testdaten, keine positiven SaaS-Live-Nachweise. Der korrigierte vollständige
CLI-Ablauf besteht 14 zusätzliche gezielte Mac-Tests einschließlich
teilweiser Schreibfehler und aller ursprünglichen Exportbytes. Vollständige neue
Quellvalidierung, Review, Commit, passende installierte Mac-/Linux-Kandidaten und
deren aktuelle Abnahme bleiben erforderlich; kein Matrixeintrag ist damit verifiziert.
