# V2: commitgebundener SBOM-Export

Der Entwicklungskandidat ergänzt den vollständigen bisherigen Export als
`sbom export` und die lesende Nachprüfung als `sbom inspect`. Der neutrale Kern
entscheidet über Commitbindung, SPDX-Inhalt, Polling, Dateireihenfolge und
Rückgabe. Das ausdrücklich gewählte Profil `legacy-commit-bound-spdx-v1`
enthält GitHubs Endpunkte, Identitätsaliasse, Meldungen und Transportregeln.
Ein GitLab- oder Atlassian-Exportprofil ist damit noch nicht implementiert.

## Export starten

In einer installierten, initialisierten V2-Instanz:

```bash
./axiom-v2 sbom export \
  --repository owner/repository \
  --commit <vollständiger-aktueller-main-commit> \
  --token-file /privater/pfad/read-token \
  --output-directory /privater/export/sbom
```

Die Token-Datei muss dem aktuellen Benutzer gehören und privat sein. Ihr Inhalt
wird weder ausgegeben noch in den Nachweisen gespeichert. Es werden keine
gespeicherten CLI-Anmeldungen und keine Umgebungs-Tokens übernommen.

Vor Installation der Python-Abhängigkeiten ist derselbe Ablauf mit der
Standardbibliothek verfügbar:

```bash
python3 -I -S -B scripts/export_axiom_v2_sbom.py export \
  --repository owner/repository \
  --commit <vollständiger-aktueller-main-commit> \
  --token-file /privater/pfad/read-token \
  --state-directory /privater/zustand/sbom \
  --output-directory /privater/export/sbom
```

`--legacy-environment --output legacy` wählt ausdrücklich die bisherige
Umgebungsschnittstelle: `GITHUB_REPOSITORY`, `GITHUB_SHA`, `GH_TOKEN`, optional
`GITHUB_REF` und `SBOM_OUTPUT_DIR`. Sie behält die ursprünglichen Ausgaben und
Rückgaben einschließlich fehlender Variablen bei. Manuelle Identitäts- oder
Credential-Optionen lassen sich damit nicht mischen. Der alte Entwicklungspfad
`scripts/export_repository_sbom.py` ist ein Kompatibilitätseinstieg zum vollständig
erhaltenen Adapter; er gehört weiter nicht zur installierten V2-Oberfläche.

Für öffentliche Repositories ist `--anonymous` eine ausdrücklich gewählte
Alternative zur Token-Datei. Sie sendet keinen Authorization-Header und prüft
vor der Erzeugungsanfrage die öffentliche Sichtbarkeit. GitHub dokumentiert
diesen Zugang für öffentliche Ressourcen; eine erfolgreiche Erzeugung bleibt
vom tatsächlichen API-Ergebnis abhängig.
[GitHub-SBOM-API](https://docs.github.com/en/rest/dependency-graph/sboms?apiVersion=2026-03-10).

## Was der Ablauf prüft

1. Repository, vollständigen SHA und den gewählten Credential-Modus prüfen.
2. Default-Branch und aktuellen Commit lesen; ein anderer Workflow-Ref oder
   veralteter Commit beendet den Ablauf vor der Erzeugungsanfrage.
3. Report anfordern, Herkunft und Kennung der Antwort prüfen und höchstens
   18-mal abfragen. Nur HTTP 202 führt zu weiteren Versuchen mit fünf Sekunden
   Abstand. Ein letzter erfolgloser Versuch wartet nicht zusätzlich.
4. Die temporäre HTTPS-Adresse ohne API-Credential herunterladen. Jede
   Weiterleitung muss die ursprüngliche Host-Allowlist erfüllen; der Download
   ist auf 25 MiB begrenzt. API-Aufrufe folgen keinen Weiterleitungen mit Token.
5. Die unveränderte enge SPDX-2.2/2.3-Prüfung anwenden: Dokument, Paketbestand,
   eindeutig beschriebene Repository-Wurzel und Namens- oder PURL-Identität.
   Das ist keine vollständige SPDX-Schema- oder Schwachstellenprüfung.
6. Default-Branch und Commit erneut lesen. Bei Bewegung entstehen keine
   Exportdateien.
7. `sbom.spdx.json` vollständig schreiben, danach die tatsächliche UTC-Zeit
   lesen und `sbom-metadata.json` schreiben. Ein Fehler beim zweiten Schritt
   kann wie bisher eine bereits geschriebene erste Datei hinterlassen.

Der automatisch gewählte temporäre State-Basispfad wird zunächst kanonisiert,
damit auch der macOS-Systemalias `/var` funktioniert. Ausdrücklich vorgegebene
State-Pfade und das private State-Verzeichnis selbst lehnen Symlinks weiterhin ab.

Ohne `--output-directory` gilt weiterhin `sbom-output` im Arbeitsverzeichnis.
Nur das entsprechende Artefaktverzeichnis direkt im Produkt darf dessen Quelle
überlappen. Andere Produktpfade, State-/Credential-Überlappungen, Symlinks,
Spezialdateien und mehrfach verlinkte Exportdateien werden zurückgewiesen.
Vorherige und nachherige Dateiinhalte bleiben im privaten Nachweis erhalten.
Ein ausdrücklich gewähltes bestehendes Exportziel wird wie bisher überschrieben.

## Ergebnis und Nachprüfung

Die JSON-Ausgabe nennt `record_root`, tatsächliche Rückgabe und Erfassungszustand.
`complete` bedeutet ein vollständig gespeichertes Ablaufprotokoll; auch ein
HTTP-Fehler mit Rückgabe 1 kann vollständig aufgezeichnet sein. Es bedeutet
keinen erfolgreichen Export. Unterbrochene Erfassungen bleiben `incomplete`
und werden nicht fortgesetzt oder als Erfolg behandelt. Der ursprüngliche
vollständige Text steht unter `result.stdout` und `result.stderr` in der privaten
`result.json`; `--output legacy` gibt ihn direkt aus.

```bash
./axiom-v2 sbom inspect --record /privater/zustand/sbom/<record-id>
python3 -I -S -B scripts/export_axiom_v2_sbom.py inspect \
  --record /privater/zustand/sbom/<record-id>
```

Die Nachprüfung prüft registrierte eigene Quell-Fingerprints, Hashkette, begrenzte
Blobs, Operationsreihenfolge, vollständige Dateiinhalte, Uhr und Rückgabe.
Sie führt keine API-Abfragen, Wartezeiten, Uhrabfragen oder Exportschreibvorgänge
erneut aus. Eine nachträglich geänderte Exportdatei verändert den gespeicherten
Nachweis nicht. Die damalige temporäre Downloadadresse kann nicht erneut geprüft
werden: Pfad und Query bleiben ausschließlich im Arbeitsspeicher; gespeichert
werden nur Hash und begrenzte beschreibende Merkmale.

Die Instanzoberfläche bindet zusätzlich ihre eigene Node-Identität. Die
Standalone-Nachprüfung kann dieselbe Aufnahme auf einem anderen Host mit exakt
gleichen registrierten Quellen prüfen. Das ist eine deklarierte Rekonstruktion,
keine unabhängige Bestätigung des Produzenten oder historische API-Attestation.
Trust bleibt `unverified`; weder offizieller Intake noch Publisher, Baseline,
Abnahme oder Betriebsautorität werden aktiviert.

## Aktueller Prüfstand

Der erste Entwicklungsstand bestand auf der VM 32 fokussierte Tests und den
beidseitigen Mac-/Linux-Replay derselben Fehleraufnahmen. Die tatsächlichen
anonymen Erzeugungsanfragen für `joku-dev/ha-CPsWMS` am festgehaltenen Commit
`5c3b5cb50d2260bfbde736c9ac80667271406d99` erhielten auf beiden Hosts HTTP 404.
Es entstanden keine SBOM-Exportdateien. Ein erfolgreicher Live-Export bleibt
offen. Der folgende Stand ergänzt lokale TLS-Tests und die Adapterverlagerung;
diese Tests bestätigen keinen positiven Vendor-Lauf. Vollständige neue
Quellvalidierung, Review, veröffentlichter Kandidat und installierte Abnahme
stehen für diesen SBOM-Baustein noch aus. Der Matrixeintrag bleibt `in_progress`.
