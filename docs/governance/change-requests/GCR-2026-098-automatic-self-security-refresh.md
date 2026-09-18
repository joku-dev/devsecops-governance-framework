# GCR-2026-098: Automatic Self-Security Refresh

## Intent

Der versionierte Self-Security-Bericht und seine Viewer-Projektion sollen dem
täglich ermittelten Live-Stand folgen, ohne direkte Commits nach `main`,
Zeitstempel-Rauschen oder automatische Freigaben zu erzeugen.

## Artifact Classification

| Field | Decision |
|---|---|
| Artifact | vertrauenswürdiger Refresh-Workflow, begrenzter PR-Publisher, Dependency-Review-Dispatch und Betriebsdokumentation |
| Type | operational automation, security evidence publication, tests and documentation |
| Target | `.github/workflows/`, `scripts/`, `tests/`, `docs/`, `README.md` |
| Owner | Governance Platform Lead |
| Source Document Intake required | no |
| Evidence contract impact | none; vorhandenes Self-Security-Berichtsschema bleibt unverändert |
| Runtime governance impact | none |
| Repository enforcement impact | keine Änderung der Main-Regeln; erforderliche Checks werden für den Bot-PR explizit gestartet |
| Release impact | none |

## Decisions

1. Der tägliche Cron `31 4 * * *` wird aus dem read-only Required-Check in
   einen getrennten Writer-Workflow verschoben. Pull Requests, Main-Pushes und
   manuelle Prüfungen behalten den bestehenden Required-Check.
2. Jeder tägliche Lauf lädt den frischen Point-in-time-Bericht als Artefakt
   hoch. Nur eine fachliche Änderung erzeugt eine versionierte Änderung.
3. Für den semantischen Vergleich werden ausschließlich `observed_at` und
   `observation.observed_at` entfernt. Alle Kriterien, Details, API-Fehler,
   GitHub-Einstellungen und Remediation-Aussagen bleiben vergleichswirksam.
4. Der Publisher darf nur den JSON-/Markdown-Bericht und
   `generated/viewer/app/data.json` verändern.
5. `automation/self-security-refresh` trägt höchstens einen offenen PR. Ein
   vorhandener PR wird ohne Force-Push fortgeschrieben; Konflikte schlagen fehl.
6. Der Workflow führt keine Freigabe, keinen Merge, keinen Main-Push, keine
   Schutzregeländerung und keinen Administrator-Bypass aus.
7. Dependency Review erhält einen sicheren `workflow_dispatch`-Pfad mit
   expliziter Base und Head, damit GITHUB_TOKEN-erzeugte operative PRs alle fünf
   erforderlichen Main-Checks ausführen können.

## Validation Plan

- [x] Unit-Tests für reinen Zeitstempelwechsel und fachliche Änderung
- [x] Unit-Test für Erstellung und Fortschreibung desselben PRs
- [x] Unit-Test gegen normative oder nicht allowlistete Änderungen
- [x] Unit-Test für Main-Unveränderlichkeit und Check-Dispatch
- [x] Workflow-Vertragstest für Main-only, Berechtigungen und fehlenden Merge
- [x] `./scripts/validate_all.sh` (`600` tests passed)
- [x] Pull-Request-Prüfungen für Implementierung PR #135
- [ ] erster manueller Live-Refresh auf `main`

Der erste Live-Versuch (Run `35308723317`) bestätigte Erfassung,
Artefakt-Upload und Viewer-Generierung, schlug aber vor der Publikation fehl,
weil im neuen Workflow der OPA-Validator auf dem Runner fehlte. Der
Follow-up-Change installiert deshalb dieselbe gepinnte OPA-Version wie
Governance CI; der Live-Refresh wird danach vollständig wiederholt.

Der zweite Live-Versuch (Run `35309466848`) bestätigte die OPA-Korrektur und
bestand die Repository-Modellvalidierung. Zwei Viewer-Tests verglichen den
frisch erfassten Bericht anschließend jedoch mit fest codierten Werten des
zuvor versionierten Berichts. Der korrigierte Live-Vertrag prüft nun die
dynamische Projektion auf Gleichheit mit dem erfassten Bericht, während die
vollständige Testsuite weiterhin die versionierte Baseline prüft. Administrative
API-Lücken führen vor jeder versionierten Publikation zu einem geschlossenen
Fehler und erfordern einen dafür begrenzten Lese-Token.

Der dritte Live-Versuch (Run `35310348134`) bestand Erfassung, OPA,
Repository-Validierung und dynamische Viewer-Projektion. Der Publisher stoppte
anschließend wie vorgesehen, weil das vorhandene Intake-Token für vier
administrative Leseendpunkte keine Berechtigung besitzt. Die dauerhafte Lösung
trennt die Aufgaben: `GH_SELF_SECURITY_READ_TOKEN` erhält nur Zugriff auf dieses
Repository und **Administration: Read-only**; der Intake-Token wird nicht für
Self-Security wiederverwendet. Bis dieses Secret gesetzt ist, bleibt die
versionierte Publikation fail-closed.

## Release Decision

Kein Baseline-Release ist erforderlich. Der Change aktualisiert ausschließlich
die Publikation eines vorhandenen report-only Sicherheitsnachweises und seine
Viewer-Projektion.
