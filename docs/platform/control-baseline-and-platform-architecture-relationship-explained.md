# Zusammenhang zwischen Control Baseline und Platform Architecture

## Zweck dieses Dokuments

Dieses Dokument erklärt den Zusammenhang zwischen:

- der **DevSecOps Control Baseline**
- der **DevSecOps Platform Reference Architecture**

Es zeigt mit konkreten Beispielen, wie beide Ebenen zusammenwirken und warum beide benötigt werden.

## Kurzfassung

Die einfachste Erklärung lautet:

- Die **Control Baseline** beschreibt, **was erfüllt werden muss**.
- Die **Platform Architecture** beschreibt, **welche Plattformfähigkeiten vorhanden sein müssen, damit diese Anforderungen überhaupt umsetzbar sind**.

Oder noch kürzer:

> Die Baseline definiert die Pflicht, die Platform Architecture definiert die technische Befähigung.

## Die unterschiedliche Rolle beider Ebenen

### Control Baseline

Die Control Baseline ist die normative Anforderungsebene.

Sie beschreibt:

- welche Controls gelten,
- auf welchem Reifegrad sie gelten,
- welche Nachweise erwartet werden,
- wie diese Anforderungen verifiziert werden sollen.

Im Repository ist das vor allem modelliert unter:

- `model/controls/dscb-l1.yaml`
- `model/controls/dscb-l2.yaml`
- `model/controls/dscb-l3.yaml`
- `model/controls/dscb-gov.yaml`

### Platform Architecture

Die Platform Architecture ist die technische Fähigkeits- und Befähigungsebene.

Sie beschreibt:

- welche Plattform-Capabilities vorhanden sein müssen,
- ab welchem Plattform-Level sie verfügbar sein sollen,
- welche Anforderungen sie unterstützen.

Im Repository ist das vor allem modelliert unter:

- `model/platform/platform-capabilities.yaml`

## Das Kernprinzip

Die Baseline stellt die Frage:

- **Welche Anforderung muss erfüllt werden?**

Die Platform Architecture stellt die Frage:

- **Welche technischen Fähigkeiten braucht die Plattform, damit diese Anforderung zuverlässig erfüllt werden kann?**

Das bedeutet:

- Ein Control allein ist noch keine technische Lösung.
- Eine Plattformfähigkeit allein ist noch keine normative Pflicht.
- Erst die Kombination aus beiden ergibt ein operativ belastbares Governance-Modell.

## Ein einfaches Beispiel

### Baseline-Sicht

In der Control Baseline steht zum Beispiel:

```yaml
- id: DSCB-L1-REQ-003
  title: Source Code Integrity
  requirement: Direct modification of protected branches SHALL be prohibited.
  required_platform_level: PRA-Level 1
```

Das sagt:

- geschützte Branches dürfen nicht direkt verändert werden,
- und dafür wird mindestens `PRA-Level 1` benötigt.

### Platform-Architecture-Sicht

In der Platform Architecture finden wir dazu passende Fähigkeiten:

```yaml
- id: branch_protection
  area: Source Control
  required_from: PRA-Level 1
  supports_requirements:
    - DSCB-L1-REQ-002
    - DSCB-L1-REQ-003
```

Das sagt:

- die Plattform muss die Capability `branch_protection` besitzen,
- diese Capability ist ab `PRA-Level 1` erforderlich,
- und sie unterstützt genau diese Baseline-Anforderungen.

### Zusammengenommen

Die fachliche Pflicht lautet:

- direkte Änderungen auf geschützten Branches sind verboten

Die technische Befähigung dazu lautet:

- die Plattform muss Branch Protection bereitstellen

Ohne Platform Capability wäre das Control kaum zuverlässig durchsetzbar.

## Ein zweites Beispiel: SBOM

### Baseline-Sicht

Ein L1-Control lautet:

```yaml
- id: DSCB-L1-REQ-006
  title: Software Supply Chain Transparency
  requirement: A Software Bill of Materials (SBOM) SHALL be generated for releasable artifacts.
  required_platform_level: PRA-Level 1
```

Das sagt:

- für releasable Artefakte muss ein SBOM erzeugt werden

### Platform-Architecture-Sicht

Dafür braucht die Plattform zum Beispiel:

```yaml
- id: sbom_generation
  area: Artifact and Dependency Management
  required_from: PRA-Level 1
  supports_requirements:
    - DSCB-L1-REQ-005
    - DSCB-L1-REQ-006
```

Zusätzlich oft:

```yaml
- id: dependency_inventory
- id: dependency_scanning
- id: evidence_repository
```

### Zusammengenommen

Die Baseline sagt:

- ein SBOM ist verpflichtend

Die Platform Architecture sagt:

- die Plattform muss Dependency-Inventarisierung, SBOM-Erzeugung und Evidence-Ablage bereitstellen

Erst dann kann ein Team die Baseline-Anforderung systematisch erfüllen.

## Ein drittes Beispiel: Pipeline Security Gates

### Baseline-Sicht

In L2 findet sich sinngemäß:

```yaml
- id: DSCB-L2-REQ-011
  title: Pipeline Security Gates
  requirement: DevSecOps pipelines SHALL enforce security gates.
  required_platform_level: PRA-Level 2
```

und:

```yaml
- id: DSCB-L2-REQ-012
  title: Pipeline Security Gates
  requirement: Releases SHALL NOT proceed when defined security thresholds are exceeded.
  required_platform_level: PRA-Level 2
```

### Platform-Architecture-Sicht

Die Plattform braucht dafür Fähigkeiten wie:

```yaml
- id: policy_gate_engine
- id: security_threshold_enforcement
- id: release_blocking
```

Diese Capabilities sind notwendig, damit ein Gate nicht nur als Wunsch formuliert ist, sondern technisch wirklich vor dem Release blockieren kann.

### Zusammengenommen

Die Baseline sagt:

- Sicherheits-Gates müssen verpflichtend vor Releases greifen

Die Platform Architecture sagt:

- die Plattform muss dafür eine Policy Engine, Threshold Enforcement und Release Blocking bereitstellen

## Warum in den Controls ein `required_platform_level` steht

In den Controls ist jeweils ein Feld wie dieses enthalten:

```yaml
required_platform_level: PRA-Level 1
```

oder:

```yaml
required_platform_level: PRA-Level 2
```

oder:

```yaml
required_platform_level: PRA-Level 3
```

Dieses Feld ist die direkte Brücke zwischen Baseline und Platform Architecture.

Es bedeutet:

- diese Anforderung ist nicht losgelöst zu sehen,
- sondern setzt ein bestimmtes Plattform-Reifeniveau voraus.

Mit anderen Worten:

- L1-Controls erwarten mindestens PRA-Level 1
- L2-Controls erwarten mindestens PRA-Level 2
- L3-Controls erwarten mindestens PRA-Level 3

## Warum Plattform-Level wichtig sind

Die Plattform-Level beschreiben nicht nur „größer“ oder „kleiner“, sondern unterschiedliche Fähigkeitsreife.

Ein vereinfachtes Bild:

- **PRA-Level 1**
  - grundlegende CI/CD- und Evidence-Fähigkeiten
  - z. B. Branch Protection, SBOM-Generierung, Pipeline-Logs

- **PRA-Level 2**
  - stärker kontrollierte Plattform
  - z. B. zentrale IAM, genehmigte Dependency-Repositories, Security Gates

- **PRA-Level 3**
  - hochvertrauenswürdige Supply-Chain- und Integritätsfähigkeiten
  - z. B. isolierte Build-Umgebungen, zentrale Signaturinfrastruktur, Runtime Integrity

Das ist wichtig, weil höhere Baseline-Anforderungen ohne höhere Plattform-Reife oft nicht seriös erfüllbar sind.

## Der Datenzusammenhang im Repository

Der Zusammenhang wird im Repository über mehrere Datenstrukturen modelliert:

### 1. Controls

Beispiel:

- `model/controls/dscb-l1.yaml`

Ein Control enthält:

- `id`
- `requirement`
- `required_platform_level`
- `platform_capabilities`
- `evidence`
- `verification`
- `policy_as_code`

### 2. Platform Capabilities

Beispiel:

- `model/platform/platform-capabilities.yaml`

Eine Capability enthält:

- `id`
- `area`
- `required_from`
- `supports_requirements`

### 3. Traceability

Die Verbindung ist bidirektional modelliert:

- im Control über `platform_capabilities`
- in der Capability über `supports_requirements`

Dadurch kann man in beide Richtungen fragen:

- Welche Plattformfähigkeiten braucht ein Control?
- Welche Controls unterstützt eine Plattformfähigkeit?

## Beispiel für die Datenbeziehung

### Control

```yaml
- id: DSCB-L1-REQ-007
  title: Controlled Build Process
  requirement: Software builds SHALL be executed through controlled automated pipelines.
  required_platform_level: PRA-Level 1
  platform_capabilities:
    - automated_pipeline_execution
    - build_pipeline_logging
    - artifact_versioning
```

### Zugehörige Plattformfähigkeiten

```yaml
- id: automated_pipeline_execution
  required_from: PRA-Level 1
  supports_requirements:
    - DSCB-L1-REQ-007
    - DSCB-L1-REQ-008

- id: build_pipeline_logging
  required_from: PRA-Level 1
  supports_requirements:
    - DSCB-L1-REQ-007
    - DSCB-L1-REQ-008

- id: artifact_versioning
  required_from: PRA-Level 1
  supports_requirements:
    - DSCB-L1-REQ-007
    - DSCB-L1-REQ-008
```

### Bedeutung

Das Control fordert:

- automatisierte kontrollierte Builds

Die Plattform muss dafür können:

- Pipelines automatisiert ausführen
- Build-Läufe protokollieren
- Artefakte eindeutig versionieren

## Was passiert, wenn Plattform und Baseline nicht zusammenpassen

Wenn eine Plattform die nötigen Fähigkeiten nicht hat, entstehen typische Probleme:

- das Control ist formal verpflichtend, aber praktisch kaum erfüllbar
- Evidence kann nicht zuverlässig erzeugt werden
- Policy-as-Code-Gates würden ständig fehlschlagen
- Teams würden viele Waiver brauchen
- Governance wird unpraktisch und verliert Akzeptanz

Deshalb ist die Platform Architecture nicht nur „nice to have“, sondern die notwendige Umsetzungsbasis für die Baseline.

## Praktische Lesart

Man kann den Zusammenhang so lesen:

### Baseline ohne Platform Architecture

- sagt nur, **was** verpflichtend ist
- aber nicht, wie die Plattform dazu befähigt wird

### Platform Architecture ohne Baseline

- sagt nur, **was technisch möglich** oder vorgesehen ist
- aber nicht, was davon verbindlich gefordert ist

### Beides zusammen

- ergibt ein steuerbares Modell:
  - Pflicht
  - technische Befähigung
  - Nachweis
  - Verifikation
  - Governance-Ausführung

## Zusammenhang mit Governance as Code

Governance as Code nutzt genau diese Beziehung.

Die Ausführung als Code funktioniert typischerweise so:

1. Die **Control Baseline** definiert das zu prüfende Soll.
2. Die **Platform Architecture** definiert, welche technischen Capabilities vorhanden sein müssen.
3. Die **Evidence** zeigt, ob diese Capabilities und Pflichten in der Praxis wirksam sind.
4. Die **Policy-as-Code-Regeln** oder Workflows prüfen den Zustand maschinenlesbar.

Beispiel:

- Baseline fordert SBOM
- Plattform muss `sbom_generation` haben
- Evidence enthält `sbom.cyclonedx.json`
- der Governance-Workflow prüft: `sbom.exists == true`

## Ein Merksatz

> Die Control Baseline definiert die verpflichtenden Sicherheits-, Qualitäts- und Nachweisanforderungen. Die Platform Architecture definiert die Plattformfähigkeiten, mit denen diese Anforderungen überhaupt wirksam, wiederholbar und auditierbar umgesetzt werden können.

## Wichtige Dateien im Repository

Für diesen Zusammenhang sind insbesondere diese Dateien zentral:

- `model/controls/dscb-l1.yaml`
- `model/controls/dscb-l2.yaml`
- `model/controls/dscb-l3.yaml`
- `model/platform/platform-capabilities.yaml`
- `model/traceability/document-to-control.yaml`
- `model/evidence/evidence-types.yaml`
- `docs/governance/policy-directive-baseline-verification-and-governance-as-code-explained.md`

## Kernaussage

Der Zusammenhang zwischen Control Baseline und Platform Architecture ist nicht optional, sondern zentral:

- die Baseline definiert die Pflicht,
- die Platform Architecture definiert die technische Befähigung,
- und nur gemeinsam ermöglichen sie eine glaubwürdige Governance-Ausführung als Code.
