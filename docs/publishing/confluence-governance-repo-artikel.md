# DevSecOps Governance Repository: Zweck, Nutzen und Funktionsweise

## Kurzfassung

Das Repository `devsecops-governance-framework` ist der zentrale Ort, an dem DevSecOps-Governance nicht nur als Dokumentation, sondern als versionierbare, prüfbare und teilweise automatisierbare Steuerungslogik gepflegt wird.

Es verbindet klassische Governance-Artefakte wie Policy, Directive, Standards und Architekturvorgaben mit maschinenlesbaren Modellen, Policy-as-Code-Regeln, Evidenzanforderungen und wiederverwendbaren CI/CD-Prüfungen.

Das Ziel ist nicht, ein weiteres Tool oder einen dauerlaufenden Service bereitzustellen. Das Repository ist vielmehr die kontrollierte Governance-Quelle: Teams pflegen dort die Baseline, generieren daraus Review- und Audit-Artefakte und stellen wiederverwendbare Prüfmechanismen für Anwendungs- und Plattform-Repositories bereit.

## Warum gibt es dieses Repository?

In vielen Organisationen existiert Governance hauptsächlich in Word-, PDF- oder Confluence-Dokumenten. Diese Form ist wichtig für Reviews, Audits und formale Freigaben, hat aber operative Grenzen:

- Anforderungen sind schwer automatisch prüfbar.
- Nachweise aus Pipelines sind nicht einheitlich strukturiert.
- Traceability zwischen Policy, Controls, Plattformfähigkeiten und Evidenz ist oft manuell.
- Abweichungen und Waiver sind schwer über Releases hinweg nachzuverfolgen.
- Teams kopieren Regeln oder Workflows in einzelne Repositories, wodurch Inkonsistenzen entstehen.

Das Governance Repository adressiert genau diese Lücke. Es macht Governance zu einem versionierten Arbeitsmodell, das sowohl von Menschen gelesen als auch von Automatisierung verarbeitet werden kann.

## Was ist im Governance Repository enthalten?

Das Repository trennt die Governance-Inhalte in mehrere klar abgegrenzte Bereiche:

| Bereich | Zweck |
|---|---|
| `docs/` | Lesbare Erklärungen, Betriebsanleitungen, Onboarding-Guides und Governance-Dokumentation. |
| `docs/governance/source-documents/` | Importierte oder referenzierte Quelldokumente, z. B. Policy-, Directive- oder Architekturvorgaben. |
| `governance/` | Strukturierte Governance-Regeln, Rollen, Reporting-, Waiver- und Adoption-Vorgaben. |
| `architecture/` | Maschinenlesbare Architektur-Governance, Guardrails, Review Gates, Quality Marker und Architekturlevel. |
| `pipeline-baseline/` | Tool-unabhängige CI/CD Pipeline Control Baseline, inklusive Stages, Gates, Evidenzverträgen und Control Placement. |
| `policies/opa/` | Ausführbare Policy-as-Code-Regeln auf Basis von OPA/Rego. |
| `schemas/` | JSON Schemas für maschinenlesbare Governance-, Evidenz- und Ergebnisformate. |
| `scripts/` | Generatoren und Validatoren für Reports, Traceability, Status-Viewer und Governance-Ergebnisse. |
| `status/` | Zentral normalisierte Ergebnisse aus angebundenen Repositories und Governance-Läufen. |
| `generated/` | Generierte Reports, Matrizen, Viewer-Ausgaben und maschinenlesbare Ergebnisse. |
| `releases/` | Versionierte Baseline-Pakete für kontrollierte Nutzung durch andere Repositories. |

Damit bildet das Repository die Brücke zwischen Governance-Dokumenten, technischen Prüfungen und nachvollziehbaren Pipeline-Ergebnissen.

## Welche Governance-Fragen beantwortet das Repository?

Das Repository hilft unter anderem bei folgenden Fragen:

- Welche DevSecOps-Anforderungen gelten für ein Repository oder Release?
- Welche Evidenz muss eine Pipeline erzeugen?
- Welche Controls können automatisch geprüft werden?
- Welche Controls brauchen manuelle Prüfung oder Governance-Entscheidung?
- Welche Plattformfähigkeiten unterstützen welche Controls?
- Welche Architektur-Guardrails gelten für Runtime, Integration, Release und Betrieb?
- Welche Waiver oder Exceptions sind erlaubt, befristet und nachvollziehbar?
- Welche Repositories erfüllen die zentrale Baseline bereits?
- Welche Gaps sind noch offen?

Die Antwort liegt nicht nur in Textdokumenten, sondern in strukturierten Modellen, generierten Reports und ausführbaren Prüfungen.

## Zentrale Vorteile

### 1. Eine zentrale Governance-Quelle

Das Repository verhindert, dass Governance-Logik in vielen Projekten dupliziert wird. Die Baseline liegt zentral und kann versioniert, reviewed und kontrolliert veröffentlicht werden.

Anwendungs-Repositories kopieren nicht das gesamte Governance Repository. Sie erzeugen eigene Evidenz und rufen die zentrale Baseline über wiederverwendbare Workflows auf.

### 2. Governance wird prüfbar

Governance-Anforderungen werden in maschinenlesbare Strukturen und Policy-as-Code-Regeln übersetzt. Dadurch können Pipeline-Artefakte, SBOMs, Vulnerability-Scans, Signaturen, Branch Protection, Waiver und Release-Evidenz automatisiert geprüft werden.

Nicht jede Governance-Regel muss automatisiert werden. Das Repository unterscheidet bewusst zwischen:

- objektiv prüfbaren Regeln,
- Regeln mit Warn- oder Review-Charakter,
- manuellen Governance-Entscheidungen,
- kontrollierten Ausnahmen.

### 3. Bessere Traceability

Ein wichtiger Nutzen ist die Nachvollziehbarkeit zwischen:

- Policy und Directive,
- Control Baseline,
- Plattformarchitektur,
- Pipeline-Gates,
- Evidenztypen,
- Waivern,
- generierten Reports,
- Repository-Ergebnissen.

Dadurch wird sichtbar, warum eine Prüfung existiert, auf welches Governance-Ziel sie einzahlt und welche Evidenz für Compliance benötigt wird.

### 4. Wiederverwendbare CI/CD Governance

Das Repository stellt wiederverwendbare GitHub Actions Workflows und Pipeline-Baselines bereit. Ein Anwendungsteam muss nur ein eigenes Workflow-File ergänzen, Evidenz erzeugen und die zentrale Baseline aufrufen.

Typische Evidenz eines Anwendungs-Repositories ist:

- ein Build- oder Source-Artefakt,
- eine SBOM,
- ein Vulnerability-Scan,
- optional Signatur- oder zusätzliche Governance-Evidenz,
- Pipeline-Metadaten.

Die zentrale Baseline bewertet diese Evidenz und erzeugt maschinenlesbare Governance-Ergebnisse.

### 5. Audit- und Review-Fähigkeit

Aus strukturierten Quellen können Reports, Matrizen und Viewer erzeugt werden. Das unterstützt:

- Governance Board Reviews,
- Architektur-Reviews,
- Audit-Vorbereitung,
- Release-Readiness-Entscheidungen,
- Gap-Analysen,
- Diskussionen zwischen Governance, Security, Plattform und Produktteams.

### 6. Kontrollierte Weiterentwicklung

Änderungen an der Governance werden wie Code behandelt:

- Branch,
- Review,
- Validierung,
- Regression Checks,
- nachvollziehbarer Commit,
- versionierte Baseline.

Damit werden Governance-Änderungen transparenter und weniger abhängig von informellen Dokumentversionen.

## Wie funktioniert es?

Das Repository folgt einem Governance-as-Code-Ansatz. Der Ablauf lässt sich in sechs Schritten beschreiben.

### Schritt 1: Governance wird strukturiert gepflegt

Governance Owner, Plattform Owner, Security Engineers und Architekturverantwortliche pflegen die relevanten Inhalte in YAML, JSON, Markdown und Rego.

Beispiele:

- Controls und Anforderungen,
- Governance-Rollen,
- Architektur-Guardrails,
- Quality Marker,
- Review Gates,
- Pipeline-Stages,
- Evidenzverträge,
- Waiver-Regeln,
- Policy-as-Code-Regeln.

Diese Dateien sind versioniert und können per Pull Request geprüft werden.

### Schritt 2: Das Repository validiert sich selbst

Validatoren prüfen, ob die Governance-Quellen konsistent sind. Dazu gehören unter anderem:

- JSON-Schema-Prüfungen,
- Konsistenz von Traceability-Mappings,
- bekannte Evidenztypen,
- bekannte Plattformfähigkeiten,
- vorhandene Governance-Dokumentpfade,
- Syntax der OPA/Rego Policies.

Ein zentraler lokaler Check ist:

```bash
python3 scripts/validate_governance_repo.py
```

Ergänzend können Regression Tests und OPA-Prüfungen ausgeführt werden:

```bash
python3 -m unittest discover -s tests
opa check policies/opa
```

### Schritt 3: Reports und Review-Artefakte werden generiert

Aus den strukturierten Quellen werden Artefakte erzeugt, zum Beispiel:

- Traceability-Matrix,
- Document-Control-Matrix,
- Open-Gap-Report,
- Control-Evaluation-Report,
- Source-Lineage-Report,
- Governance-Status-Viewer,
- Architektur-Governance-Reports,
- End-to-End-Governance-Reports.

Diese Artefakte können für Reviews, Audits oder Confluence-Dokumentation verwendet werden.

### Schritt 4: Andere Repositories erzeugen Evidenz

Ein angebundenes Anwendungs-Repository bleibt fachlich für seine eigene Evidenz verantwortlich. Es baut oder paketiert sein Artefakt, erzeugt eine SBOM und stellt Scan-Ergebnisse bereit.

Beispielhafte Evidenz:

| Evidenz | Beispielpfad | Zweck |
|---|---|---|
| Build- oder Source-Artefakt | `dist/application-source.tar.gz` | Das zu prüfende Lieferobjekt. |
| SBOM | `security/sbom.cyclonedx.json` | Software Bill of Materials. |
| Vulnerability Scan | `security/vulnerability-scan.json` | Maschinenlesbare Security-Ergebnisse. |
| Governance Run Input | `governance/governance-run-input.json` | Erweiterte Control- und Evidenzdaten. |

### Schritt 5: Die zentrale Baseline bewertet die Evidenz

Das Anwendungs-Repository ruft einen wiederverwendbaren Workflow aus dem Governance Repository auf. Dadurch wird die zentrale Baseline angewendet, ohne dass die Governance-Logik in das Anwendungs-Repository kopiert wird.

Das Ergebnis ist ein Pipeline- und Governance-Nachweis, zum Beispiel:

```text
generated/evidence/pipeline-evidence.json
```

Dieses Ergebnis kann später zentral eingelesen, normalisiert und im Status-Viewer sichtbar gemacht werden.

### Schritt 6: Ergebnisse werden zentral sichtbar

Governance-Ergebnisse aus Downstream-Repositories können in das Governance Repository übernommen werden. Dadurch entsteht ein zentraler Überblick darüber, welche Repositories integriert sind und welche Baseline-Ergebnisse vorliegen.

Das ist besonders hilfreich für:

- Portfolio-Übersicht,
- Governance Reporting,
- Nachweisführung gegenüber Audit und Management,
- Erkennung von wiederkehrenden Gaps.

## Beispiel: Onboarding eines Anwendungs-Repositories

Ein Team integriert sein Repository typischerweise so:

1. Workflow-Datei `.github/workflows/devsecops-baseline.yml` erstellen.
2. Build- oder Source-Artefakt erzeugen.
3. SBOM erzeugen.
4. Vulnerability Scan erzeugen.
5. Evidenz als GitHub Actions Artifact hochladen.
6. Zentralen Governance Workflow aufrufen.
7. Ergebnis prüfen.
8. Nach Stabilisierung den Governance Check als Required Check für `main` aktivieren.

Das Anwendungsteam bleibt für den Inhalt der Evidenz verantwortlich. Das Governance Repository stellt die Baseline, die Bewertungslogik und die einheitlichen Ergebnisformate bereit.

## Rolle der Architektur-Governance

Neben DevSecOps Controls enthält das Repository auch eine Runtime- und Architektur-Governance. Diese basiert auf strukturierten Architekturartefakten wie:

- Guardrails,
- Quality Markers,
- Review Gates,
- Architekturlevel L1 bis L3,
- Architektur-Governance-Regeln,
- Release-Readiness-Prüfungen,
- Integration-Readiness-Prüfungen,
- Operation-Readiness-Prüfungen.

Damit kann nicht nur geprüft werden, ob eine Pipeline Sicherheitsartefakte erzeugt, sondern auch, ob ein Produkt oder Release architektonische Mindestanforderungen erfüllt.

Beispiele für Architekturfragen:

- Ist die Runtime-Architektur dokumentiert?
- Sind Deployment- und Rollback-Annahmen geprüft?
- Sind Schnittstellen und Datenverträge versioniert?
- Gibt es eine Release Compatibility Declaration?
- Sind Architektur-Ausnahmen dokumentiert, befristet und genehmigt?

## Rolle der Pipeline Baseline

Die Pipeline Baseline beschreibt tool-unabhängig, welche Governance-Prüfungen in einer CI/CD Pipeline stattfinden sollen.

Sie definiert:

- verpflichtende und bedingte Pipeline-Stages,
- Gate-Semantik wie Pass, Warn, Fail, Waiver und Manual Review,
- Mindestanforderungen an Evidenz,
- erforderliche Metadaten für Traceability,
- Zuordnung von Controls zu Pipeline-Orten,
- Referenzmappings für GitHub Actions, GitLab CI und Jenkins.

Dadurch bleibt die Governance nicht an ein einzelnes CI/CD-Tool gebunden.

## Was ist bewusst nicht Ziel des Repositories?

Das Repository ist kein Ersatz für Produktverantwortung, Security Engineering oder Architekturarbeit.

Es erzeugt auch keine echte Compliance allein durch seine Existenz. Compliance entsteht erst, wenn:

- Anforderungen gepflegt sind,
- Teams valide Evidenz erzeugen,
- Pipelines die Baseline ausführen,
- Findings bearbeitet werden,
- Waiver kontrolliert und befristet bleiben,
- Governance-Ergebnisse regelmäßig reviewed werden.

Das Repository stellt dafür den kontrollierten Rahmen und die Automatisierung bereit.

## Wer arbeitet mit dem Repository?

| Rolle | Typische Verantwortung |
|---|---|
| Governance Owner | Pflegt Controls, Policies, Directives, Waiver-Modell und Governance-Änderungen. |
| Platform Owner | Verknüpft Plattformfähigkeiten mit Controls und Baseline-Leveln. |
| Security / Policy Engineer | Entwickelt und testet Policy-as-Code-Regeln. |
| Architect / Architecture Board | Pflegt Guardrails, Quality Marker, Review Gates und Architekturentscheidungen. |
| Application Team | Erzeugt Evidenz und bindet die zentrale Baseline in die eigene Pipeline ein. |
| Audit / Compliance Reviewer | Nutzt Reports, Matrizen und Nachweise für Reviews und Audits. |

## Erfolgsbild

Das Governance Repository ist erfolgreich eingesetzt, wenn:

- Governance-Anforderungen zentral versioniert sind,
- Anwendungs-Repositories die zentrale Baseline wiederverwenden,
- Pipeline-Evidenz maschinenlesbar erzeugt wird,
- Ergebnisse zentral sichtbar sind,
- Reviews auf Traceability und Evidenz statt auf manuelle Dokumentensuche zurückgreifen,
- Ausnahmen kontrolliert, befristet und nachvollziehbar bleiben,
- Governance-Änderungen nachvollziehbar reviewed und released werden.

## Fazit

Das DevSecOps Governance Repository macht Governance operativ nutzbar. Es übersetzt Anforderungen aus Policy, Directive, Standards und Architekturvorgaben in strukturierte Modelle, wiederverwendbare Pipeline-Prüfungen, Policy-as-Code und nachvollziehbare Evidenz.

Der wichtigste Vorteil ist die Verbindung von menschlicher Governance und technischer Automatisierung: Governance bleibt erklärbar und auditierbar, wird aber gleichzeitig in CI/CD-Prozesse eingebettet. Dadurch entsteht ein gemeinsames Arbeitsmodell für Governance Owner, Plattformteams, Security Engineers, Architekten und Anwendungsteams.

Kurz gesagt: Das Repository ist der zentrale Governance-Baseline-Hub für DevSecOps und Architektur-Readiness. Es sorgt dafür, dass Anforderungen nicht nur dokumentiert, sondern auch überprüfbar, wiederverwendbar und nachweisbar werden.
