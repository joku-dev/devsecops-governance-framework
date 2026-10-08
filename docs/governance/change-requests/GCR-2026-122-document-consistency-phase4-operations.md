# GCR-2026-122: Providerneutrale Phase-4-Betriebsinfrastruktur

## Anfrage und Einordnung

Implementiere nach der angenommenen Phase 3 die unabhängig von vertraulichen
Originalen und einem Live-Provider mögliche Phase-4-Infrastruktur. Rollout und
fachliche Pilotbewertung bleiben ausstehend.

| Feld | Wert |
| --- | --- |
| Änderungstyp | additive Betriebs-, Schema- und Evidence-Infrastruktur |
| Enforcement | report-only; keine neue blockierende Inhaltsregel |
| Quellen | bestehende registrierte Pilot-Auszüge und synthetische Fixtures |
| Provider / Modell | nicht konfiguriert; kein Aufruf |
| Lokale Zusatzdateien | ausgeschlossen, nicht gelesen oder übertragen |
| Rollout | `pending` |
| Veröffentlichung | nicht autorisiert |
| Release-/Baseline-Auswirkung | keine |

## Gelieferter Umfang

- Schema-validierte Finding-Kontinuität mit `new`, `unchanged`, `worsened`,
  `resolved`, `reopened` und `not_reassessed`.
- Scope-begrenzte Triage mit bestehenden Rollenwegen, Priorität, Entscheidung,
  nächster Aktion, optionalem Termin und Eskalationsroute.
- Maschinenlesbare Trigger-/Scope-Matrix für Quellen-, Beziehungs-, Autoritäts-,
  Implementierungs- und Methodikänderungen.
- Versionierte Candidate-Reviewer-Konfiguration mit dokumentiertem Rollback und
  ausstehendem Livevergleich.
- Hash-gebundenes, ausdrücklich unvollständiges Candidate-Paket.
- Maschinenlesbare Rolloutentscheidung `pending` mit Voraussetzungen und
  verbotenen Aussagen.
- Zentraler Validator, Repository-Validierungsintegration und synthetische
  Negativtests.

## Governance-Auswirkung

Die Änderung ist nicht normativ. Sie verändert keine Quelle, keinen
Registerstatus, Control, Architekturmarker, OPA-Entscheidung, Release-Baseline,
Statusindex oder Consumer-Schnittstelle. Rollen im Betriebsmodell sind
Review-Routing und keine persönlichen Ernennungen. Die Themenautorität bleibt
unbestätigt und erzeugt keine automatische Vorrangregel.

Das Candidate-Paket ist von einer Governance-Baseline getrennt. Technische
Schema- und Hashprüfung verleiht weder fachliche Akzeptanz noch normative
Freigabe. Da der semantische Bericht `not_run` ist, kann noch kein vollständiger
Review-Ausgangsstand festgeschrieben werden.

## Offene Entscheidungen

- zugelassener Provider, exakte Modellkennung und Parameter;
- Datenfluss, Aufbewahrung und zulässige Zitate;
- konkrete menschliche Reviewer und bestätigte Themenautorität;
- realer Pilot, bekannte Fehlalarme und übersehene Fälle;
- Triage-Aufwand, Laufzeit und Kosten;
- vollständiger registrierter und freigegebener Quellumfang;
- Rollout und etwaige spätere Veröffentlichung.

## Abnahmematrix

| Kriterium | Status | Nachweis / Grenze |
| --- | --- | --- |
| Finding-Kontinuität und Wiederöffnung | `pass` | Schema, Klassifikator und synthetische Tests |
| Nicht erneut geprüft wird nicht gelöst | `pass` | `not_reassessed`-Negativtest |
| Scope-begrenzte Triage | `pass` | synthetischer Fehlalarm mit Scope und Begründung |
| Trigger-/Scope-Matrix | `pass` | inkrementell, full, Methodik und unbekannter Trigger getestet |
| Reviewer-Konfiguration und Rollback | `pass` | Candidate-Konfiguration, Provider `not_configured` |
| Hash-gebundenes Candidate-Paket | `pass` | Referenz- und Manipulationstest |
| Vollständiger realer Review-Ausgangsstand | `blocked` | realer semantischer Pilot fehlt |
| Menschliche Pilotbewertung | `not_run` | keine echten Findings oder Reviewerentscheidung |
| Rolloutentscheidung | `pending` | Voraussetzungen maschinenlesbar offen |
| Veröffentlichung | `not_in_scope` | separat zu autorisieren |

## Abnahmeentscheidung

Der Maintainer hat Phase 4 am 7. Oktober 2026 auf Basis von PR #224 mit
folgendem technischen Scope angenommen:

> Ich nehme Phase 4 auf Basis von PR #224 technisch ab. Die Abnahme gilt für
> Finding-Kontinuität, Triage, Trigger- und Scope-Planung,
> Konfigurationsversionierung und das Candidate-Reviewpaket. Sie autorisiert
> keinen Live-Provider-Lauf, keine Veröffentlichung, keine normative
> Bestätigung von Findings und keinen produktiven Rollout. Die
> Rolloutentscheidung bleibt `pending`.

Die Entscheidung bindet die technische Abnahme an den in PR #224 gemergten
Stand. Sie ändert den `pending`-Status der maschinenlesbaren Rolloutentscheidung
nicht und erteilt keine Provider-, Publikations-, Betriebs- oder normative
Freigabe. Ein realer semantischer Pilot und seine menschliche Bewertung
benötigen eine separate, konkret begrenzte Folgeentscheidung.

## Release-Einordnung

Kein Release und keine Consumer-Migration. Die Verträge sind interne
Candidate-Infrastruktur und werden von keiner freigegebenen Baseline oder
Consumer-Pipeline referenziert. Eine spätere operative Nutzung muss
Kompatibilität und Versionierung neu bewerten.
