# GCR-2026-120: Providerneutraler Phase-2-Validierungskern

## Anfrage und Einordnung

Implementiere auf Basis des gemergten GCR-2026-119 die Infrastruktur, die ohne
Provider und ohne Zugriff auf lokale Originaldokumente möglich ist. Der Kern
validiert synthetische beziehungsweise später normalisierte Modellantworten
deterministisch, quarantänisiert unbelegte Aussagen und hält menschliche
Entscheidungen getrennt.

| Feld | Wert |
| --- | --- |
| Artefakte | Antwort-, Report- und Human-Decision-Schema; Finding-Validator; synthetische Fixtures; `not_run`-Beispielreport; Tests und Bedienungsanleitung |
| Pilotquellen | Manifest aus Phase 1 mit `DSCB-STD-REQ-001` und `PRA-STD-REQ-001`; keine inhaltliche Modellverarbeitung |
| Provider / Modell | keiner; Status `not_run` |
| Lokale Zusatzdateien | ausgeschlossen, nicht gelesen und nicht übertragen |
| Betriebsart | lokal und report-only |
| Enforcement | keine neue CI- oder Mergeblockade |
| Viewer / Veröffentlichung | nicht enthalten |
| Release- oder Baseline-Auswirkung | keine |
| Status | zur technischen Abnahme vorbereitet; echter semantischer Pilot weiterhin nicht freigegeben |

## Gelieferter Umfang

- Normalisierte Antwortstruktur trennt Aussage, Interpretation, Empfehlung,
  Anwendbarkeit, Konfidenz, Quellenbelege und Suchscope.
- Der Validator prüft Manifestdigest, Quellen-ID, aktuellen Quellenhash,
  Requirement-ID und exakten Kurzbeleg.
- Falsche Fundstellen, erfundene Zitate, Quellen außerhalb des Manifests,
  veraltete Hashes, doppelte IDs und unvollständige Konflikt-/Lückenbehauptungen
  gelangen in sichtbare Quarantäne.
- `context_missing`, `not_assessable`, `not_run`, `provider_failed` und
  `synthetic_only` bleiben von einem positiven semantischen Ergebnis getrennt.
- Menschliche Entscheidungen besitzen einen eigenen Vertrag und werden an
  Manifest und Finding gebunden. Dieser Änderungssatz nimmt keine Entscheidung
  auf.
- Ein Dokument-Prompt-Injection-Fixture belegt, dass Quelltext nur als Daten
  behandelt wird.
- Der Beispielreport enthält null Findings und kennzeichnet dies als
  `not_run`, nicht als Konsistenznachweis.

## Governance-Auswirkung

Die Änderung ist ein additiver report-only Validierungskern. Sie erzeugt keine
normative Anforderung und keine fachlich akzeptierten Findings. Quellenregister,
Controls, Traceability, Architekturmarker, OPA, Releasepakete, Statusindizes und
Viewer bleiben unverändert. Es entsteht keine Consumer-Migration.

Die Schemas sind neue interne Phase-2-Verträge. Sie werden noch nicht von einem
Consumer oder einer blockierenden Pipeline verwendet und benötigen daher keine
Baseline-Version. Ein späterer operativer Provider- oder Decision-Intake muss
Kompatibilität und Versionierung separat bewerten.

## Offene Entscheidungen

- zugelassener Provider und exakte Modellkennung;
- Provider- und lokale Aufbewahrung einschließlich Rohantwort;
- Provideradapter und Laufparameter;
- menschliche Reviewer für quellenübergreifende Aussagen;
- Kosten-, Größen- und Kontextgrenzen;
- echte Pilotbewertung und Rolloutentscheidung.

GCR-2026-119 bleibt das Freigabetor. Der vorliegende Kern schließt keines
dieser offenen Felder durch technische Voreinstellungen.

## Abnahmekriterien

- [x] Alle drei Schemas validieren ihre synthetischen Beispiele.
- [x] Gültige synthetische Belege bleiben `unconfirmed`.
- [x] Erfundenes Zitat, falsche Fundstelle, fremde Quelle und veralteter Hash
      werden quarantänisiert.
- [x] Konflikt ohne zweiten Beleg und Lücke ohne Suchscope werden als
      `incomplete` quarantänisiert.
- [x] Providerfehler und `not_run` können keinen grünen Status erzeugen.
- [x] Modellkonfidenz überstimmt keinen Belegfehler.
- [x] Prompt-Injection-Text bleibt Daten und verändert keine Validatorregel.
- [x] Human Decision bleibt getrennt und wird nicht automatisch erzeugt.
- [x] Vollständige Repository-Validierung, strikter Dokumentationsbuild und
      `git diff --check` sind erfolgreich.

## Validierungsnachweis

- `tests.test_document_consistency_review_manifest`,
  `tests.test_document_consistency_review_model` und
  `tests.test_document_consistency_semantic_review`: 39 Tests bestanden.
- `./scripts/validate_all.sh`: OPA, Runtime Governance,
  Repository-Validierung, Provenance-Prüfung und 699 Unit-Tests bestanden.
  `commit.gpgsign=false` galt ausschließlich über Prozessvariablen für
  temporäre Test-Repositories; die Repository-Konfiguration blieb unverändert.
- `mkdocs build --strict`: erfolgreich; die bestehenden Hinweise auf nicht in
  `nav` geführte Seiten sind nicht buildblockierend.
- `git diff --check`: bestanden.
- Der eingecheckte `not_run`-Report stimmt bytegenau mit der erneuten
  Validatorausgabe überein.
