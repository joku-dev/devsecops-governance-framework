# GCR-2026-166 — Begrenzte optionale Ausführung fachlicher Reviews

## Auftrag und Einordnung

Viertes Paket des Maintainerauftrags vom 13. November 2026. Der neutrale Vertrag
`.agents/execution-contract.yaml` ergänzt die bestehende Reviewplanung um eine
ausdrücklich optionale Ausführung. Provideradapter bleiben Projektionen dieses
Vertrags; Governancezuständigkeiten werden nicht an Codex gebunden.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact type | execution contract, provider adapter, local tooling, tests, guide |
| Target path | `.agents/execution-contract.yaml`, `.agents/providers/codex/`, `scripts/run_agent_reviews.py`, `scripts/lib/agent_execution.py`, harness |
| Owner | Repository maintainer |
| Source Document Intake required? | no |
| Evidence contract impact | private execution traces; existing public receipt unchanged |
| Runtime governance impact | review-only, no approval or remediation authority |
| Release impact | internal agent-system candidate, no baseline release |
| Validation required | pinned full validation, mocked-provider regressions, MkDocs strict |

## Umfang und Abnahmekriterien

- Standardmäßig ausschließlich Vorbereitung privater Aufgaben, ohne Provideraufruf.
  Nur `--execute` startet reale Sessions; in CI wird dies verweigert. Die aktuelle
  Implementierung und ihre Tests benötigen keine Live-Modellaufrufe.
- Sauberer, committeter, vollständig gebundener Branch-Review. Rollen-, Skill-,
  Ausführungsvertrag und vorhandene ausgewählte Codexadapter werden gebunden.
- Lesender Codex-Adapter mit bestehenden Modell-/Efforteinstellungen, ohne
  Genehmigungseskalation, automatischen Modellwechsel oder Wiederholungen.
- Fachreviews standardmäßig seriell; ausdrücklich angeforderte Parallelität
  bleibt auf drei lesende Sessions begrenzt. Steward startet erst nach deren
  Erfolg und erhält die exakten Ergebnisse; Eingabedigests werden aufgezeichnet.
- Fehler, Timeout, ungültige Antworten oder unvollständiger Scope erzeugen keine
  abgeschlossene Prüfung. Lokale Prozessgruppen werden bei Timeout beendet.
  Quelländerungen brechen den Lauf ab und werden niemals zurückgesetzt.
- Private Traces trennen angefordertes Modell von beobachteter Identität;
  fehlende Laufzeitangaben bleiben unbekannt. Tokenzahlen werden nur aus
  tatsächlichen Laufzeitereignissen übernommen. Kein Teststatus wird erfunden.

## Grenzen

Keine Quellen-, Anforderungs-, Waiver-, Release- oder Mergefreigabe und keine
automatische Behebung. Der lesende Sandboxmodus ersetzt keine isolierte
Dateileseberechtigung. Prompts/Antworten bleiben privat; Repositorytext und
andere Agentenantworten werden als Daten behandelt. Das Paket verändert keine
Consumerpins, freigegebenen Baselines oder Fingerprints der Betriebsabnahme.
Die Lieferung dokumentiert ausschließlich deterministische Provider-Fixtures,
keine behauptete Live-Modellbewertung oder unabhängig authentifizierte Ausführung.
