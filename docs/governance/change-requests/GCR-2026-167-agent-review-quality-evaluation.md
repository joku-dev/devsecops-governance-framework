# GCR-2026-167 — Reproduzierbare Offlinebewertung von Agentenreviews

## Auftrag und Einordnung

Fünftes Paket des Maintainerauftrags vom 13. November 2026. Zehn synthetische,
versionierte Fälle und eine strukturierte Rubrik bereiten spätere, gesondert
beauftragte Modellvergleiche vor. Dieses Paket führt selbst keine Modelle aus
und verändert weder die neun vorhandenen Modellkonfigurationen noch die
Governancezuständigkeiten.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact type | synthetic evaluation examples/rubric, offline tooling, tests, guide |
| Target path | `.agents/evaluations/`, `scripts/evaluate_agent_reviews.py`, `scripts/lib/agent_evaluation.py`, harness |
| Owner | Repository maintainer |
| Source Document Intake required? | no; labels restate existing repository boundaries |
| Evidence contract impact | none; optional private, case-bound runtime metadata |
| Runtime governance impact | none; offline evaluation only |
| Release impact | internal agent-system candidate, no baseline release |
| Validation required | pinned full validation, rubric/CLI/privacy regressions, MkDocs strict |

## Umfang und Abnahmekriterien

- Acht bekannte Fehlerfälle und zwei gutartige Gegenbeispiele für Kandidaten,
  Baselineintegrität, Blocking, PR-Evidenz, veraltete Reviews, Ausführungsangaben,
  private Texte und überzogene CI-/Complianceaussagen.
- Private Vorbereitung von Prompt-/Antwortschemapaketen, ohne Goldlabels in den
  Providerpaketen. Rollen-/Skillrevisionen und Datensatzdigest sind gebunden.
- Offlineauswertung mit erkannten/übersehenen Findings, Fehlalarmen,
  Schweregradtreffern und Release-/Enforcement-/Kontextklassifikation.
  Fehlende oder ungültige Antworten reduzieren die sichtbare Abdeckung;
  unbekannte/doppelte Fälle und fremde Datensatzrevisionen werden abgewiesen.
- Zeit-/Tokenangaben nur aus mitgelieferten, digestgeprüften Laufzeitdatensätzen
  mit exaktem Fall, Datensatzrevision und unterschiedlicher Laufkennung.
  Fehlende Messungen bleiben unbekannt; Gesamtwerte erfordern volle Messabdeckung.
  Cached Input wird getrennt ausgewiesen, nicht zum Input addiert.
- Keine rohen Antworten oder Begründungen im Ergebnisbericht. Externe private
  Ausgaben werden exklusiv angelegt und überschreiben keine anderen Läufe.

## Grenzen und Prüfung

Strukturierte Labels bewerten keine allgemeine Argumentationsqualität oder
Modellüberlegenheit. Gründe, Evidenzbezug, Laufzeitauthentizität und Varianz
benötigen separate Bewertung. Test-Goldantworten und synthetische Traces sind
ausschließlich Regressionen, keine veröffentlichten Live-Benchmark-Ergebnisse.
Es gibt keine automatischen Provideraufrufe oder neuen Modellkosten und keine
Änderung von Consumerergebnissen, Trust, Baselines oder Abnahmefingerprints.
Der gemeinsame private Dateischreiber wird ohne Abhängigkeit des Graders vom
Codexadapter wiederverwendet. Konkrete Lieferung und Rollenprüfungen stehen im PR.
