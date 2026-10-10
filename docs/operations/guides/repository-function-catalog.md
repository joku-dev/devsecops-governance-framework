# Detaillierter Funktionskatalog des Governance-Repositories

## Dokumentzweck und Geltungsbereich

Dieser Katalog beschreibt die fachlichen und betrieblichen Funktionen von
`joku-dev/devsecops-governance-framework`. Er erklärt, welche Aufgaben das
Repository übernimmt, wie Daten verarbeitet werden und welche Ergebnisse
entstehen. Die Gliederung umfasst 22 Funktionsbereiche einschließlich des GitHub-Lifecycle-Piloten und des Dokumentationsabgleichs nach Implementierungs-Merges.
Interne Hilfsfunktionen werden ihrem jeweiligen Funktionsbereich zugeordnet.
Die [technische Funktionsliste](repository-technical-function-inventory.md) erfasst
zusätzlich alle Skripte, Bibliotheksmodule, Workflows und OPA-Module des Quellstands.

| Merkmal | Wert |
| --- | --- |
| Dokumentationsabgleich | 3. Oktober 2026; gezielter Status-/Inventarabgleich, keine neue fachliche Abnahme |
| Betrachteter Quellstand | `46b33429a6f271273e33508f26275ed8ba7f1f2c`; ursprünglicher Katalog vom 19. September bleibt Grundlage |
| Zielgruppe | Geschäftsführung, Governance-Verantwortliche, Architektur, Security, Plattformbetrieb und Anwendungsteams |
| Dokumenttyp | Erläuternder Funktionskatalog |
| Änderungsnachweis | Ursprung: [GCR-2026-056](../../governance/change-requests/GCR-2026-056-detailed-function-catalog.md); Aktualisierungen: [GCR-2026-058](../../governance/change-requests/GCR-2026-058-current-documentation-refresh.md), [GCR-2026-078](../../governance/change-requests/GCR-2026-078-documentation-and-function-audit.md), [GCR-2026-093](../../governance/change-requests/GCR-2026-093-current-documentation-capabilities-refresh.md), [GCR-2026-101](../../governance/change-requests/GCR-2026-101-consumer-scale-capacity-assessment.md) |

Der Katalog beschreibt vorhandene Fähigkeiten zum genannten Quellstand. Er
bestätigt keine aktuelle Betriebsbereitschaft einer Anwendung und erzeugt keine
neue fachliche Vorgabe. Genehmigte Quellen, Modelle, Schemas und veröffentlichte
Baselines bleiben für ihre jeweiligen Bereiche maßgeblich.

## Ergänzungen nach dem dokumentierten 3.-Oktober-Quellstand

<!-- DOCS_REFRESH_CATALOG:start -->
### PR #272: docs: PRA-Review-Empfehlung dokumentieren (`ee20f518dc03`)

- docs: PRA-Review-Empfehlung dokumentieren

Die fachliche Zuordnung und Auswirkungen auf bestehende Funktionsbereiche sind vor dem Merge dieses Dokumentations-PRs redaktionell zu prüfen.
<!-- DOCS_REFRESH_CATALOG:end -->

Seit der Beobachtung `46b33429` wurden PR #200 und PR #178 gemergt. Der Viewer
zeigt nun einen validierten, lesenden Lifecycle-Nächste-Schritte-Bereich mit
Quellnachweisen. Der Repository-SBOM-Export erzeugt ein commitgebundenes SPDX-
Artefakt aus dem GitHub-Dependency-Graph und verändert weder Prüf-Gates noch
Governance-Ergebnisse. Diese nachträglichen Funktionen sind keine Erweiterung
der persönlichen Betriebsabnahme oder Produktionsfreigabe. Die drei neuen
Python-Dateien sind in der [technischen Funktionsliste](repository-technical-function-inventory.md)
ausgewiesen; der dortige Zähler für den historischen Stand bleibt nachvollziehbar.

### Bedeutung der Einordnung

| Einordnung | Bedeutung |
| --- | --- |
| Implementiert | Ausführbarer Code oder ein nutzbarer Workflow ist vorhanden. Konfiguration und geeignete Eingaben bleiben erforderlich. |
| Modelliert | Strukturierte Anforderungen, Zuordnungen oder Zustände sind vorhanden. Daraus folgt keine vollständige technische Durchsetzung. |
| Report-only | Die Funktion erzeugt Befunde oder Entscheidungshilfen, ohne dadurch die fachliche Lieferung automatisch zu sperren. Technische Fehler können weiterhin zum Abbruch führen. |
| Pilot | Ein begrenzter Mechanismus ist implementiert und demonstrierbar. Allgemeine produktive Nutzung ist damit nicht zugesichert. |
| Vorlage oder Verfahren | Das Repository liefert eine Integrationsvorlage oder Arbeitsanleitung. Ausführung und Erprobung liegen beim jeweiligen Betreiber. |

## Überblick über den Datenfluss

1. Fachlich Verantwortliche registrieren Quellen und entscheiden über deren Verwendung.
2. Modelle verbinden Anforderungen mit Kontrollen, Architekturmerkmalen und Nachweisen.
3. Veröffentlichte Baselines legen einen identifizierbaren Prüfstand fest.
4. Anwendungsteams erzeugen Nachweise und führen die Governance-Prüfungen aus.
5. Der zentrale Intake übernimmt Ergebnisse in normalisierte Datensätze.
6. Ein überprüfter PR bringt diese Datensätze und ihre Projektionen nach `main`.
7. Berichte und Viewer unterstützen die Bewertung und Bearbeitung offener Punkte.
8. Der abgegrenzte Lifecycle-Pilot verbindet akzeptierte Beobachtungen mit persönlich freigegebenen Maßnahmen, Fortschritt, Abschluss und Widerruf.

Die technische Umsetzung verbindet Git, YAML- und JSON-Modelle, Python-Skripte,
OPA/Rego, GitHub Actions und einen statischen Viewer. Eine dauerhaft laufende
Governance-API oder zentrale Datenbank gehört nicht zur betrachteten Architektur.

## 1. Governance-Quellen verwalten

**Zweck:** Die Herkunft und der Lebenszyklus fachlicher Vorgaben sollen
nachvollziehbar bleiben. Dazu gehören Policies, Directives, Standards und
Architekturquellen.

**Eingaben:** Ein Quelldokument, seine Identität, Version, Herkunft, fachliche
Zuständigkeit und gegebenenfalls eine vermutete Beziehung zu einer älteren Quelle.

**Ablauf:** Das Quellenregister erfasst diese Angaben und den Bearbeitungsstatus.
Ein möglicher Ersatz oder eine Dublette kann zunächst als `candidate` registriert
werden. Nach menschlicher Entscheidung lässt sich die Quelle in den vorgesehenen
weiteren Lebenszyklus überführen. Ersetzte oder stillgelegte Quellen bleiben mit
ihren Beziehungen erhalten.

**Ergebnisse:** Ein strukturiertes Quellenregister und eine überprüfbare
Quellgeschichte. Validatoren prüfen unter anderem registrierte Pfade und
notwendige Herkunftsverknüpfungen.

**Implementierungsstellen:** `model/documents/source-document-register.yaml`,
`docs/governance/source-documents/`, `scripts/validate_governance_repo.py`.

**Einordnung und Grenzen:** Register und Validierung sind implementiert. Ein
Statuswechsel ist eine fachliche Entscheidung. Aus einem ungeprüften Kandidaten
dürfen keine aktiven Kontrollen oder Baselines abgeleitet werden. Die früheren
`*.public.md`-Platzhalter wurden entfernt; die getrackten
`*.requirements.md`-Dateien sind die bestätigten, sanitisierten Anforderungen,
nicht die Originalvolltexte. Fünf neue Intake-Dokumente bleiben `candidate`, bis
ihre dokumentierten offenen Entscheidungen abgeschlossen sind.

## 2. Änderungen an Vorgaben vorbereiten

**Zweck:** Vor einer Umsetzung klären, welche Modelle, Regeln, Nachweisverträge und
Veröffentlichungen durch eine Governance-Änderung betroffen sein könnten.

**Eingaben:** Quellenregister, vorhandene Ableitungen, neue oder geänderte
Dokumente und ein Governance Change Request.

**Ablauf:** Generatoren erstellen einen Änderungsfolgebericht, den Intake-Status
und menschlich lesbare Review-Briefe. Der Anforderungsvergleich untersucht
normativ wirkende Aussagen auf Ergänzungen, Änderungen, Entfernungen und
Übereinstimmungen. Für mögliche Architektur-Ablösungen gibt es eine zusätzliche
Bewertung. Der Change Request hält Anlass, Entscheidung und Umsetzungsumfang fest.

**Ergebnisse:** Review-Unterlagen, Hinweise auf betroffene Artefakte und ein
protokollierter Änderungsweg.

**Implementierungsstellen:** `scripts/generate_governance_change_impact_report.py`,
`scripts/generate_source_document_intake_status.py`,
`scripts/generate_source_document_intake_review_briefs.py`,
`scripts/generate_source_document_requirement_delta.py`,
`scripts/generate_architecture_source_replacement_assessment.py`.

**Einordnung und Grenzen:** Die Berichtserstellung ist implementiert und dient
der Entscheidungsvorbereitung. Der Impact-Bericht nutzt Register und
Herkunftsbeziehungen. Er beweist keine vollständige semantische Interpretation
aller fachlichen Änderungen. Die Berichte genehmigen oder ersetzen keine Quelle.

## 3. Herkunft und Zusammenhänge nachweisen

**Zweck:** Eine implementierte Kontrolle oder ein Artefakt soll auf seine
fachliche Herkunft zurückgeführt werden können.

**Eingaben:** Quellenregister, Verknüpfungen zwischen Dokumenten und Artefakten,
Kontrollmodelle sowie Architektur- und Governance-Zuordnungen.

**Ablauf:** Generatoren verfolgen die hinterlegten Beziehungen und erstellen
Source-Lineage-Berichte, Dokument-Kontroll-Matrizen und CSV-Exporte. Die
Repository-Validierung erkennt unter anderem Verweise auf fehlende abgeleitete
Dateien.

**Ergebnisse:** Nachvollziehbare Verknüpfungen zwischen Quellen, Anforderungen,
Modellen, Regeln und weiteren Artefakten. Diese unterstützen Audits,
Änderungsanalysen und die Erklärung einzelner Prüfungen.

**Implementierungsstellen:** `scripts/generate_source_lineage_report.py`,
`scripts/generate_document_control_matrix.py`,
`scripts/generate_traceability_csv.py`,
`scripts/generate_governance_traceability_csv.py`,
`scripts/generate_architecture_traceability_csv.py`, `model/traceability/`.

**Einordnung und Grenzen:** Implementiert. Eine vorhandene Verknüpfung belegt,
dass eine Beziehung dokumentiert wurde. Ihre fachliche Richtigkeit und
Vollständigkeit benötigen weiterhin Review.

## 4. DevSecOps-Kontrollen modellieren

**Zweck:** Fachliche Anforderungen in einer einheitlichen Struktur verwalten und
mit Nachweisen, Plattformfähigkeiten und Prüfverfahren verbinden.

**Eingaben:** Akzeptierte Governance-Anforderungen und Plattformmodelle.

**Ablauf:** Die Kataloge für L1, L2, L3 und Governance beschreiben Kontroll-ID,
Ziel, Anforderung, Plattformlevel, Nachweise und Prüfung. Soweit vorgesehen,
verweisen sie auf ausführbare Policies und Zuständigkeiten für Ausnahmen. Die
Coverage-Zuordnung dokumentiert die vorhandene technische Prüfunterstützung.

**Ergebnisse:** Maschinenlesbare Kontrollkataloge und eine nachvollziehbare
Abgrenzung automatischer, hybrider und manueller Prüfanteile.

**Implementierungsstellen:** `model/controls/dscb-l1.yaml`,
`model/controls/dscb-l2.yaml`, `model/controls/dscb-l3.yaml`,
`model/controls/dscb-gov.yaml`, `model/controls/control-coverage.yaml`,
`model/platform/`, `model/evidence/`.

**Einordnung und Grenzen:** Die Kataloge sind modelliert. Ihre Existenz bedeutet
nicht, dass jede Kontrolle vollständig automatisiert, veröffentlicht oder in
jeder Anwendung aktiv ist. Die verwendete Baseline bestimmt den konkreten Umfang.

## 5. DevSecOps-Kontrollen auswerten

Ergänzend erhebt `ha-CPsWMS` [gemessene L1-Nachweise](../evidence/l1-measured-evidence-ha-cpswms.md)
mit Anwendungstests, echter HTTP-/Neo4j-Integration, Image-SBOMs und Scans.
Die Abdeckungsmatrix aller 16 Kontrollen unterscheidet gemessene Nachweise,
Teilabdeckung, Befunde und Lücken. Sie ersetzt keinen freigegebenen
Compliance-Bericht und erteilt keine Deployment-Freigabe.

**Zweck:** Aus strukturierten Anwendungsnachweisen verständliche Ergebnisse je
Kontrolle und für den gesamten betrachteten Lauf erzeugen.

**Eingaben:** Governance-Run-Input, Kontrollmodelle, Plattformkontext und
Ergebnisse der zugehörigen Policies.

**Ablauf:** Die Auswertungslogik berücksichtigt Kontroll-ID, benötigte Angaben
und den Kontext des Laufs. Automatisierbare Bedingungen werden geprüft. Bei
manuellen oder hybriden Anforderungen bleibt die notwendige fachliche Prüfung
sichtbar. Berichtsgeneratoren fassen Entscheidungen und Erläuterungen zusammen.

**Ergebnisse:** Kontrollauswertungen, DevSecOps-Berichte und ein strukturiertes
Governance-Compliance-Ergebnis für weitere Verarbeitung.

**Implementierungsstellen:** `scripts/control_evaluation.py`,
`scripts/generate_control_evaluation_report.py`,
`scripts/generate_devsecops_governance_report.py`,
`scripts/generate_governance_compliance_result.py`,
`scripts/generate_platform_context.py`.

**Einordnung und Grenzen:** Implementiert. Die Auswertung beurteilt die
verfügbaren Angaben. Ein bestandener Kontrollbericht beweist weder die
Vollständigkeit der Nachweise noch die allgemeine Sicherheit der Anwendung.

## 6. OPA-Prüfregeln ausführen

**Zweck:** Objektiv prüfbare Bedingungen wiederholbar als Policy-as-Code
bewerten. OPA steht für Open Policy Agent; Rego ist die hier verwendete
Regelsprache.

**Eingaben:** Ein zur jeweiligen Regel passendes JSON-Objekt mit Anwendungs-,
Artefakt-, Pipeline- oder Governance-Angaben.

**Ablauf:** OPA wertet die Regeln gegen die Eingaben aus. Aufrufende Skripte und
Workflows verarbeiten die Ergebnisse weiter. Ob ein Befund einen Workflow
scheitern lässt, hängt zusätzlich vom gewählten Ausführungsmodus ab.

| Regeldatei unter `policies/opa/` | Prüfgebiet |
| --- | --- |
| `branch_protection.rego` | Schutz des Quellcodes über Branch-Regeln |
| `sbom_required.rego` | Vorhandensein und Artefaktzuordnung einer SBOM |
| `vulnerability_gate.rego` | Schwachstellenbedingungen und konfigurierte Schwellen |
| `artifact_integrity.rego` | Angaben zur Integrität eines Artefakts |
| `dependency_source_control.rego` | Zulässige Quellen für Abhängigkeiten |
| `iac_required.rego` | Nachweise zu Infrastructure as Code |
| `access_control.rego` | Strukturierte Angaben zum Zugriffsschutz |
| `artifact_signing.rego` | Angaben zu Artefaktsignaturen |
| `pipeline_security_gates.rego` | Sicherheitsgates in der Pipeline |
| `waiver_validity.rego` | Gültigkeit dokumentierter Ausnahmen |
| `devsecops_release_readiness.rego` | DevSecOps-Bedingungen für den Release-Kontext |
| `architecture_*.rego` | Architekturbezogene Bereitschaftsprüfungen |

**Konkretes Beispiel:** `DSCB-L1-REQ-006` verlangt eine SBOM für auslieferbare
Artefakte. Bei `release_candidate = true` erzeugt `sbom_required.rego` einen
Befund, wenn die SBOM fehlt. Existiert sie, fehlt aber ihre Zuordnung zum
Artefakt, entsteht ebenfalls ein Befund. Sind beide Angaben erfüllt, erzeugt
diese Einzelregel keinen SBOM-Befund.

**Ergebnisse:** Regelentscheidungen und Befundmeldungen, die Kontroll- und
Release-Berichte weiterverwenden.

**Einordnung und Grenzen:** Ausführbare Regeln sind vorhanden. Einige werden
als generische Policy-Kandidaten geführt. Nicht jede Datei ist Teil jeder
veröffentlichten Baseline. Eine Prüfung von Signaturangaben ist zudem von der
kryptografischen Attestierungsprüfung in Abschnitt 14 zu unterscheiden.

## 7. Architektur-Governance modellieren

**Zweck:** Architekturqualität und notwendige Nachweise strukturiert beschreiben,
sodass Bewertungen und Entscheidungen vergleichbar werden.

**Eingaben:** Akzeptierte Architekturvorgaben, Qualitätsmerkmale,
Verantwortlichkeiten und Review-Erwartungen.

**Ablauf:** Die Modelle ordnen Architekturleveln Merkmale und Anforderungen zu.
Qualitätsmarker beschreiben zu bewertende Aspekte. Guardrails und Review-Gates
legen relevante Bedingungen und erwartete Nachweise fest. Maßnahmenkataloge
geben Hinweise zur Bearbeitung von Abweichungen.

**Ergebnisse:** Ein Architekturmodell mit Leveln, Markern, Gates,
Nachweiserwartungen und möglichen Folgemaßnahmen.

**Implementierungsstellen:** `architecture/arch-l1.yaml`,
`architecture/arch-l2.yaml`, `architecture/arch-l3.yaml`,
`architecture/arch-gov.yaml`, `architecture/quality-markers.yaml`,
`architecture/guardrails.yaml`, `architecture/review-gates.yaml`,
`architecture/remediation-actions.yaml`.

**Einordnung und Grenzen:** Modelliert und durch Validatoren abgesichert.
Markerbewertungen und fachliche Architekturentscheidungen benötigen geeignete
Nachweise und menschliche Zuständigkeit.

## 8. Architektur-Bereitschaft bewerten

**Zweck:** Erkennen, welche Voraussetzungen für Architekturarbeit, Integration,
Release und Betrieb im betrachteten Nachweisstand erfüllt sind.

**Eingaben:** Strukturierter Architektur-Eingang mit Baselinebezug, bewerteten
Merkmalen und unterstützenden Nachweisen.

**Ablauf:** Die Architekturprüfungen werten die Bedingungen der jeweiligen Gates
aus. Berichtsgeneratoren ordnen Befunde den Gates zu und erstellen
maschinenlesbare und menschlich lesbare Ergebnisse.

| Gate | Leitfrage |
| --- | --- |
| Architecture Readiness | Sind Entwurf, Verantwortung und notwendige Grundlagen ausreichend beschrieben? |
| Integration Readiness | Sind Schnittstellen, Verträge und Integrationsannahmen hinreichend belegt? |
| Release Readiness | Ist die Baseline-Kompatibilität mit den benötigten Nachweisen belegt? |
| Operation Readiness | Sind Beobachtbarkeit, Betriebsnachweise und Rückkopplung berücksichtigt? |

**Ergebnisse:** Gate-Status, Befundlisten und Architektur-Governance-Berichte.

**Implementierungsstellen:** `scripts/generate_architecture_governance_report.py`,
`policies/opa/architecture_readiness.rego`,
`policies/opa/architecture_integration_readiness.rego`,
`policies/opa/architecture_release_readiness.rego`,
`policies/opa/architecture_operation_readiness.rego`.

**Einordnung und Grenzen:** Implementiert. Der Architektur-Workflow kann Befunde
berichten oder bei entsprechender Konfiguration fehlschlagen. Automatische
Gate-Ergebnisse ersetzen keine umfassende fachliche Produktionsfreigabe.

## 9. Nachweise sammeln und vereinheitlichen

**Zweck:** Anwendungsspezifische Informationen in die gemeinsam erwarteten
Datenstrukturen überführen.

**Eingaben:** Repository-Dateien, Release-Angaben, Anwendungsartefakte, SBOM,
normalisierte Scan-Ergebnisse und fachliche Nachweisdateien.

**Ablauf:** Collector-Skripte sammeln DevSecOps- oder Architektur-Eingaben.
Pipeline-Werkzeuge stellen Artefakt- und Nachweisinformationen zusammen.
Schemas definieren die zulässige Struktur. Der optionale Schwachstellen-Collector
prüft normalisierte Scan-Eingaben und erfasst den zugehörigen Nachweiskontext.

**Ergebnisse:** Governance-Run-Input, Architektur-Release-Input,
Pipeline-Evidence und typisierte Nachweise für spätere Trust-Bewertungen.

**Implementierungsstellen:** `scripts/collect_devsecops_release_input.py`,
`scripts/collect_architecture_release_input.py`,
`scripts/generate_pipeline_evidence.py`,
`scripts/collect_vulnerability_scan_evidence.py`,
`schemas/governance-run-input.schema.json`,
`schemas/architecture-release-candidate.schema.json`.

**Einordnung und Grenzen:** Collector- und Schemafunktionen sind implementiert.
Der Schwachstellen-Collector ist ein optionaler report-only Pilot. Er ist kein
nativer Universalparser für Trivy, Grype, Snyk, CodeQL oder SARIF. Eingangsdaten
müssen zunächst das erwartete normalisierte Format erfüllen. Eine gültige
Datenstruktur allein beweist keine korrekte Herkunft.

## 10. Baselines veröffentlichen und konsumieren

**Zweck:** Anwendungen mit einem identifizierbaren und bewusst gewählten
Governance-Prüfstand verbinden.

**Eingaben:** Überprüfte Modelle, Policies, Schemas, Workflow-Anteile und eine
Release-Entscheidung.

**Ablauf:** Release-Pakete halten den jeweiligen Stand mit Metadaten,
Dokumentation und Prüfsummen fest. Veröffentlichte Tags oder festgelegte Commits
ermöglichen die gezielte Verwendung. Wiederverwendbare Workflows führen die
jeweiligen Prüfungen im Kontext einer Anwendung aus.

**Ergebnisse:** Versionierte Baseline-Pakete und konsumierbare
Workflow-Schnittstellen. Zum betrachteten Stand sind DevSecOps
`l1-baseline-v1.1.3` und Architektur `architecture-baseline-l1-v0.1.0`
die hier relevanten veröffentlichten L1-Baselines.

**Implementierungsstellen:** `releases/l1/v1.1.3/`,
`releases/architecture/l1/v0.1.0/`, `docs/releases/`,
`.github/workflows/devsecops-baseline-l1-v1.1.3.yml`,
`.github/workflows/devsecops-baseline-reusable.yml`,
`.github/workflows/architecture-baseline-l1-v0.1.0.yml`.

**Einordnung und Grenzen:** Release-Artefakte und konsumierbare Workflows sind
vorhanden. Die Release-Entscheidung erfolgt kontrolliert. Eine Datei gleichen
Namens auf `main` ist von ihrem Stand unter einem veröffentlichten Tag zu
unterscheiden. Änderungen an `main` ändern nicht rückwirkend das Release-Paket.

## 11. Ergebnisse zentral aufnehmen

**Zweck:** Ergebnisse unterschiedlicher Anwendungsläufe in ein gemeinsames
zentrales Statusmodell überführen.

**Eingaben:** Repository-ID, Lauf-ID, Domäne, Artefaktname, Baselinekontext und die
zugehörigen Berichte. Alternativ kann ein unterstütztes CI-Artefaktbundle als
Eingang dienen.

**Ablauf:** GitHub-Intakes lesen Laufmetadaten und laden die passenden Artefakte.
Sie normalisieren Berichte und erfassen Kontext sowie verfügbare Trust-Metadaten.
Separate Wege behandeln DevSecOps, Architektur und typisierte Nachweise.
Workflows unterstützen manuelle Auslösung und definierte Repository-Ereignisse.
Bundle-Validierung und Bundle-Intake ermöglichen einen weiteren Übergabepfad.

**Ergebnisse:** Normalisierte Snapshots in `status/results/`,
`status/architecture-results/` und `status/typed-evidence-results/` sowie
aktualisierbare Projektionen.

**Implementierungsstellen:** `scripts/intake_governance_result.py`,
`scripts/intake_github_actions_run.py`,
`scripts/intake_architecture_github_actions_run.py`,
`scripts/intake_evidence_trust_github_actions_run.py`,
`scripts/intake_ha_container_trust.py`,
`scripts/lib/container_typed_evidence.py`,
`scripts/intake_ci_artifact_bundle.py`, `scripts/validate_ci_artifact_bundle.py`,
`.github/workflows/intake-governance-result.yml`,
`.github/workflows/intake-architecture-result.yml`,
`.github/workflows/intake-evidence-trust.yml`.

**Einordnung und Grenzen:** Implementiert. Zugänge, vorhandene Laufartefakte und
passende Formate sind notwendig. Ein erfolgreicher Download oder lokaler Intake
macht die Daten noch nicht zum offiziellen veröffentlichten `main`-Stand.
Das feste ha-CPsWMS-Profil nimmt fünf vollständige Container-Archive gemeinsam
auf, verifiziert Vulnerability-Scan und CycloneDX-SBOM getrennt und verwirft
unvollständige, veraltete oder widersprüchlich gebundene Läufe.

## 12. Ergebnisgeschichte schützen

**Zweck:** Bereits erfasste Nachweise erhalten und widersprüchliche
Wiederholungen sichtbar behandeln.

**Eingaben:** Ein neuer normalisierter Snapshot und die bereits vorhandene
Ergebnisgeschichte mit Laufidentitäten und Digests.

**Ablauf:** Das Ledger legt neue Snapshots einmalig an. Eine identische
Wiederholung bleibt ohne Änderung. Abweichende Inhalte zu einer vorhandenen
Snapshot-Identität überschreiben das Original nicht, sondern erzeugen einen
Konfliktdatensatz. Für bestimmte ältere Identitäten existiert eine dokumentierte
Kompatibilitätsregel zur nachträglichen Digest-Anreicherung ohne Umschreiben des
Originals.

**Ergebnisse:** Ergänzbare, nicht überschreibende Ergebnisgeschichte und eine
separate Konfliktablage unter `status/intake-conflicts/`.

**Implementierungsstellen:** `scripts/lib/result_ledger.py`,
`schemas/intake-conflict.schema.json`, die Intake-Skripte und die Statusspeicher.

**Einordnung und Grenzen:** Implementiert. Append-only beschreibt das Verhalten
der unterstützten Schreibpfade. Es ist keine Behauptung eines physisch
unveränderbaren Speichermediums und ersetzt weder Git-Schutz noch Sicherung.

## 13. Vertrauen in Nachweise bewerten

**Zweck:** Die Verlässlichkeit eines Nachweises getrennt vom fachlichen Inhalt
seines Ergebnisses beurteilen.

**Eingaben:** Erfasste Nachweise, Prüfsummen, Lauf- und Artefaktkontext,
Collector-Angaben sowie die zugehörigen Trust- und Freshness-Regeln.

**Ablauf:** Die Verifikation prüft verfügbare Hashes und Kontextbindungen. Sie
bewertet Aktualität und dokumentiert nicht ausgeführte oder fehlgeschlagene
Prüfungen. Die Erfassung beschreibt auch den Übernahmekontext. Typisierte
Nachweise bleiben in einem eigenen Speicher, damit ihre Qualität nicht mit einem
Governance-Ergebnis verwechselt wird.

**Ergebnisse:** Trust-Bewertungen mit nachvollziehbaren Einzelprüfungen und
sichtbaren Grenzen, etwa `unverified` oder `integrity_verified`.

Der feste ha-CPsWMS-Fünf-Image-Intake kann inzwischen auf neu aufgenommenen
Snapshots `provenance_verified` erreichen. Er prüft zusätzlich die unveränderliche
Baseline-Bindung über den passenden erfolgreichen Main-Push-Lauf desselben
Commits sowie die Rohartefakt-/Normalisierungs-Custody. Der übernommene SBOM-Snapshot
für Lauf `36997124065`, Versuch 2, erreicht diese Stufe. Alte Snapshots werden
nicht hochgestuft; eine kryptografische Producer-Attestierung ist damit nicht
nachgewiesen. Verfahren und Grenzen: [Evidence Trust](../evidence/evidence-trust-model.md#ha-cpswms-container-evidence).

**Implementierungsstellen:** `scripts/lib/evidence_trust.py`,
`model/evidence/evidence-trust-model.yaml`,
`model/evidence/evidence-freshness-policies.yaml`,
`model/evidence/evidence-collector-contract.yaml`,
`scripts/generate_typed_evidence_results_index.py`,
`scripts/lib/container_typed_evidence.py`.

**Einordnung und Grenzen:** Implementiert und report-only. Ein korrekter Hash
belegt für sich keine fachliche Wahrheit oder unabhängig bestätigte Herkunft.
Freshness-Grenzen unterscheiden sich nach Nachweistyp und Verwendungszweck.
Trust verändert weder das fachliche Ergebnis noch automatisch die Auswahl des
letzten offiziellen Ergebnisses.

Für die gemessene ha-CPsWMS-L1-Bewertung ordnet ein eigenes Profil allen 16
Kontrollen Nachweistyp, Freshness, Entscheidungskontext und Subjektbindung zu.
Vorhandene und fehlende Nachweisgruppen werden getrennt bewertet; fehlender
Pflichtumfang setzt den aggregierten Kontroll-Trust konservativ auf `unverified`.
Implementiert in `model/evidence/control-evidence-assurance-profile.yaml`,
`scripts/lib/control_evidence_assurance.py`,
`schemas/control-evidence-assurance.schema.json` und
`status/control-evidence-assurance/`.

Für ein exakt passendes reales Staging-Deployment erzeugt
`scripts/lib/consolidated_l1.py` eine zusätzliche append-only 16-Kontroll-Sicht.
Sie übernimmt ausschließlich die Staging-Aussagen zu 013, 014 und 016 und nur
bei identischem Repository, Baseline, Commit, Producer-Run und Versuch. Vertrag
und Ergebnisse liegen in `schemas/consolidated-l1-assessment.schema.json` und
`status/consolidated-l1-results/`.

## 14. Replay und Attestierungen untersuchen

**Zweck:** Unpassende Wiederverwendung von Nachweisen erkennen und eine
kryptografische Bindung an ihren Kontext erproben.

**Eingaben:** Historische Nachweise und ihre Repository-, Commit-, Lauf-,
Artefakt- und Digest-Identitäten. Für den Attestierungs-Pilot kommt eine signierte
Aussage mit registriertem öffentlichem Schlüssel hinzu.

**Ablauf:** Replay-Prüfungen untersuchen die Verwendung in unterschiedlichen
Entscheidungskontexten. Replay-Triage stellt das ursprüngliche Ergebnis seiner
Interpretation unter den aktuellen Regeln gegenüber und empfiehlt weitere
Schritte. Der Attestierungs-Verifier prüft Ed25519-Signatur, Schlüsselzuständigkeit,
Repository-Scope und die Bindung an den erwarteten Inhalt und Laufkontext.

**Ergebnisse:** Replay-Befunde und Triage-Berichte sowie ein separates
Attestierungs-Assessment.

**Implementierungsstellen:** `scripts/lib/result_ledger.py`,
`scripts/generate_replay_triage_report.py`,
`scripts/lib/evidence_attestation.py`, `scripts/verify_evidence_attestation.py`,
`model/evidence/evidence-trust-roots.yaml`.

**Einordnung und Grenzen:** Replay und Triage sind implementierte report-only
Funktionen. Die Attestierung ist ein interner Pilot mit Demo-Vertrauensanker. Ein
erfolgreicher Pilot kann `candidate_level: attested` ausweisen; der effektive
Level bleibt `integrity_verified`. Daraus folgt keine produktive
Schlüsselverwaltung und keine neue Blocking-Berechtigung.

## 15. Sammlungsfehler behandeln

**Zweck:** Fehlgeschlagene Nachweisübernahmen sichtbar halten und eine
kontrollierte Wiederholung ermöglichen.

**Eingaben:** Angeforderte Repository- und Laufidentität, Artefaktname,
Fehlercodes sowie die Einstufung, ob ein Fehler wiederholbar ist.

**Ablauf:** Ein Collection Attempt dokumentiert den fehlgeschlagenen Versuch.
Wenn GitHub-Metadaten nicht verfügbar sind, bleibt die angeforderte Identität mit
dem entsprechenden Fehler erhalten. Der Retry-Prozess validiert einen
bestehenden Datensatz und löst nur einen unterstützten Intake für zulässige
wiederholbare Fehler aus. Eine spätere erfolgreiche Sammlung kann den angezeigten
Lebenszyklus als erledigt darstellen, ohne den Originalfehler zu verändern.

**Ergebnisse:** Historische Fehlerdatensätze, Retry-Kontext und die
Lebenszykluszustände `open`, `resolved` oder `permanent`.

**Implementierungsstellen:** `scripts/record_collection_attempt.py`,
`scripts/lib/collection_attempts.py`,
`scripts/prepare_collection_attempt_retry.py`,
`.github/workflows/retry-collection-attempt.yml`, `status/collection-attempts/`.

**Einordnung und Grenzen:** Implementiert. Retries sind ausdrückliche
Operator-Aktionen. Ein behobener Sammlungsfehler bedeutet nur, dass Nachweise
schließlich übernommen werden konnten. Ihr Governance-Ergebnis kann weiterhin
Befunde enthalten. Auch Fehlerdatensätze benötigen den Veröffentlichungsweg.

## 16. Operative Änderungen über PRs veröffentlichen

**Zweck:** Automatisch erzeugte operative Daten kontrolliert in den offiziellen
Repository-Stand übernehmen.

**Eingaben:** Von Intake- oder Projektionsläufen erzeugte Änderungen und der für
diesen Operationstyp erlaubte Dateiumfang.

**Ablauf:** Das Veröffentlichungswerkzeug prüft den Ausführungskontext und die
zulässigen Pfade. Es schützt bestehende Append-only-Nachweise, erstellt einen
Automation-Branch und eröffnet einen PR. Die Workflows können erforderliche
Prüfungen gezielt anstoßen. Erst Review und Merge übernehmen den vorgeschlagenen
Stand nach `main`.

**Ergebnisse:** Ein überprüfbarer Bot-PR mit begrenztem Änderungsumfang und
anschließend, bei Annahme, aktualisierte offizielle Indizes und Viewer-Daten.

**Implementierungsstellen:** `scripts/publish_operational_update.py`, die drei
Intake-Workflows, `.github/workflows/portfolio-status.yml` und
`.github/workflows/lifecycle-pilot-update.yml`. Der Publisher unterscheidet
sechs Umfänge: DevSecOps, Architektur, typisierte Evidenz, Portfolio, synthetischer
Lifecycle und der abgenommene GitHub-Lifecycle-Pilot.

**Einordnung und Grenzen:** Implementiert. Der Bot genehmigt oder merged seine
PRs nicht selbst. Parallele Intake-Läufe besitzen getrennte Identitäten. Bei
Merge-Konflikten müssen alle angenommenen Datensätze erhalten und gemeinsame
Projektionen neu berechnet werden. Ein ungemergter PR ist noch kein offizieller
Status.

## 17. Status anzeigen und untersuchen

**Zweck:** Ergebnisse und ihre Zusammenhänge für Menschen zugänglich machen.

**Eingaben:** Angenommene Snapshots, Quellenregister, Lineage-Berichte und die
jeweiligen Statusindizes.

**Ablauf:** Generatoren erstellen DevSecOps-, Architektur- und
Typed-Evidence-Indizes. Die offizielle Auswahl berücksichtigt Mainline-Kontext;
ein vorhandenes letztes `main`-`push`-Ergebnis wird nicht durch einen manuellen
Diagnoselauf oder Branch-Lauf verdrängt. Historische Ergebnisse bleiben
untersuchbar. Der Governance-Graph verknüpft Quellen, Artefakte, Repositories,
Läufe, Commits, Baselines, Trust und Nachweise. Er projiziert die von den Indizes
ausgewählten aktuellen Ergebnisse, nicht die gesamte Historie.

**Ergebnisse:** Eine eigenständige [Viewer-Anwendung](governance-viewer-app.md)
mit Übersicht, Repository-Details, filterbaren Container-Befunden, einem eigenen
Repository-Security-Bereich und Nachweisen
sowie integrierten Governance- und Betriebsansichten;
zusätzlich der bisherige technische HTML-Viewer, strukturierte Indizes und ein
maschinenlesbarer Graph. Im Graph lassen sich Knoten suchen, Typen filtern und
Beziehungen untersuchen. Integrierte Ansichten zeigen Befunde, Trust, Replay, Laufhistorie,
Sammlungsfehler, Modelle und Agent-Nutzung. Technische Tabellen unterstützen
Suche und Seitennavigation; auf Mobilgeräten werden Unterbereiche ausgewählt.
Die L1-Detailansicht zeigt für jede der 16 Kontrollen zusätzlich Trust, Freshness,
Integrität, Provenienz, Replay, Custody, Attestation und fehlende Nachweisgruppen.
Der Repository-Reiter **Staging** zeigt reale Deployment-Identität, Approval,
Health-, Funktions-, Persistenz- und Wiederanlaufprüfungen sowie die getrennte
L1-Ergänzung für 013, 014 und 016. Bei exakter Subjektbindung zeigt der
L1-Reiter die daraus erzeugte konsolidierte Bewertung als primäre Sicht.

**Implementierungsstellen:** `scripts/generate_repository_results_index.py`,
`scripts/generate_architecture_results_index.py`,
`scripts/generate_typed_evidence_results_index.py`,
`scripts/intake_staging_deployment_evidence.py`,
`scripts/lib/consolidated_l1.py`,
`scripts/generate_governance_graph.py`, `scripts/generate_status_viewer.py`,
`generated/viewer/status-viewer.html`, `generated/graph/governance-graph.json`,
`apps/governance-viewer/`, `scripts/lib/viewer_app.py`, `generated/viewer/app/`.

**Einordnung und Grenzen:** Implementiert und lesend. Der Viewer verändert keine
Nachweise, Regeln oder Freigaben. Seine Daten sind abgeleitete Sichten.
Veröffentlichung und Aktualität hängen vom angenommenen Datenstand und dem
Publikationslauf ab.

## 18. Einführung und Betriebsreife bewerten

**Zweck:** Integrationslücken und Voraussetzungen für einen breiteren oder
verbindlicheren Einsatz sichtbar machen.

**Eingaben:** Anwendungs-Repositories, Integrationsregister, Ergebnisse,
Betriebsmodelle und dokumentierte Reifeanforderungen.

**Ablauf:** Ein Integrationscheck untersucht vorhandene CI-Anbindungen.
Onboarding-Readiness bewertet erkennbare Voraussetzungen und gibt Empfehlungen.
Portfolio-Berichte verbinden registrierte Zuständigkeiten mit Baselines und
Ergebnisdaten. Multi-Consumer-Readiness prüft unter anderem Speicherung,
Trennung und Projektion mehrerer Consumer. Blocking-Readiness bewertet die
Voraussetzungen für neue verbindliche Gates. Mode Alignment macht Abweichungen
zwischen registriertem Modus und dem vorgesehenen Umgang damit sichtbar.

**Ergebnisse:** Integrations- und Onboarding-Berichte, Portfolio-Übersichten,
Readiness-Befunde und Hinweise auf notwendige Entscheidungen.

**Implementierungsstellen:** `scripts/check_repo_governance_integration.py`,
`scripts/check_repository_onboarding_readiness.py`,
`scripts/generate_portfolio_onboarding_status.py`,
`scripts/generate_multi_consumer_readiness.py`,
`scripts/simulate_consumer_scale.py`,
`scripts/generate_blocking_readiness.py`,
`scripts/generate_blocking_mode_alignment.py`,
`status/application-repository-integrations.yaml`, `model/enforcement/`.

Die [Consumer-Scale-Simulation](../planning/consumer-scale-capacity-assessment.md)
misst zusätzlich die isolierte Index-, Portfolio- und Viewer-Verarbeitung für
synthetische 300- und 1.500-Consumer-Szenarien. Sie verwendet temporäre Daten
und verändert keine offiziellen Ergebnisse. GitHub-API-, PR-, Review- und
Browserlast bleiben getrennte Produktionsabnahmen.

**Einordnung und Grenzen:** Implementierte Entscheidungshilfen. Die
Portfolio-Berichterstattung ist einfacher als das umfassendere fachliche
Adoptionsmodell: Der aktuelle Generator leitet `pilot` beziehungsweise `active`
aus dem registrierten Modus ab. `active` beweist deshalb für sich weder frische
noch bestandene Nachweise. Readiness-Berichte ändern keine Consumer-Workflows,
keinen Branch-Schutz und keine Freigaben. Neu berechnete Berichte machen alte
Anwendungsnachweise nicht aktuell.

## 19. Betrieb und eigene Sicherheit überwachen

**Zweck:** Sowohl den Übernahmebetrieb als auch Schutzmaßnahmen des zentralen
Governance-Repositories untersuchen.

**Eingaben:** Intake-Ereignisse, Collection Attempts, Snapshots, offene PRs,
Workflow-Läufe, GitHub-Einstellungen und das Repository-Sicherheitsmodell.

**Ablauf:** Intake Events erfassen auch erfolgreiche Ausführungen und ihre Dauer.
Die Intake-Health-Projektion berechnet im standardmäßigen 30-Tage-Fenster
Erfolgs- und Fehlerraten sowie Laufzeitkennzahlen und differenziert nach Kontext.
Der tägliche Betriebsbericht sammelt Beobachtungen zu Workflows, Publikation,
PR-Warteschlange, Nachweisen und Sicherheit. Die Self-Security-Bewertung untersucht
beobachtbare Repository-Schutzmaßnahmen. Separate Workflows führen CodeQL und
Dependency Review aus. GitHub erzwingt vollständige Action-SHAs, beschränkt
Action-Quellen und verlangt Dependency Review auf `main`. Hash-Locks schützen
die Python-Installation der nicht durch die bestehende Lifecycle-Abnahme
gebundenen Betriebs- und Publikationsworkflows. Artefakthygiene prüft öffentliche
Veröffentlichungsinhalte.

**Ergebnisse:** Intake Health, Betriebsbericht, Sicherheitsassessment und
CI-Sicherheitsbefunde. Der Viewer projiziert das schema-validierte
Self-Security-Assessment als eigenen Bereich mit Gesamtstatus, allen Kriterien
und dokumentierten Maßnahmen. Nicht verfügbare Informationen bleiben als
fehlende Beobachtbarkeit erkennbar.

**Implementierungsstellen:** `scripts/record_intake_event.py`,
`scripts/generate_intake_health.py`, `scripts/generate_operations_report.py`,
`scripts/assess_governance_repository_security.py`,
`scripts/lib/release_integrity.py`,
`scripts/check_public_artifact_hygiene.py`,
`.github/workflows/governance-operations.yml`,
`.github/workflows/governance-repository-security.yml`,
`.github/workflows/codeql.yml`, `.github/workflows/dependency-review.yml`.

**Einordnung und Grenzen:** Implementiert. Der tägliche Bericht läuft nach der
hinterlegten Planung um 06:43 UTC und dient der Beobachtung. Er verschickt selbst
keine Warnmeldungen und erstellt keine Aufgaben. Fehlende Berechtigungen können
Beobachtungen verhindern. Self-Security nimmt keine selbstständige Reparatur von
GitHub-Einstellungen vor. Berechnete Raten benötigen stets den zugehörigen
Stichprobenumfang.

## 20. Reviews, Validierung und Kommunikation unterstützen

**Zweck:** Die Pflege des Governance-Systems wiederholbar organisieren und seine
Inhalte nutzbar vermitteln.

**Eingaben:** Geänderte Dateien, Rollenverträge, Routing-Regeln, Modelle,
Nachweisbeispiele und redaktionelle Dokumentquellen.

**Ablauf und Teilfunktionen:**

- **Review-Routing:** Geänderte Pfade werden erforderlichen Governance-Rollen
  zugeordnet. Modellneutrale Verträge liegen unter `.agents/`; Codex- und
  Mistral-Unterlagen bilden Provider-spezifische Adapter.
- **Nutzungsdokumentation:** Werkzeuge erfassen Dispatch-Nutzung und erzeugen
  Zusammenfassungen. Evidence-Agent-Provenance dokumentiert und validiert die
  Beteiligung an Nachweisprozessen und stellt einen zugehörigen Index bereit.
- **Deterministische Prüfung:** Der lokale Agent-Harness prüft Routing und
  Sicherheitsinvarianten ohne Live-LLM-Aufrufe. Die vollständige Validierung
  verbindet OPA-, Modell-, Schema-, Repository- und Unit-Test-Prüfungen.
- **Anforderungsaufbereitung:** Ein Importer übernimmt das vorgesehene Format
  harmonisierter Anforderungen aus einem Workbook. Reifegradzuordnungen und
  Coverage-Berichte unterstützen die anschließende Prüfung.
- **Berichtserzeugung:** Generatoren erstellen Abdeckungs-, Lücken-,
  Automatisierungs-, Pipeline- und End-to-End-Berichte sowie Dokumentausgaben.
- **Veröffentlichung:** MkDocs und GitHub Pages veröffentlichen die
  Dokumentation. Publishing-Builder erzeugen das Executive-Whitepaper und seine
  PowerPoint aus einer gemeinsamen redaktionellen Quelle.
- **Demo und Integration:** Runbooks, Beispiele und Pipeline-Vorlagen
  unterstützen die Erprobung und den Anschluss weiterer Anwendungen.

**Ergebnisse:** Review-Zuordnung, Nutzungsnachweise, Prüfberichte,
Anforderungsaufbereitung, verständliche Dokumentation und wiederverwendbare
Integrationsunterlagen.

**Implementierungsstellen:** `scripts/dispatch_governance_agents.py`,
`scripts/generate_agent_usage_snapshot.py`,
`scripts/record_evidence_agent_provenance.py`,
`scripts/validate_evidence_agent_provenance.py`,
`scripts/generate_evidence_agent_provenance_index.py`,
`scripts/import_harmonized_requirements_workbook.py`,
`scripts/generate_harmonized_requirements_maturity_report.py`,
`scripts/render_governance_documents.py`, `scripts/run_demo.py`,
`scripts/publishing/`, `tests/agent_harness/`,
`.github/workflows/governance-ci.yml`, `.github/workflows/publish-docs.yml`.

**Einordnung und Grenzen:** Werkzeuge sind implementiert; Provider-Unterlagen
und CI-Adapter haben teilweise Vorlagencharakter. Rollenrouting führt allein
noch keinen fachlichen Review durch und erteilt keine Freigabe. Importierte
Kandidatenanforderungen werden durch den Import nicht genehmigt.
Publishing-Builder benötigen ihre eigene Artefaktumgebung; sie sind keine
Laufzeitabhängigkeit der Governance-Prüfung.

## 21. Findings, Entscheidungen und Maßnahmen im Lifecycle verfolgen

**Zweck:** Einen Governance-Befund vom nachgewiesenen Fehler über eine bewusste
menschliche Entscheidung und Behebung bis zum evidenzgebundenen Abschluss verfolgen.

**Eingaben:** Zulässige GRS-002-Beobachtungen mit vollständigem Capture-Paket,
versioniertes Betriebsprofil und Rollenbindung, persönliche GitHub-Erklärungen
zu unveränderlichen Anträgen sowie erwartete Verlaufsrevisionen.

| Teilfunktion | Verarbeitung und Ergebnis | Geltungsbereich |
|---|---|---|
| Verträge und synthetischer Kern | Schemas, kanonische Digests, Ereignisse, Findings, vollständiger Replay | CLG-01/02; drei getrennte synthetische Historien |
| Echte Beobachtungen | GitHub-Lauf, Commit, Versuch, Artefakt, Producer-Dateien und Frische prüfen; unveränderliche Receipts | Nur freigegebenes GRS-002/main im Governance-Repository |
| Wiederholung und Konflikt | Identische erneute Zustellung ohne neue Wirkung; abweichende Herkunft/Inhalte quarantänisieren | Keine Überschreibung angenommener Geschichte |
| Persönliche Betriebsabnahme | Identität, Inhalt und unveränderte Implementierung prüfen; separate offizielle Pilotprojektion freischalten | LD-07 persönlich bestätigt, PR #92 gemergt |
| Behebungsentscheidung | Reales FAIL, vollständigen Plan, benannten Owner, Zieltermin, Arbeitsreferenz und Einzelfreigabe prüfen | Keine automatische Behebung |
| Fortschritt | Persönlich bestätigte Zustände `in_progress` und `completed` mit Nachweisnotiz aufnehmen | Kein unabhängiger Beweis, dass ein referenziertes Ticket erledigt wurde |
| Abschluss und Wiedereröffnung | Aktive Entscheidung, abgeschlossene Behebung, neueres frisches PASS und eigene Abschlussfreigabe verbinden; neueres FAIL wieder öffnen | PASS allein schließt kein Finding |
| Widerruf und Korrektur | Erklärungswiderruf, geänderte/gelöschte Erklärungen und Rollenentzug berücksichtigen; abhängige Freigaben ungültig machen | Historische Entscheidungen/Abschlüsse bleiben nachvollziehbar |
| Befristete Ausnahmen | Teilabdeckung, Überlappung, Ablauf und Widerruf mit explizitem Auswertungszeitpunkt | CLG-05 nur synthetisch; kein Live-Waiver freigegeben |
| Szenarioübersicht und Viewer | Getrennte Testhistorien, Zustände, Kennzahlen, Ereignisfilter und Referenzen anzeigen | CLG-06.1/06.2 lesend; keine realen Portfolioquoten |
| Weitere Ergebnisadapter | DevSecOps-Control- und Architektur-Gate-Kandidaten samt Herkunft und Granularität aufbereiten | CLG-06.3 diagnostisch; keine automatische Lifecycle-Annahme |
| Betriebsvorschlag | `acceptance`, `observe`, `action`, `refresh` auf `main`; begrenzten PR erzeugen und Provider unabhängig nachprüfen | Manuell, report-only, keine automatische Freigabe oder Merge |

**Ergebnisse:** Unveränderliche Transaktionen, technische Zulässigkeitsindizes,
separate wirksame Live-Ansicht, JSON-/Markdown-Berichte und synthetischer Viewer.
Am geprüften Stand sind zwei reale PASS-Receipts angenommen, null Findings und
null Maßnahmen vorhanden. Die vollständige Fehlerfolge ist durch Tests belegt;
sie wird nicht als tatsächlich abgeschlossene Live-Behebung ausgegeben.

**Implementierungsstellen:** `scripts/lib/governance_lifecycle/`,
`scripts/run_lifecycle_pilot_update.py`, `scripts/prepare_lifecycle_pilot_action.py`,
`scripts/intake_lifecycle_pilot_action.py`, `scripts/validate_governance_lifecycle_ledger.py`,
`.github/workflows/lifecycle-pilot-update.yml`, `model/governance/lifecycle/`,
`governance/lifecycle/` und `status/governance-lifecycle-live.json`.

**Einordnung und Grenzen:** Der [begrenzte GitHub-Pilot ist aktiv](../status/governance-lifecycle-current-state.md).
Die Einzelfreigaben bleiben erforderlich. Es gibt keine kontinuierliche
Providerüberwachung, keinen automatischen Remediation-Executor und keinen
zugelassenen Bitbucket-Lifecycle-Adapter. Weitere Consumer, Live-Waiver,
Lifecycle-Portfolio und optionale KI-Unterstützung bleiben außerhalb der Abnahme.

Der [separate Consumer-Lifecycle](../evidence/consumer-lifecycle-operation.md)
ist für genau `governance-framework-demo-consumer` / `operation_readiness`
technisch implementiert. Rollen und Demo-Evidenzumfang sind bestätigt;
Die persönliche Betriebsabnahme und erste Behebungsentscheidung vom 16. September
sind erfasst; Fortschritt und Abschluss benötigen ihre eigenen Erklärungen. `run_consumer_lifecycle.py`
prüft GitHub-Artefakt/Commit/Baseline und berechnet das Gate mit OPA neu;
`publish_consumer_lifecycle.py` erzeugt ausschließlich Consumer-PRs.
Die neuen Workflows `consumer-lifecycle-update.yml` und
`consumer-lifecycle-guard.yml` übernehmen manuellen Betrieb und unabhängige
Providerprüfung. Die eigene Projektion `status/governance-consumer-lifecycle.json`
verhindert eine Vermischung mit dem bestehenden GRS-002-Piloten.

Die übernommene Consumer-Projektion vom `2026-10-03T10:58:04Z` dokumentiert
inzwischen `closed`, drei Receipts und vier Aktionsdatensätze. Fortschritt und
Abschluss wurden persönlich gebunden erfasst; die oben genannten Erklärungen
sind notwendige Bedingungen, nicht weiterhin ausstehende Aufgaben dieses Falls.
Die [Closed-Loop-Lesekarte](../evidence/governance-lifecycle-overview.md)
führt Verträge, Betrieb, Tests und Grenzen zusammen.

## Berichte und Exporte im Überblick

| Ausgabegruppe | Zweck | Wesentliche Generatoren unter `scripts/` |
| --- | --- | --- |
| Source Lineage | Herkunft abgeleiteter Dateien | `generate_source_lineage_report.py` |
| Dokument-Kontroll-Matrix | Quellen und Kontrollen gegenüberstellen | `generate_document_control_matrix.py` |
| Traceability-CSV | Beziehungen weiterverarbeiten | `generate_traceability_csv.py`, `generate_governance_traceability_csv.py`, `generate_architecture_traceability_csv.py` |
| Kontrollabdeckung | Technische Prüfunterstützung darstellen | `generate_control_coverage_report.py` |
| Automatisierung | Automatisierungsstand aufbereiten | `generate_automation_report.py` |
| Offene Lücken | Noch offene Abdeckung sichtbar machen | `generate_open_gap_report.py` |
| Pipeline-Baseline | Vorgesehene Pipeline-Zuordnung darstellen | `generate_pipeline_baseline_report.py` |
| Kontrollauswertung | Anwendungseingaben je Kontrolle bewerten | `generate_control_evaluation_report.py` |
| Domänenberichte | DevSecOps und Architektur zusammenfassen | `generate_devsecops_governance_report.py`, `generate_architecture_governance_report.py` |
| End-to-End | Governance-Zusammenhang erläutern | `generate_end_to_end_governance_report.py` |
| Compliance-Ergebnis | Strukturierte Gesamtausgabe erzeugen | `generate_governance_compliance_result.py` |
| Quellenänderung und Intake | Review und Auswirkungsprüfung vorbereiten | Die fünf Generatoren aus Abschnitt 2 |
| Harmonisierte Anforderungen | Reifegradzuordnung auswerten | `generate_harmonized_requirements_maturity_report.py` |
| Portfolio und Readiness | Einführung und Modusentscheidungen unterstützen | Die Generatoren aus Abschnitt 18 |
| Replay und Trust | Nachweiskontext untersuchen | `generate_replay_triage_report.py`, `verify_evidence_attestation.py` |
| Betrieb und Sicherheit | Operativen Handlungsbedarf erkennen | `generate_intake_health.py`, `generate_operations_report.py`, `assess_governance_repository_security.py` |
| Indizes und Graph | Daten für die Statusanzeige projizieren | Die Generatoren aus Abschnitt 17 |
| Agentennutzung | Routing-Nutzung und Beteiligung darstellen | `generate_agent_usage_snapshot.py`, `generate_evidence_agent_provenance_index.py` |
| Lifecycle | Echte Pilotansicht, Zulässigkeit, synthetische Ereignisse und Szenarien | `run_lifecycle_pilot_update.py`, `generate_lifecycle_pilot_validation.py`, `generate_lifecycle_pilot_actions.py`, `generate_governance_lifecycle_overview.py`, `generate_governance_lifecycle_viewer.py` |
| Dokumente und Kommunikation | Inhalte für Leser und Vorträge ausgeben | `render_governance_documents.py`, Builder unter `scripts/publishing/` |

Nicht jeder Bericht erzeugt dasselbe Dateiformat. Die jeweiligen Generatoren
und ihre Aufrufhilfe definieren die konkreten Ausgaben. Neu erzeugte
Berichtszeitstempel sind vom Entstehungszeitpunkt der zugrunde liegenden
Anwendungsnachweise zu unterscheiden.

## Schnittstellen und Integrationsgrenzen

| Schnittstelle | Vorhandene Unterstützung | Grenze |
| --- | --- | --- |
| GitHub Actions | Wiederverwendbare Baseline-Workflows, Ereignisse, Artefakt-Intake und PR-Veröffentlichung | Erfordert passende Zugänge und Consumer-Konfiguration |
| Allgemeines CI-Artefaktbundle | Validierung und normalisierte Übernahme | Producer muss das definierte Bundle liefern |
| GitLab CI | Governance-Check-Vorlage | Keine pauschal belegte Betriebsintegration |
| Jenkins | Pipeline-Vorlagen für DevSecOps und Architektur | Anpassung und Erprobung beim Betreiber |
| Bitbucket Data Center und Bamboo | Bamboo-Specs und Adapterunterlagen | Firmenversionen noch unbekannt, nicht live validiert; GitHub-Pilotabnahme gilt hier nicht |
| Bitbucket Cloud | Bitbucket-Pipelines-Vorlage | Eigener Cloud-Pfad, kein ausführbares Data-Center-Pipelineformat |
| Agentenprovider | Modellneutrale Verträge und Codex-/Mistral-Adapter | Kein automatischer Ersatz menschlicher Entscheidungszuständigkeit |
| Darstellung | Statischer Viewer, Graph und Dokumentationssite | Kein interaktiver Schreibzugriff auf Governance-Daten |

## Betrieb, Zuständigkeit und Freigaben

Fachlich Verantwortliche entscheiden über Quellen, Kontrollabsicht und
Ausnahmen. Anwendungsteams verantworten ihre Nachweise und die Einbindung der
gewählten Baseline. Der Plattformbetrieb betreut Zugänge, Intake, Publikation,
Fehlerbearbeitung und Sicherung. Reviewer prüfen vorgeschlagene Änderungen.

Das Repository enthält Verfahren für Zugangspflege, Tokenwechsel, Sicherung,
Wiederherstellung und Pilotabnahme. Diese Verfahren müssen mit benannten
Verantwortlichen tatsächlich ausgeführt werden. Ihre Dokumentation ist kein
Nachweis eines vollständig automatisierten oder unternehmensweit erprobten
Notfallbetriebs.

Neue Piloten wählen Report-only ausdrücklich für ihre Trigger. Der
wiederverwendbare DevSecOps-Workflow besitzt zum betrachteten Stand den Default
`block-on-error`; der Architektur-Wrapper verwendet `fail_on_findings=false`.
Die konkrete Consumer-Konfiguration ist deshalb entscheidend. Die bestehende
ha-CPsWMS-DevSecOps-Integration ist als älteres Blocking-Bestandsrisiko mit
Überprüfung bis 12. Dezember 2026 dokumentiert. Daraus folgt keine Freigabe für
neues Blocking.

## 22. Dokumentation nach Implementierungs-Merges abgleichen

**Zweck:** Nach einem Merge von Implementierung nach `main` einen geprüften
Dokumentationsvorschlag für README, Funktionskatalog, technisches Inventar und
Querverweise bereitstellen.

**Eingaben:** Zusammenfassung und Titel des gemergten PRs, dessen Merge-Commit,
die geänderten Implementierungspfade und der aktuelle Main-Stand.

**Ablauf:** `Documentation Refresh` reagiert auf den geschlossenen, gemergten
PR. Der Generator übernimmt die PR-Zusammenfassung als redaktionellen Entwurf,
listet betroffene Implementierungspfade und aktualisiert markierte Abschnitte
in README, Katalog und Inventar. Eine lokale Markdown-Linkprüfung und ein
strikter MkDocs-Build werden im Auditbericht festgehalten. Bei Änderungen an
Implementierungspfaden erstellt die Action einen Draft-PR und dispatcht die
erforderlichen Prüfungen. Reine Dokumentations-Merges erzeugen keinen Folge-PR.

**Ergebnisse:** Ein Draft-PR mit vorgeschlagenen Dokumentationsänderungen und
`generated/reports/documentation-refresh-audit.md`. Nach menschlicher
Vervollständigung und Freigabe werden sie über den normalen PR-Prozess nach
`main` gemergt.

**Implementierungsstellen:** `.github/workflows/documentation-refresh.yml`,
`scripts/reconcile_documentation_after_merge.py` und
`docs/operations/guides/documentation-after-merge.md`.

**Einordnung und Grenzen:** Der Workflow schreibt nie direkt nach `main` und
führt keinen semantischen Document Consistency Review aus. Die PR-Zusammenfassung
und Pfadliste sind nur ein Ausgangspunkt. Maintainer müssen die fachliche
Zuordnung, Auswirkungen auf weitere Dokumente und Vollständigkeit des Katalogs
prüfen. Der MkDocs-Build und die Linkprüfung beurteilen Form und Pfade, nicht
fachliche Konsistenz.

## Pflege und Überprüfung dieses Katalogs

Bei funktionalen Änderungen sollten Zweck, Verarbeitung, Eingaben, Ausgaben und
Grenzen des betroffenen Abschnitts aktualisiert werden. Die Beschreibung muss
zum tatsächlich implementierten Verhalten passen. Besonders bei Begriffen wie
`active`, `approved`, `pass` und `attested` ist die konkrete Bedeutung des Felds
zu prüfen.

Für Änderungen an diesem Katalog gelten die Repository-Prüfungen:

```bash
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh
.venv-docs/bin/mkdocs build --strict
```

Zusätzlich sind genannte Pfade und Beschreibungen mit dem Code abzugleichen.
Diese Validierung erzeugt keinen neuen Consumer-Lauf. Unbeabsichtigte reine
Zeitstempeländerungen in generierten Dateien gehören nicht in einen
Dokumentations-PR.

## Weiterführende Dokumentation

- [AI-Index mit Datei- und Themenzuordnung](../../ai-index.md)
- [Implementierte Systemarchitektur](../../governance/architecture/governance-as-code-system-architecture.md)
- [Governance Change Lifecycle](../../governance/governance-change-lifecycle.md)
- [Nachweisvertrag](../evidence/governance-evidence-contract.md)
- [Ergebnisaufnahme und Viewer](../evidence/governance-result-intake-and-viewer-usage.md)
- [Evidence Trust](../evidence/evidence-trust-model.md)
- [Attestierungs-Pilot](../evidence/evidence-attestation-pilot.md)
- [Betriebshandbuch](governance-repository-operations-handbook.md)
- [Täglicher Betriebsbericht](../status/daily-governance-operations.md)
- [Governance-Graph](../status/governance-intelligence-graph-viewer.md)
- [Agentensystem](../agents/agent-system-usage.md)
- [Veröffentlichte Baselines](../../releases/index.md)

## Gemessene Container-Schwachstellen im Viewer

Der Bereich **Container Security** zeigt echte ha-CPsWMS-Image-Scans, Schweregrade,
Vorher-/Nachher-Zahlen, Image-IDs und filterbare HIGH-/CRITICAL-Details. Der
Intake `scripts/intake_measured_security.py` prüft erfolgreiche Main-Runs,
Producer-Manifeste, Rohdatei-Hashes und Scan-Zuordnung und schreibt append-only
Snapshots. Aktualisierung erfolgt durch erneuten Intake, Validierung und Merge;
keine Live-Abfrage oder automatische Compliance-Freigabe. Ablauf und Grenzen:
[L1 measured evidence](../evidence/l1-measured-evidence-ha-cpswms.md).

## Zentrale L1-Bewertung aus Messdaten

Der neue Viewer zeigt unter **Repositories → ha-CPsWMS → L1-Nachweise** alle
16 bestehenden L1-Kontrollen mit tatsächlichen Prüfergebnissen, Werkzeugen,
Nachweis-Hashes und offenen Punkten. Ein separater Intake prüft JUnit, SAST,
SBOMs, Scans, Image-IDs und Plattformdaten und bewertet die technische Abdeckung
zentral. Deklarierte Freigaben werden nicht als Messung übernommen. Der offizielle
Baseline-Status und Replay bleiben unverändert daneben sichtbar.
Vertrag, Grenzen und wiederholbare Aufnahme:
[L1-Nachweise](../evidence/l1-measured-evidence-ha-cpswms.md#zentrale-bewertung-je-l1-kontrolle).

Der historische Referenzlauf `35241262722` umfasst 58 bestandene Tests, fünf gebaute und
gescannte Images, 749 SBOM-Komponenten und eine Assurance-Aussage für jede der
16 L1-Kontrollen. Sieben Kontrollen besitzen vollständige, frische und
integritätsgeprüfte Evidenz; fehlende organisatorische, Deployment- oder
Betriebsnachweise halten die übrigen neun ausdrücklich auf `unverified`.

Diese Zahlen gelten nur für den genannten Referenzlauf. Neuere übernommene
Snapshots und ihre individuellen Zeit-/Run-Bindungen stehen unter
`status/measured-l1-results/`, `status/control-evidence-assurance/` und
`status/typed-evidence-results/`. Der
[Plattformstatus](../status/current-governance-platform-state.md) zeigt den
datierten Dokumentationsabgleich und verweist auf die maßgeblichen Quellen.

## Hybrid requirement authority and migration

`scripts/manage_requirement_lifecycle.py` guides approved source documents and Git-native proposals through deterministic comparison, explicit human decision, immutable catalog activation, and authority transition. The Authority Ledger prevents an incomplete migration from silently replacing the external normative source. `scripts/validate_requirement_lifecycle.py` enforces schemas, coverage, source fingerprints, append-only history, catalog integrity, and the separation of blocking enforcement. Active catalog revisions feed the shared Doc-as-Code renderer for reviewable HTML, Word and PDF outputs.
