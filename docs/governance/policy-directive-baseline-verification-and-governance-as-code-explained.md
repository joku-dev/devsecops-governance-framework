# Policy, Directive, Baseline, Verification und Governance as Code

## Zweck dieses Dokuments

Dieses Dokument erklärt den fachlichen und operativen Zusammenhang zwischen:

- **Policy**
- **Directive**
- **Baseline / Standard**
- **Anforderungen**
- **Verifikationsmethoden**
- **Governance-Ausführung als Code**

Es dient als Orientierungsdokument für Governance Owner, Plattform-Verantwortliche, Security Engineers, Auditoren und anbindende Application-Repositories.

## Kurzfassung

Die drei wichtigsten Dokumentebenen haben unterschiedliche Rollen:

1. **Policy** sagt, **was verbindlich ist und wer verantwortlich ist**.
2. **Directive** sagt, **wie diese Verbindlichkeit organisatorisch und operativ ausgeführt werden muss**.
3. **Baseline / Standards** sagen, **welche konkreten Anforderungen technisch und fachlich erfüllt werden müssen**.

Governance as Code ist dann die ausführbare Umsetzung ausgewählter Teile dieser Anforderungen in:

- strukturierte Daten,
- Traceability,
- Evidence-Modelle,
- Policy-as-Code,
- CI/CD-Gates,
- maschinenlesbare Compliance-Evidence.

## Die Dokumentenhierarchie im Governance-Stack

### 1. Policy

Die Policy ist die oberste normative Ebene in diesem Modell.

Sie beantwortet vor allem die Fragen:

- Was ist verpflichtend?
- Für wen gilt es?
- Welche Grundprinzipien gelten?
- Wer trägt die Verantwortung?

Die Policy ist also **nicht** das operative Arbeitsdokument für die tägliche Pipeline-Entscheidung, sondern das Dokument, das die grundlegende Verbindlichkeit herstellt.

Im Repository liegt die aktuelle Arbeitsfassung hier:

- `docs/governance/devsecops-policy.md`

### 2. Directive

Die Directive ist die operative Governance-Ebene unterhalb der Policy.

Sie beantwortet vor allem die Fragen:

- Wie wird die Policy praktisch ausgeführt?
- Wer entscheidet bei Abweichungen?
- Wie funktioniert Waiver- und Eskalationsmanagement?
- Wie wird Compliance überwacht und berichtet?

Die Directive übersetzt also den normativen Willen der Policy in bindende organisatorische und prozedurale Ausführung.

Im Repository liegt die aktuelle Arbeitsfassung hier:

- `docs/governance/devsecops-directive.md`

### 3. Baseline / Standards

Die Baseline beziehungsweise die Standards sind die konkrete normative Anforderungsebene.

Sie beantworten vor allem die Fragen:

- Welche Controls müssen auf L1, L2, L3 oder GOV erfüllt werden?
- Welche Plattformfähigkeiten werden dafür benötigt?
- Welche technischen oder prozessualen Nachweise werden erwartet?

In diesem Repository sind die importierten Ursprungsdokumente derzeit:

- `docs/governance/source-documents/DSCB-STD-SRC-001.public.md`
- `docs/governance/source-documents/PRA-STD-SRC-001.public.md`

Zusätzlich liegt die strukturierte Repräsentation der Anforderungen in YAML-Dateien, insbesondere unter:

- `model/controls/`
- `model/platform/`
- `model/traceability/`
- `model/evidence/`

## Der fachliche Zusammenhang zwischen Policy, Directive und Baseline

Die Beziehung lässt sich so ausdrücken:

- **Policy** legitimiert und verpflichtet.
- **Directive** operationalisiert und regelt die Governance-Ausführung.
- **Baseline** konkretisiert die zu erfüllenden Anforderungen.

Oder anders formuliert:

- Die **Policy** sagt: _DevSecOps ist verpflichtend._
- Die **Directive** sagt: _So wird diese Verpflichtung gesteuert, überwacht und bei Abweichungen behandelt._
- Die **Baseline** sagt: _Diese konkreten Controls und Anforderungen müssen erfüllt oder nachweisbar behandelt werden._

## Der Zusammenhang zwischen Dokumenten und Anforderungen

Nicht jede Anforderung steht direkt in der Policy oder Directive selbst.

Die typische Struktur ist:

1. **Policy** definiert die Pflicht und Verantwortlichkeit.
2. **Directive** definiert die Ausführungs- und Entscheidungslogik.
3. **Standards/Baseline** enthalten die einzelnen technischen und organisatorischen Anforderungen.
4. **Structured YAML** modelliert diese Anforderungen in maschinenverarbeitbarer Form.

Die Zuordnung der Governance-Dokumente zu Controls wird im Repository explizit modelliert, insbesondere in:

- `model/documents/governance-documents.yaml`
- `model/traceability/document-to-control.yaml`

Dadurch ist nachvollziehbar:

- welches Dokument welche Anforderungen autorisiert,
- welche Controls auf welche Dokumente zurückgehen,
- welche Baseline-Level durch welche Governance-Artefakte gestützt werden.

## Konkrete Datenstruktur: Dokumentenkatalog

Eine zentrale Datenstruktur ist der Governance-Dokumentenkatalog in:

- `model/documents/governance-documents.yaml`

Ein stark vereinfachtes Beispiel sieht so aus:

```yaml
documents:
  - id: DEVSECOPS-POL-001
    type: policy
    title: DevSecOps Policy - Software Defined Defence (SDD)
    status: draft
    repository_path: docs/governance/devsecops-policy.md

  - id: DEVSECOPS-DIR-001
    type: directive
    title: DevSecOps Directive
    status: draft
    repository_path: docs/governance/devsecops-directive.md

  - id: DSCB-STD-001
    type: standard
    title: DevSecOps Control Baseline Standard
    status: imported
    repository_path: docs/governance/source-documents/DSCB-STD-SRC-001.public.md
```

Diese Struktur macht maschinenlesbar sichtbar:

- welche Dokumente es gibt,
- welchen Typ sie haben,
- welchen Freigabestatus sie haben,
- wo ihre Repräsentation im Repository liegt.

## Konkrete Datenstruktur: Document-to-Control-Traceability

Die normative Beziehung zwischen Dokumenten und Controls wird in:

- `model/traceability/document-to-control.yaml`

modelliert.

Beispiel:

```yaml
mappings:
  - document_id: DEVSECOPS-POL-001
    control_levels:
      - L1
      - L2
      - L3
      - GOV
    rationale: Establishes that the DevSecOps governance baseline is mandatory.

  - document_id: DEVSECOPS-DIR-001
    control_ids:
      - DSCB-GOV-REQ-002
      - DSCB-GOV-REQ-003
    control_levels:
      - L2
      - L3
    rationale: Defines operational compliance workflow and waiver handling.
```

Damit kann man später auswerten:

- warum ein Control überhaupt verbindlich ist,
- ob es eher durch Policy oder Directive gestützt ist,
- auf welcher Governance-Ebene eine Anforderung verankert ist.

## Der Zusammenhang zwischen Anforderungen und Verifikationsmethoden

Eine Anforderung allein reicht operativ nicht aus. Sie muss auch verifizierbar sein.

Deshalb braucht jede relevante Anforderung eine oder mehrere Verifikationsmethoden.

Typische Verifikationsmethoden sind:

- Dokumentenprüfung
- Konfigurationsprüfung
- Pipeline-Prüfung
- Repository-Prüfung
- Policy-as-Code-Auswertung
- Evidence-Prüfung gegen strukturierte Kriterien
- manuelle Governance- oder Auditfreigabe

Im Governance-as-Code-Modell bedeutet das:

- Eine Anforderung wird nicht nur textuell beschrieben,
- sondern idealerweise mit erwarteter Evidence und möglicher Prüfmechanik verknüpft.

Diese Verknüpfung wird im Repository über Evidence-Definitionen und Traceability modelliert, insbesondere in:

- `model/evidence/evidence-types.yaml`
- `model/traceability/`
- `model/controls/`

## Konkrete Datenstruktur: Ein einzelnes Control

Der Kern der Governance-as-Code-Modellierung liegt in den strukturierten Controls, zum Beispiel in:

- `model/controls/dscb-l1.yaml`

Ein echtes Beispiel aus dem Repository:

```yaml
- id: DSCB-L1-REQ-003
  domain: source_code_integrity
  title: Source Code Integrity
  requirement: Direct modification of protected branches SHALL be prohibited.
  required_platform_level: PRA-Level 1
  platform_capabilities:
    - approved_version_control
    - code_review
    - branch_protection
    - repository_audit_log
  evidence:
    - commit_history
    - code_review_records
    - branch_protection_configuration
  verification:
    method: automated
    frequency: release_candidate
  policy_as_code:
    candidate: true
    enforcement: automated_gate
    rule: policies/opa/branch_protection.rego
  waiver:
    allowed: true
    authority: DevSecOps Governance Board
```

Dieses eine Objekt zeigt bereits den ganzen Mechanismus:

- **fachliche Anforderung**: direkte Änderungen auf geschützten Branches sind verboten
- **technische Voraussetzungen**: Branch Protection, Code Review, Audit Log
- **erwartete Evidence**: Commit-Historie, Review-Daten, Branch-Protection-Konfiguration
- **Verifikationsmethode**: automatisiert
- **Governance-Ausführung**: als ausführbare Policy-Regel
- **Abweichungslogik**: Waiver grundsätzlich erlaubt, zuständig ist das Governance Board

## Konkrete Datenstruktur: Evidence-Typen

Die Evidence wird nicht nur im Control genannt, sondern auch zentral beschrieben, zum Beispiel in:

- `model/evidence/evidence-types.yaml`

Beispiel:

```yaml
- id: branch_protection_configuration
  name: Branch Protection Configuration
  category: repository
  producer: devsecops_platform
  format:
    - json
  retention: project_lifecycle
  supports_requirements:
    - DSCB-L1-REQ-002
    - DSCB-L1-REQ-003

- id: sbom
  name: Sbom
  category: artifact
  producer: devsecops_platform
  format:
    - json
  retention: project_lifecycle
  supports_requirements:
    - DSCB-L1-REQ-005
    - DSCB-L1-REQ-006
```

Diese Datenstruktur ist wichtig, weil sie nicht nur sagt _dass_ Evidence existiert, sondern:

- wer sie erzeugen soll,
- in welchem Format sie vorliegen soll,
- welche Anforderungen durch sie gestützt werden.

## Der Zusammenhang zwischen Anforderungen und Evidence

Eine Verifikationsmethode braucht in der Regel einen Nachweis.

Dieser Nachweis ist die **Evidence**.

Beispiele:

- SBOM-Datei
- Vulnerability-Scan-Report
- Branch-Protection-Konfiguration
- Review-Historie
- Build-Logs
- Pipeline-Execution-Logs
- Artifact-Digest
- Signatur-Nachweis
- Approval-Records

Im Repository wird modelliert:

- welche Evidence-Typen existieren,
- wer sie erzeugt,
- in welchem Format sie vorliegen,
- welche Anforderungen sie unterstützen.

Das ist wichtig, weil Governance as Code nicht nur Regeln ausführt, sondern auch festlegt, **welcher Nachweis für welche Anforderung gilt**.

## Beispielhafte Beziehung als Kette

Ein Leser kann sich die Beziehung idealerweise so merken:

```text
Policy
  -> macht DevSecOps verbindlich

Directive
  -> regelt Rollen, Waiver, Reporting, Governance-Abläufe

Control / Baseline Requirement
  -> beschreibt die konkrete Anforderung

Evidence Type
  -> beschreibt den erwarteten Nachweis

Verification Method
  -> beschreibt, wie dieser Nachweis geprüft wird

Policy-as-Code / Gate
  -> führt die Prüfung technisch aus

Compliance Result
  -> speichert das Ergebnis maschinenlesbar
```

## Der Zusammenhang zwischen Verifikationsmethode und Governance-Ausführung als Code

Governance-Ausführung als Code bedeutet nicht einfach nur „ein paar Regeln in einer Pipeline“.

Vielmehr umfasst sie mehrere Ebenen:

1. **Strukturierte Modellierung**
   - Anforderungen, Dokumente, Evidence und Traceability liegen maschinenlesbar vor.

2. **Validierung**
   - Schemas und Konsistenzprüfungen stellen sicher, dass das Governance-Modell intern korrekt ist.

3. **Ausführbare Regeln**
   - ausgewählte Anforderungen werden als Policy-as-Code oder Gate-Logik implementiert.

4. **Evidence-Erzeugung**
   - Pipelines und Plattformen erzeugen maschinenlesbare Nachweise.

5. **Evidence-Auswertung**
   - die erzeugte Evidence wird gegen die Governance-Anforderungen geprüft.

6. **Compliance-Ergebnis**
   - das Ergebnis wird als maschinenlesbare Governance-Evidence gespeichert.

## Konkrete Datenstruktur: Compliance-Eingabedaten

Damit Governance as Code funktioniert, braucht die Policy-Auswertung Eingabedaten.

Ein Beispiel dafür ist:

- `demo/inputs/release-candidate-green.json`

Ein gekürzter Ausschnitt:

```json
{
  "contract_version": "1.0",
  "release_candidate": true,
  "repository": {
    "protected_branch": true,
    "direct_push_allowed": false,
    "review_required": true
  },
  "evidence": {
    "sbom": {
      "exists": true,
      "linked_to_artifact": true
    },
    "vulnerability_scan": {
      "exists": true
    }
  },
  "artifact": {
    "digest": {
      "exists": true,
      "linked_to_artifact": true
    },
    "signature": {
      "exists": true
    }
  },
  "pipeline": {
    "security_gates": {
      "enforced": true
    },
    "security_thresholds_exceeded": false
  }
}
```

Das ist praktisch die maschinenlesbare Beschreibung eines zu bewertenden Zustands.

Die Policy-Regeln fragen dann zum Beispiel:

- ist der Branch geschützt?
- ist ein SBOM vorhanden?
- ist ein Vulnerability-Scan vorhanden?
- ist ein Digest oder eine Signatur vorhanden?
- wurden Security Gates tatsächlich ausgeführt?

## Konkrete Datenstruktur: Compliance-Ergebnis

Nach der Auswertung entsteht ein Ergebnisobjekt, zum Beispiel in:

- `generated/governance-compliance-result.json`

Ein gekürzter Ausschnitt:

```json
{
  "status": "pass",
  "checks": [
    {
      "check_id": "governance_ci_file_present",
      "status": "pass"
    }
  ],
  "execution": {
    "validator": {
      "status": "pass"
    },
    "opa_check": {
      "status": "pass"
    }
  },
  "policy_evaluations": [
    {
      "policy_id": "branch_protection",
      "status": "pass",
      "deny_count": 0
    },
    {
      "policy_id": "sbom",
      "status": "pass",
      "deny_count": 0
    }
  ]
}
```

Wichtig daran ist:

- das Ergebnis ist **nicht nur ein grünes oder rotes Signal**,
- sondern ein strukturierter Nachweis,
- der später für Audits, Management-Auswertungen oder weitere Automatisierung genutzt werden kann.

## Was Governance as Code in diesem Repository konkret bedeutet

In diesem Repository wird Governance as Code durch mehrere Bausteine umgesetzt:

### 1. Strukturierte Governance-Daten

Zum Beispiel:

- `model/controls/`
- `model/documents/`
- `model/platform/`
- `model/traceability/`
- `model/evidence/`
- `model/waivers/`

### 2. Validierung der Governance-Struktur

Zum Beispiel:

- `scripts/validate_governance_repo.py`
- Schemas unter `schemas/`
- Tests unter `tests/`

### 3. Policy-as-Code

Zum Beispiel:

- `policies/opa/`

Hier werden ausgewählte objektiv prüfbare Anforderungen in ausführbare Rego-Regeln übersetzt.

### 4. Generierung von Review- und Audit-Artefakten

Zum Beispiel:

- Traceability-Matrizen
- Document-Control-Matrix
- Open-Gap-Reports
- gerenderte Policy- und Directive-Dokumente

### 5. Wiederverwendbare Governance-Ausführung in CI/CD

Zum Beispiel:

- `.github/workflows/devsecops-baseline-reusable.yml`

Dieser wiederverwendbare Workflow ermöglicht es, dass andere Repositories zentral definierte Governance-Logik auf ihre eigene Pipeline-Evidence anwenden.

## Echte End-to-End-Beispielkette mit einem Application-Repository

Die Theorie wird besonders verständlich, wenn man den tatsächlichen Ablauf in einem angebundenen Repository betrachtet.

Mit `ha-CPsWMS` wurde dieser Ablauf bereits praktisch demonstriert:

1. Das Application-Repository erzeugt:
   - ein Build- oder Source-Artefakt,
   - ein SBOM,
   - ein Vulnerability-Scan-Evidence-File.

2. Diese Dateien werden über GitHub Actions als Artifact hochgeladen.

3. Das Application-Repository ruft den zentralen Workflow aus diesem Repository auf:
   - `.github/workflows/devsecops-baseline-reusable.yml`

4. Der zentrale Workflow prüft:
   - Artefakt vorhanden?
   - Digest vorhanden?
   - SBOM vorhanden?
   - Vulnerability-Scan vorhanden?
   - Security Gate aktiv?
   - für höhere Level zusätzlich weitere Bedingungen

5. Das Ergebnis wird als maschinenlesbare Pipeline-Evidence erzeugt.

Ein Beispiel für ein solches operatives Ergebnis ist die Pipeline-Evidence aus dem erfolgreichen `ha-CPsWMS`-Lauf:

```json
{
  "pipeline": {
    "pipeline_id": "DevSecOps Baseline",
    "status": "success",
    "security_gates": {
      "enforced": true
    }
  },
  "repository": {
    "repository_id": "joku-dev/ha-CPsWMS",
    "branch": "main"
  },
  "artifact": {
    "artifact_id": "ha-cpswms-source.tar.gz",
    "digest": {
      "exists": true,
      "algorithm": "sha256"
    }
  },
  "evidence": {
    "sbom": {
      "exists": true
    },
    "vulnerability_scan": {
      "exists": true,
      "max_severity": "none"
    }
  }
}
```

Das zeigt sehr konkret:

- die Governance-Regel ist nicht nur modelliert,
- die Evidence ist nicht nur theoretisch beschrieben,
- sondern die Ausführung ist tatsächlich in einer realen Pipeline erfolgt.

## Beispielhafte Leselogik für den Leser

Wenn man dieses Repository verstehen will, kann man die wichtigsten Dateien in dieser Reihenfolge lesen:

1. `docs/governance/devsecops-policy.md`
2. `docs/governance/devsecops-directive.md`
3. `model/controls/dscb-l1.yaml`
4. `model/evidence/evidence-types.yaml`
5. `model/traceability/document-to-control.yaml`
6. `policies/opa/`
7. `.github/workflows/devsecops-baseline-reusable.yml`
8. `generated/governance-compliance-result.json`

Dann sieht man nacheinander:

- die normative Absicht,
- die operative Governance-Logik,
- die konkrete Anforderung,
- den erwarteten Nachweis,
- die Dokumentenautorität,
- die technische Regel,
- die technische Ausführung,
- und das strukturierte Ergebnis.

## Wie der operative Fluss aussieht

Der operative Zusammenhang lässt sich in einer Kette darstellen:

1. **Policy** macht DevSecOps verbindlich.
2. **Directive** definiert Governance, Rollen, Waiver und Reporting.
3. **Baseline/Standards** definieren konkrete Anforderungen.
4. **Structured Controls und Evidence-Modelle** übersetzen diese Anforderungen in maschinenlesbare Form.
5. **Application-Repositories und Plattformen** erzeugen Evidence.
6. **Governance-as-Code-Workflows und Policy-as-Code-Regeln** prüfen die Evidence.
7. **Maschinenlesbare Governance-Ergebnisse** dokumentieren, ob Anforderungen erfüllt, verletzt oder per Waiver behandelt wurden.

## Was nicht alles automatisiert werden kann

Ein wichtiger Grundsatz dieses Repositories ist:

> Nicht jede Governance-Anforderung sollte oder kann als Code ausgeführt werden.

Es gibt drei verschiedene Typen von Anforderungen:

### 1. Rein normative Anforderungen

Beispiel:

- ein Governance Board muss eingerichtet werden
- Verantwortlichkeiten müssen formal zugewiesen sein

Diese Anforderungen sind wichtig, aber oft nicht vollständig technisch prüfbar.

### 2. Evidence-basierte Anforderungen

Beispiel:

- ein SBOM muss vorliegen
- ein Vulnerability-Scan muss nachweisbar sein

Diese Anforderungen sind gut für Governance as Code geeignet.

### 3. Technische Gate-Anforderungen

Beispiel:

- Artifact-Digest muss vorhanden sein
- Severity-Threshold darf nicht überschritten sein
- Signatur muss vorhanden sein

Diese Anforderungen lassen sich besonders gut als automatisierte Gates ausführen.

## Warum dieser Zusammenhang wichtig ist

Ohne diese Trennung entstehen typische Probleme:

- Controls sind da, aber niemand weiß, welches Dokument sie autorisiert
- Evidence wird erzeugt, aber niemand weiß, gegen welche Anforderung sie geprüft wird
- Pipeline-Gates laufen, aber sie sind nicht sauber auf die Governance-Dokumente zurückführbar
- Auditoren sehen technische Checks, aber nicht die normative Grundlage

Dieses Repository adressiert genau diese Lücke:

- **Policy** liefert die normative Legitimation
- **Directive** liefert die Governance-Ausführung und Entscheidungslogik
- **Baseline** liefert die konkret zu verifizierenden Anforderungen
- **Evidence** liefert den Nachweis
- **Governance as Code** liefert die ausführbare Prüfung

## Praktische Lesart für unterschiedliche Zielgruppen

### Für Management

Die Policy ist die verbindliche Aussage, dass DevSecOps eingehalten werden muss.

### Für Governance und Compliance

Die Directive regelt, wie die Einhaltung organisatorisch gesteuert, berichtet und bei Abweichungen behandelt wird.

### Für Plattform- und Security-Teams

Die Baseline enthält die konkreten Anforderungen, die technisch oder prozessual umgesetzt werden müssen.

### Für CI/CD und Application-Repositories

Governance as Code ist die operative Ausführung ausgewählter Anforderungen gegen maschinenlesbare Evidence.

## Repository-Dateien mit zentraler Bedeutung

Für diesen Zusammenhang sind insbesondere diese Dateien wichtig:

- `docs/governance/devsecops-policy.md`
- `docs/governance/devsecops-directive.md`
- `docs/governance/source-documents/DSCB-STD-SRC-001.public.md`
- `docs/governance/source-documents/PRA-STD-SRC-001.public.md`
- `model/documents/governance-documents.yaml`
- `model/traceability/document-to-control.yaml`
- `model/evidence/evidence-types.yaml`
- `docs/governance/source-of-truth.md`
- `docs/governance/governance-document-hierarchy.md`
- `.github/workflows/devsecops-baseline-reusable.yml`

## Kernaussage

Der Gesamtzusammenhang lautet:

> Die Policy macht DevSecOps verbindlich, die Directive regelt die bindende Ausführung, die Baseline definiert die konkreten Anforderungen, die Verifikationsmethoden bestimmen, wie diese Anforderungen geprüft werden, und Governance as Code führt ausgewählte Teile dieser Prüfung automatisiert auf Basis maschinenlesbarer Evidence aus.
