# Document Consistency Review — providerneutraler Phase-2-Kern

## Zweck und Status

Der Phase-2-Kern validiert untrusted semantische Reviewer-Ausgaben gegen ein
exaktes Quellenmanifest. Er akzeptiert keine Modellinterpretation als
Governance-Entscheidung. Der aktuelle Repository-Stand enthält keinen
Provideradapter und führt keinen Modellaufruf aus.

Der mitgelieferte Beispielreport hat deshalb den Status `not_run`. Die
synthetischen Fixtures unter
`tests/fixtures/document-consistency-review-semantic/` prüfen ausschließlich
den Validator und sind keine Findings über die registrierten Pilotquellen.

## Verträge

| Vertrag | Zweck |
| --- | --- |
| `schemas/document-consistency-semantic-response.schema.json` | Normalisierte, noch unbestätigte Provider- oder Fixture-Antwort |
| `schemas/document-consistency-semantic-report.schema.json` | Deterministisch validierter report-only Bericht einschließlich Quarantäne |
| `schemas/document-consistency-human-decision.schema.json` | Separate, an Manifest und Finding gebundene menschliche Bewertung |

Der Provideradapter muss später ausschließlich den normalisierten
Antwortvertrag erzeugen. Er darf den Finding-Validator weder ersetzen noch
dessen Ergebnis als menschliche Entscheidung deklarieren.

## Validierungskette

```text
manifestierte Quelle
  -> normalisierte untrusted Antwort
  -> Schema- und Laufstatusprüfung
  -> Manifest-, Hash- und Scopeprüfung
  -> Requirement-ID und exakter Kurzbeleg
  -> unconfirmed / context_missing / not_assessable / quarantined
  -> separate menschliche Bewertung
```

Der Validator prüft:

- Antwort- und Manifest-Schema;
- exakten SHA-256 des verwendeten Manifestdokuments;
- ausschließlich im Manifest enthaltene Quellen;
- aktuelle Quellenbytes gegen den Manifesthash;
- stabile Requirement-ID in genau der angegebenen Quelle;
- unveränderten, höchstens 500 Zeichen langen Auszug aus der Requirement-Zelle;
- mindestens zwei Belege für Konflikte;
- Erwartungsbeleg und expliziten Suchscope für Lücken;
- eindeutige Finding- und Evidence-IDs;
- klare Providerzustände einschließlich `failed` und `not_run`.

Eine hohe Modellkonfidenz ändert kein ungültiges Belegergebnis. Ein valider
Beleg bestätigt nur die Herkunft des Textes. Interpretation, Anwendbarkeit und
Lösung bleiben unbestätigt.

## Zustände

| Zustand | Bedeutung |
| --- | --- |
| `unconfirmed` | Beleg ist technisch gültig; fachliche Bewertung fehlt |
| `context_missing` | Beleg kann gültig sein, der erforderliche Anwendungskontext fehlt |
| `not_assessable` | Im freigegebenen Scope ist keine belastbare Bewertung möglich |
| `quarantined` | Beleg ist ungültig, veraltet oder unvollständig |
| `not_run` | Kein Provider wurde ausgeführt; eine leere Findingliste ist kein positives Ergebnis |
| `provider_failed` | Providerlauf ist fehlgeschlagen; kein grüner semantischer Status |
| `synthetic_only` | Nur versionierte Fixtures wurden verarbeitet |

## Lokaler Aufruf ohne Provider

Das eingecheckte Beispiel belegt ausdrücklich, dass kein Provider lief:

```bash
./.venv-validation/bin/python \
  scripts/validate_document_consistency_semantic_review.py \
  --manifest docs/examples/document-consistency-review-phase1-source-manifest.json \
  --response docs/examples/document-consistency-review-phase2-not-run-response.json \
  --output-json docs/examples/document-consistency-review-phase2-report.json \
  --output-markdown docs/examples/document-consistency-review-phase2-report.md
```

Der Befehl liefert bei erfolgreich verarbeitbaren Eingaben Exit-Code `0`, auch
wenn Aussagen quarantänisiert werden. Das ist beabsichtigtes report-only
Verhalten. Nicht lesbare oder schema-ungültige Eingaben liefern Exit-Code `2`.
Quarantäne und Providerfehler bleiben im Report sichtbar und dürfen von einem
späteren Workflow nicht in einen grünen semantischen Nachweis umgedeutet
werden.

## Menschliche Bewertung

Menschliche Entscheidungen werden getrennt gespeichert. Ein Datensatz bindet
sich an:

- Review-ID und Finding-ID;
- SHA-256 des Quellenmanifests;
- SHA-256 der kanonisch gespeicherten Findingfassung;
- Reviewer-ID und Reviewrolle;
- Klassifikation `helpful`, `false_positive`, `unclear` oder
  `not_assessable`;
- Zeitpunkt, Begründung und nächste Aktion.

Der Schema-Fixture ist ausdrücklich synthetisch. Dieser Änderungssatz liefert
noch keinen operativen Decision-Intake und zeichnet keine echte menschliche
Bewertung auf.

## Sicherheits- und Geltungsgrenzen

- Erlaubt sind nur `DSCB-STD-REQ-001`, `PRA-STD-REQ-001` und versionierte
  synthetische Fixtures.
- Die fünf lokal vorhandenen, unregistrierten Dateien bleiben ausgeschlossen.
- Quelleninhalte werden als Daten behandelt; eingebettete Aufforderungen
  ändern weder Scope noch Validatorregeln.
- Kein Internetwissen, keine automatische Quellenpromotion und keine
  automatische Reparatur.
- Keine Änderungen an Controls, OPA, Architekturmarkern, Baselines oder
  Consumer-Repositories.
- Kein Viewer, keine Veröffentlichung und kein neues blockierendes CI-Gate.

## Noch offene Phase-2-Schritte

Vor einem echten Modelllauf bleiben Provider, exakte Modellkennung,
Aufbewahrung, Rohantwortbehandlung, Kosten-/Kontextlimit und menschliche
Reviewer gemäß GCR-2026-119 ausdrücklich zu bestätigen. Ein Provideradapter,
ein echter Pilotreport und operative menschliche Decision-Intake werden erst
danach separat umgesetzt und abgenommen.
