x

| Process Description |
| --- |
|  **Software Life-Cycle Process with integrated DevSecOps Operational Model** |

Contents

1	General	4

1.1	Aim and Purpose	4

1.2	Responsibilities	4

1.3	Applicable Documents	4

1.4	Referenced Documents	4

1.5	Definition of Terms	5

1.6	Abbreviations	5

2	Zweck und Scope	5

3	Normative Control Baseline Referenzen	6

4	Prozessprinzipien	6

5	Production und Pre-Production Entwicklungsphasen	7

6	Prozessübersicht	8

7	Prozessbeschreibung je Phase	10

7.1	P0 Applicability & DevSecOps Baseline Selection	10

7.2	Aktivitaets-, RACI- und Artefaktzuordnung	10

7.3	P1 Software Planning Process	11

7.4	Aktivitaets-, RACI- und Artefaktzuordnung	11

7.5	P2 pre-production Development Phase	12

7.6	Aktivitaets-, RACI- und Artefaktzuordnung	13

7.7	P3 Software Requirements Process	13

7.8	Aktivitaets-, RACI- und Artefaktzuordnung	14

7.9	P4 Software Design Process	15

7.10	Aktivitaets-, RACI- und Artefaktzuordnung	15

7.11	P5 Software Coding Process	16

7.12	Aktivitaets-, RACI- und Artefaktzuordnung	16

7.13	P6 Software Integration and Test Process	17

7.14	Aktivitaets-, RACI- und Artefaktzuordnung	17

7.15	P6a Software Dry Run Process	18

7.16	Aktivitaets-, RACI- und Artefaktzuordnung	18

7.17	P7 Software Verification Process	19

7.18	Aktivitaets-, RACI- und Artefaktzuordnung	20

7.19	P8 Release & Operational Traceability	20

7.20	Aktivitaets-, RACI- und Artefaktzuordnung	21

7.21	P9 In-Service Software Maintenance, Update & Patch Process	21

7.22	Aktivitaets-, RACI- und Artefaktzuordnung	22

7.22.1	P9 Change Classification and Lifecycle Treatment	23

8	Gate- und Entscheidungsmodell	24

9	Rollen und Verantwortlichkeiten	25

9.1	Rollenmodell	25

9.2	RACI Matrix - Phasen- und Entscheidungssicht	27

10	Zentrale Traceability-Kette	28

General

Aim and Purpose

Responsibilities

The Chief Digitalisation Office owns the enterprise process framework and the normative DevSecOps governance baseline. Operational responsibility for process execution, evidence creation, reviews, gate preparation, release and in-service maintenance is assigned to the roles defined in Chapter 9. Project-specific role assignments and delegations shall be documented in the Applicability Assessment and Software Planning Data / SDP. Where one person performs more than one role, required review and approval independence shall be preserved.

Applicable Documents

The following publications form a part of this document to the extent specified herein. In case no version is quoted for a document the current version is deemed to apply. When a version is quoted, this version shall be used.

Policy

Directive

DevSecOps Control Baseline Standard

DevSecOps Platform Stack Reference Architecture Standard

COMPANY Agile Baseline: Internal reference: [removed]

SDD Architecture Governance Framework: Internal reference: [removed]

SDD Enterprise Architecture Guideline: Internal reference: [removed]

SDD Solution Architecture Guidelines: Internal reference: [removed]

Product Architecture Guidelines: Internal reference: [removed]

SDD Architecture Templates and Checklists: Internal reference: [removed]

COMPANY Agile Baseline; Executive Summary Version: Internal reference: [removed]

-

Referenced Documents

The following publications contain further input and background information relating the subject addressed. In case no version is quoted for a document the current version is deemed to apply. When a version is quoted, this version shall be used.

DevSecOps Control Baseline Standard

COMPANY Agile Baseline: Internal reference: [removed]

SDD Architecture Governance Framework: Internal reference: [removed]

SDD Enterprise Architecture Guideline: Internal reference: [removed]

SDD Solution Architecture Guidelines: Internal reference: [removed]

Product Architecture Guidelines: Internal reference: [removed]

-

Definition of Terms

The terms and definitions established for the Business Management System are listed in the common “BMS Glossary”. The following terms are specific to this document.

| Term | Explanation |
| --- | --- |
|  |  |

Abbreviations

| Abbreviation | Term |
| --- | --- |
| RACI | Responsible, Accountable, Consulted, Informed |
|  |  |
|  |  |

Zweck und Scope

| **Prozessziel.**Der Prozess stellt sicher, dass Software nicht nur entwickelt, getestet und freigegeben wird, sondern dass die zugehoerige DevSecOps-Evidence entlang des gesamten Lifecycles erzeugt, bewertet und fuer Governance-Entscheidungen nutzbar gemacht wird. |
| --- |

Der Prozess basiert auf dem vorhandenen SDP-Phasenmodell und ergaenzt dieses um DevSecOps Governance, Evidence Collection, Control-Baseline-Referenzen sowie eine In-Service-Erweiterung fuer Updates, Patches, Vulnerability Handling und Operational Traceability.

Der Prozess ist fuer zulassungsrelevante Software unmittelbar anwendbar und kann fuer hoehere Kritikalitaet / Security erweitert werden, indem staerkere Baselines wie L2 oder L3 verpflichtend angewendet werden.

Der Prozess ist abgestimmt mit [RD02] [RD03] [RD04] [RD05] [RD06]. Das bedeutet das die fachlichen Inhalte der Themen z.b Architektur auf den verschiedenen Ebenen in [RD04] [RD05] [RD06] beschrieben sind und nicht Teil der Prozessbeschreibung.

Normative Control Baseline Referenzen

Die folgenden Control Baselines [RD01] bilden die normative Referenz fuer die DevSecOps-Anforderungen im Prozess. In einer Umsetzung sollten diese Dateien versioniert, freigegeben und nicht direkt aus einem ungeschuetzten Main-Branch konsumiert werden.

| Baseline | Repository-Datei | Rolle im Prozess | Typische Controls |
| --- | --- | --- | --- |
| DSCB L1 - Enterprise DevSecOps Baseline | model/controls/dscb-l1.yaml | Mindestbaseline fuer Traceability, Source Code Integrity, SBOM, Vulnerability Scan, Build Control, Artifact Integrity, Release Authorization und Pipeline Evidence. | DSCB-L1-REQ-001 bis DSCB-L1-REQ-016 |
| DSCB L2 - Secure DevSecOps | model/controls/dscb-l2.yaml | Erweiterte Baseline fuer sichere Entwicklungsumgebungen, IAM/MFA, Dependency Source Control, Artifact Signing, IaC und Pipeline Security Gates. | DSCB-L2-REQ-001 bis DSCB-L2-REQ-014 |
| DSCB L3 - Trusted Software Supply Chain / SDD | model/controls/dscb-l3.yaml | Starke Baseline fuer reproducible builds, isolierte Build-Umgebungen, Provenance, enterprise signing, End-to-End Traceability und Continuous Compliance. | DSCB-L3-REQ-001 bis DSCB-L3-REQ-011 |
| DSCB GOV - Governance Requirements | model/controls/dscb-gov.yaml | Governance-Baseline fuer Applicability, Compliance Verification, Waiver, Deviations und Review-Entscheidungen. | DSCB-GOV-REQ-001 bis DSCB-GOV-REQ-005 |

Prozessprinzipien

- Der SDLC bleibt die fuehrende Lifecycle- und Prozessstruktur.
- Die DevSecOps Control Baselines [RD01] definieren, welche Anforderungen pro Phase nachweisbar erfuellt werden muessen.
- Evidence wird moeglichst automatisch aus ALM, Repository, CI/CD, Artifact Repository, Security Scans und Review Records erzeugt.
- Jede Phase endet mit einem Gate: pass, fail, manual review, waiver required oder not applicable.
- Release-relevante Entscheidungen duerfen nur auf Basis verlinkter Evidence und dokumentierter Abweichungen getroffen werden.
- Prozessrelevante Dokumentation wird möglichst versioniert, reviewbar und automatisierbar geführt.

Production und Pre-Production Entwicklungsphasen

Der Prozess unterscheidet explizit zwischen der pre-production Entwicklungsphase und der Production Entwicklungsphase. P2 dient der iterativen Vorentwicklung und Risikoreduktion; P3 bis P7 bilden den production kontrollierten Lifecycle mit freigegebenen Baselines, formalen Reviews, formalen Konfigurationsmanagement und release-relevanter Evidence.

P0 und P1 liegen vor dieser Trennung und schaffen Scope, Planning Data, Control-Baseline-Auswahl und Evidence-Strategie. P8 stellt die freigegebene Release- und Operational-Traceability-Baseline her; P9 nutzt diese Baseline fuer kontrollierte In-Service Updates, Patches und Maintenance Releases.

| **Prozessbereich** | **Phasenstatus** | **Governance-Konsequenz** |
| --- | --- | --- |
| **P0-P1** | Vorbereitende Governance- und Planungsphase | Applicability, DevSecOps Baseline, SDP-Anwendung, Toolchain, CM/SCM und Evidence-Strategie werden festgelegt. |
| **P2 pre-production Development Phase** | Pre-production | Agile/iterative Vorentwicklung. Requirements, Design, Code, Tests und Evidence entstehen als Drafts. Artefakte werden unter Configuration Management gefuehrt, aber noch nicht unter formales Change-Management gestellt. Ergebnisse aus P2 sind keine formale Release-Freigabe. |
| **Transition P2 -> P3** | Formalisierungsgate | Draft Lifecycle Data aus P2 werden auf Konsistenz, Vollstaendigkeit und Control-Baseline-Abdeckung bewertet. Mit Eintritt in P3 beginnt die formale production Lifecycle-Fuehrung. |
| **P3-P7** | Production Development Phase | Requirements, Design, Code, Integration/Test und Verification werden formal erstellt, geprueft, baselined und release-relevant bewertet. Formales Change Management und auditierbare Evidence sind verpflichtend. |
| **P6a Dry Run** | Pre-Production Verification-Unterstuetzung | Dry Runs reduzieren Risiko und bereiten P7 vor. Sie ersetzen nicht die formale Verification und erzeugen fuer sich allein keine Release-Freigabe. |
| **P8** | Nachgelagerte Release- und Betriebsphase | Approved Release, Deployment Records, Artifact Identity und Operational Traceability werden in Betrieb und Incident Handling fortgefuehrt. |
| **P9** | In-Service Maintenance Phase | Updates, Patches, Vulnerability Findings, Incidents, SBOM-Drift und Operational Changes werden bewertet, priorisiert, nach DevSecOps Controls geprueft und als Maintenance Release kontrolliert, freigegeben oder dokumentiert verworfen. |

Prozessübersicht

| Prozessschritt | Ziel | Haupt-Gate |
| --- | --- | --- |
| P0 Applicability & Baseline | Governance-Scope, anwendbare DevSecOps-Baseline und formalen Lifecycle-Scope bestimmen. | Baseline assignment approved. |
| P1 Software Planning | Prozess, Standards, Toolchain, Evidence-Strategie, CM/SCM und Uebergang von nicht formal zu formal planen. | Planning data under CM. |
| P2 pre-production Development | Pre-production, agile/iterative Vorentwicklung mit Draft Requirements, Draft Design, Non Formal Source Code, Tests und frueher Evidence. | Readiness for production Development assessed. |
| P3 Requirements | Production Phase: Software Requirements erstellen, reviewen, traceable machen und als Baseline freigeben. | Requirements baseline approved. |
| P4 Design | Production Phase: Software Architecture und Design aus freigegebenen Requirements ableiten und baselinen. | Design baseline approved. |
| P5 Coding | production Phase: Source Code kontrolliert aus Requirements und Design ableiten, reviewen und unter SCM baselinen. | Source baseline ready. |
| P6 Integration & Test | production Phase: Build, Integration, Test Evidence, SBOM, Vulnerability- und Artifact-Integrity-Nachweise erzeugen. | SQA transition ready. |
| P6a Dry Run | Pre-production Verification-Unterstuetzung zur Risikoreduktion vor P7; ersetzt keine formale Verification. | production verification readiness improved. |
| P7 Verification | production Phase: offizielle Verification durchfuehren und Release-Entscheidung mit Compliancy Matrix und Evidence vorbereiten. | Verification approved. |
| P8 Release & Operational Traceability | Nachgelagerte Phase: Approved Release deployen und Traceability in Betrieb und Incident Handling erhalten. | Operational traceability active. |
| P9 In-Service Maintenance, Update & Patch | In-Service Trigger wie CVEs, Incidents, Dependency Updates, SBOM-Drift oder Betriebsabweichungen bewerten und kontrolliert in Updates, Patches, Waiver oder Monitoring ueberfuehren. | Patch release or maintenance decision approved. |

Prozessbeschreibung je Phase

Operationalisierung der Verantwortlichkeiten: Direkt nach jeder Phasenbeschreibung wird die dort definierte Aktivitaet mit RACI und dem daraus entstehenden Artefakt / Output / Evidence verknuepft. R = Responsible, A = Accountable fuer das konkrete Ergebnis/Artefakt, C = Consulted, I = Informed. Kurzformen: DM = Software Development Manager / Project Lead; PO = Product Owner; RE = System Engineering / Requirements Engineering; DEV = Development Team; ARCH = Software Architect; V&V = Test / Verification Lead; SQA = SQA / Quality; DSO = Security / DevSecOps; CM = Configuration Manager; GOV = Governance Board; OPS = Service Owner / Operations; PSIRT = Product Security / PSIRT; RM = Release / Maintenance Manager.

P0 Applicability & DevSecOps Baseline Selection

| Element | Beschreibung |
| --- | --- |
| Ziel | Festlegen, ob L1, L2 oder L3 anzuwenden ist und welche Governance-Anforderungen fuer das Projekt gelten. |
| Inputs | Projektauftrag, System-/Software-Scope, Kritikalitaetseinschaetzung, Vertrags-/Programmkontext, bekannte regulatorische oder interne Vorgaben. |
| Outputs | Applicability Assessment, ausgewaehlte DevSecOps Baseline L1/L2/L3, Scope-Entscheidung, initiale Governance-Verantwortlichkeiten, erste Waiver-Kandidaten. |
| Aktivitäten | Kritikalitaet bewerten, System-/Software-Scope klaeren, Baseline auswaehlen, Toolchain-Faehigkeit pruefen, Abweichungen frueh identifizieren. |
| Evidence / Nachweise | Applicability Assessment, Program Control Baseline Assignment, initial Waiver Records falls erforderlich. |
| Control Baseline Referenzen | DSCB-GOV-REQ-001; DSCB-GOV-REQ-002; bei hoeherer Kritikalitaet zusaetzlich DSCB-L2 oder DSCB-L3. |
| Gate / Exit Decision | Projekt darf in die Planung uebergehen, wenn Baseline, Verantwortlichkeiten und Evidence-Strategie festgelegt sind. |

Aktivitaets-, RACI- und Artefaktzuordnung

| Aktivitaet / Entscheidung | R | A | C | I | Artefakt / Output / Evidence |
| --- | --- | --- | --- | --- | --- |
| Kritikalitaet bewerten | DM; DSO | GOV | ARCH; SQA; RE | CM; PO | Applicability Assessment |
| System-/Software-Scope klaeren | DM; RE | DM | PO; ARCH; DSO | SQA; CM | Scope-Entscheidung; Applicability Assessment |
| DevSecOps Baseline L1/L2/L3 auswaehlen | DSO; DM | GOV | SQA; ARCH; CM | PO; DEV; V&V; OPS | Program Control Baseline Assignment |
| Toolchain-Faehigkeit pruefen | DSO; CM | DM | DEV; SQA | GOV | Toolchain-Faehigkeit als Teil des Applicability Assessment |
| Abweichungen / Waiver-Kandidaten frueh identifizieren | DSO; SQA | DM | ARCH; CM; GOV | PO | Initial Waiver Records, falls erforderlich |
| Gate: Baseline assignment approved | DM; DSO | GOV | SQA; ARCH; CM; RE | PO; DEV; V&V; OPS | Baseline Assignment Approval; Scope-Entscheidung |

*A bezeichnet die Ergebnis-/Artefaktverantwortung fuer die jeweilige Aktivitaet. Die phasenbezogene Gate- und Gesamtverantwortung bleibt zusaetzlich gemaess Kapitel 9 bestehen.*

P1 Software Planning Process

| Element | Beschreibung |
| --- | --- |
| Ziel | Entwicklungsprozess, Standards, Toolchain, CM/SCM, CI/CD, DevSecOps Gates und den expliziten Uebergang von nicht formaler Entwicklung zu formaler Lifecycle-Fuehrung planen. |
| Inputs | Applicability Assessment, ausgewaehlte Control Baseline, vorlaeufige System Requirements, Programmplanung, vorhandene Standards, Toolchain-Rahmenbedingungen. |
| Outputs | Freigegebene Software Planning Data, SDP-Anwendung, Quality-/CM-/SCM-Planung, Evidence-Strategie, CI/CD Control Strategy, Document-as-Code Scope, Definition der P2 Non Formal Development Phase und der Formal Development Phase P3-P7. |
| Aktivitäten | SDP anwenden, Software Requirements/Design/Code Standards festlegen, CI/CD-Strategie definieren, Evidence Contract vorbereiten, Document-as-Code-Anwendungsumfang für prozessrelevante Lifecycle-Artefakte festlegen, Review- und Releasepunkte planen. |
| Evidence / Nachweise | SDP, Software Quality Plan, CM Plan, Toolchain Records, Governance Run Input Template, SCM Records. |
| Control Baseline Referenzen | DSCB-GOV-REQ-001; DSCB-GOV-REQ-002; DSCB-L1-REQ-015; optional DSCB-L2-REQ-001/002. |
| Gate / Exit Decision | Planning Process Data sind freigegeben, versioniert und unter Konfigurationsmanagement. |

Aktivitaets-, RACI- und Artefaktzuordnung

| Aktivitaet / Entscheidung | R | A | C | I | Artefakt / Output / Evidence |
| --- | --- | --- | --- | --- | --- |
| SDP anwenden und Prozessumfang festlegen | DM; SQA | DM | DSO; CM; ARCH; V&V | GOV; PO | Software Planning Data / SDP |
| Software Requirements-/Design-/Code-Standards festlegen | RE; ARCH; DM | DM | SQA; DSO; DEV | V&V; CM | Software Planning Data; referenzierte Standards |
| CI/CD-Strategie definieren | DSO; DEV | DM | CM; SQA; V&V | GOV; RM | CI/CD Control Strategy; Toolchain Records |
| Evidence Contract / Evidence-Strategie vorbereiten | DSO; SQA | DM | CM; V&V; RE | GOV | Evidence-Strategie; Governance Run Input Template |
| Review- und Releasepunkte planen | DM; SQA; RM | DM | V&V; CM; GOV; PO | DEV; OPS | SDP; Software Quality Plan |
| Gate: Planning Data freigeben, versionieren und unter CM stellen | CM; SQA; DM | DM | DSO | GOV; PO; DEV | Freigegebene Software Planning Data; CM Plan; SCM Records |

*A bezeichnet die Ergebnis-/Artefaktverantwortung fuer die jeweilige Aktivitaet. Die phasenbezogene Gate- und Gesamtverantwortung bleibt zusaetzlich gemaess Kapitel 9 bestehen.*

P2 pre-production Development Phase

| Element | Beschreibung |
| --- | --- |
| Ziel | Nicht formale, agile/iterative Vorentwicklung, um Requirements, Design, Code, Tests und fruehe DevSecOps Evidence schrittweise aufzubauen und technische Risiken vor Eintritt in die formale Phase zu reduzieren. |
| Inputs | Planning Data, Product Backlog, Vertrags-/Systemanforderungen als Draft oder Baseline, Architekturannahmen, Toolchain und initialer Evidence Contract. |
| Outputs | Draft Requirements, Draft Design, pre-production Source Code, erste Review Records, Static Analysis Results, Draft Test Cases/Procedures, pre-production Test Results, initiale SBOM/Vulnerability Evidence und Readiness Assessment fuer P3. Diese Outputs sind nicht als formale Release-Freigabe zu verwenden. |
| Aktivitäten | Iterative Backlog-Arbeit, Prototyping, Draft Reviews, fruehe Security Checks, statische Analysen, Dependency Checks, CI/CD Probelauf, Problem Report Erfassung und Vorbereitung der formalen Baselines. |
| Evidence / Nachweise | Nicht formale Review Results, Draft Traceability, CI/CD Run Records, Static Analysis Reports, Dependency Findings, Non Formal Test Results, Draft SBOM und dokumentierte offene Punkte fuer den P2->P3 Uebergang. |
| Control Baseline Referenzen | DSCB-L1-REQ-001; DSCB-L1-REQ-002; DSCB-L1-REQ-004; DSCB-L1-REQ-015. |
| Gate / Exit Decision | Exit aus P2 bedeutet Readiness for Formal Development Phase (P3-P7): Draft Lifecycle Data sind vorhanden, wesentliche Risiken sind bekannt und der Formalisierungsgate kann entscheiden. Es ist keine formale Release-Freigabe. |

Aktivitaets-, RACI- und Artefaktzuordnung

| Aktivitaet / Entscheidung | R | A | C | I | Artefakt / Output / Evidence |
| --- | --- | --- | --- | --- | --- |
| Iterative Backlog-Arbeit und Draft Requirements | DEV; RE | DM | PO; ARCH | SQA; DSO; V&V | Draft Requirements; Draft Traceability |
| Prototyping, Draft Design und pre-production Source Code | DEV; ARCH | DM | RE; DSO | SQA; V&V | Draft Design; pre-production Source Code |
| Draft Reviews durchfuehren | ARCH; RE; DEV | DM | SQA; V&V; DSO | PO; CM | Non Formal Review Results; Review Records |
| Fruehe Security Checks, Static Analysis und Dependency Checks | DSO; DEV | DM | ARCH; SQA | CM | Static Analysis Reports; Dependency Findings; Draft SBOM/Vulnerability Evidence |
| CI/CD Probelauf durchfuehren | DEV; DSO | DM | CM; SQA | V&V | CI/CD Run Records |
| Problem Reports und offene Punkte erfassen | DEV; V&V | DM | ARCH; SQA | PO | Problem Reports; dokumentierte offene Punkte |
| Formale Baselines vorbereiten und Readiness bewerten | CM; SQA; ARCH; RE | DM | DSO; V&V | GOV; PO | Readiness Assessment fuer P3; Draft Lifecycle Data |
| Gate: P2 -> P3 Formalisierung | SQA; CM; ARCH | DM | RE; V&V; DSO; PO; GOV | DEV; RM | P2 Readiness Decision; non_formal_ready |

*A bezeichnet die Ergebnis-/Artefaktverantwortung fuer die jeweilige Aktivitaet. Die phasenbezogene Gate- und Gesamtverantwortung bleibt zusaetzlich gemaess Kapitel 9 bestehen.*

P3 Software Requirements Process

| Element | Beschreibung |
| --- | --- |
| Ziel | Start der Formal Development Phase: Software High-Level Requirements formal erstellen, validieren, reviewen, traceable machen und unter Configuration Management baselinen. |
| Inputs | Formal freigegebene System Requirements Specification, Draft Software Requirements aus P2, Review Findings, Applicability Assessment, Control Baseline und P2 Readiness Decision. |
| Outputs | Freigegebene Software Requirements Specification, Requirements Traceability Matrix, Requirements Review Record, Acceptance Record, Requirements Baseline. |
| Aktivitäten | System Requirements akzeptieren, Software Requirements ableiten, Requirements Specification erstellen, Traceability Matrix erzeugen, Requirements Review durchfuehren, Baseline bilden. |
| Evidence / Nachweise | Software Requirements Specification, Requirements Traceability Records, Requirements Review Record, Acceptance Record, SCM/CM Baseline. |
| Control Baseline Referenzen | DSCB-L1-REQ-001; DSCB-L3-REQ-009 fuer End-to-End Traceability in hoeherer Baseline. |
| Gate / Exit Decision | Requirements Baseline approved. Ab P3 unterliegen Aenderungen der formal definierten Change- und Configuration-Management-Logik. |

Aktivitaets-, RACI- und Artefaktzuordnung

| Aktivitaet / Entscheidung | R | A | C | I | Artefakt / Output / Evidence |
| --- | --- | --- | --- | --- | --- |
| System Requirements akzeptieren | RE | DM | PO; ARCH; SQA | DEV; V&V | Acceptance Record |
| Software Requirements ableiten und Specification erstellen | RE | DM | ARCH; PO; DEV | DSO; V&V | Software Requirements Specification |
| Requirements Traceability erzeugen | RE | DM | SQA; CM; DSO | ARCH; V&V | Requirements Traceability Matrix / Records |
| Requirements Review durchfuehren | RE; SQA | DM | PO; ARCH; DSO; CM | DEV; V&V | Requirements Review Record |
| Requirements Baseline bilden | CM; RE | DM | SQA | GOV; DEV; V&V | Requirements Baseline; SCM/CM Baseline |
| Gate: Requirements Baseline approved | DM; SQA; CM | DM | PO; RE; ARCH; DSO | GOV; DEV; V&V | Approved Requirements Baseline; formal_base_ok |

*A bezeichnet die Ergebnis-/Artefaktverantwortung fuer die jeweilige Aktivitaet. Die phasenbezogene Gate- und Gesamtverantwortung bleibt zusaetzlich gemaess Kapitel 9 bestehen.*

P4 Software Design Process

| Element | Beschreibung |
| --- | --- |
| Ziel | Formal Development Phase: Software Architecture und Software Design aus freigegebenen Requirements ableiten, reviewen, traceable machen und baselinen. |
| Inputs | Freigegebene Software Requirements Specification, Traceability Matrix, Architecture Constraints, Design Standards, offene Problem Reports. |
| Outputs | Software Architecture, Software Design Description, Interface Description, Design Review Record, Problem Reports, Design Baseline. |
| Aktivitäten | Architektur entwickeln, Software Design Description und Interfaces beschreiben, Design Review durchfuehren, Abweichungen und Problem Reports dokumentieren. |
| Evidence / Nachweise | Software Design Data, Architecture Review Record, Design Review Record, Problem Reports, CM Baseline. |
| Control Baseline Referenzen | DSCB-GOV-REQ-002; DSCB-L1-REQ-001; optional DSCB-L3-REQ-009. |
| Gate / Exit Decision | Design Baseline approved; Design Data sind formal konsistent mit Requirements, Traceability und Control-Baseline-Nachweisen. |

Aktivitaets-, RACI- und Artefaktzuordnung

| Aktivitaet / Entscheidung | R | A | C | I | Artefakt / Output / Evidence |
| --- | --- | --- | --- | --- | --- |
| Software Architecture entwickeln | ARCH; DEV | ARCH | RE; DSO; SQA | DM; V&V | Software Architecture |
| Software Design Description und Interfaces beschreiben | ARCH; DEV | ARCH | RE; V&V | DM; CM | Software Design Description; Interface Description |
| Architecture / Design Review durchfuehren | ARCH | ARCH | RE; SQA; DSO; V&V | DM; CM | Architecture Review Record; Design Review Record |
| Abweichungen und Problem Reports dokumentieren | ARCH; DEV | ARCH | SQA; DSO; CM | DM | Problem Reports |
| Gate: Design Baseline bilden und freigeben | CM; ARCH | ARCH | SQA; RE; DSO | DM; PO; V&V | Design Baseline; CM Baseline; formal_base_ok |

*A bezeichnet die Ergebnis-/Artefaktverantwortung fuer die jeweilige Aktivitaet. Die phasenbezogene Gate- und Gesamtverantwortung bleibt zusaetzlich gemaess Kapitel 9 bestehen.*

P5 Software Coding Process

| Element | Beschreibung |
| --- | --- |
| Ziel | Formal Development Phase: Requirements und Design kontrolliert in Source Code umsetzen, Reviews durchfuehren und Source Code unter SCM baselinen. |
| Inputs | Freigegebene Software Architecture, Software Design Data, Coding Standards, Requirements Links, Branch-/Repository-Regeln. |
| Outputs | Source Code Baseline, Commit History, Pull Request und Code Review Records, Static Analysis Reports, Buildability Evidence, Problem Reports. |
| Aktivitäten | Source Code entwickeln, Pull Requests verwenden, Code Reviews durchfuehren, Branch Protection anwenden, Static Analysis ausfuehren, Buildability nachweisen. |
| Evidence / Nachweise | Commit History, Code Review Records, Branch Protection Configuration, Static Analysis Reports, Source Code Baseline, Problem Reports. |
| Control Baseline Referenzen | DSCB-L1-REQ-002; DSCB-L1-REQ-003; DSCB-L1-REQ-004; bei hoeherer Baseline DSCB-L2-REQ-011/012. |
| Gate / Exit Decision | Source Code Baseline ready; offene Findings, Waiver und Abweichungen sind formal bewertet und traceable. |

Aktivitaets-, RACI- und Artefaktzuordnung

| Aktivitaet / Entscheidung | R | A | C | I | Artefakt / Output / Evidence |
| --- | --- | --- | --- | --- | --- |
| Source Code entwickeln | DEV | DM | ARCH; RE | PO; V&V | Source Code |
| Pull Requests und kontrollierten Branch Workflow verwenden | DEV | DM | ARCH; CM; DSO; SQA | PO | Commit History; Pull Request Records |
| Code Reviews durchfuehren | DEV; ARCH | DM | SQA; DSO | CM | Code Review Records |
| Branch Protection anwenden | DSO; CM | DM | DEV; SQA | ARCH | Branch Protection Configuration |
| Static Analysis ausfuehren | DEV; DSO | DM | SQA; ARCH | V&V | Static Analysis Reports |
| Buildability nachweisen | DEV; DSO | DM | CM | V&V; SQA | Buildability Evidence |
| Gate: Source Code Baseline herstellen und Findings traceable bewerten | CM; DEV | DM | SQA; DSO; ARCH | GOV; PO | Source Code Baseline; Problem Reports / Waiver Records, falls erforderlich; formal_base_ok |

*A bezeichnet die Ergebnis-/Artefaktverantwortung fuer die jeweilige Aktivitaet. Die phasenbezogene Gate- und Gesamtverantwortung bleibt zusaetzlich gemaess Kapitel 9 bestehen.*

P6 Software Integration and Test Process

| Element | Beschreibung |
| --- | --- |
| Ziel | Formal Development Phase: Software bauen, integrieren, testbar machen und release-relevante Evidence wie Build Logs, SBOM, Vulnerability Scan und Artifact Integrity erzeugen. |
| Inputs | Source Code Baseline, Build Configuration, Test Cases Draft, Test Data Draft, Toolchain-Konfiguration, Repository- und Pipeline-Kontext. |
| Outputs | Executable Object Code, Installation Packages, Build Logs, SBOM, Vulnerability Scan Report, Artifact Digest, SCID, Test Cases, Test Data, Test Environment Description. |
| Aktivitäten | Build ausfuehren, Komponenten integrieren, Executable Object Code und Installationspakete erstellen, SBOM erzeugen, Vulnerability Scan ausfuehren, Artifact Digest erzeugen, Test-Cases und Test Data baselinen. |
| Evidence / Nachweise | Build Pipeline Logs, Artifact Version Identifiers, SBOM, Dependency Scan Reports, Vulnerability Scan Reports, Artifact Digest, SCID, Test Cases, Test Data, Test Environment Description. |
| Control Baseline Referenzen | DSCB-L1-REQ-005; DSCB-L1-REQ-006; DSCB-L1-REQ-007; DSCB-L1-REQ-008; DSCB-L1-REQ-009; DSCB-L1-REQ-010; DSCB-L1-REQ-011; DSCB-L1-REQ-012; DSCB-L1-REQ-015. |
| Gate / Exit Decision | SQA Transition ready; Build, Integration, Test Evidence, SBOM, Vulnerability Status und Artifact Integrity sind formal pruefbar. |

Aktivitaets-, RACI- und Artefaktzuordnung

| Aktivitaet / Entscheidung | R | A | C | I | Artefakt / Output / Evidence |
| --- | --- | --- | --- | --- | --- |
| Build ausfuehren | DEV; DSO | DM | CM | SQA; V&V | Build Pipeline Logs; Executable Object Code |
| Komponenten integrieren und Installationspakete erstellen | DEV; V&V | DM | ARCH; CM | SQA | Installation Packages; Artifact Version Identifiers |
| SBOM erzeugen | DSO; DEV | DM | CM | SQA | SBOM |
| Vulnerability / Dependency Scan ausfuehren | DSO | DM | SQA; DEV | GOV; RM | Vulnerability Scan Reports; Dependency Scan Reports |
| Artifact Digest erzeugen | DSO; CM | DM | DEV | SQA; RM | Artifact Digest |
| Test Cases, Test Data und Test Environment baselinen | V&V; CM | V&V | SQA; DEV | DM | Test Cases; Test Data; Test Environment Description |
| SCID und Configuration Identifiers herstellen | CM | DM | DSO; DEV; V&V | SQA; RM | SCID; Artifact Version Identifiers |
| Gate: SQA Transition Readiness herstellen | SQA; V&V | SQA | DSO; CM; DM | GOV; RM | SQA Transition Record; formal_base_ok |

*A bezeichnet die Ergebnis-/Artefaktverantwortung fuer die jeweilige Aktivitaet. Die phasenbezogene Gate- und Gesamtverantwortung bleibt zusaetzlich gemaess Kapitel 9 bestehen.*

P6a Software Dry Run Process

| Element | Beschreibung |
| --- | --- |
| Ziel | Nicht formale Verification-Unterstuetzung und Risikoreduktion vor der formalen Verification in P7. |
| Inputs | pre-production Source Code oder Source Baseline, Draft Test Cases, Draft Test Procedures, Referenzanlage, Test Plan, bekannte Problem Reports. |
| Outputs | Dry Run Test Results, PTC Test Session Results, neue oder aktualisierte Problem Reports, Change Decisions, aktualisierte Testdaten und Readiness Findings fuer P7. Dry-Run-Ergebnisse sind unterstuetzende Evidence, aber keine formale Verification Approval. |
| Aktivitäten | Build auf Referenzanlage installieren, Testplan in ALM anlegen, Test Cases ausfuehren, Ergebnisse erfassen, Problem Reports analysieren und Change Decisions treffen. |
| Evidence / Nachweise | Dry Run Test Results, PTC Test Session Results, Problem Reports, Change Decisions, Waiver Records falls erforderlich. |
| Control Baseline Referenzen | DSCB-L1-REQ-001; DSCB-L1-REQ-009; DSCB-L1-REQ-010; DSCB-GOV-REQ-004; DSCB-GOV-REQ-005. |
| Gate / Exit Decision | Dry Run completed or waived. Das Ergebnis verbessert die Readiness fuer P7, ersetzt aber weder formale Verification noch Release Approval. |

Aktivitaets-, RACI- und Artefaktzuordnung

| Aktivitaet / Entscheidung | R | A | C | I | Artefakt / Output / Evidence |
| --- | --- | --- | --- | --- | --- |
| Build auf Referenzanlage installieren | V&V; DEV | V&V | CM | DM; SQA | PTC Test Session / Dry Run Setup |
| Testplan in ALM anlegen | V&V | V&V | SQA; CM | DM | Test Plan; PTC Test Session |
| Test Cases ausfuehren und Ergebnisse erfassen | V&V | V&V | DEV; SQA | DM | Dry Run Test Results; PTC Test Session Results |
| Problem Reports analysieren | V&V; DEV | V&V | ARCH; DSO; SQA | DM | Problem Reports |
| Change Decisions treffen | V&V; DM | DM | ARCH; SQA; DSO; CM | PO; GOV | Change Decisions; Waiver Records, falls erforderlich |
| Gate: Dry Run abschliessen / waiven und P7 Readiness bewerten | V&V; SQA | V&V | DM; ARCH; DSO | GOV; RM | Readiness Findings fuer P7; Dry Run completed or waived |

*A bezeichnet die Ergebnis-/Artefaktverantwortung fuer die jeweilige Aktivitaet. Die phasenbezogene Gate- und Gesamtverantwortung bleibt zusaetzlich gemaess Kapitel 9 bestehen.*

P7 Software Verification Process

| Element | Beschreibung |
| --- | --- |
| Ziel | Formal Development Phase: formale Verifikation der Software durchfuehren, Compliance gegen Requirements und Control Baselines bewerten und die Release-Entscheidung vorbereiten. |
| Inputs | SQA Transition Record aus P6, freigegebene Test Cases und Procedures, Test Environment, Installation Kit Candidate, offene Problem Reports, Release Candidate Evidence. |
| Outputs | Software Verification Results, Compliancy Matrix, Release Notes, Installation Kit, SQA Transition Record, Release Approval Records, finaler Evidence Package Status. |
| Aktivitäten | Alle Test Procedures ausfuehren, Compliancy Matrix erstellen, Problem Reports klassifizieren, Verification Results reviewen, Release Notes und Installation Kit erstellen. |
| Evidence / Nachweise | Software Verification Results, Compliancy Matrix, Release Notes, Installation Kit, SQA Transition Record, Release Approval Records. |
| Control Baseline Referenzen | DSCB-L1-REQ-013; DSCB-L1-REQ-014; DSCB-L1-REQ-015; DSCB-GOV-REQ-002/003. |
| Gate / Exit Decision | Formal Verification approved; Compliancy Matrix, Verification Results, Release Notes und offene Waiver/Findings sind vollstaendig und release-relevant entschieden. |

Aktivitaets-, RACI- und Artefaktzuordnung

| Aktivitaet / Entscheidung | R | A | C | I | Artefakt / Output / Evidence |
| --- | --- | --- | --- | --- | --- |
| Alle freigegebenen Test Procedures ausfuehren | V&V | V&V | SQA | DM; DEV | Software Verification Results |
| Compliancy Matrix erstellen | V&V; SQA | V&V | RE; DSO; CM | DM; GOV | Compliancy Matrix |
| Problem Reports klassifizieren | V&V; SQA | V&V | DEV; ARCH; DSO | DM; RM | Problem Reports / Classification |
| Verification Results reviewen | V&V; SQA | V&V | RE; ARCH; DSO; CM | DM; GOV | Verification Results; Review Records |
| Release Notes und Installation Kit erstellen | V&V; DEV; CM | V&V | SQA; RM | DM; OPS | Release Notes; Installation Kit |
| Final Evidence Package und Release Approval vorbereiten | SQA; RM; V&V | GOV | DSO; CM; ARCH; DM | PO; OPS | SQA Transition Record; Release Approval Records; finaler Evidence Package Status |
| Gate: Formal Verification approved | V&V; SQA | V&V | DSO; RE; ARCH; CM | GOV; RM; DM | Formal Verification Approval; formal_base_ok |

*A bezeichnet die Ergebnis-/Artefaktverantwortung fuer die jeweilige Aktivitaet. Die phasenbezogene Gate- und Gesamtverantwortung bleibt zusaetzlich gemaess Kapitel 9 bestehen.*

P8 Release & Operational Traceability

| Element | Beschreibung |
| --- | --- |
| Ziel | Freigegebenes Artifact deployen, Betriebstraceability herstellen und die Operational Baseline fuer In-Service Maintenance, Updates und Patches an P9 uebergeben. |
| Inputs | Freigegebener Release Candidate, Release Approval, Artifact Identity, Deployment Plan, approved Artifact Evidence, Betriebs-/Monitoring-Kontext. |
| Outputs | Deployment Records, Runtime Version Records, System Logs, Incident Records, Operational Traceability Baseline, Deployed Artifact Identity und In-Service Monitoring Inputs fuer P9. |
| Aktivitäten | Approved Artifact deployen, Deployment Records erzeugen, Runtime Version erfassen, Monitoring- und Incident-Records mit Release verbinden. |
| Evidence / Nachweise | Deployment Logs, Deployment Records, System Logs, Incident Records, Runtime Version Records, Compliance Evidence Repository. |
| Control Baseline Referenzen | DSCB-L1-REQ-014; DSCB-L1-REQ-016; DSCB-L2-REQ-013/014; DSCB-L3-REQ-011. |
| Gate / Exit Decision | Nur freigegebene Artifacts werden deployed; Deployment, Betrieb und Artifact Identity bleiben rueckverfolgbar und bilden die Baseline fuer In-Service Updates und Patches. |

Aktivitaets-, RACI- und Artefaktzuordnung

| Aktivitaet / Entscheidung | R | A | C | I | Artefakt / Output / Evidence |
| --- | --- | --- | --- | --- | --- |
| Approved Artifact deployen | OPS; RM | RM | CM; DSO; SQA | GOV; PO; PSIRT | Deployment Logs; Deployment Records |
| Runtime Version und deployed Artifact Identity erfassen | OPS; CM | OPS | RM | SQA; DSO | Runtime Version Records; Deployed Artifact Identity |
| Monitoring- und Incident Records mit Release verbinden | OPS | OPS | RM; DSO; PSIRT | GOV; DM | System Logs; Incident Records |
| Operational Traceability Baseline herstellen | OPS; CM | RM | SQA; DSO | GOV; PO | Operational Traceability Baseline; Compliance Evidence Repository |
| Gate: Operational Traceability aktivieren und an P9 uebergeben | OPS; RM | RM | CM; SQA; DSO; PSIRT | GOV; DM; PO | In-Service Monitoring Inputs fuer P9; operational traceability active |

*A bezeichnet die Ergebnis-/Artefaktverantwortung fuer die jeweilige Aktivitaet. Die phasenbezogene Gate- und Gesamtverantwortung bleibt zusaetzlich gemaess Kapitel 9 bestehen.*

P9 In-Service Software Maintenance, Update & Patch Process

| **Element** | **Beschreibung** |
| --- | --- |
| Ziel | Sicherstellen, dass freigegebene Software im Betrieb kontrolliert ueberwacht, bewertet, aktualisiert, gepatcht und rueckverfolgbar gehalten wird. P9 verbindet Betrieb, Vulnerability Management, Patch Management, CI/CD Evidence und Release Governance. |
| Trigger | CVE/Vulnerability Advisory, Incident, Kundenmeldung, Obsoleszenz, Dependency Update, Zertifikatsablauf, Plattform-/OS-Update, SBOM Drift, Penetration-Test-Finding oder Betriebserfahrung. |
| Inputs | Approved Release aus P8, Deployed Artifact Identity, SBOM, Vulnerability Scan Results, Runtime Logs, Incident Records, Asset Inventory, Configuration Baseline, Control Baseline L1/L2/L3. |
| Outputs | Maintenance Decision Record, Impact Assessment, Patch Plan, updated SBOM, Vulnerability Disposition, Build/Test Evidence, Waiver Record falls erforderlich, Patch Release Approval, Deployment Record und updated Operational Traceability. |
| Aktivitaeten | Operational Monitoring, Schwachstellenbewertung, Impact Analysis, Priorisierung, Change-Klassifikation, Patch-Entwicklung, CI/CD Control Evaluation, Regression Test, Security Scan, Artifact Signing, Deployment und Post-Deployment Verification. |
| Evidence / Nachweise | Vulnerability Triage Record, Maintenance Decision Record, Impact Assessment, SBOM Diff/Drift Report, CI/CD Run Records, Test Results, Scan Reports, Artifact Digest/Signature, Waiver Record, Patch Release Approval und Post-Deployment Verification Record. |
| Control Baseline Referenzen | DSCB-L1-REQ-001; DSCB-L1-REQ-009; DSCB-L1-REQ-010; DSCB-L1-REQ-015; DSCB-GOV-REQ-004; DSCB-GOV-REQ-005; bei L2/L3 zusaetzlich Controls fuer Artifact Integrity, Provenance, Signing und isolierte/reproduzierbare Builds. |
| Gate / Exit Decision | Patch, Update oder Maintenance Release darf nur deployed werden, wenn Impact, Change Classification, Evidence, SBOM, Vulnerability Status, Artifact Integrity, Waiver Status und Release Approval dokumentiert sind. Nicht erforderliche Patches werden mit Begruendung und Monitoring-Entscheidung geschlossen. |

Aktivitaets-, RACI- und Artefaktzuordnung

| Aktivitaet / Entscheidung | R | A | C | I | Artefakt / Output / Evidence |
| --- | --- | --- | --- | --- | --- |
| Operational Monitoring und In-Service Trigger erfassen | OPS | OPS | RM; PSIRT | DSO; SQA | Runtime Logs; Incident Records; Asset Inventory |
| Schwachstellenbewertung / Vulnerability Triage | PSIRT | PSIRT | DSO; OPS; ARCH | RM; SQA | Vulnerability Triage Record; Vulnerability Disposition |
| Impact Analysis durchfuehren | ARCH; PSIRT; RE | RM | DSO; CM; OPS | DM; PO | Impact Assessment |
| Priorisierung und Change Classification durchfuehren | RM; PSIRT; CM | RM | PO; ARCH; SQA; DSO | GOV; DEV; V&V | Maintenance Decision Record; Patch Plan |
| Patch / Maintenance Change entwickeln | DEV; ARCH | RM | RE; DSO; CM; PSIRT | DM; PO | Patch-Implementierung; Patch Plan |
| CI/CD Control Evaluation und Build durchfuehren | DSO; DEV | RM | CM; SQA | PSIRT | CI/CD Run Records; Build Evidence |
| Regression Test durchfuehren | V&V | V&V | DEV; SQA; ARCH | RM; PSIRT | Test Results |
| Security Scan und SBOM Update durchfuehren | DSO; DEV | DSO | PSIRT; CM; SQA | RM | Updated SBOM; Scan Reports; Vulnerability Status |
| Artifact Integrity / Signing herstellen | DSO; CM | RM | SQA | GOV; OPS | Artifact Digest / Signature |
| Gate: Patch Release Approval | RM; SQA; DSO | GOV | PSIRT; OPS; CM; DM; V&V | PO; DEV; ARCH | Patch Release Approval; Waiver Record, falls erforderlich |
| Maintenance Release deployen | OPS; RM | RM | CM; DSO; SQA | GOV; PO | Deployment Record |
| Post-Deployment Verification und Operational Traceability aktualisieren | OPS; RM | OPS | PSIRT; DSO; CM; SQA | GOV; DM; PO; DEV | Post-Deployment Verification Record; updated Operational Traceability |
| Kein Patch erforderlich: begruendete Disposition / Monitoring | PSIRT; OPS | RM | DSO; SQA | GOV; PO | Maintenance Decision Record; Monitoring Decision |
| Emergency Patch Path | RM; DEV; V&V | GOV* | PSIRT; DSO; SQA; OPS; CM; ARCH | DM; PO | Emergency Approval; minimal required tests; Waiver/Deviation; post-release Evidence Completion |

*A bezeichnet die Ergebnis-/Artefaktverantwortung fuer die jeweilige Aktivitaet. Die phasenbezogene Gate- und Gesamtverantwortung bleibt zusaetzlich gemaess Kapitel 9 bestehen.*

P9 Change Classification and Lifecycle Treatment

| **Change Type** | **Lifecycle Treatment** | **DevSecOps Evidence** |
| --- | --- | --- |
| Kein Software Change | Operational Record, Monitoring oder begruendete Disposition. | Triage Record, Vulnerability Disposition, Monitoring Decision. |
| Configuration / Parameter Change | Kontrollierter Maintenance Change mit CM Record und Testnachweis. | CM Record, Regression Evidence, Deployment Record. |
| Dependency Update | Maintenance Change mit SBOM Diff, Vulnerability Bewertung und CI/CD Control Evaluation. | updated SBOM, Dependency Scan, Build/Test Logs, Artifact Digest. |
| Code Patch | Proportionaler Re-entry in P3-P7 ab betroffenem Lifecycle-Element. | Impact Assessment, Requirements/Design/Code/Test Delta, Scan und Patch Approval. |
| Emergency Patch | Beschleunigter Pfad mit dokumentierter Risikoentscheidung und nachgelagerter Formalisierung. | Emergency Approval, minimal required tests, Waiver/Deviation, post-release Evidence Completion. |
| Major Upgrade | Neuer oder teilweiser Lifecycle-Durchlauf ab P1/P3. | Planning Update, formal baselines, full CI/CD and release evidence. |

Gate- und Entscheidungsmodell

| Entscheidung | Bedeutung | Folge |
| --- | --- | --- |
| pass | Alle anwendbaren Controls sind erfuellt. | Phase oder Release darf fortgesetzt werden. |
| fail | Mindestens ein blockierender Control ist nicht erfuellt. | Phase oder Release wird blockiert. |
| manual_review | Evidence ist vorhanden, benoetigt aber fachliche Bewertung. | Review durch definierte Rolle oder Governance Board. |
| waiver_required | Control kann nicht erfuellt werden, Abweichung muss entschieden werden. | Waiver mit Risiko, Ablaufdatum und compensating controls erforderlich. |
| not_applicable | Control ist fuer Kontext oder Run nicht anwendbar. | Begruendung wird dokumentiert. |
| **non_formal_ready** | P2 hat ausreichend Draft Lifecycle Data und bekannte Restpunkte fuer den Eintritt in die Formal Development Phase erzeugt. | P3 darf starten; die Artefakte werden formalisiert und unter formale Change-/Configuration-Management-Regeln gestellt. |
| **formal_base_ok** | Eine formale Baseline in P3-P7 ist reviewt, traceable und durch Evidence gegen die Control Baseline abgesichert. | Der Prozess darf im formalen Lifecycle fortgesetzt werden. |
| **maint_triage** | In-Service Trigger wurde bewertet, klassifiziert und einer Maintenance-Entscheidung zugeordnet. | Patch, Update, Waiver, Monitoring oder kein Change wird als naechster Pfad festgelegt. |
| **patch_required** | Impact und Risiko zeigen, dass eine Softwareaenderung erforderlich ist. | Patch Plan und proportionaler Lifecycle Re-entry werden gestartet. |
| **emerg_patch_ok** | Kritikalitaet erfordert beschleunigten Patchpfad. | Minimal erforderliche Evidence, Risikoakzeptanz und nachgelagerte Formalisierung sind verpflichtend. |
| **patch_evid_ok** | Build, Test, Scan, SBOM, Artifact Integrity und Waiver Status sind vollstaendig. | Patch Release Approval darf bewertet werden. |
| **patch_release_ok** | Maintenance Release ist freigegeben. | Deployment in die In-Service Umgebung ist erlaubt. |
| **post_deploy_ok** | Deployment wurde verifiziert und Operational Traceability aktualisiert. | P9 wird geschlossen oder Monitoring wird fortgefuehrt. |

Rollen und Verantwortlichkeiten

Die nachfolgenden Rollen sind funktionale Verantwortlichkeiten innerhalb des Software Life-Cycle Process. Sie beschreiben keine zwingende Organisationsstruktur. Rollen koennen projektspezifisch kombiniert oder delegiert werden, sofern Verantwortlichkeit, Entscheidungsbefugnis, Traceability sowie gegebenenfalls erforderliche Unabhaengigkeit erhalten bleiben. Die konkrete Besetzung wird in P0/P1 festgelegt und unter Konfigurationsmanagement gehalten.

Rollenmodell

| **Rolle** | **Verantwortung und Entscheidungsbefugnis** | **Typische Artefakte / Evidence** |
| --- | --- | --- |
| Software Development Manager / Project Lead | Traegt die end-to-end Verantwortung fuer die korrekte Anwendung des SDLC im Projekt. Stellt Rollenbesetzung, Planung, Gate-Readiness, Ressourcen und Eskalationen sicher und bereitet formale Entscheidungen vor. Er ersetzt keine explizit zugewiesene Approval Authority. | Applicability-/Planning Records, Gate Readiness, Lifecycle Status, Eskalationen, Decision Inputs. |
| Product Owner | Priorisiert Work Items und Product Backlog, klaert fachliche Prioritaeten und bestaetigt fachliche Akzeptanz. Wird bei Scope-, Change- und Release-Auswirkungen auf Produktnutzen und Lieferumfang konsultiert. | Product Backlog, Acceptance Records, Priorisierungs- und Scope-Entscheidungen. |
| System Engineering / Requirements Engineering | Stellt die Schnittstelle zu System Requirements und Vertragsanforderungen sicher, leitet Software Requirements ab bzw. pflegt deren fachliche Konsistenz und unterstuetzt Impact Assessments sowie End-to-End Traceability. | System-/Software Requirements, Traceability Matrix, Requirements Review Records, Impact Analysis. |
| Development Team | Erstellt und aendert Source Code, Unit-/Integrationstests und technische Evidence; behebt Findings und Problem Reports; stellt die technische Umsetzbarkeit innerhalb der definierten Architektur, Standards und Controls sicher. | Commits, Pull Requests, Code Reviews, Test Results, Static Analysis, Build Evidence, Problem Reports. |
| Software Architect | Verantwortet Software Architecture, Designkonsistenz, technische Reviews und Architekturentscheidungen. Bewertet technische Auswirkungen von Changes, Dependencies, Patches und Abweichungen. | Software Architecture, Design Description, Interface Description, Architecture/Design Review Records, ADRs/technical decisions. |
| Test / Verification Lead | Plant und steuert Test- und Verification-Aktivitaeten, stellt geeignete Testfaelle, Testdaten und Testumgebungen sicher und verantwortet die fachliche Vollstaendigkeit der Verification Evidence. | Test Plan, Test Cases/Procedures, Test Environment Description, Dry Run Results, Verification Results. |
| SQA / Quality | Prueft Prozesskonformitaet, Vollstaendigkeit und formale Qualitaet von Review Records, Baselines und Evidence. Verantwortet SQA Transition Records und unterstuetzt bzw. fuehrt Quality-relevante Gate Reviews. | SQA Transition Records, Quality Reviews, Compliance Findings, Gate/Review Records. |
| Security / DevSecOps | Definiert und operationalisiert Security- und DevSecOps-Controls, bewertet Scan- und Pipeline-Ergebnisse, betreut Policy-as-Code und Security Gates und stellt die technische Nachweisbarkeit der Control Baseline sicher. | Control Baseline Mapping, Scan Reports, Pipeline Evidence, Policy-as-Code Results, Security Gate Records. |
| Configuration Manager | Verantwortet CM/SCM Baselines, kontrollierte Versionen, Artifact Identity und Change-/Configuration Records. Stellt sicher, dass freigegebene Lifecycle-Artefakte eindeutig identifizierbar und reproduzierbar referenziert werden koennen. | CM/SCM Baselines, Configuration Records, Artifact/Version Identifiers, SCID, Change Records. |
| Governance Board | Entscheidet ueber Governance-relevante Baseline-Zuordnung, Waiver, Deviations, Risk Acceptance und definierte Freigaben. Kann Entscheidungsbefugnisse fuer Standard- oder Emergency-Pfade formal delegieren. | Baseline Assignment Approval, Waiver/Deviation Decisions, Risk Acceptance, Governance Release Decisions. |
| Service Owner / Operations | Betreibt und deployed freigegebene Software, pflegt Operational Traceability und liefert Runtime Logs, Incidents, Asset Inventory und Betriebsfeedback. Bestaetigt Post-Deployment Verification und Betriebsstatus. | Deployment Records, Runtime Version Records, System Logs, Incident Records, Asset Inventory, Post-Deployment Verification. |
| Product Security / PSIRT | Bewertet CVEs, Advisories und Vulnerability Findings, fuehrt bzw. unterstuetzt Triage und Vulnerability Disposition und priorisiert sicherheitsgetriebenen Patchbedarf. Beratet bei Waiver- und Risk Decisions. | Vulnerability Triage, Vulnerability Disposition, Advisory/CVE Assessment, Security Impact and Patch Priority. |
| Release / Maintenance Manager | Koordiniert Release- und Maintenance-Readiness, Patch Plan, Maintenance Release Approval, Deployment Coordination und Emergency-Patch-Pfad. Stellt sicher, dass nach beschleunigten Pfaden die erforderliche Formalisierung und Evidence Completion erfolgt. | Release/Patch Plan, Release Readiness, Maintenance Decision Record, Release Approval Package, Emergency Path Records. |

RACI Matrix - Phasen- und Entscheidungssicht

Die nachfolgende Matrix ist die zusammenfassende Phasen- und Entscheidungssicht. Die operative, artefaktbezogene RACI-Zuordnung befindet sich direkt bei den Aktivitaeten in Kapitel 7. Dort bezeichnet A die Ergebnis- bzw. Artefaktverantwortung fuer die jeweilige Aktivitaet; fuer Gate- oder Freigabeentscheidungen gilt die explizit ausgewiesene Approval Authority. RACI-Legende: R = Responsible (fuehrt die Aktivitaet aus), A = Accountable (traegt die Ergebnis- und Entscheidungsverantwortung), C = Consulted (wird vor der Entscheidung oder Fertigstellung aktiv eingebunden), I = Informed (wird ueber Ergebnis oder Entscheidung informiert). Pro Aktivitaet ist genau eine Accountable-Rolle vorgesehen. Projektspezifische Anpassungen sind in P0/P1 zu dokumentieren.

Kurzformen in der Matrix: Dev Mgr = Software Development Manager / Project Lead; Req Eng = System Engineering / Requirements Engineering; SW Arch = Software Architect; V&V = Test / Verification Lead; Release Mgr = Release / Maintenance Manager; Ops = Service Owner / Operations.

| Prozess / Entscheidung | A | R | C | I |
| --- | --- | --- | --- | --- |
| P0 Applicability & Baseline Selection | Governance Board | Dev Mgr; DevSecOps | SW Arch; SQA; Req Eng; CM | PO; Dev Team; V&V; Ops; PSIRT; Release Mgr |
| P1 Software Planning | Dev Mgr | Dev Mgr; SQA; CM; DevSecOps | PO; Req Eng; SW Arch; V&V; Ops | Governance Board; Dev Team; PSIRT; Release Mgr |
| P2 Pre-Production Development | Dev Mgr | Dev Team; SW Arch | PO; Req Eng; V&V; SQA; DevSecOps | CM; Governance Board; Ops |
| P2 -> P3 Formalisierungsgate | Dev Mgr | SQA; CM; SW Arch | Req Eng; V&V; DevSecOps; PO; Governance Board | Dev Team; Release Mgr |
| P3 Software Requirements | Dev Mgr | Req Eng | PO; SW Arch; SQA; DevSecOps; CM | Dev Team; V&V; Governance Board |
| P4 Software Design | SW Arch | SW Arch; Dev Team | Req Eng; SQA; DevSecOps | Dev Mgr; PO; CM; V&V |
| P5 Software Coding | Dev Mgr | Dev Team | SW Arch; DevSecOps; SQA; CM | PO; Req Eng; V&V |
| P6 Integration & Test | Dev Mgr | Dev Team; V&V | SW Arch; DevSecOps; SQA; CM | PO; Governance Board; Release Mgr |
| P6a Software Dry Run | V&V | V&V; Dev Team | SW Arch; SQA; DevSecOps | Dev Mgr; PO; CM; Governance Board |
| P7 Formal Verification | V&V | V&V | SQA; DevSecOps; SW Arch; CM; Req Eng | Dev Mgr; PO; Governance Board; Release Mgr |
| P7/P8 Release Approval | Governance Board | Release Mgr; SQA | Dev Mgr; DevSecOps; CM; V&V; SW Arch | PO; Dev Team; Ops; PSIRT |
| P8 Deployment & Operational Traceability | Release Mgr | Ops; Release Mgr | CM; SQA; DevSecOps; Dev Mgr | Governance Board; PO; PSIRT; Dev Team |
| P9 In-Service Triage / Maintenance Decision | Release Mgr | Ops; PSIRT | DevSecOps; SW Arch; SQA; CM; Dev Mgr | PO; Governance Board; Dev Team; V&V |
| P9 Patch / Maintenance Implementation | Release Mgr | Dev Team; SW Arch; V&V; DevSecOps | CM; SQA; PSIRT; Ops; Req Eng | Dev Mgr; PO; Governance Board |
| P9 Patch Release Approval | Governance Board | Release Mgr; SQA; DevSecOps | PSIRT; Ops; CM; Dev Mgr; V&V | PO; Dev Team; SW Arch |
| Emergency Patch Path | Governance Board* | Release Mgr; Dev Team; V&V | PSIRT; DevSecOps; SQA; Ops; CM; SW Arch | Dev Mgr; PO |
| Waiver / Deviation Decision | Governance Board | DevSecOps; SQA; Dev Mgr | SW Arch; PSIRT; CM; Release Mgr; Ops | PO; Dev Team; V&V |
| Post-Deployment Verification / P9 Closure | Ops | Ops; Release Mgr | PSIRT; DevSecOps; CM; SQA | Governance Board; Dev Mgr; PO; Dev Team |

** Bei Emergency Patches kann die Accountable-Rolle nur durch eine formal definierte und dokumentierte Emergency Approval Authority ersetzt werden. Die nachgelagerte Formalisierung und Evidence Completion bleiben verpflichtend.*

Zentrale Traceability-Kette

| Nachweiskette. Der Prozess erzeugt eine durchgehende, auditierbare Kette: Requirement -> Design -> Code -> Build -> Test -> Artifact -> Release -> Deployment -> Operation -> Monitoring/Vulnerability Trigger -> Maintenance Decision -> Patch/Update -> Post-Deployment Verification. |
| --- |

Diese Kette ist der eigentliche Wert der Integration: Der Entwicklungsprozess bleibt fachlich anschlussfaehig an den SDP, waehrend DevSecOps die Nachweise automatisiert, Governance-Entscheidungen wiederholbar macht und In-Service Updates sowie Patches operational rueckverfolgbar haelt.

Document as Code stärkt diese Nachweiskette, indem geeignete Lifecycle-Artefakte versioniert, reviewbar und maschinenlesbar geführt werden. Dadurch bleiben Änderungen, Reviews, Freigaben und Evidence-Beziehungen über den gesamten Lifecycle nachvollziehbar und automatisiert auswertbar.
