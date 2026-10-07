# GCR-2026-126: Kuratierter semantischer Evaluationskatalog

## Zweck

Der zweite begrenzte semantische Pilot belegte den technischen Datenfluss,
lieferte aber keine Finding-Kandidaten. Dadurch blieben Erkennung bekannter
Fälle, Fehlalarme und Auslassungen unmessbar. Dieser Änderungssatz ergänzt einen
providerneutralen, ausschließlich synthetischen Erwartungskatalog und einen
deterministischen Auswerter.

## Umfang

Der erste Katalog enthält drei bewusst kleine Fälle:

1. einen erwarteten Konflikt mit zwei exakten synthetischen Fundstellen;
2. ein verbotenes Konflikt-Finding für unterschiedliche Security-Aussagen;
3. ein verbotenes Finding, das eine eingebettete Aufforderung als
   Agentenanweisung behandeln würde.

Der Auswerter berücksichtigt nur Findings mit technisch validen Belegen, die
nicht quarantänisiert sind. Ein Report mit anderem Manifest oder anderer
Quellenmenge wird `not_applicable` und nicht als Fehler oder Erfolg gewertet.

## Aussagegrenze

Die Ergebniszahlen gelten nur für die expliziten Katalogfälle. Sie sind keine
allgemeine Recall-, Precision- oder Fehlalarmrate. Reale Anforderungen werden
nicht ohne menschlich bestätigte Erwartung zur Ground Truth. Der bestehende
zweite Live-Pilot bleibt deshalb außerhalb dieses synthetischen Katalogscopes.

## Governance-Auswirkung

- Kein Providerlauf und keine Providerwahl.
- Keine Finding-Bestätigung oder Quellenpromotion.
- Keine Änderung an Controls, Architekturmarkern, OPA oder Baselines.
- Kein neues blockierendes Gate.
- Rollout bleibt `pending`.
