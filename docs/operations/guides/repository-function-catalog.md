# Detaillierter Funktionskatalog des Governance-Repositories

## Dokumentzweck und Geltungsbereich

Dieser Katalog beschreibt die fachlichen und betrieblichen Funktionen von
`joku-dev/devsecops-governance-framework`. Er erklärt, welche Aufgaben das
Repository übernimmt, wie Daten verarbeitet werden und welche Ergebnisse
entstehen. Die Gliederung umfasst die zwanzig Bereiche der Funktionsübersicht.
Interne Hilfsfunktionen werden ihrem jeweiligen Funktionsbereich zugeordnet.

| Merkmal | Wert |
| --- | --- |
| Dokumentstand | 9. September 2026 |
| Betrachteter Quellstand | `80ba315e56828f5186303045cc2792b576396c26` |
| Zielgruppe | Geschäftsführung, Governance-Verantwortliche, Architektur, Security, Plattformbetrieb und Anwendungsteams |
| Dokumenttyp | Erläuternder Funktionskatalog |
| Änderungsnachweis | [GCR-2026-056](../../governance/change-requests/GCR-2026-056-detailed-function-catalog.md) |

Der Katalog beschreibt vorhandene Fähigkeiten zum genannten Quellstand. Er
bestätigt keine aktuelle Betriebsbereitschaft einer Anwendung und erzeugt keine
neue fachliche Vorgabe. Genehmigte Quellen, Modelle, Schemas und veröffentlichte
Baselines bleiben für ihre jeweiligen Bereiche maßgeblich.

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
dürfen keine aktiven Kontrollen oder Baselines abgeleitet werden. Öffentliche
Platzhalter vertreten teilweise Originalquellen, deren Volltext zurückgehalten
wird.

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
`scripts/intake_ci_artifact_bundle.py`, `scripts/validate_ci_artifact_bundle.py`,
`.github/workflows/intake-governance-result.yml`,
`.github/workflows/intake-architecture-result.yml`,
`.github/workflows/intake-evidence-trust.yml`.

**Einordnung und Grenzen:** Implementiert. Zugänge, vorhandene Laufartefakte und
passende Formate sind notwendig. Ein erfolgreicher Download oder lokaler Intake
macht die Daten noch nicht zum offiziellen veröffentlichten `main`-Stand.

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

**Implementierungsstellen:** `scripts/lib/evidence_trust.py`,
`model/evidence/evidence-trust-model.yaml`,
`model/evidence/evidence-freshness-policies.yaml`,
`model/evidence/evidence-collector-contract.yaml`,
`scripts/generate_typed_evidence_results_index.py`.

**Einordnung und Grenzen:** Implementiert und report-only. Ein korrekter Hash
belegt für sich keine fachliche Wahrheit oder unabhängig bestätigte Herkunft.
Freshness-Grenzen unterscheiden sich nach Nachweistyp und Verwendungszweck.
Trust verändert weder das fachliche Ergebnis noch automatisch die Auswahl des
letzten offiziellen Ergebnisses.

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
Intake-Workflows und `.github/workflows/portfolio-status.yml`.

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

**Ergebnisse:** Ein statischer HTML-Viewer, strukturierte Indizes und ein
maschinenlesbarer Graph. Im Graph lassen sich Knoten suchen, Typen filtern und
Beziehungen untersuchen. Weitere Ansichten zeigen Befunde, Trust, Replay und
Sammlungsfehler.

**Implementierungsstellen:** `scripts/generate_repository_results_index.py`,
`scripts/generate_architecture_results_index.py`,
`scripts/generate_typed_evidence_results_index.py`,
`scripts/generate_governance_graph.py`, `scripts/generate_status_viewer.py`,
`generated/viewer/status-viewer.html`, `generated/graph/governance-graph.json`.

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
`scripts/generate_blocking_readiness.py`,
`scripts/generate_blocking_mode_alignment.py`,
`status/application-repository-integrations.yaml`, `model/enforcement/`.

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
Dependency Review aus. Artefakthygiene prüft öffentliche Veröffentlichungsinhalte.

**Ergebnisse:** Intake Health, Betriebsbericht, Sicherheitsassessment und
CI-Sicherheitsbefunde. Nicht verfügbare Informationen bleiben als fehlende
Beobachtbarkeit erkennbar.

**Implementierungsstellen:** `scripts/record_intake_event.py`,
`scripts/generate_intake_health.py`, `scripts/generate_operations_report.py`,
`scripts/assess_governance_repository_security.py`,
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
| Bitbucket und Bamboo | Pipeline- und Adapterunterlagen | Plattformumgebung und Nachweiserzeugung gesondert einrichten |
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
