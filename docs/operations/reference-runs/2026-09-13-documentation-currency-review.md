# Dokumentationsprüfung vom 13. September 2026

Geprüfter Ausgangsstand: `8df643db37ec4d6da7196b94aaa77b5e0e0844d8`.
Anlass: vollständige Aktualitätsprüfung und Ergänzung des Funktionsumfangs auf
Wunsch des Maintainers. Einordnung: [GCR-2026-078](../../governance/change-requests/GCR-2026-078-documentation-and-function-audit.md),
erläuternde Dokumentationspflege ohne neue Governance-Vorgabe oder Betriebsfreigabe.

## Umfang und Methode

Alle **366 versionierten Markdown-Dateien** wurden inventarisiert und auf relative
Links, Repository-Pfadverweise und veraltete Status-/Funktionsaussagen durchsucht.
Betroffene aktuelle Aussagen wurden gegen Implementierung, Workflows, Modelle,
angenommene Indizes und die GitHub-Nachweise abgeglichen. Die technische Funktionsliste
deckt **120 Skripte/Module, 19 Workflows und 15 OPA-Module** exakt ab.
Die Prüfung ist keine erneute fachliche Genehmigung jeder historischen Vorgabe.
Originalquellen, GCRs, eingefrorene Releases und datierte Berichte behalten ihre
Aussagen zum jeweiligen Stand. Neue Dokumentationsdateien dieses PRs kommen hinzu.

| Dokumentklasse | Dateien am Ausgangsstand | Behandlung |
|---|---:|---|
| Repository- und Komponenten-Dokumentation | 36 | Inventarisierung und Verweis-/Aktualitätsscan; aktuelle Aussagen abgleichen, historische Bedeutung erhalten |
| Gepflegte Dokumentation, Navigation und Publikationsfassungen | 150 | Inventarisierung und Verweis-/Aktualitätsscan; aktuelle Aussagen abgleichen, historische Bedeutung erhalten |
| Historische Change Requests und Vorlage | 78 | Inventarisierung und Verweis-/Aktualitätsscan; aktuelle Aussagen abgleichen, historische Bedeutung erhalten |
| Governance-Quellen und Platzhalter | 21 | Inventarisierung und Verweis-/Aktualitätsscan; aktuelle Aussagen abgleichen, historische Bedeutung erhalten |
| Datierte Referenzläufe | 12 | Inventarisierung und Verweis-/Aktualitätsscan; aktuelle Aussagen abgleichen, historische Bedeutung erhalten |
| Release-Pakete und Release-Dokumentation | 28 | Inventarisierung und Verweis-/Aktualitätsscan; aktuelle Aussagen abgleichen, historische Bedeutung erhalten |
| Generierte Berichte und historische Ausgaben | 41 | Inventarisierung und Verweis-/Aktualitätsscan; aktuelle Aussagen abgleichen, historische Bedeutung erhalten |

## Ergebnisse und Änderungen

- **Lifecycle:** Aktive begrenzte Betriebsabnahme nach #92/#93 in Plattformstatus,
  Entscheidungsblatt, Plan, Architektur, Katalog, Einstiegseiten und Confluence erläutert.
  Überholte pauschale Aussagen über eine noch ausstehende Live-Abnahme korrigiert.
- **Funktionen:** 21 fachliche Bereiche mit eigenem Lifecycle-Abschnitt; vollständige
  technische Liste einschließlich bisher fehlender CLG-Werkzeuge und Publisher-Umfänge.
- **Betrieb:** Aktuelle Statusseite verknüpft persönliche Erklärung, Capture, Merges,
  Source-Run und zwei reale PASS-Receipts. Beobachtung, Erfassung und Dokumentationsdatum
  werden unterschieden; technische Prüfergebnisse erzeugen keine reale Behebung.
- **Referenzen:** Keine fehlenden relativen Markdown-Dateiziele im Ausgangsbestand.
  Von 38 zunächst auffälligen Inline-Pfaden war ein Releasepfad im Lesekompass falsch;
  er ist korrigiert. Die übrigen bezeichnen Consumer-Dateien, Beispiel-/Ausgabepfade,
  erst bei Bedarf angelegte Verzeichnisse, geplante Pfade oder einen Python-Symbolbezug.
- **Consumer-Demo:** Falsche pauschale Bezeichnung aller Run-IDs als Juli-Evidenz
  korrigiert; angenommene September-Consumer-Ergebnisse und ihre Trust-Grenzen bleiben erhalten.
- **Quellenstrategie:** Verweis auf private Original-DOCX präzisiert; öffentliche
  Platzhalter werden nicht als vorhandene vollständige Originale bezeichnet.
- **Plattformen:** Bitbucket Data Center/Bamboo von Bitbucket Cloud Pipelines getrennt;
  Bamboo 12.1.9 als vorhandene Vorlagenannahme, nicht als bekannte Firmenversion markiert.
  Grundlage: [Atlassian-Vergleich](https://www.atlassian.com/migration/assess/compare-cloud-data-center/bitbucket), geprüft am 13. September 2026.
- **Publishing:** Edition 1.1 bleibt datierte Publikation vom 11. September. Die
  Downloadseiten verweisen auf den aktuellen Katalog und Live-Stand. Ihre JSON-,
  Markdown-, DOCX-, PDF- und PPTX-Inhalte werden nicht unter neuem Datum ausgegeben.
  Es wurde keine neue Binärausgabe oder Veröffentlichung außerhalb des Repositories erstellt.

## Geschützte Abnahme und Historie

Der persönlich abgenommene Leitfaden enthält absichtlich den Vorbereitungsstand
des Antrags. Alle in `model/governance/lifecycle/operating-acceptance/00000001.json`
gebundenen Dateien bleiben bytegleich. Die neue aktuelle Statusseite beschreibt
die spätere Aktivierung, ohne den abgenommenen Antrag umzuschreiben. Ebenso bleiben
Rollen-/Betriebsprofile, Transaktionen, Quellenregister, OPA, Schemas, Consumer-Indizes,
Baseline-Pakete und Publishing-Exportdateien unverändert.
An der Governance-CI oder den Betriebsworkflows wird nichts geändert.

## Validierung

| Prüfung | Ergebnis |
|---|---|
| Gepinnter Bootstrap und vollständige Repository-Validierung | Bestanden; OPA, Runtime, Modelle, Schemas, Berichte und 470 Unit-Tests |
| Demo-Ablauf `scripts/run_demo.py` | Bestanden; grünes Beispiel erfolgreich, rotes Beispiel mit erwarteten Befunden |
| Strikter MkDocs-Build | Bestanden, keine Warnungen oder Fehler |
| Technisches Inventar | Exakte Mengengleichheit aller 154 Skript-/Modul-, Workflow- und OPA-Dateien |
| Relative Markdown-Dateiziele | Alle vorhanden, einschließlich der neu ergänzten Dokumentation |
| LD-07-Implementierungsdigests | Alle unverändert; lokale Projektion wirksam und persönliche Erklärung erneut gegen GitHub bestätigt |
| Quellen, Verträge, Baselines, Evidenz, Publishing-Exporte | Unverändert |
| Generierte Validierungsdateien | 18 ausschließlich zeitstempel-/lokalpfadbedingte Änderungen nach semantischem Vergleich ausgeschlossen |
| Git-Hygiene | `git diff --check` bestanden; lokale Office-Sperrdateien und Eingangsentwurf nicht übernommen |

Der PR liefert den finalen Commit und unabhängige GitHub-CI-Nachweise. Die
Prüfungen erzeugen keinen neuen Consumer-Lauf oder neuen Behebungsnachweis.

## Weiterhin offene Sachverhalte

Live-Waiver, weitere Lifecycle-Consumer und deren Portfolio-Grundgesamtheit,
optionale KI-Unterstützung, Runtime-Release und Bitbucket-Betrieb sind nicht Teil
der begrenzten LD-07-Abnahme. Der echte Pilot hat PASS; reale Fehler-, Behebungs-
und Abschlussentscheidungen sind daher nicht nachgewiesen. Bestehende Consumer-
Befunde, Kandidatenentscheidungen, Retentionsabschluss, produktive Attestierungs-
aussteller und allgemeine organisatorische Betriebsabnahmen werden nicht durch
diese Dokumentationspflege erledigt. Frische wird nicht durch neue Berichtszeitstempel erzeugt.

## Vollständiges Markdown-Inventar am Ausgangsstand

Die folgenden Links sind auf den geprüften Commit festgelegt. Aufnahme in diese
Liste bedeutet Inventarisierung/Scan, keine neue Genehmigung des Dokumentinhalts.

### Repository- und Komponenten-Dokumentation

- [.agents/providers/mistral/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.agents/providers/mistral/README.md)
- [.agents/providers/mistral/governance-agent-dispatch.prompt.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.agents/providers/mistral/governance-agent-dispatch.prompt.md)
- [.agents/providers/mistral/role-execution-contract.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.agents/providers/mistral/role-execution-contract.md)
- [.agents/skills/architecture-runtime-governance/SKILL.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.agents/skills/architecture-runtime-governance/SKILL.md)
- [.agents/skills/demo-readiness/SKILL.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.agents/skills/demo-readiness/SKILL.md)
- [.agents/skills/devsecops-baseline/SKILL.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.agents/skills/devsecops-baseline/SKILL.md)
- [.agents/skills/evidence-and-intake/SKILL.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.agents/skills/evidence-and-intake/SKILL.md)
- [.agents/skills/governance-analysis/SKILL.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.agents/skills/governance-analysis/SKILL.md)
- [.agents/skills/policy-as-code/SKILL.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.agents/skills/policy-as-code/SKILL.md)
- [.agents/skills/release-management/SKILL.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.agents/skills/release-management/SKILL.md)
- [.agents/skills/repo-steward/SKILL.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.agents/skills/repo-steward/SKILL.md)
- [.agents/skills/source-document-intake/SKILL.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.agents/skills/source-document-intake/SKILL.md)
- [.github/codex/prompts/governance-agent-dispatch.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/codex/prompts/governance-agent-dispatch.md)
- [.github/codex/prompts/repo-steward-review.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/codex/prompts/repo-steward-review.md)
- [.github/pull_request_template.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/pull_request_template.md)
- [AGENTS.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/AGENTS.md)
- [LICENSE_AND_PERMISSIONS.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/LICENSE_AND_PERMISSIONS.md)
- [README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/README.md)
- [SECURITY.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/SECURITY.md)
- [adoption-package/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/adoption-package/README.md)
- [adoption-package/checklists/first-adoption-checklist.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/adoption-package/checklists/first-adoption-checklist.md)
- [adoption-package/templates/adoption-decision-record.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/adoption-package/templates/adoption-decision-record.md)
- [demo/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/demo/README.md)
- [demo/sample-service/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/demo/sample-service/README.md)
- [pipeline-baseline/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/pipeline-baseline/README.md)
- [pipeline-baseline/templates/app-architecture-evidence/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/pipeline-baseline/templates/app-architecture-evidence/README.md)
- [pipeline-baseline/templates/bamboo/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/pipeline-baseline/templates/bamboo/README.md)
- [pipeline-baseline/templates/bitbucket/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/pipeline-baseline/templates/bitbucket/README.md)
- [pipeline-baseline/templates/github-actions/ADOPTION.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/pipeline-baseline/templates/github-actions/ADOPTION.md)
- [pipeline-baseline/templates/github-actions/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/pipeline-baseline/templates/github-actions/README.md)
- [pipeline-baseline/templates/jenkins/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/pipeline-baseline/templates/jenkins/README.md)
- [policies/opa/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/README.md)
- [status/collection-attempts/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/status/collection-attempts/README.md)
- [status/evidence-agent-provenance/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/status/evidence-agent-provenance/README.md)
- [status/intake-conflicts/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/status/intake-conflicts/README.md)
- [status/intake-events/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/status/intake-events/README.md)

### Gepflegte Dokumentation, Navigation und Publikationsfassungen

- [docs/ai-index.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/ai-index.md)
- [docs/automation-classification.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/automation-classification.md)
- [docs/controls/index.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/controls/index.md)
- [docs/demos/demo-consumer-typed-evidence-trust.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/demos/demo-consumer-typed-evidence-trust.md)
- [docs/demos/demo-end-to-end-governance.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/demos/demo-end-to-end-governance.md)
- [docs/demos/demo-governance-lifecycle-pilot.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/demos/demo-governance-lifecycle-pilot.md)
- [docs/demos/demo-guide-2026-07-02-ha-cpswms.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/demos/demo-guide-2026-07-02-ha-cpswms.md)
- [docs/demos/demo-ha-cpswms-runtime-governance.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/demos/demo-ha-cpswms-runtime-governance.md)
- [docs/demos/ha-cpswms-architecture-governance-results.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/demos/ha-cpswms-architecture-governance-results.md)
- [docs/demos/presentation-guide-typed-evidence-trust-de.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/demos/presentation-guide-typed-evidence-trust-de.md)
- [docs/examples/artifact-intake-checklist.template.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/examples/artifact-intake-checklist.template.md)
- [docs/examples/artifact-intake-classification.example.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/examples/artifact-intake-classification.example.md)
- [docs/examples/index.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/examples/index.md)
- [docs/foundation/01_VISION.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/foundation/01_VISION.md)
- [docs/foundation/02_CONSTITUTION.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/foundation/02_CONSTITUTION.md)
- [docs/foundation/03_ARCHITECTURE_PRINCIPLES.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/foundation/03_ARCHITECTURE_PRINCIPLES.md)
- [docs/foundation/04_REFERENCE_ARCHITECTURE.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/foundation/04_REFERENCE_ARCHITECTURE.md)
- [docs/foundation/05_CURRENT_DIRECTION.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/foundation/05_CURRENT_DIRECTION.md)
- [docs/foundation/06_KEYNOTE_STORY.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/foundation/06_KEYNOTE_STORY.md)
- [docs/foundation/07_AI_CONTEXT.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/foundation/07_AI_CONTEXT.md)
- [docs/foundation/08_GLOSSARY.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/foundation/08_GLOSSARY.md)
- [docs/governance/MANAGEMENT_READOUT.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/MANAGEMENT_READOUT.md)
- [docs/governance/architecture/ado-devsecops-integrated-governance-model.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/architecture/ado-devsecops-integrated-governance-model.md)
- [docs/governance/architecture/governance-as-code-system-architecture.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/architecture/governance-as-code-system-architecture.md)
- [docs/governance/architecture/governance-repository-architecture-comparison.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/architecture/governance-repository-architecture-comparison.md)
- [docs/governance/architecture/runtime-governance-addendum.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/architecture/runtime-governance-addendum.md)
- [docs/governance/architecture/runtime-governance-transformation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/architecture/runtime-governance-transformation.md)
- [docs/governance/architecture/software-industrialisation-problem-capability-map.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/architecture/software-industrialisation-problem-capability-map.md)
- [docs/governance/devsecops-directive.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/devsecops-directive.md)
- [docs/governance/devsecops-governance-organisational-role-model.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/devsecops-governance-organisational-role-model.md)
- [docs/governance/devsecops-policy.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/devsecops-policy.md)
- [docs/governance/governance-change-lifecycle.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/governance-change-lifecycle.md)
- [docs/governance/governance-document-hierarchy.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/governance-document-hierarchy.md)
- [docs/governance/governance-roles-and-agent-profiles.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/governance-roles-and-agent-profiles.md)
- [docs/governance/operating-model.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/operating-model.md)
- [docs/governance/policy-directive-baseline-verification-and-governance-as-code-explained.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/policy-directive-baseline-verification-and-governance-as-code-explained.md)
- [docs/governance/review-packets/CISO-REQ-SRC-001/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/review-packets/CISO-REQ-SRC-001/README.md)
- [docs/governance/review-packets/CISO-REQ-SRC-001/ciso-review-brief.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/review-packets/CISO-REQ-SRC-001/ciso-review-brief.md)
- [docs/governance/review-packets/CISO-REQ-SRC-001/harmonized-requirements-candidate.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/review-packets/CISO-REQ-SRC-001/harmonized-requirements-candidate.md)
- [docs/governance/source-of-truth.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-of-truth.md)
- [docs/index.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/index.md)
- [docs/lesekompass.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/lesekompass.md)
- [docs/migration-status.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/migration-status.md)
- [docs/official-entrypoints.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/official-entrypoints.md)
- [docs/onboarding/application-repo-onboarding.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/onboarding/application-repo-onboarding.md)
- [docs/onboarding/external-evaluator-guide.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/onboarding/external-evaluator-guide.md)
- [docs/onboarding/external-review-brief.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/onboarding/external-review-brief.md)
- [docs/onboarding/how-other-repos-use-this-governance-repo.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/onboarding/how-other-repos-use-this-governance-repo.md)
- [docs/onboarding/how-other-repositories-use-the-central-governance-baseline.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/onboarding/how-other-repositories-use-the-central-governance-baseline.md)
- [docs/onboarding/pilot-runbook.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/onboarding/pilot-runbook.md)
- [docs/onboarding/public-repo-quickstart.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/onboarding/public-repo-quickstart.md)
- [docs/onboarding/validated-demo-consumer.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/onboarding/validated-demo-consumer.md)
- [docs/operations/adapters/bitbucket-bamboo-governance-adapter.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/adapters/bitbucket-bamboo-governance-adapter.md)
- [docs/operations/adapters/cicd-platform-adapter-strategy.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/adapters/cicd-platform-adapter-strategy.md)
- [docs/operations/adapters/company-bitbucket-bamboo-mistral-target-path.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/adapters/company-bitbucket-bamboo-mistral-target-path.md)
- [docs/operations/adapters/github-reference-path.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/adapters/github-reference-path.md)
- [docs/operations/adapters/github-reference-validation-runbook.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/adapters/github-reference-validation-runbook.md)
- [docs/operations/agents/agent-harness-usage.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/agents/agent-harness-usage.md)
- [docs/operations/agents/agent-system-usage.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/agents/agent-system-usage.md)
- [docs/operations/agents/agent-usage-snapshot-2026-07-06.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/agents/agent-usage-snapshot-2026-07-06.md)
- [docs/operations/agents/agent-usage-snapshot-latest.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/agents/agent-usage-snapshot-latest.md)
- [docs/operations/agents/agent-usage-tracking.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/agents/agent-usage-tracking.md)
- [docs/operations/agents/how-to-run-agent-review.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/agents/how-to-run-agent-review.md)
- [docs/operations/ai-working-rules.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/ai-working-rules.md)
- [docs/operations/evidence/application-repo-architecture-evidence-flow.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/application-repo-architecture-evidence-flow.md)
- [docs/operations/evidence/application-repo-evidence-flow.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/application-repo-evidence-flow.md)
- [docs/operations/evidence/architecture-evidence-ea-decision-brief.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/architecture-evidence-ea-decision-brief.md)
- [docs/operations/evidence/architecture-evidence-ea-package.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/architecture-evidence-ea-package.md)
- [docs/operations/evidence/architecture-evidence-taxonomy-mapping.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/architecture-evidence-taxonomy-mapping.md)
- [docs/operations/evidence/architecture-evidence-type-taxonomy.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/architecture-evidence-type-taxonomy.md)
- [docs/operations/evidence/detailed-architecture-evidence-adoption-guide.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/detailed-architecture-evidence-adoption-guide.md)
- [docs/operations/evidence/evidence-attestation-pilot.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/evidence-attestation-pilot.md)
- [docs/operations/evidence/evidence-collector-contract.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/evidence-collector-contract.md)
- [docs/operations/evidence/evidence-trust-model.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/evidence-trust-model.md)
- [docs/operations/evidence/governance-evidence-contract.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-evidence-contract.md)
- [docs/operations/evidence/governance-evidence-schema-versioning.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-evidence-schema-versioning.md)
- [docs/operations/evidence/governance-lifecycle-action-consent.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-action-consent.md)
- [docs/operations/evidence/governance-lifecycle-closure.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-closure.md)
- [docs/operations/evidence/governance-lifecycle-contract.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-contract.md)
- [docs/operations/evidence/governance-lifecycle-decisions.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-decisions.md)
- [docs/operations/evidence/governance-lifecycle-durable-pilot-intake.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-durable-pilot-intake.md)
- [docs/operations/evidence/governance-lifecycle-exceptions.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-exceptions.md)
- [docs/operations/evidence/governance-lifecycle-input-candidates.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-input-candidates.md)
- [docs/operations/evidence/governance-lifecycle-kernel.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-kernel.md)
- [docs/operations/evidence/governance-lifecycle-live-decision-brief.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-live-decision-brief.md)
- [docs/operations/evidence/governance-lifecycle-live-evidence-preflight.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-live-evidence-preflight.md)
- [docs/operations/evidence/governance-lifecycle-live-operation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-live-operation.md)
- [docs/operations/evidence/governance-lifecycle-live-preparation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-live-preparation.md)
- [docs/operations/evidence/governance-lifecycle-overview.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-overview.md)
- [docs/operations/evidence/governance-lifecycle-personal-channel.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-personal-channel.md)
- [docs/operations/evidence/governance-lifecycle-pilot-decisions.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-pilot-decisions.md)
- [docs/operations/evidence/governance-lifecycle-viewer.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-lifecycle-viewer.md)
- [docs/operations/evidence/governance-result-intake-and-viewer-usage.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-result-intake-and-viewer-usage.md)
- [docs/operations/evidence/governance-results-storage-model.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/governance-results-storage-model.md)
- [docs/operations/evidence/how-to-read-control-evaluation-status.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/how-to-read-control-evaluation-status.md)
- [docs/operations/evidence/intake-health-projection.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/intake-health-projection.md)
- [docs/operations/evidence/intake-operation-telemetry.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/intake-operation-telemetry.md)
- [docs/operations/evidence/replay-triage.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/replay-triage.md)
- [docs/operations/evidence/vulnerability-scan-collector-usage.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/evidence/vulnerability-scan-collector-usage.md)
- [docs/operations/guides/beginner-step-by-step-operations-guide.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/guides/beginner-step-by-step-operations-guide.md)
- [docs/operations/guides/evidence-and-governance-hardening-guide.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/guides/evidence-and-governance-hardening-guide.md)
- [docs/operations/guides/governance-repository-operations-handbook.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/guides/governance-repository-operations-handbook.md)
- [docs/operations/guides/how-to-add-a-new-artifact.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/guides/how-to-add-a-new-artifact.md)
- [docs/operations/guides/how-to-update-baseline-input-documents.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/guides/how-to-update-baseline-input-documents.md)
- [docs/operations/guides/how-to-use-this-repo.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/guides/how-to-use-this-repo.md)
- [docs/operations/guides/index.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/guides/index.md)
- [docs/operations/guides/local-validation-toolchain.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/guides/local-validation-toolchain.md)
- [docs/operations/guides/mkdocs-and-github-pages-step-by-step.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/guides/mkdocs-and-github-pages-step-by-step.md)
- [docs/operations/guides/repository-function-catalog.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/guides/repository-function-catalog.md)
- [docs/operations/planning/closed-loop-governance-implementation-plan.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/planning/closed-loop-governance-implementation-plan.md)
- [docs/operations/planning/document-structure-audit.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/planning/document-structure-audit.md)
- [docs/operations/planning/document-structure-model.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/planning/document-structure-model.md)
- [docs/operations/planning/replace-governance-placeholders-plan.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/planning/replace-governance-placeholders-plan.md)
- [docs/operations/planning/repository-target-structure-and-migration-plan.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/planning/repository-target-structure-and-migration-plan.md)
- [docs/operations/processes/application-repo-governance-timing.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/processes/application-repo-governance-timing.md)
- [docs/operations/processes/blocking-enforcement-migration-guide.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/processes/blocking-enforcement-migration-guide.md)
- [docs/operations/processes/governance-repository-backup-and-recovery.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/processes/governance-repository-backup-and-recovery.md)
- [docs/operations/processes/index.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/processes/index.md)
- [docs/operations/processes/new-artifact-intake-process.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/processes/new-artifact-intake-process.md)
- [docs/operations/processes/operational-governance-enforcement-options.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/processes/operational-governance-enforcement-options.md)
- [docs/operations/processes/source-document-intake-process.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/processes/source-document-intake-process.md)
- [docs/operations/processes/source-document-intake-review-operating-model.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/processes/source-document-intake-review-operating-model.md)
- [docs/operations/processes/spot-check-governance-intake.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/processes/spot-check-governance-intake.md)
- [docs/operations/processes/waiver-management-standard.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/processes/waiver-management-standard.md)
- [docs/operations/security/github-access-and-token-maintenance.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/security/github-access-and-token-maintenance.md)
- [docs/operations/security/governance-repository-self-security.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/security/governance-repository-self-security.md)
- [docs/operations/status/blocking-mode-alignment.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/status/blocking-mode-alignment.md)
- [docs/operations/status/blocking-readiness.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/status/blocking-readiness.md)
- [docs/operations/status/current-governance-platform-state.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/status/current-governance-platform-state.md)
- [docs/operations/status/daily-governance-operations.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/status/daily-governance-operations.md)
- [docs/operations/status/governance-intelligence-graph-viewer.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/status/governance-intelligence-graph-viewer.md)
- [docs/operations/status/ha-cpswms-governance-lessons-learned.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/status/ha-cpswms-governance-lessons-learned.md)
- [docs/operations/status/ha-cpswms-governance-validation-status.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/status/ha-cpswms-governance-validation-status.md)
- [docs/operations/status/multi-consumer-readiness.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/status/multi-consumer-readiness.md)
- [docs/operations/status/portfolio-adoption-reporting.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/status/portfolio-adoption-reporting.md)
- [docs/paths/auditor-path.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/paths/auditor-path.md)
- [docs/paths/beginner-path.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/paths/beginner-path.md)
- [docs/paths/index.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/paths/index.md)
- [docs/paths/maintainer-path.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/paths/maintainer-path.md)
- [docs/paths/operator-path.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/paths/operator-path.md)
- [docs/pipeline-baseline/index.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/pipeline-baseline/index.md)
- [docs/platform/control-baseline-and-platform-architecture-relationship-explained.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/platform/control-baseline-and-platform-architecture-relationship-explained.md)
- [docs/publishing/confluence-governance-repo-artikel.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/publishing/confluence-governance-repo-artikel.md)
- [docs/publishing/executive-briefing/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/publishing/executive-briefing/README.md)
- [docs/publishing/executive-briefing/presentation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/publishing/executive-briefing/presentation.md)
- [docs/publishing/executive-briefing/whitepaper.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/publishing/executive-briefing/whitepaper.md)
- [docs/publishing/index.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/publishing/index.md)
- [docs/publishing/repository-walkthrough/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/publishing/repository-walkthrough/README.md)
- [docs/publishing/repository-walkthrough/presentation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/publishing/repository-walkthrough/presentation.md)
- [docs/roadmap.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/roadmap.md)

### Historische Change Requests und Vorlage

- [docs/governance/change-requests/GCR-2026-001-architecture-source-candidates.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-001-architecture-source-candidates.md)
- [docs/governance/change-requests/GCR-2026-002-ado-devsecops-integrated-governance-model.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-002-ado-devsecops-integrated-governance-model.md)
- [docs/governance/change-requests/GCR-2026-003-devsecops-organisational-role-model.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-003-devsecops-organisational-role-model.md)
- [docs/governance/change-requests/GCR-2026-004-bamboo-12-1-9-adapter.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-004-bamboo-12-1-9-adapter.md)
- [docs/governance/change-requests/GCR-2026-005-source-document-intake-review-operating-model.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-005-source-document-intake-review-operating-model.md)
- [docs/governance/change-requests/GCR-2026-006-software-industrialisation-capability-map.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-006-software-industrialisation-capability-map.md)
- [docs/governance/change-requests/GCR-2026-007-governance-repository-architecture-comparison.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-007-governance-repository-architecture-comparison.md)
- [docs/governance/change-requests/GCR-2026-008-document-structure-model.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-008-document-structure-model.md)
- [docs/governance/change-requests/GCR-2026-009-agent-operations-documentation-migration.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-009-agent-operations-documentation-migration.md)
- [docs/governance/change-requests/GCR-2026-010-evidence-operations-documentation-migration.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-010-evidence-operations-documentation-migration.md)
- [docs/governance/change-requests/GCR-2026-011-platform-adapter-documentation-migration.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-011-platform-adapter-documentation-migration.md)
- [docs/governance/change-requests/GCR-2026-012-demo-documentation-migration.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-012-demo-documentation-migration.md)
- [docs/governance/change-requests/GCR-2026-013-governance-architecture-documentation-migration.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-013-governance-architecture-documentation-migration.md)
- [docs/governance/change-requests/GCR-2026-014-runtime-governance-documentation-migration.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-014-runtime-governance-documentation-migration.md)
- [docs/governance/change-requests/GCR-2026-015-document-structure-audit.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-015-document-structure-audit.md)
- [docs/governance/change-requests/GCR-2026-016-mkdocs-validation-confirmation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-016-mkdocs-validation-confirmation.md)
- [docs/governance/change-requests/GCR-2026-017-status-documentation-migration.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-017-status-documentation-migration.md)
- [docs/governance/change-requests/GCR-2026-018-planning-documentation-migration.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-018-planning-documentation-migration.md)
- [docs/governance/change-requests/GCR-2026-019-examples-documentation-migration.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-019-examples-documentation-migration.md)
- [docs/governance/change-requests/GCR-2026-020-publishing-documentation-migration.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-020-publishing-documentation-migration.md)
- [docs/governance/change-requests/GCR-2026-021-operations-guides-documentation-migration.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-021-operations-guides-documentation-migration.md)
- [docs/governance/change-requests/GCR-2026-022-operations-process-documentation-migration.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-022-operations-process-documentation-migration.md)
- [docs/governance/change-requests/GCR-2026-023-new-artifact-intake-preparation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-023-new-artifact-intake-preparation.md)
- [docs/governance/change-requests/GCR-2026-024-artifact-intake-examples.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-024-artifact-intake-examples.md)
- [docs/governance/change-requests/GCR-2026-025-how-to-add-new-artifact-guide.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-025-how-to-add-new-artifact-guide.md)
- [docs/governance/change-requests/GCR-2026-026-evidence-trust-model.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-026-evidence-trust-model.md)
- [docs/governance/change-requests/GCR-2026-027-evidence-trust-additive-capture.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-027-evidence-trust-additive-capture.md)
- [docs/governance/change-requests/GCR-2026-028-evidence-trust-verification-projection.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-028-evidence-trust-verification-projection.md)
- [docs/governance/change-requests/GCR-2026-029-provisional-evidence-freshness-policies.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-029-provisional-evidence-freshness-policies.md)
- [docs/governance/change-requests/GCR-2026-030-evidence-collector-contract.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-030-evidence-collector-contract.md)
- [docs/governance/change-requests/GCR-2026-031-vulnerability-scan-collector-pilot.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-031-vulnerability-scan-collector-pilot.md)
- [docs/governance/change-requests/GCR-2026-032-typed-evidence-trust-viewer-projection.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-032-typed-evidence-trust-viewer-projection.md)
- [docs/governance/change-requests/GCR-2026-033-governance-intelligence-graph-viewer.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-033-governance-intelligence-graph-viewer.md)
- [docs/governance/change-requests/GCR-2026-034-evidence-ledger-hardening.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-034-evidence-ledger-hardening.md)
- [docs/governance/change-requests/GCR-2026-035-governance-as-code-system-architecture.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-035-governance-as-code-system-architecture.md)
- [docs/governance/change-requests/GCR-2026-036-intake-operation-telemetry.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-036-intake-operation-telemetry.md)
- [docs/governance/change-requests/GCR-2026-037-legacy-artifact-digest-compatibility.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-037-legacy-artifact-digest-compatibility.md)
- [docs/governance/change-requests/GCR-2026-038-intake-health-projection.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-038-intake-health-projection.md)
- [docs/governance/change-requests/GCR-2026-039-intake-health-viewer.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-039-intake-health-viewer.md)
- [docs/governance/change-requests/GCR-2026-040-multi-consumer-readiness.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-040-multi-consumer-readiness.md)
- [docs/governance/change-requests/GCR-2026-041-evidence-attestation-pilot.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-041-evidence-attestation-pilot.md)
- [docs/governance/change-requests/GCR-2026-042-blocking-readiness.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-042-blocking-readiness.md)
- [docs/governance/change-requests/GCR-2026-043-blocking-mode-alignment.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-043-blocking-mode-alignment.md)
- [docs/governance/change-requests/GCR-2026-044-replay-triage.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-044-replay-triage.md)
- [docs/governance/change-requests/GCR-2026-045-replay-triage-intake-integration.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-045-replay-triage-intake-integration.md)
- [docs/governance/change-requests/GCR-2026-046-replay-remediation-state.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-046-replay-remediation-state.md)
- [docs/governance/change-requests/GCR-2026-047-harmonized-requirements-candidate.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-047-harmonized-requirements-candidate.md)
- [docs/governance/change-requests/GCR-2026-048-governance-repository-self-security.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-048-governance-repository-self-security.md)
- [docs/governance/change-requests/GCR-2026-049-current-governance-security-report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-049-current-governance-security-report.md)
- [docs/governance/change-requests/GCR-2026-050-blocking-risk-review-extension.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-050-blocking-risk-review-extension.md)
- [docs/governance/change-requests/GCR-2026-051-reviewed-operational-writes-and-main-protection.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-051-reviewed-operational-writes-and-main-protection.md)
- [docs/governance/change-requests/GCR-2026-052-daily-governance-operations-report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-052-daily-governance-operations-report.md)
- [docs/governance/change-requests/GCR-2026-053-consistent-pilot-and-operations-documentation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-053-consistent-pilot-and-operations-documentation.md)
- [docs/governance/change-requests/GCR-2026-054-executive-whitepaper-and-presentation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-054-executive-whitepaper-and-presentation.md)
- [docs/governance/change-requests/GCR-2026-055-repository-function-presentation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-055-repository-function-presentation.md)
- [docs/governance/change-requests/GCR-2026-056-detailed-function-catalog.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-056-detailed-function-catalog.md)
- [docs/governance/change-requests/GCR-2026-057-september-operational-evidence-refresh.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-057-september-operational-evidence-refresh.md)
- [docs/governance/change-requests/GCR-2026-058-current-documentation-refresh.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-058-current-documentation-refresh.md)
- [docs/governance/change-requests/GCR-2026-059-operational-pilot-release.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-059-operational-pilot-release.md)
- [docs/governance/change-requests/GCR-2026-060-closed-loop-governance-plan.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-060-closed-loop-governance-plan.md)
- [docs/governance/change-requests/GCR-2026-061-codex-agent-model-upgrade.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-061-codex-agent-model-upgrade.md)
- [docs/governance/change-requests/GCR-2026-062-governance-lifecycle-contracts.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-062-governance-lifecycle-contracts.md)
- [docs/governance/change-requests/GCR-2026-063-governance-lifecycle-kernel.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-063-governance-lifecycle-kernel.md)
- [docs/governance/change-requests/GCR-2026-064-governance-lifecycle-decisions.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-064-governance-lifecycle-decisions.md)
- [docs/governance/change-requests/GCR-2026-065-governance-lifecycle-closure.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-065-governance-lifecycle-closure.md)
- [docs/governance/change-requests/GCR-2026-066-governance-lifecycle-exceptions.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-066-governance-lifecycle-exceptions.md)
- [docs/governance/change-requests/GCR-2026-067-governance-lifecycle-metrics.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-067-governance-lifecycle-metrics.md)
- [docs/governance/change-requests/GCR-2026-068-governance-lifecycle-viewer.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-068-governance-lifecycle-viewer.md)
- [docs/governance/change-requests/GCR-2026-069-lifecycle-devsecops-candidates.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-069-lifecycle-devsecops-candidates.md)
- [docs/governance/change-requests/GCR-2026-070-lifecycle-architecture-candidates.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-070-lifecycle-architecture-candidates.md)
- [docs/governance/change-requests/GCR-2026-071-lifecycle-live-pilot-roles.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-071-lifecycle-live-pilot-roles.md)
- [docs/governance/change-requests/GCR-2026-072-lifecycle-live-evidence-preflight.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-072-lifecycle-live-evidence-preflight.md)
- [docs/governance/change-requests/GCR-2026-073-lifecycle-durable-pilot-intake.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-073-lifecycle-durable-pilot-intake.md)
- [docs/governance/change-requests/GCR-2026-074-lifecycle-personal-channel-probe.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-074-lifecycle-personal-channel-probe.md)
- [docs/governance/change-requests/GCR-2026-075-personal-channel-confirmation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-075-personal-channel-confirmation.md)
- [docs/governance/change-requests/GCR-2026-076-lifecycle-action-consent.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-076-lifecycle-action-consent.md)
- [docs/governance/change-requests/GCR-2026-077-lifecycle-operating-acceptance.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/GCR-2026-077-lifecycle-operating-acceptance.md)
- [docs/governance/change-requests/TEMPLATE.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/change-requests/TEMPLATE.md)

### Governance-Quellen und Platzhalter

- [docs/governance/source-documents/ARCH-EA-SRC-001.public.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/ARCH-EA-SRC-001.public.md)
- [docs/governance/source-documents/ARCH-EA-SRC-001.requirements.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/ARCH-EA-SRC-001.requirements.md)
- [docs/governance/source-documents/ARCH-GOV-SRC-002.public.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/ARCH-GOV-SRC-002.public.md)
- [docs/governance/source-documents/ARCH-GOV-SRC-002.requirements.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/ARCH-GOV-SRC-002.requirements.md)
- [docs/governance/source-documents/ARCH-PA-SRC-001.public.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/ARCH-PA-SRC-001.public.md)
- [docs/governance/source-documents/ARCH-PA-SRC-001.requirements.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/ARCH-PA-SRC-001.requirements.md)
- [docs/governance/source-documents/ARCH-SA-SRC-001.public.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/ARCH-SA-SRC-001.public.md)
- [docs/governance/source-documents/ARCH-SA-SRC-001.requirements.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/ARCH-SA-SRC-001.requirements.md)
- [docs/governance/source-documents/ARCH-SDD-SRC-001.public.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/ARCH-SDD-SRC-001.public.md)
- [docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md)
- [docs/governance/source-documents/ARCH-TPL-SRC-001.public.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/ARCH-TPL-SRC-001.public.md)
- [docs/governance/source-documents/ARCH-TPL-SRC-001.requirements.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/ARCH-TPL-SRC-001.requirements.md)
- [docs/governance/source-documents/CISO-REQ-SRC-001.public.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/CISO-REQ-SRC-001.public.md)
- [docs/governance/source-documents/DEVSECOPS-DIR-SRC-001.public.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/DEVSECOPS-DIR-SRC-001.public.md)
- [docs/governance/source-documents/DEVSECOPS-DIR-SRC-001.requirements.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/DEVSECOPS-DIR-SRC-001.requirements.md)
- [docs/governance/source-documents/DEVSECOPS-POL-SRC-001.public.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/DEVSECOPS-POL-SRC-001.public.md)
- [docs/governance/source-documents/DEVSECOPS-POL-SRC-001.requirements.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/DEVSECOPS-POL-SRC-001.requirements.md)
- [docs/governance/source-documents/DSCB-STD-SRC-001.public.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/DSCB-STD-SRC-001.public.md)
- [docs/governance/source-documents/DSCB-STD-SRC-001.requirements.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/DSCB-STD-SRC-001.requirements.md)
- [docs/governance/source-documents/PRA-STD-SRC-001.public.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/PRA-STD-SRC-001.public.md)
- [docs/governance/source-documents/PRA-STD-SRC-001.requirements.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/governance/source-documents/PRA-STD-SRC-001.requirements.md)

### Datierte Referenzläufe

- [docs/operations/reference-runs/2026-07-04-ha-cpswms-github-reference-run.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/reference-runs/2026-07-04-ha-cpswms-github-reference-run.md)
- [docs/operations/reference-runs/2026-07-06-agent-system-dispatch-reference-run.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/reference-runs/2026-07-06-agent-system-dispatch-reference-run.md)
- [docs/operations/reference-runs/2026-07-06-architecture-findings-reference-run.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/reference-runs/2026-07-06-architecture-findings-reference-run.md)
- [docs/operations/reference-runs/2026-07-06-codex-multi-agent-platform-adapter-review.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/reference-runs/2026-07-06-codex-multi-agent-platform-adapter-review.md)
- [docs/operations/reference-runs/2026-07-06-codex-provider-agent-review-pr12.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/reference-runs/2026-07-06-codex-provider-agent-review-pr12.md)
- [docs/operations/reference-runs/2026-07-06-codex-provider-detailed-evidence-review.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/reference-runs/2026-07-06-codex-provider-detailed-evidence-review.md)
- [docs/operations/reference-runs/2026-07-06-detailed-architecture-evidence-reference-run.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/reference-runs/2026-07-06-detailed-architecture-evidence-reference-run.md)
- [docs/operations/reference-runs/2026-09-11-documentation-currency-review.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/reference-runs/2026-09-11-documentation-currency-review.md)
- [docs/operations/reference-runs/2026-09-11-operational-evidence-refresh.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/reference-runs/2026-09-11-operational-evidence-refresh.md)
- [docs/operations/reference-runs/2026-09-12-gpt6-agent-evaluation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/reference-runs/2026-09-12-gpt6-agent-evaluation.md)
- [docs/operations/reference-runs/2026-09-13-clg-live-evidence-preflight.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/reference-runs/2026-09-13-clg-live-evidence-preflight.md)
- [docs/operations/reference-runs/2026-09-13-clg04-live-observation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/operations/reference-runs/2026-09-13-clg04-live-observation.md)

### Release-Pakete und Release-Dokumentation

- [docs/releases/architecture-baseline-l1-v0.1.0-release-statement.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/architecture-baseline-l1-v0.1.0-release-statement.md)
- [docs/releases/architecture-baseline-l1-v0.1.0.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/architecture-baseline-l1-v0.1.0.md)
- [docs/releases/index.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/index.md)
- [docs/releases/l1-baseline-v1.0.0-release-statement.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/l1-baseline-v1.0.0-release-statement.md)
- [docs/releases/l1-baseline-v1.0.0.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/l1-baseline-v1.0.0.md)
- [docs/releases/l1-baseline-v1.1.0-release-statement.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/l1-baseline-v1.1.0-release-statement.md)
- [docs/releases/l1-baseline-v1.1.0.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/l1-baseline-v1.1.0.md)
- [docs/releases/l1-baseline-v1.1.1-release-statement.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/l1-baseline-v1.1.1-release-statement.md)
- [docs/releases/l1-baseline-v1.1.1.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/l1-baseline-v1.1.1.md)
- [docs/releases/l1-baseline-v1.1.2-release-statement.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/l1-baseline-v1.1.2-release-statement.md)
- [docs/releases/l1-baseline-v1.1.2.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/l1-baseline-v1.1.2.md)
- [docs/releases/l1-baseline-v1.1.3-release-statement.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/l1-baseline-v1.1.3-release-statement.md)
- [docs/releases/l1-baseline-v1.1.3.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/l1-baseline-v1.1.3.md)
- [docs/releases/release-and-migration-model.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/release-and-migration-model.md)
- [docs/releases/release-publication-checklist.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/release-publication-checklist.md)
- [docs/releases/v0.1.0-public-adoption.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/v0.1.0-public-adoption.md)
- [docs/releases/v0.2.0-public-adoption.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/docs/releases/v0.2.0-public-adoption.md)
- [releases/architecture/l1/v0.1.0/baseline-package.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/releases/architecture/l1/v0.1.0/baseline-package.md)
- [releases/l1/v1.0.0/baseline-package.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/releases/l1/v1.0.0/baseline-package.md)
- [releases/l1/v1.0.0/source/policies/opa/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/releases/l1/v1.0.0/source/policies/opa/README.md)
- [releases/l1/v1.1.0/baseline-package.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/releases/l1/v1.1.0/baseline-package.md)
- [releases/l1/v1.1.0/source/policies/opa/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/releases/l1/v1.1.0/source/policies/opa/README.md)
- [releases/l1/v1.1.1/baseline-package.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/releases/l1/v1.1.1/baseline-package.md)
- [releases/l1/v1.1.1/source/policies/opa/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/releases/l1/v1.1.1/source/policies/opa/README.md)
- [releases/l1/v1.1.2/baseline-package.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/releases/l1/v1.1.2/baseline-package.md)
- [releases/l1/v1.1.2/source/policies/opa/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/releases/l1/v1.1.2/source/policies/opa/README.md)
- [releases/l1/v1.1.3/baseline-package.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/releases/l1/v1.1.3/baseline-package.md)
- [releases/l1/v1.1.3/source/policies/opa/README.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/releases/l1/v1.1.3/source/policies/opa/README.md)

### Generierte Berichte und historische Ausgaben

- [generated/control-evaluation-report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/control-evaluation-report.md)
- [generated/current-main/ha-cpswms/architecture-governance-report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/current-main/ha-cpswms/architecture-governance-report.md)
- [generated/current-main/ha-cpswms/devsecops-governance-report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/current-main/ha-cpswms/devsecops-governance-report.md)
- [generated/current-main/ha-cpswms/end-to-end-governance-report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/current-main/ha-cpswms/end-to-end-governance-report.md)
- [generated/demo/demo-run.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/demo/demo-run.md)
- [generated/demo/green-control-evaluation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/demo/green-control-evaluation.md)
- [generated/demo/green-summary.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/demo/green-summary.md)
- [generated/demo/ha-cpswms-architecture-governance-report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/demo/ha-cpswms-architecture-governance-report.md)
- [generated/demo/ha-cpswms-devsecops-governance-report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/demo/ha-cpswms-devsecops-governance-report.md)
- [generated/demo/ha-cpswms-end-to-end-governance-report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/demo/ha-cpswms-end-to-end-governance-report.md)
- [generated/demo/red-control-evaluation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/demo/red-control-evaluation.md)
- [generated/demo/red-summary.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/demo/red-summary.md)
- [generated/documents/devsecops-dir-001.rendered.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/documents/devsecops-dir-001.rendered.md)
- [generated/documents/devsecops-pol-001.rendered.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/documents/devsecops-pol-001.rendered.md)
- [generated/html/automation_report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/html/automation_report.md)
- [generated/html/pipeline_baseline_report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/html/pipeline_baseline_report.md)
- [generated/reports/ai-native-engineering-factory-onboarding-readiness.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/ai-native-engineering-factory-onboarding-readiness.md)
- [generated/reports/architecture-source-replacement-assessment.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/architecture-source-replacement-assessment.md)
- [generated/reports/control-coverage-report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/control-coverage-report.md)
- [generated/reports/document-control-matrix.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/document-control-matrix.md)
- [generated/reports/governance-change-impact.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/governance-change-impact.md)
- [generated/reports/governance-lifecycle-exceptions.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/governance-lifecycle-exceptions.md)
- [generated/reports/governance-lifecycle-live-validation.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/governance-lifecycle-live-validation.md)
- [generated/reports/governance-lifecycle-live.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/governance-lifecycle-live.md)
- [generated/reports/governance-lifecycle-overview.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/governance-lifecycle-overview.md)
- [generated/reports/governance-lifecycle-pilot-actions.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/governance-lifecycle-pilot-actions.md)
- [generated/reports/governance-lifecycle-pilot.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/governance-lifecycle-pilot.md)
- [generated/reports/governance-repository-security.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/governance-repository-security.md)
- [generated/reports/harmonized-requirements-coverage.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/harmonized-requirements-coverage.md)
- [generated/reports/harmonized-requirements-maturity.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/harmonized-requirements-maturity.md)
- [generated/reports/lifecycle-operating-acceptance-statement.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/lifecycle-operating-acceptance-statement.md)
- [generated/reports/lifecycle-personal-channel-evidence.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/lifecycle-personal-channel-evidence.md)
- [generated/reports/lifecycle-personal-channel-statement.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/lifecycle-personal-channel-statement.md)
- [generated/reports/multi-consumer-readiness.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/multi-consumer-readiness.md)
- [generated/reports/open-gap-report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/open-gap-report.md)
- [generated/reports/portfolio-onboarding-status.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/portfolio-onboarding-status.md)
- [generated/reports/replay-triage.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/replay-triage.md)
- [generated/reports/source-document-intake-review-briefs.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/source-document-intake-review-briefs.md)
- [generated/reports/source-document-intake-status.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/source-document-intake-status.md)
- [generated/reports/source-document-requirement-delta.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/source-document-requirement-delta.md)
- [generated/reports/source-lineage-report.md](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/generated/reports/source-lineage-report.md)
