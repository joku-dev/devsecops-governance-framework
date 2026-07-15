# Präsentationsanleitung: Typed Evidence Trust

## Zweck

Diese Anleitung beschreibt Schritt für Schritt, wie das Zusammenspiel aus
`governance-framework-demo-consumer` und
`devsecops-governance-framework` als technische Präsentation gezeigt wird.

Die Präsentation beantwortet vier Fragen:

1. Wie erzeugt ein Anwendungs-Repository reale Security-Evidenz?
2. Wie wird diese Evidenz transportiert und einem konkreten Artefakt zugeordnet?
3. Wie prüft die zentrale Governance die Evidenz unabhängig erneut?
4. Wie wird das Ergebnis sichtbar, ohne daraus automatisch eine Freigabe oder
   ein blockierendes Gate zu machen?

Die empfohlene Dauer beträgt 25 bis 35 Minuten. Für eine Kurzfassung können
die optional gekennzeichneten Schritte ausgelassen werden.

## Kernaussage Der Präsentation

> Governance übernimmt nicht blind die Aussage eines Produzenten. Sie sammelt
> die Evidenz, prüft deren Integrität und Aktualität erneut und stellt das
> Ergebnis getrennt von der fachlichen Governance-Entscheidung dar.

Wichtig ist die Trennung dieser drei Signale:

| Signal | Beantwortete Frage |
|---|---|
| Scan-Ergebnis | Welche Vulnerabilities wurden gefunden? |
| Evidence Trust | Sind Identität, Bytes, Alter und Erfassungskontext der Evidenz überprüft? |
| Governance-Ergebnis | Erfüllt die Anwendung die aktuell ausgewerteten Governance-Regeln? |

## Validierter Referenzzustand

Die Präsentation verwendet standardmäßig diesen unveränderlichen Referenzlauf:

| Feld | Referenzwert |
|---|---|
| Consumer | `joku-dev/governance-framework-demo-consumer` |
| Consumer-Commit | `4ec2b2bd53560e010ebb1c078c4d3bd41b0bfcc6` |
| Workflow | `DevSecOps Baseline` |
| Workflow-Lauf | `29432884108` |
| Event und Branch | `push` auf `main` |
| Scanner | Trivy `v0.70.0` |
| Findings | `0`, maximale Severity `none` |
| Collector-Status | `collected` |
| Zentrale Content-Integrität | `pass` |
| Zentrale Freshness | `pass` |
| Effektives Trust-Level | `integrity_verified` |
| Subject Binding | `co_collected`, nicht scanner-attested |
| Enforcement | `report_only` |

Der Referenzlauf ist bereits zentral aufgenommen. Für die Standardpräsentation
muss deshalb weder ein Workflow gestartet noch ein Status-Index verändert
werden.

## Rollen Der Beiden Repositories

| Repository | Rolle in der Demo |
|---|---|
| `governance-framework-demo-consumer` | Baut das Beispielartefakt, führt Trivy aus, normalisiert den Scan und erzeugt den producer-seitigen Trust Record. |
| `devsecops-governance-framework` | Definiert Collector, Schemas und Trust-Semantik, lädt das Artefakt herunter, prüft die Subjects erneut und zeigt den zentralen Status. |

Sprechtext:

> Das Anwendungs-Repository besitzt die Anwendung und erzeugt die Evidenz. Das
> Governance-Repository besitzt die wiederverwendbaren Regeln, Verträge,
> Verifikation und zentrale Sicht. Dadurch muss eine Anwendung die Governance-
> Logik nicht kopieren.

## Teil 1: Präsentation Vorbereiten

### Schritt 1: Lokale Pfade Festlegen

Öffne ein Terminal und setze die Pfade:

```bash
export GOV_REPO=/Users/joku/Development/devsecops-governance-framework
export CONSUMER_REPO=/Users/joku/Development/governance-framework-demo-consumer
export REFERENCE_RUN=29432884108
```

Wenn die Repositories an einem anderen Ort liegen, passe nur die ersten beiden
Variablen an.

### Schritt 2: Sauberen Repository-Stand Prüfen

```bash
git -C "$GOV_REPO" status --short
git -C "$CONSUMER_REPO" status --short
```

Erwartung: Beide Befehle liefern keine Ausgabe.

Prüfe danach Branch und Remote-Stand:

```bash
git -C "$GOV_REPO" branch --show-current
git -C "$CONSUMER_REPO" branch --show-current
git -C "$GOV_REPO" rev-parse HEAD
git -C "$GOV_REPO" rev-parse origin/main
git -C "$CONSUMER_REPO" rev-parse HEAD
git -C "$CONSUMER_REPO" rev-parse origin/main
```

Erwartung:

- Branch ist jeweils `main`.
- Lokaler `HEAD` und `origin/main` stimmen pro Repository überein.

Führe vor einer Präsentation kein unkontrolliertes `git pull` aus. Wenn ein
Update nötig ist, prüfe zuerst die Änderungen und validiere den neuen Stand.

### Schritt 3: Benötigte Werkzeuge Prüfen

```bash
python3 --version
git --version
jq --version
gh --version
gh auth status
```

Pflicht für die lokale Standarddemo sind `python3` und ein Browser. `jq` wird
für gut lesbare JSON-Ausschnitte verwendet. `gh` ist nur für GitHub-Run- und
Artefaktzugriff erforderlich.

### Schritt 4: Governance-Repository Validieren

Beim ersten Lauf oder nach Toolchain-Änderungen:

```bash
cd "$GOV_REPO"
./scripts/bootstrap_validation_env.sh
```

Danach:

```bash
cd "$GOV_REPO"
./scripts/validate_all.sh
```

Erwartete Kernausgaben:

```text
Runtime governance validation passed
Validation passed
OK
```

Die Validierung bestätigt die Konsistenz von Modellen, Schemas, Policies,
Lineage, Statusdaten und Tests. Sie startet keinen neuen Consumer-Lauf.

### Schritt 5: Consumer Validieren

```bash
cd "$CONSUMER_REPO"
PYTHONPATH=src python3 -m unittest discover -s tests
```

Erwartung: fünf Tests laufen erfolgreich.

### Schritt 6: Referenzstatus Prüfen

```bash
jq '.repositories[] |
  select(.repository_id == "joku-dev/governance-framework-demo-consumer") |
  .latest_result' \
  "$GOV_REPO/status/typed-evidence-results-index.json"
```

Prüfe insbesondere:

- `pipeline_run_id` ist `29432884108`
- `pipeline_event` ist `push`
- `branch` ist `main`
- `content_integrity` ist `pass`
- `freshness` ist `pass`
- `trust.effective_level` ist `integrity_verified`
- `enforcement` ist `report_only`

### Schritt 7: Referenzartefakt Vorab Herunterladen

Dieser Schritt ist empfohlen, damit die Präsentation nicht vom Netzwerk
abhängt:

```bash
rm -rf /tmp/evidence-trust-presentation
mkdir -p /tmp/evidence-trust-presentation
gh run download "$REFERENCE_RUN" \
  --repo joku-dev/governance-framework-demo-consumer \
  --name application-evidence \
  --dir /tmp/evidence-trust-presentation
find /tmp/evidence-trust-presentation -maxdepth 3 -type f | sort
```

Erwartete relevante Dateien:

```text
dist/application-source.tar.gz
governance/vulnerability-scan-trust.json
security/trivy-scan.raw.json
security/vulnerability-scan.json
```

Das Verzeichnis unter `/tmp` ist nur eine Präsentationskopie und wird nicht
committet.

### Schritt 8: Viewer Lokal Starten

Starte einen lokalen Webserver in einem separaten Terminal:

```bash
python3 -m http.server 8000 \
  --directory "$GOV_REPO/generated/viewer"
```

Öffne im Browser:

```text
http://localhost:8000/status-viewer.html
```

Prüfe, dass der Bereich **Typed Evidence Trust** sichtbar ist und folgende
Werte zeigt:

| Viewer-Feld | Erwartung |
|---|---|
| Repository | `joku-dev/governance-framework-demo-consumer` |
| Scanner | `trivy v0.70.0` |
| Trust | `integrity_verified` |
| Integrity | `pass` |
| Freshness | `pass` |
| Findings | `0 · none` |
| Subject Binding | `co_collected`, scanner attested: `no` |
| Run | `29432884108` |

### Schritt 9: Browser-Tabs Vorbereiten

Öffne die Tabs in dieser Reihenfolge:

1. Consumer-README oder Consumer-Workflow
2. GitHub-Actions-Referenzlauf `29432884108`
3. lokal heruntergeladene normalisierte Scan-Datei
4. lokal heruntergeladener producer-seitiger Trust Record
5. zentraler Snapshot im Governance-Repository
6. zentraler typed-evidence Index
7. lokaler Status Viewer
8. diese Präsentationsanleitung als Sprecher-Backup

GitHub-URL des Referenzlaufs:

```text
https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/29432884108
```

Relevante lokale Governance-Dateien:

```text
status/typed-evidence-results/joku-dev__governance-framework-demo-consumer/2026-07-15T16-33-38Z-run-29432884108-vulnerability-scan.json
status/typed-evidence-results-index.json
generated/viewer/status-viewer.html
```

### Schritt 10: Präsentationsmodus Vorbereiten

- Browser-Zoom auf eine gut lesbare Größe setzen.
- Benachrichtigungen deaktivieren.
- Terminal-Fenster vergrößern und sensible Umgebungsvariablen nicht anzeigen.
- Keine Token, Secrets oder vollständigen GitHub-Header präsentieren.
- Viewer und Referenzdateien einmal ohne Netzwerk öffnen.
- Einen Screenshot des Viewer-Bereichs als letzte Rückfallebene bereithalten.

## Teil 2: Empfohlener Live-Ablauf

## Schritt 1: Problem Und Ziel Erklären

Zeit: etwa 2 Minuten.

Sprechtext:

> Ein Scanner-Ergebnis allein beantwortet noch nicht, ob die vorgelegte Datei
> echt, unverändert, aktuell und dem richtigen Build zugeordnet ist. Diese Demo
> ergänzt deshalb den Scan um einen expliziten Evidence-Trust-Nachweis.

Zeige zunächst nur die zwei Repositories und deren Rollen. Vermeide zu Beginn
Schema- oder Implementierungsdetails.

Erwartete Publikumsfrage:

> Ist das nur ein weiterer Security Scanner?

Antwort:

> Nein. Trivy bleibt der Scanner. Evidence Trust bewertet die Qualität und
> Nachvollziehbarkeit der vorgelegten Evidenz, nicht die fachliche Zulässigkeit
> einzelner Vulnerabilities.

## Schritt 2: Consumer-Workflow Zeigen

Zeit: etwa 3 Minuten.

Öffne im Consumer:

```text
.github/workflows/devsecops-baseline.yml
```

Zeige in dieser Reihenfolge:

1. Erstellung von `application-source.tar.gz`
2. realer Trivy-Scan
3. Normalisierung des Scanner-Outputs
4. Aufruf des Vulnerability-Collectors
5. Upload von `application-evidence`
6. Aufruf des veröffentlichten DevSecOps-Baselines

Sprechtext:

> Die Anwendung erzeugt ihr Artefakt und ihre Evidenz selbst. Der Collector
> kommt aus dem Governance-Repository. Das Ergebnis bleibt report-only und wird
> zusätzlich zum Governance-Baseline-Lauf erzeugt.

Wichtiger Hinweis:

- Der Workflow nutzt einen realen Trivy-Scan.
- Die Normalisierung ist aktuell ein Consumer-Adapter.
- Der Collector ist ein Pilot und noch kein veröffentlichtes Baseline-Paket.

## Schritt 3: GitHub-Actions-Lauf Zeigen

Zeit: etwa 3 Minuten.

Öffne den Referenzlauf `29432884108` und zeige:

1. Event `push`
2. Branch `main`
3. erfolgreichen Job `Prepare Evidence`
4. erfolgreichen zentralen DevSecOps-Baseline-Job
5. Artefakt `application-evidence`

Sprechtext:

> Dieser Lauf ist kein lokales Beispiel. Er wurde auf `main` ausgeführt und die
> daraus entstandene Evidenz wurde später vom zentralen Governance-Repository
> aufgenommen.

Wenn GitHub nicht erreichbar ist, überspringe die Webansicht und arbeite mit
dem vorher heruntergeladenen Artefakt weiter.

## Schritt 4: Rohscan Und Normalisierung Vergleichen

Zeit: etwa 4 Minuten.

Zeige zuerst den Scanner-Output:

```bash
jq '{SchemaVersion, ArtifactName, ArtifactType,
  Results: [.Results[]? | {Target, Class, Type,
  vulnerability_count: (.Vulnerabilities // [] | length)}]}' \
  /tmp/evidence-trust-presentation/security/trivy-scan.raw.json
```

Zeige danach das normalisierte Format:

```bash
jq '.' \
  /tmp/evidence-trust-presentation/security/vulnerability-scan.json
```

Erkläre:

- Der Rohscan gehört dem Scanner.
- Das normalisierte Format ist der kleine, stabile Collector-Eingang.
- Scanneridentität, Produktionszeit, Findings und maximale Severity bleiben
  nachvollziehbar.
- Die Normalisierung entscheidet nicht, ob Findings akzeptiert sind.

Bei diesem Referenzlauf wurden null Findings beobachtet. Sage ausdrücklich,
dass sich die Zahl bei einem späteren Lauf durch Updates der Trivy-Datenbank
ändern kann.

## Schritt 5: Producer-Seitigen Trust Record Zeigen

Zeit: etwa 4 Minuten.

```bash
jq '{
  effective_level,
  assessment_status,
  verifier,
  verified_at,
  capture: {
    status: .capture.status,
    produced_at: .capture.produced_at,
    captured_at: .capture.captured_at,
    enforcement: .capture.enforcement,
    subjects: .capture.subjects,
    observations: .capture.observations
  },
  selected_checks: [.checks[] |
    select(.id == "content_digest_verified" or
           .id == "freshness_evaluated")]
}' /tmp/evidence-trust-presentation/governance/vulnerability-scan-trust.json
```

Zeige besonders die beiden Subjects:

- `vulnerability_scan_report`
- `evaluated_artifact`

Sprechtext:

> Der Trust Record trägt für beide Dateien Größe und SHA-256-Digest. Damit ist
> klar, welche Scan-Datei und welches Anwendungsartefakt gemeinsam erfasst
> wurden. Diese producer-seitige Aussage ist aber noch nicht die zentrale
> Verifikation.

## Schritt 6: Subject Binding Erklären

Zeit: etwa 2 Minuten.

Zeige:

```text
capture.observations.subject_binding.mode = co_collected
capture.observations.subject_binding.scanner_attested = false
```

Sprechtext:

> `co_collected` bedeutet, dass Collector und Workflow genau diese beiden
> Bytefolgen gemeinsam behandelt haben. Es bedeutet nicht, dass Trivy den
> Digest des Artefakts kryptografisch signiert oder attestiert hat.

Diese Formulierung verhindert, dass das Publikum `co_collected` versehentlich
mit einer signierten Supply-Chain-Attestation gleichsetzt.

## Schritt 7: Zentrale Re-Verifikation Zeigen

Zeit: etwa 5 Minuten.

Öffne:

```text
scripts/intake_evidence_trust_github_actions_run.py
```

Erkläre den Ablauf:

1. GitHub-Metadaten für Repository und Run laden.
2. `application-evidence` herunterladen.
3. genau einen Vulnerability Trust Record suchen.
4. Scan und evaluiertes Artefakt im Paket auflösen.
5. Repository, Commit, Run und Artefakt an die autoritativen Metadaten binden.
6. beide SHA-256-Digests zentral neu berechnen.
7. die 24-Stunden-Freshness erneut auswerten.
8. einen unveränderlichen typed-evidence Snapshot schreiben.

Zeige anschließend den zentralen Snapshot:

```bash
jq '{
  repository_id,
  generated_at,
  pipeline,
  repository,
  source_artifact,
  trust: {
    effective_level: .trust.effective_level,
    assessment_status: .trust.assessment_status,
    verifier: .trust.verifier,
    verified_at: .trust.verified_at,
    selected_checks: [.trust.checks[] |
      select(.id == "content_digest_verified" or
             .id == "freshness_evaluated")]
  }
}' "$GOV_REPO/status/typed-evidence-results/joku-dev__governance-framework-demo-consumer/2026-07-15T16-33-38Z-run-29432884108-vulnerability-scan.json"
```

Hebe hervor:

```text
verifier = central-evidence-trust-intake/v1
```

Sprechtext:

> Die zentrale Governance übernimmt nicht einfach das producer-seitige
> Trust-Level. Sie berechnet die Digests über die heruntergeladenen Dateien
> erneut und ersetzt die Verifikationsbewertung durch ihre eigene Bewertung.

## Schritt 8: Freshness Erklären

Zeit: etwa 2 Minuten.

Sprechtext:

> Freshness ist ein Zeitfenster für die Verwendbarkeit der Evidenz in einem
> bestimmten Entscheidungskontext. Für diesen Pilot gilt maximal 24 Stunden
> zwischen Produktion und Verifikation. Ein veralteter Scan kann weiterhin
> unveränderte Bytes haben, bekommt aber einen separaten Freshness-Fund.

Wichtig:

- Freshness `pass` ist keine Aussage über die Anzahl der Vulnerabilities.
- Freshness `fail` setzt nicht automatisch die Content-Integrität auf `fail`.
- Der aktuelle Finding Effect ist `report_only`.
- Das 24-Stunden-Fenster ist provisional und kann später kontrolliert geändert
  werden.

## Schritt 9: Zentralen Index Zeigen

Zeit: etwa 2 Minuten.

```bash
jq '.summary,
  (.repositories[] |
    select(.repository_id == "joku-dev/governance-framework-demo-consumer") |
    .latest_result)' \
  "$GOV_REPO/status/typed-evidence-results-index.json"
```

Erkläre:

- Snapshots bilden die Historie.
- Der Index projiziert den aktuellen Präsentationszustand.
- Ein `main`-`push` wird als offizieller letzter typed-evidence Stand bevorzugt.
- Ein späterer manueller Diagnoselauf bleibt in der Historie, ersetzt diesen
  Mainline-Stand aber nicht.
- Der typed-evidence Index ist von den DevSecOps- und Architektur-Ergebnis-
  Indizes getrennt.

## Schritt 10: Viewer Als Abschluss Zeigen

Zeit: etwa 4 Minuten.

Öffne im Viewer den Bereich **Typed Evidence Trust**.

Gehe die Spalten von links nach rechts durch:

1. Repository und Evidence Type
2. Scanner und Version
3. effektives Trust-Level
4. Content-Integrität
5. Freshness
6. Findings und maximale Severity
7. Subject Binding
8. Link zum Workflow-Lauf

Sprechtext:

> Der Viewer ist die menschliche Projektion desselben maschinenlesbaren
> Indexes. Er zeigt Evidence Trust bewusst getrennt von Governance-Resultaten.
> `integrity_verified` wertet deshalb weder ein Governance-`pass` auf noch
> ersetzt es eine Vulnerability-Entscheidung.

## Schritt 11: Sicheres Manipulationsbeispiel Zeigen

Zeit: optional, etwa 3 Minuten.

Nutze den vorhandenen Test. Er arbeitet ausschließlich in einem temporären
Verzeichnis und verändert keine committed Evidenz:

```bash
cd "$GOV_REPO"
source .venv-validation/bin/activate
python3 -m unittest \
  tests.test_typed_evidence_intake.TypedEvidenceIntakeTests.test_central_intake_makes_tampered_subject_visible \
  -v
```

Falls das Validierungs-Venv an einem anderen Ort liegt, aktiviere dieses oder
starte den Test über die Umgebung aus `bootstrap_validation_env.sh`.

Erwartung: Der Test ist erfolgreich, weil er bestätigt, dass ein verändertes
Subject zu diesen fachlichen Werten führt:

```text
effective_level = unverified
content_digest_verified = fail
```

Sprechtext:

> Der grüne Test bedeutet hier nicht, dass manipulierte Evidenz akzeptiert
> wurde. Er bestätigt, dass die Manipulation korrekt erkannt und als
> `unverified` projiziert wird.

## Schritt 12: Präsentation Abschließen

Zeit: etwa 2 Minuten.

Fasse zusammen:

1. Reale Scanner-Evidenz wird im Consumer erzeugt.
2. Scan und Anwendungsartefakt werden über Digests identifiziert.
3. Die zentrale Governance prüft die heruntergeladenen Bytes unabhängig.
4. Integrität, Freshness und Binding bleiben eigenständige Trust-Signale.
5. Der Viewer macht diese Signale sichtbar.
6. Enforcement bleibt heute bewusst `report_only`.

Abschlusssatz:

> Die Demo zeigt einen überprüfbaren Evidence-Flow. Der nächste Reifegrad wäre
> nicht eine andere Governance-Logik, sondern stärkere Scanner-Attestations,
> zusätzliche Collector-Profile und kontrolliert eingeführte Blocking-Regeln.

## Teil 3: Empfohlener Zeitplan

| Abschnitt | Dauer |
|---|---:|
| Problem und Repository-Rollen | 3 Minuten |
| Consumer-Workflow und GitHub Run | 5 Minuten |
| Scan, normalisierte Evidenz und Trust Record | 7 Minuten |
| Zentrale Re-Verifikation und Freshness | 7 Minuten |
| Index und Viewer | 5 Minuten |
| Zusammenfassung und Fragen | 3–8 Minuten |

Kurzfassung für 10 Minuten:

1. Rollen der Repositories
2. Referenzlauf und `application-evidence`
3. producer-seitiger Trust Record
4. zentrale Re-Verifikation
5. Viewer
6. Abgrenzung `report_only`

## Teil 4: Optionaler Echter Live-Lauf

Ein echter Live-Lauf ist nur sinnvoll, wenn Netzwerk, GitHub-Berechtigungen und
Präsentationszeit vorher geprüft wurden. Er ist für den Nachweis nicht
erforderlich, weil der zentrale Referenzsnapshot bereits committed ist.

### Variante A: Consumer-Lauf Manuell Starten

Im GitHub UI:

1. `joku-dev/governance-framework-demo-consumer` öffnen.
2. **Actions** auswählen.
3. **DevSecOps Baseline** auswählen.
4. **Run workflow** auf `main` starten.
5. Run-ID notieren und Lauf beobachten.

Terminal-Alternative:

```bash
gh workflow run devsecops-baseline.yml \
  --repo joku-dev/governance-framework-demo-consumer \
  --ref main
```

Danach den jüngsten Lauf suchen:

```bash
gh run list \
  --repo joku-dev/governance-framework-demo-consumer \
  --workflow "DevSecOps Baseline" \
  --limit 5
```

Ein manueller Lauf hat das Event `workflow_dispatch` und ist diagnostisch. Er
soll einen vorhandenen offiziellen `main`-`push` im typed-evidence Index nicht
ersetzen.

### Variante B: Zentrale Intake Manuell Starten

Bevorzugt über das GitHub UI des Governance-Repositories:

1. **Actions** öffnen.
2. **Intake Typed Evidence Trust** auswählen.
3. **Run workflow** wählen.
4. Repository-ID eingeben:
   `joku-dev/governance-framework-demo-consumer`.
5. neue Run-ID eingeben.
6. Artifact Name `application-evidence` beibehalten.
7. Workflow starten und bis zum Commit beobachten.

Voraussetzung:

```text
GH_RESULT_INTAKE_TOKEN
```

Der Token benötigt Leserechte auf die Actions-Artefakte des Consumer-
Repositories. Zeige oder drucke den Token niemals während der Präsentation.

Hinweis: Diese Variante verändert den zentralen Status und erzeugt einen
Commit. Verwende sie nur, wenn die Veränderung für den Termin ausdrücklich
gewollt ist. Für eine reine Präsentation ist der Referenzlauf sicherer.

## Teil 5: Typische Fragen Und Antworten

### Bedeutet `integrity_verified`, Dass Der Scan Gut Ist?

Nein. Es bedeutet, dass die erwarteten Content-Digests über die zentral
verifizierten Subjects reproduziert wurden. Die fachliche Bewertung der
Findings ist davon getrennt.

### Warum Reicht Der Producer-Seitige Hash Nicht?

Weil ein Producer seine eigene Aussage und seinen eigenen Hash gemeinsam
liefern könnte. Die zentrale Stelle muss die heruntergeladenen Bytes selbst
hashen und mit dem gebundenen Record vergleichen.

### Was Bedeutet `co_collected`?

Scan und evaluiertes Artefakt wurden in demselben Collection-Vorgang erfasst.
Es ist keine scanner-signierte Bestätigung, dass der Scanner exakt diesen
Artefakt-Digest attestiert hat.

### Warum Sind Einige Checks `not_evaluated`?

Der aktuelle Pilot prüft insbesondere Content-Integrität und Freshness. Höhere
Trust-Level wie verifizierte Provenance oder Attestation benötigen zusätzliche
Nachweise, die der Pilot noch nicht behauptet.

### Warum Ist Alles Report-Only?

Die Trust-Signale sollen zuerst sichtbar, stabil und mit realen Produzenten
erprobt werden. Blocking erfordert zusätzlich abgestimmte Schwellenwerte,
Ausnahmen, Verantwortlichkeiten und einen Release-Review.

### Kann Das Freshness-Fenster Später Geändert Werden?

Ja. Das 24-Stunden-Fenster ist eine versionierte, provisional Policy. Eine
Änderung muss dokumentiert, getestet und auf bestehende Produzenten bewertet
werden, ohne historische Records still umzuschreiben.

### Was Passiert Bei Einem Veralteten Scan?

Der Freshness-Check wird `fail`. Die Content-Integrität kann trotzdem `pass`
bleiben. Im aktuellen Modus bleibt der Fund sichtbar und report-only.

### Ist Das Bereits Eine SLSA- Oder Sigstore-Attestation?

Nein. Der Pilot modelliert Collection, Digests, Freshness und zentrale
Verifikation. Scanner-attestierte Subject-Bindung und signierte Provenance sind
separate zukünftige Ausbaustufen.

### Kann Das Für Andere Evidence Types Verwendet Werden?

Ja, über zusätzliche Collector-Profile, Schemas, Trust-Regeln und Viewer-
Projektionen. Der aktuell zentral aufgenommene typed-evidence Typ ist
`vulnerability_scan`.

## Teil 6: Troubleshooting

### Viewer Ist Nicht Erreichbar

Prüfe, ob Port 8000 belegt ist:

```bash
lsof -i :8000
```

Nutze alternativ Port 8001:

```bash
python3 -m http.server 8001 \
  --directory "$GOV_REPO/generated/viewer"
```

### Viewer Zeigt Keinen Typed-Evidence-Bereich

```bash
cd "$GOV_REPO"
python3 scripts/generate_typed_evidence_results_index.py
python3 scripts/generate_status_viewer.py
```

Danach Browser vollständig neu laden. Wenn dadurch Dateien geändert werden,
prüfe die Ursache und verwirf oder committe sie nicht unkontrolliert.

### GitHub-Artefakt Kann Nicht Heruntergeladen Werden

```bash
gh auth status
gh auth refresh -s repo
```

Bei privaten Repositories muss das verwendete Token Actions-Leserechte haben.
Nutze für die Präsentation andernfalls die vorbereitete Kopie unter `/tmp`.

### Referenzlauf Hat Ein Anderes Live-Ergebnis

Ein historischer GitHub-Lauf verändert sich nicht. Ein neu gestarteter Trivy-
Lauf kann aber wegen einer aktualisierten Vulnerability-Datenbank andere
Findings liefern. Kehre zum Referenzlauf `29432884108` und dessen committed
zentralem Snapshot zurück.

### Freshness Ist Bei Einer Wiederholten Intake `fail`

Das ist bei einem alten historischen Run erwartbar, weil die zentrale
Verifikation jetzt außerhalb des 24-Stunden-Fensters stattfindet. Für die
Präsentation verwende den committed Snapshot mit der ursprünglichen zentralen
Verifikationszeit. Er beschreibt den damaligen, tatsächlich geprüften Zustand.

### Testumgebung Fehlt

```bash
cd "$GOV_REPO"
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh
```

### Ein Live-Workflow Schlägt Fehl

1. Standarddemo nicht abbrechen.
2. Referenzlauf öffnen.
3. vorbereitete Artefakte unter `/tmp` verwenden.
4. committed Snapshot und Viewer zeigen.
5. Fehler nach der Präsentation separat analysieren.

Ein fehlgeschlagener Live-Lauf ändert nicht die Aussage des bereits
validierten Referenzlaufs.

## Teil 7: Sicherheits- Und Governance-Grenzen

Während der Präsentation keine der folgenden Aussagen machen:

- `integrity_verified` bedeute eine Security-Freigabe.
- null Findings bedeute, dass die Anwendung frei von Schwachstellen ist.
- `co_collected` sei eine kryptografische Scanner-Attestation.
- `report_only` bedeute, dass ein Fund unwichtig ist.
- ein Demo-Pass sei eine formale Produktionsfreigabe.

Stattdessen:

- Trust beschreibt Evidenzqualität.
- Findings beschreiben Scannerbeobachtungen.
- Governance-Ergebnisse beschreiben die ausgewertete Baseline.
- Enforcement beschreibt, ob Findings nur berichtet oder blockierend
  behandelt werden.

## Teil 8: Nach Der Präsentation

Stoppe den lokalen Viewer mit `Ctrl-C` im Server-Terminal.

Entferne die temporäre Artefaktkopie:

```bash
rm -rf /tmp/evidence-trust-presentation
```

Prüfe beide Repositories:

```bash
git -C "$GOV_REPO" status --short
git -C "$CONSUMER_REPO" status --short
```

Wenn die Standarddemo verwendet wurde, sollten beide Worktrees weiterhin
sauber sein. Dokumentiere neue Publikumsfragen als mögliche Ergänzungen des
Runbooks, aber ändere keine Governance-Policy unmittelbar während des Termins.

## Kompakte Checkliste

### Am Vortag

- [ ] Beide Repositories sauber und auf geprüftem `main`
- [ ] Governance-Validierung erfolgreich
- [ ] Consumer-Tests erfolgreich
- [ ] Referenzartefakt heruntergeladen
- [ ] Viewer lokal geprüft
- [ ] GitHub-Run und lokale Fallback-Dateien verfügbar
- [ ] Browser-Tabs vorbereitet
- [ ] Keine Secrets im Terminal sichtbar

### Zehn Minuten Vor Beginn

- [ ] Netzwerk und Bildschirmfreigabe geprüft
- [ ] Viewer gestartet
- [ ] Viewer-Bereich **Typed Evidence Trust** sichtbar
- [ ] Referenzlauf `29432884108` geöffnet
- [ ] Terminal im richtigen Verzeichnis
- [ ] Benachrichtigungen deaktiviert

### Während Der Präsentation

- [ ] Scan, Trust und Governance-Resultat getrennt erklären
- [ ] zentrale Re-Verifikation hervorheben
- [ ] Freshness als separates Signal erklären
- [ ] `co_collected` klar begrenzen
- [ ] `report_only` ausdrücklich nennen

### Nach Der Präsentation

- [ ] lokalen Webserver stoppen
- [ ] temporäre Artefakte entfernen
- [ ] Worktrees auf unbeabsichtigte Änderungen prüfen
- [ ] offene Fragen und Follow-ups notieren

## Weiterführende Dokumente

- `docs/demos/demo-consumer-typed-evidence-trust.md`
- `docs/operations/evidence/vulnerability-scan-collector-usage.md`
- `docs/operations/evidence/evidence-collector-contract.md`
- `docs/operations/evidence/evidence-trust-model.md`
- `docs/operations/evidence/governance-result-intake-and-viewer-usage.md`
- `docs/governance/change-requests/GCR-2026-032-typed-evidence-trust-viewer-projection.md`
