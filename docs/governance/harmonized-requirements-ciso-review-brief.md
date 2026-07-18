# CISO Review Brief: Harmonisiertes DevSecOps-Requirements-Modell

## Dokumentstatus

| Merkmal | Wert |
|---|---|
| Zweck | Fachliche Besprechungs- und Entscheidungsvorlage |
| Stand | 18. Juli 2026 |
| Version | 0.1 Review Draft |
| Darstellungsform | Public-neutral |
| Governance-Status | Candidate, nicht normativ |
| Source-ID | `CISO-REQ-SRC-001` |
| Change Request | `GCR-2026-047` |

## 1. Executive Summary

Eine bereitgestellte Excel-Liste mit DevSecOps- und Product-Security-Anforderungen
wurde lokal analysiert und in ein öffentlich neutralisiertes, strukturiertes
Requirements-Modell überführt. Ziel war, die fachlichen Inhalte vergleichbar,
prüfbar und später technisch nutzbar zu machen, ohne die Originaldatei,
Originalformulierungen oder organisationsspezifische Metadaten zu veröffentlichen.

Die Analyse ergab:

| Kennzahl | Ergebnis |
|---|---:|
| Zeilen in der analysierten Excel-Liste | 264 |
| Eindeutige Quellanforderungen | 233 |
| Doppelte Kombinationen aus Quellen- und Anforderungs-ID | 29 |
| Quellanforderungen ohne vorhandene ID | 10 |
| Daraus gebildete harmonisierte Anforderungen | 44 |
| Nicht zugeordnete eindeutige Quellanforderungen | 0 |
| Vorläufige gewichtete Design-Abdeckung | 50,4 % |

Die 44 harmonisierten Anforderungen bilden sieben Themenbereiche ab:

1. Governance und Secure Development Lifecycle
2. Risiko- und Threat-Management
3. Application und Product Security
4. Sichere Entwicklung
5. Software Supply Chain und SBOM
6. Verifikation und Security Testing
7. Betrieb, Release, Monitoring und Außerbetriebnahme

Das Ergebnis ist derzeit bewusst ein **Candidate-Modell**. Es ist eine
Entscheidungsgrundlage, aber noch keine verbindliche Governance-Quelle. Es wurden
keine bestehenden Controls, OPA-Policies, Evidence-Verträge, Workflows oder
veröffentlichten Baselines verändert.

Die wichtigste anstehende Entscheidung ist, ob die Excel-Liste als verwandte
Governance-Quelle bestätigt wird und in welchem Umfang aus ihr später verbindliche
Controls, Nachweisanforderungen oder technische Prüfungen abgeleitet werden dürfen.

## 2. Ausgangslage und Zielsetzung

Die ursprüngliche Excel-Liste fasst Anforderungen aus mehreren Standards und
Anforderungskontexten zusammen. In ihrer ursprünglichen Form ist sie für eine
Governance-as-Code-Nutzung nur eingeschränkt geeignet:

- Anforderungen können inhaltlich mehrfach vorkommen.
- Quell-IDs sind teilweise doppelt oder fehlen.
- Verschiedene Quellen verwenden unterschiedliche Granularitäten und Begriffe.
- Einzelne Zeilen beschreiben ähnliche oder überlappende Kontrollziele.
- Die direkte Veröffentlichung der Arbeitsdatei könnte unerwünschte Inhalte oder
  versteckte Office-Metadaten offenlegen.
- Eine reine Zeilenliste stellt noch keine belastbare Verbindung zu bestehenden
  Controls, Evidences, Policies und Releases her.

Das Vorhaben verfolgt deshalb fünf Ziele:

1. die Excel-Inhalte strukturell erfassen und qualifizieren;
2. gleiche und verwandte Anforderungen zusammenführen;
3. eine stabile, technologieunabhängige Requirements-Ebene schaffen;
4. die vorläufige Abdeckung durch das bestehende Framework sichtbar machen;
5. eine kontrollierte fachliche Entscheidung ermöglichen, bevor normative oder
   technische Änderungen erfolgen.

## 3. Schutz der Originaldatei und Public-Hygiene

Die Original-Excel wurde ausschließlich lokal als Analysequelle verwendet. Sie ist
nicht Bestandteil des öffentlichen Git-Commits und wird durch eine exakte
`.gitignore`-Regel vom Versionsmanagement ausgeschlossen.

Für die öffentlichen Artefakte gelten folgende Schutzmaßnahmen:

- keine Veröffentlichung der Original-Excel;
- keine Übernahme der ursprünglichen Anforderungstexte;
- keine Übernahme von Autoren-, Firmen- oder Dokumenteigenschaften;
- keine Übernahme organisationsspezifischer Labels;
- Verwendung neutraler Quellen-Aliasse und stabiler technischer IDs;
- Veröffentlichung nur paraphrasierter harmonisierter Anforderungen;
- Prüfung aller vorgesehenen Commit-Dateien mit einem Hygiene-Scanner;
- Unterstützung der Prüfung eingebetteter XML-Inhalte in Office-/ZIP-Containern;
- neutrale Formulierung von Branch-, Commit- und Pull-Request-Metadaten.

Der Public-Hygiene-Scan war für alle 35 Dateien der Candidate-Änderung erfolgreich.
Die vertraulichen Suchbegriffe werden dem Scanner nur zur Laufzeit übergeben und
selbst nicht im Repository gespeichert.

## 4. Verarbeitung der Excel-Liste

### 4.1 Technischer Import

Ein reproduzierbares Importskript liest die für die Analyse benötigten sichtbaren
Zellwerte aus dem XLSX-Container. Die Originaldatei wird dabei nicht verändert.

Der Import umfasst:

- Erkennung der relevanten Tabellenzeilen;
- Normalisierung von elf Quellenbezeichnungen auf öffentliche neutrale Aliasse;
- Erhaltung vorhandener Quellen- und Anforderungs-IDs;
- Vergabe neutraler Review-IDs für zehn Einträge ohne vorhandene ID;
- Ermittlung mehrfach vorkommender Einträge;
- Zusammenführung identischer Beschreibungen bei Erhaltung aller Referenzen und
  Vorkommenszahlen.

### 4.2 Deduplizierung

Aus 264 Tabellenzeilen wurden 233 eindeutige Quellanforderungen gebildet. Die
Reduktion entfernt keine fachliche Referenz: Bei zusammengeführten Inhalten bleiben
die zugehörigen Quellen-IDs, Anforderungs-IDs und Vorkommenszahlen erhalten.

Die festgestellten 29 doppelten Kombinationen aus Quellen- und Anforderungs-ID sind
als Datenqualitätsbefund dokumentiert. Sie wurden nicht stillschweigend als
fachlich identisch erklärt. Die zehn Anforderungen ohne ID erhielten neutrale
technische Review-IDs und bleiben für eine fachliche Quellenbereinigung markiert.

### 4.3 Harmonisierung

Die 233 eindeutigen Quellanforderungen wurden auf 44 übergreifende Anforderungen
abgebildet. Eine harmonisierte Anforderung beschreibt ein zusammenhängendes
Kontrollziel, beispielsweise Artifact Integrity, Threat Modeling, Security Update
Management oder Secure Decommissioning.

Jede harmonisierte Anforderung besitzt:

- eine stabile ID, zum Beispiel `HREQ-SC-003`;
- einen Themenbereich;
- einen neutral formulierten Titel;
- eine paraphrasierte Soll-Aussage;
- eine vorläufige Zuordnung zum bestehenden Governance-Bereich;
- einen Coverage-Status;
- eine dokumentierte Lücke, sofern die Abdeckung nicht vollständig ist;
- mindestens eine Referenz auf eine Quellanforderung.

Alle 233 eindeutigen Quellanforderungen sind zugeordnet. Jede Zuordnung ist mit
`human_review_required` gekennzeichnet. Die technische Vollständigkeit des Mappings
ist damit erreicht; seine fachliche Bestätigung ist noch offen.

## 5. Ergebnis: Harmonisiertes Requirements-Modell

### 5.1 Governance und Risiko

Das Modell enthält Anforderungen für:

- einen kontrollierten Secure Development Lifecycle;
- risikobasierte Anwendbarkeit;
- Rollen, Kompetenz und Review-Unabhängigkeit;
- kontrollierte Security-Dokumentation;
- Asset-, Risiko- und Bedrohungsidentifikation;
- Threat Modeling und Risk Treatment;
- Security Architecture Reviews.

Die vorhandene Governance adressiert diese Themen grundsätzlich, jedoch fehlen
teilweise maschinenlesbare Anwendbarkeitsentscheidungen, strukturierte
Risk-Treatment-Nachweise und einheitlich prüfbare Aktualitätsanforderungen.

### 5.2 Application und Product Security

Das Modell behandelt:

- Authentisierung und Autorisierung;
- Session Security;
- Daten- und Kryptographieschutz;
- Input Validation und Business Logic;
- sichere Dateiverarbeitung;
- Logging und Error Handling;
- Secure Defaults und Hardening.

In diesem Bereich liegen mehrere der deutlichsten strukturellen Lücken. Das
bestehende Framework besitzt übergreifende Architektur- und Security-Governance,
aber noch keine vollständige atomare Abdeckung aller anwendungsbezogenen
Security-Anforderungen.

### 5.3 Sichere Entwicklung und Software Supply Chain

Abgedeckt werden unter anderem:

- Source-Control-Integrität;
- Secure Coding und Code Review;
- sichere Entwicklungsumgebungen;
- Supplier und External Component Assurance;
- kontrollierte und reproduzierbare Builds;
- Artifact Identity, Digests und Signaturen;
- Dependency Provenance;
- SBOM-Erstellung, -Inhalt, -Integrität und Lizenzinformationen.

Die stärkste bestehende Abdeckung liegt bei Build-, Artifact- und Supply-Chain-
Grundlagen. Erweiterungsbedarf besteht insbesondere bei detaillierten SBOM-Feldern,
Lizenz-Compliance, Supplier Assurance und der Überprüfung von Schlüssel- und
Signaturprozessen.

### 5.4 Verifikation und Betrieb

Das Modell umfasst:

- Teststrategie und Akzeptanzkriterien;
- funktionale, nichtfunktionale und Regressionstests;
- Security Requirements Verification;
- Vulnerability und Penetration Testing;
- unabhängige und geschützte Testdurchführung;
- Security Release Gates;
- Vulnerability Triage und Remediation;
- Security Update Management;
- Monitoring und Alerting;
- Deployment- und Konfigurationsverifikation;
- Secure Operations Guidance;
- sichere Außerbetriebnahme;
- Product Security Response und regelmäßige Health Reviews.

Die bestehende Governance deckt Vulnerability Testing und Release Gates gut ab.
Größere Lücken bestehen beim vollständigen Update-Lifecycle, bei verbindlichen
Remediation-Zeiten, bei unabhängigen Tests und bei der sicheren Außerbetriebnahme.

## 6. Vorläufige Coverage-Bewertung

### 6.1 Ergebnisse auf Ebene der harmonisierten Anforderungen

| Coverage-Status | Anzahl | Anteil |
|---|---:|---:|
| `covered` | 9 | 20,5 % |
| `partial` | 26 | 59,1 % |
| `gap` | 9 | 20,5 % |
| **Gesamt** | **44** | **100 %** |

### 6.2 Ergebnisse auf Ebene der eindeutigen Quellanforderungen

| Zuordnung | Anzahl | Anteil |
|---|---:|---:|
| Mapping auf `covered` | 45 | 19,3 % |
| Mapping auf `partial` | 145 | 62,2 % |
| Mapping auf `gap` | 43 | 18,5 % |
| **Gesamt** | **233** | **100 %** |

### 6.3 Berechnung der gewichteten Design-Abdeckung

Für die vorläufige Kennzahl wird folgende einfache Gewichtung verwendet:

```text
covered = 1,0
partial = 0,5
gap     = 0,0
```

Auf Basis der Zuordnung der 233 eindeutigen Quellanforderungen ergibt sich eine
gewichtete Design-Abdeckung von **50,4 %**.

Diese Zahl bedeutet nicht, dass das Unternehmen zu 50,4 % compliant ist. Sie zeigt
lediglich, in welchem Umfang das bestehende Repository nach aktueller Modellanalyse
bereits passende Governance-Strukturen enthält.

Insbesondere sind noch nicht vollständig bewertet:

- tatsächliche Umsetzung in allen Consumer-Repositories;
- Qualität, Aktualität und Integrität der operativen Evidences;
- Wirksamkeit der Controls;
- organisationsweite Anwendbarkeit und Ausnahmen;
- fachliche Richtigkeit jeder einzelnen Zuordnung;
- Auditierbarkeit gegenüber den jeweiligen Originalstandards;
- Lizenz- und Publikationsrechte für weitergehende Standardinhalte.

Die 50,4 % dürfen daher nur als **vorläufige Design-Coverage** und nicht als
offizielle Compliance-Kennzahl verwendet werden.

### 6.4 Vorgeschlagene Zuordnung zu L1, L2, L3 und GOV

Alle 44 harmonisierten Anforderungen wurden zusätzlich einem vorgeschlagenen
Mindest-Maturity-Level zugeordnet. Die Zuordnung ist kumulativ:

- Eine L1-Anforderung bleibt auf L2 und L3 aktiv.
- Eine L2-Anforderung bleibt auf L3 aktiv.
- Eine L3-Anforderung beschreibt eine High-Assurance-Mindestanforderung.
- GOV ist ein separates, levelübergreifendes Overlay für Governance-Pflichten.

| Level | Bedeutung | Neu auf diesem Level | Kumulativ aktiv |
|---|---|---:|---:|
| `L1` | Foundational – wiederholbare Mindestpraktiken und Evidences | 22 | 22 |
| `L2` | Managed – zentrale Fähigkeiten, standardisierte Verifikation, Monitoring und Gates | 17 | 39 |
| `L3` | High Assurance – Isolation, Provenance und kontinuierlich prüfbare Evidences | 1 | 40 |
| `GOV` | Governance Overlay – Applicability, Rollen, Reviews und Lifecycle-Entscheidungen | 4 | 4 |

Die vier GOV-Anforderungen betreffen Secure Development Lifecycle,
risikobasierte Anwendbarkeit, Rollen und Kompetenz sowie kontrollierte
Security-Dokumentation.

Die Verteilung bedeutet nicht, dass L3 nur eine Anforderung enthält. Auf L3
gelten kumulativ 40 fachliche Anforderungen. Lediglich eine Anforderung –
reproduzierbare und isolierte Builds – beginnt ausschließlich auf L3. Weitere
Anforderungen erhalten auf L3 zusätzliche High-Assurance-Ausprägungen, die bei
einer späteren Control-Ableitung konkretisiert werden müssen.

Die Maturity-Zuordnung ersetzt nicht die fachliche Anwendbarkeit. Beispielsweise
gilt Session Security nur für Software mit Session-Funktion, File Handling nur
für dateiverarbeitende Software und Penetration Testing risikobasiert für
exponierte oder hochkritische Produkte.

Die vorgeschlagenen Routing-Lanes verteilen sich wie folgt:

| Review- und Ableitungsbereich | Anforderungen |
|---|---:|
| DevSecOps Baseline | 15 |
| Product Security | 11 |
| Architecture | 5 |
| Governance | 4 |
| Operations | 4 |
| Evidence | 3 |
| Platform | 2 |

Die vollständige Zuordnung mit Begründung, bestehender Control-Referenz,
Coverage-Status, Applicability und Review-Status steht im Report
`generated/reports/harmonized-requirements-maturity.md`. Alle 44 Zuordnungen
sind `human_review_required`.

## 7. Bestehende Stärken und wesentliche Lücken

### 7.1 Aktuelle Stärken

Das bestehende Framework besitzt bereits eine vergleichsweise starke Grundlage in
folgenden Bereichen:

- Source-Control- und Artifact-Integrität;
- kontrollierte und reproduzierbare Builds;
- Artifact-Digests und Signaturen;
- vertrauenswürdige Dependency-Quellen und Provenance;
- SBOM-Erstellung;
- Vulnerability Testing;
- Security Release Gates;
- Traceability, Evidence Intake und Governance Reporting.

### 7.2 Prioritäre strukturelle Lücken

Die neun als `gap` bewerteten harmonisierten Anforderungen sind:

| ID | Anforderung | Wesentliche Lücke |
|---|---|---|
| `HREQ-APP-002` | Session Security | Keine explizite atomare Anforderung |
| `HREQ-APP-004` | Input Validation und Business Logic | Keine vollständige Requirement-Abdeckung |
| `HREQ-APP-005` | Secure File Handling | Kein eigenständiges Kontrollziel |
| `HREQ-SC-009` | SBOM License Metadata | Nicht Teil des aktuellen Evidence-Vertrags |
| `HREQ-SC-010` | Component License Compliance | Kein Control und kein Evidence-Typ |
| `HREQ-TEST-006` | Independent and Protected Testing | Keine einheitliche Anforderung für Unabhängigkeit und Testdaten |
| `HREQ-OPS-003` | Security Update Management | Kein vollständiger Update-Lifecycle |
| `HREQ-OPS-007` | Secure Decommissioning and Disposal | Keine End-to-End-Anforderung |
| `HREQ-OPS-008` | Product Security Response and Health Review | Noch keine vollständige gesteuerte Capability |

Zusätzlich bestehen 26 teilweise abgedeckte Anforderungen. Dort ist häufig bereits
eine Governance-Grundlage vorhanden, aber Detailtiefe, maschinenlesbare Evidences,
Verantwortlichkeiten, Zeitvorgaben oder technische Prüfbarkeit fehlen.

## 8. Governance-Status und Entscheidungsgrenzen

Das Modell ist mit folgenden Grenzen angelegt:

```text
status: candidate
normative: false
enforcement: none
derivation_policy: review_only
```

Der Candidate-Status erlaubt:

- fachliche Diskussion und Korrektur;
- Review der Zuordnungen;
- Priorisierung von Lücken;
- Vorbereitung einer Governance-Entscheidung;
- Planung späterer Controls und Evidences.

Der Candidate-Status erlaubt noch nicht:

- Änderungen an veröffentlichten DevSecOps-Baselines;
- neue oder geänderte OPA-Enforcement-Regeln;
- verpflichtende Evidence-Verträge für Consumer-Repositories;
- neue Blocking Gates;
- offizielle Compliance-Aussagen;
- automatische Ableitung normativer Controls;
- Ablösung oder Superseding bestehender Governance-Quellen.

Die Quelle ist momentan als **related and overlapping candidate** klassifiziert.
Sie wird damit weder als Duplikat noch als Ersatz einer bestehenden Quelle
behandelt. Diese Einordnung verhindert eine stille Veränderung der bisherigen
Source-of-Truth-Struktur.

## 9. Erforderliche Entscheidungen

### 9.1 Entscheidung zur Quelle

Für den Source-Document-Intake stehen drei sachgerechte Optionen zur Verfügung:

| Option | Bedeutung | Konsequenz |
|---|---|---|
| `related_source_confirmed` | Die Liste wird als verwandte Quelle mit definiertem Geltungsbereich anerkannt. | Eine nachfolgende, separat genehmigte Ableitung kann vorbereitet werden. |
| `keep_related_candidate` | Die Liste bleibt sichtbar, aber noch nicht freigegeben. | Weitere Analyse; keine normative oder technische Ableitung. |
| `not_relevant_retire` | Die Liste wird nicht als Governance-Quelle verwendet. | Review-Historie bleibt erhalten; keine künftige Ableitung. |

### 9.2 Entscheidungen zum Geltungsbereich

Vor einer Freigabe sollten mindestens folgende Fragen beantwortet werden:

1. Für welche Produkte, Schutzbedarfe und Entwicklungsmodelle soll das Modell
   gelten?
2. Welche Anforderungen sind organisationsweit verpflichtend und welche
   risikobasiert anwendbar?
3. Welche bestehenden Governance-Quellen bleiben vorrangig?
4. Welche Anforderungen gehören in die DevSecOps Control Baseline, welche in
   Architecture Governance und welche in Product-Security-Vorgaben?
5. Welche Nachweise müssen Consumer-Repositories liefern?
6. Welche Anforderungen sollen zunächst report-only und welche später blocking
   werden?
7. Welche Ausnahmen, Waiver und Risikoakzeptanzen sind zulässig?
8. Welche Anforderungen benötigen Legal- oder License-Compliance-Review?
9. Ist für die spätere Einführung ein neuer Baseline-Release erforderlich?

### 9.3 Benötigte Review-Rollen

| Rolle | Entscheidungsbeitrag |
|---|---|
| CISO | Authority, Schutzziel, Enterprise-Anwendbarkeit und Priorität |
| Governance Owner | Quellenstatus, Geltungsbereich und Freigabeweg |
| DevSecOps Baseline Owner | Control-Mapping und Baseline-Änderungen |
| Enterprise Architect | Architecture- und Product-Security-Zuordnung |
| Platform Owner | Umsetzbarkeit durch Plattform-Capabilities |
| Legal oder License Compliance | Publikations- und Lizenzgrenzen |
| Release Manager | Release-, Migrations- und Rollout-Entscheidung |

## 10. Empfohlene Entscheidung

Als risikoarmer nächster Schritt wird empfohlen:

1. die Quelle grundsätzlich als `related_source_confirmed` anzuerkennen;
2. den Candidate-Status des harmonisierten Modells vorerst beizubehalten;
3. noch keine Runtime-Ableitung und kein Blocking Enforcement zu erlauben;
4. die 44 harmonisierten Anforderungen und 233 Zuordnungen fachlich zu reviewen;
5. die vorgeschlagenen L1-L3-/GOV-Mindestlevel zu bestätigen oder anzupassen;
6. die neun vollständigen Gaps und die kritischsten Partial Gaps zu priorisieren;
7. anschließend einen separaten Change Request für die erste genehmigte
   Control-/Evidence-Tranche zu erstellen.

Diese Variante erkennt den fachlichen Wert der Liste an, ohne ungeprüfte Inhalte
direkt in operative Governance oder veröffentlichte Baselines zu übernehmen.

## 11. Vorgeschlagener Umsetzungsplan nach der Entscheidung

### Phase 1: Fachliche Validierung

- Authority und Anwendungsbereich bestätigen;
- Quellenbezeichnungen und IDs fachlich prüfen;
- zehn fehlende IDs mit der Quellliste klären;
- 29 doppelte Quellen-ID-Kombinationen bereinigen oder begründen;
- alle 233 Mappings stichprobenbasiert und risikoorientiert reviewen;
- 44 harmonisierte Formulierungen bestätigen oder korrigieren.
- 44 vorgeschlagene Mindestlevel und sieben Routing-Lanes bestätigen oder
  korrigieren.

**Ergebnis:** fachlich bestätigtes Candidate-Modell mit dokumentierten
Review-Entscheidungen.

### Phase 2: Gap-Priorisierung

- Gaps nach Risiko, regulatorischer Relevanz und Umsetzungsaufwand bewerten;
- Product-Security-, Supply-Chain-, Testing- und Operations-Gaps routen;
- Must-have-, Should-have- und Later-Tranchen definieren;
- betroffene Consumer-Repositories und Plattformen identifizieren.

**Ergebnis:** genehmigte Roadmap mit Verantwortlichen und Zielterminen.

### Phase 3: Normatives Control Design

- priorisierte Requirements auf bestehende Controls abbilden;
- neue Controls nur dort definieren, wo echte Lücken bestehen;
- Applicability, Ausnahmen und Waiver festlegen;
- Evidence-Typen und Akzeptanzkriterien spezifizieren;
- Architekturmarker und Plattformfähigkeiten zuordnen.

**Ergebnis:** reviewfähiger Baseline-Änderungsvorschlag ohne voreilige
Enforcement-Änderung.

### Phase 4: Report-only Pilot

- Schemas und Evidence Collectors ergänzen;
- Policies zunächst report-only implementieren;
- ausgewählte Consumer-Repositories pilotieren;
- False Positives, Evidenzqualität und Betriebsaufwand messen;
- Viewer und Management Reporting aktualisieren.

**Ergebnis:** operative Wirksamkeitsdaten für die Freigabeentscheidung.

### Phase 5: Release und schrittweise Durchsetzung

- Release-Impact bewerten;
- neue Baseline oder Release Candidate erstellen;
- Migration und Kommunikation vorbereiten;
- nur ausreichend stabile Controls gezielt auf blocking umstellen;
- Ausnahmen und Risikoakzeptanzen revisionssicher dokumentieren.

**Ergebnis:** kontrollierte, nachvollziehbare Einführung in die Runtime Governance.

## 12. Vorschlag für die CISO-Besprechung

Für einen fokussierten Termin wird folgende Agenda empfohlen:

1. **Ziel und Herkunft** – Warum wurde die Liste harmonisiert?
2. **Informationsschutz** – Welche Inhalte wurden bewusst nicht veröffentlicht?
3. **Modellergebnis** – Was bedeuten 44 harmonisierte Anforderungen?
4. **Coverage** – Warum sind 50,4 % keine offizielle Compliance-Aussage?
5. **Top Gaps** – Welche neun Themen sind aktuell strukturell nicht abgedeckt?
6. **Maturity-Modell** – Sind 22 L1, 17 L2, eine L3 und vier GOV-Einstufungen sachgerecht?
7. **Quellenentscheidung** – Related Source bestätigen oder Candidate belassen?
8. **Geltungsbereich** – Für welche Produkte und Risikoklassen soll das Modell gelten?
9. **Mandat für Phase 1** – Wer reviewed Mappings, Level, Gaps und Publikationsgrenzen?
10. **Nächster Entscheidungspunkt** – Wann wird über normative Ableitung entschieden?

## 13. Entscheidungsvorlage

Die folgende Vorlage kann im Termin ausgefüllt und anschließend in den Governance
Change Request übernommen werden:

```text
Review decision:
  [ ] related_source_confirmed
  [ ] keep_related_candidate
  [ ] not_relevant_retire

Decision owner:
Decision date:

Enterprise applicability:
Applicable products / risk classes:
Excluded scope:

Proposed maturity assignment:
  [ ] confirm 22 L1 / 17 L2 / 1 L3 / 4 GOV
  [ ] confirm with recorded adjustments
  [ ] return for further analysis

GOV overlay applies across adopted levels:
  [ ] yes
  [ ] no

Derived artifacts currently allowed:
  [ ] no
  [ ] review artifacts only
  [ ] separately approved control/evidence design

Runtime governance change currently allowed:
  [ ] no
  [ ] report-only pilot after separate approval
  [ ] blocking only after release decision

Priority gaps:
Required reviewers:
Target date for mapping review:
Release decision:
Additional conditions:
```

## 14. Technische und Governance-Artefakte

Die Analyse ist im Repository über folgende Artefakte nachvollziehbar:

| Artefakt | Zweck |
|---|---|
| `model/requirements/harmonized-devsecops-requirements.yaml` | 44 harmonisierte Candidate-Anforderungen |
| `model/traceability/standards-to-harmonized-requirements.yaml` | Zuordnung aller 233 eindeutigen Quellanforderungen |
| `generated/reports/harmonized-requirements-coverage.md` | Lesbarer Coverage-Bericht |
| `generated/reports/harmonized-requirements-coverage.json` | Maschinenlesbarer Coverage-Bericht |
| `model/traceability/harmonized-requirements-to-maturity-levels.yaml` | Reviewpflichtige Zuordnung aller 44 Anforderungen zu L1-L3/GOV |
| `generated/reports/harmonized-requirements-maturity.md` | Vollständiger lesbarer Maturity-Report mit Begründungen |
| `generated/reports/harmonized-requirements-maturity.json` | Maschinenlesbarer Maturity-Report |
| `docs/governance/source-documents/CISO-REQ-SRC-001.public.md` | Öffentliche neutrale Quellenbeschreibung |
| `docs/governance/change-requests/GCR-2026-047-harmonized-requirements-candidate.md` | Governance Change Request |
| `scripts/import_harmonized_requirements_workbook.py` | Reproduzierbarer lokaler Import |
| `scripts/check_public_artifact_hygiene.py` | Prüfung öffentlicher Artefakte auf vertrauliche Begriffe und Metadaten |

## 15. Validierungsnachweis

Vor Veröffentlichung des Candidate-Modells wurden folgende Prüfungen erfolgreich
durchgeführt:

- Runtime-Governance-Validierung;
- Repository-Governance-Validierung;
- Schema- und Mapping-Integritätsprüfung;
- vollständige Unit-Test-Suite mit 194 erfolgreichen Tests;
- zusätzliche Candidate- und Intake-Tests;
- strikter MkDocs-Dokumentations-Build;
- Public-Hygiene-Scan über alle 35 Änderungsdateien;
- Git-Diff- und Commit-Scope-Prüfung;
- zentraler Governance-CI-Lauf.

## 16. Schlussfolgerung

Mit dem Candidate-Modell liegt erstmals eine konsolidierte und technisch
verarbeitbare Sicht auf die Excel-Anforderungen vor. Das Modell macht bestehende
Stärken, partielle Abdeckung und strukturelle Lücken transparent, ohne vor einer
menschlichen Entscheidung normative oder operative Änderungen auszulösen.

Der aktuelle Stand ist geeignet, um die fachliche Diskussion mit CISO, Governance,
Architektur, Plattform und DevSecOps zu führen. Für eine offizielle Aufnahme sind
als nächste Schritte die Quellenentscheidung, die Bestätigung des Geltungsbereichs,
der fachliche Mapping-Review und eine priorisierte Ableitungsentscheidung
erforderlich.
