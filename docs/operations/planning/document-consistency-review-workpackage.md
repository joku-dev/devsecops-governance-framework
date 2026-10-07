# WP-DCR-001 — Doc-as-Code und kontinuierlicher Dokumentenkonsistenzreview

Version: 0.15
Datum: 2026-10-07
Zielrepository: https://github.com/joku-dev/devsecops-governance-framework.git
Status: Phase 0 am 2026-10-07 angenommen; Phase 1 begrenzter technischer Strukturkern am 2026-10-07 angenommen, Ergebnis `partial`; providerneutraler Phase-2-Validierungskern gemergt; einmaliger begrenzter Live-Lauf am 2026-10-07 ausgeführt, Providerantwort schemaungültig und fail-closed abgewiesen, kein validierter Pilotreport; sichere Phase-3-Viewer-Projektion auf Basis von PR #222 am 2026-10-07 angenommen; providerneutrale Phase-4-Betriebsinfrastruktur auf Basis von PR #224 am 2026-10-07 technisch angenommen; Rollout `pending`, keine Veröffentlichung und keine normative Governance-Freigabe

Änderung v0.2: Verbindliche Review-Leitplanken, fachliche Beziehungsprüfung und getrennte Implementierungsabdeckung ergänzt; Abnahmekriterien und Testfälle erweitert.

Änderung v0.3: Halluzinationskontrolle mit Finding-Validator, belegpflichtigen Aussagen, Unsicherheitsregeln und Negativtests als verbindlichen Umfang ergänzt.

Änderung v0.4: Lesende Integration in den bestehenden Governance Viewer mit Reviewansichten, Aktualitätsprüfung, sicherem Publikationsmodell und UI-Abnahmekriterien ergänzt.

Änderung v0.5: Review-Betrieb und Baseline-Management mit Zuständigkeiten, Finding-Kontinuität, Review-Auslösern, Reviewer-Änderungskontrolle und gestaffelter Einführung ergänzt.

Änderung v0.6: Umsetzung in fünf separat abnehmbare Phasen aufgeteilt und die sechs vorgeschlagenen Dokumentklassen gegen das vorhandene Quellenregister abgeglichen. Fehlende Originalquellen, zulässige Startquellen und Freigabebedingungen für semantischen Review und Viewer konkretisiert.

Änderung v0.7: Begrenzten Phase-1-Strukturkern auf Basis von GCR-2026-118 mit Status `partial` angenommen. Rollen-, Gate-, Evidenz- und Autoritätsmodelle bleiben im requirements-only Pilot `not_in_scope`; Phase 2 wird separat entschieden.

Änderung v0.9: Phase-2-Entscheidungsrahmen mit den beiden registrierten requirements-only Auszügen, synthetischen Pilotfällen, Beleggrenzen und menschlicher Bewertung vorbereitet. Provider, Modellkennung, Aufbewahrung und Live-Lauf bleiben bis zur ausdrücklichen Folgeentscheidung offen.

Änderung v0.10: Providerneutralen Phase-2-Antwortvertrag, Finding-Validator, Quarantäne, getrennten Human-Decision-Vertrag, synthetische Negativfixtures und einen ausdrücklich `not_run` bleibenden Beispielreport zur technischen Abnahme vorbereitet. Kein Provider wurde aufgerufen; Providerfreigabe und echter Pilot bleiben offen.

Änderung v0.11: Sichere Phase-3-Projektion in den bestehenden Viewer integriert. Die öffentliche Allowlist enthält ausschließlich Reviewmetadaten, leitet Aktualität aus Manifest- und Quellenhashes ab und hält interne Vollinhalte ohne Zugriffsschutz vollständig aus dem Viewer heraus. Veröffentlichung und Deployment bleiben offen.

Änderung v0.12: Persönliche Phase-3-Abnahme auf Basis von PR #222 erfasst. Die Abnahme gilt ausschließlich für die sichere, öffentliche und redigierte Viewer-Projektion. Veröffentlichung, Live-Provider-Lauf und fachliche Bestätigung von Findings bleiben ausdrücklich nicht autorisiert.

Änderung v0.13: Providerneutrale Phase-4-Betriebsverträge für Finding-Kontinuität, Triage, Trigger-/Scope-Planung, Reviewer-Konfiguration, Candidate-Paket und Rolloutentscheidung ergänzt. Mangels realem semantischem Pilot bleiben vollständiger Review-Ausgangsstand und Rollout ausdrücklich `blocked` beziehungsweise `pending`.

Änderung v0.14: Persönliche technische Phase-4-Abnahme auf Basis von PR #224 erfasst. Die Abnahme gilt für Finding-Kontinuität, Triage, Trigger-/Scope-Planung, Konfigurationsversionierung und das Candidate-Reviewpaket. Live-Provider-Lauf, Veröffentlichung, normative Bestätigung von Findings und produktiver Rollout bleiben ausdrücklich nicht autorisiert; die Rolloutentscheidung bleibt `pending`.

Änderung v0.15: Den separat genehmigten einmaligen, begrenzten ChatGPT-Pro-Pilotlauf erfasst. Der tatsächliche Modelllauf lieferte eine schemaungültige Antwort, die der Repositoryvalidator fail-closed abwies; die Rohantwort wurde nach technischer Triage gelöscht. Es entstand kein validierter Pilotreport und keine menschliche Finding-Entscheidung. Ein providerkompatibles Projektionsschema und ein normalisierender Adapter bleiben vor einem erneut zu genehmigenden Lauf erforderlich; Rollout bleibt `pending`.

## 1. Auftrag an Codex

Ziel ist eine nachvollziehbare Doc-as-Code-Fähigkeit und ein Document Consistency Reviewer für den verbundenen Governance-Dokumentensatz, integriert mit dem bestehenden Source Document Intake Agent. Die Umsetzung erfolgt ausschließlich in den fünf Phasen aus Abschnitt 3.2; jede Phase erhält einen eigenen reviewfähigen PR beziehungsweise Draft PR und eine explizite Abnahme. Eine Phase darf später abhängige Fähigkeiten als `not_run`, `blocked` oder `not_in_scope` ausweisen, statt sie vorzutäuschen. Ohne externe Quellen oder Provider wird die getestete und dokumentierte Infrastruktur geliefert, die unabhängig davon möglich ist. Diese Planrevision selbst startet keine Implementierungsphase. Das Vorhaben umfasst keine automatische Freigabe von Quelldokumenten, keine Änderung freigegebener Governance-Baselines und keinen Merge.

Lies zuerst die geltenden AGENTS.md-Dateien, `.ai/project-context.md`, sofern vorhanden, sowie die aktuellen Agentenrollen, Skills, Register, Validatoren und CI-Konventionen. Prüfe den aktuellen Repository-Stand; die unten genannten Dateien sind Orientierung, keine Garantie unveränderter Pfade. Nutze vorhandene Mechanismen statt parallele Register oder Governance-Systeme aufzubauen.

Arbeite alle unabhängig von externen Eingabedokumenten möglichen Schritte vollständig ab. Wenn Originaldokumente fehlen, implementiere und teste die Infrastruktur mit ausdrücklich synthetischen Fixtures; dokumentiere die fehlenden Inputs und den exakten anschließenden Importbefehl. Behaupte dann keine vollständige Konvertierung oder fachliche Prüfung des realen Dokumentensatzes.

## 2. Problem und Ziel

Policy, Control Baseline, Platform Reference Architecture, SDLC, Operating Model und Toolchain Reference Architecture enthalten miteinander verbundene Anforderungen, Rollen, Begriffe, Aktivitäten und Nachweispflichten. Einzelreviews machen dokumentübergreifende Konflikte nur begrenzt sichtbar. Änderungen sollen deshalb anhand expliziter Beziehungen geprüft werden.

Ziel ist eine versionierte, überprüfbare Dokumentenbasis mit:

- nachvollziehbarer Überführung verfügbarer DOCX-/Markdown-Quellen;
- expliziten Themenverantwortlichkeiten und Referenzen;
- deterministischen Struktur-, Referenz- und Abdeckungsprüfungen;
- KI-gestütztem semantischem Review mit überprüfbaren Fundstellen;
- vollständigem Baseline-Review sowie inkrementellem Review bei Änderungen;
- menschlicher Entscheidung über Findings, Quellenstatus und normative Änderungen.

Keine Aussage einer garantierten vollständigen semantischen Konsistenz. Ein erfolgreicher Validatorlauf und ein abgeschlossener semantischer Review sind getrennte Ergebnisse.

## 3. Ausgangspunkt im Repository

Die Phase-0-Inventur und Entscheidung beziehen sich auf Commit
`a8fc36f3de7f33cd2a26dff94f9a28985e78d64f`. Vor jeder späteren Phase ist der
Repository-Stand erneut zu prüfen.

Relevante vorhandene Komponenten:

- `.agents/roles/source-document-intake.yaml`
- `.agents/skills/source-document-intake/SKILL.md`
- `.codex/agents/source-document-intake.toml`
- `docs/operations/processes/source-document-intake-process.md`
- `docs/operations/processes/source-document-intake-review-operating-model.md`
- `model/documents/source-document-register.yaml`
- `scripts/generate_source_document_intake_status.py`
- `scripts/generate_source_document_intake_review_briefs.py`
- `scripts/generate_source_document_requirement_delta.py`
- `scripts/generate_governance_change_impact_report.py`
- `scripts/validate_governance_repo.py`
- `scripts/validate_runtime_governance.py`

Der bestehende Intake unterstützt Klassifizierung und Entscheidungsvorbereitung. Review Briefs sind überwiegend status-/metadatenbasiert. Requirement Deltas verwenden Schlüsselwörter und Textähnlichkeit; diese Ergebnisse dürfen nicht als semantische Gleichwertigkeitsbeweise behandelt werden.

### 3.1 Abgleich der vorgeschlagenen sechs Dokumentklassen mit dem aktuellen Quellenregister

Der Abgleich unten beruht auf `model/documents/source-document-register.yaml` und den dort referenzierten Dateien im Repository. Er beschreibt den bei Erstellung dieser Version sichtbaren Bestand; vor jeder Phase ist er gegen den dann aktuellen Commit erneut zu prüfen. Ein Registerstatus oder ein sanitisiertes Exzerpt ist keine Freigabe des vertraulichen Originals.

| Vorgeschlagene Dokumentklasse | Im Register vorhandene Einträge | Tatsächlich verfügbare Repository-Eingabe | Konsequenz für den Pilot |
| --- | --- | --- | --- |
| DevSecOps Policy | `DEVSECOPS-POL-SRC-001` (`draft`); `DEVSECOPS-POL-REQ-001` (`review`) | Öffentlicher Platzhalter und bereinigter Anforderungsauszug; Original zurückgehalten | Den Auszug nur als registrierte, bereinigte Review-Eingabe verwenden. Keine Aussage über das vollständige Original oder dessen Autorität treffen. |
| DevSecOps Control Baseline | `DSCB-STD-SRC-001` (`intake`); `DSCB-STD-REQ-001` (`intake`) | Öffentlicher Platzhalter und bereinigter Anforderungsauszug; Original zurückgehalten | Geeignete Startquelle für strukturelle Prüfungen, innerhalb des registrierten `intake`-Scopes. Keine Controls oder Baselines daraus neu ableiten. |
| DevSecOps Platform Reference Architecture | `PRA-STD-SRC-001` (`intake`); `PRA-STD-REQ-001` (`intake`) | Öffentlicher Platzhalter und bereinigter Anforderungsauszug; Original zurückgehalten | Als zusammenhängende zweite Startquelle mit dem Control-Baseline-Auszug verwendbar; nur Review-Unterstützung, keine neue normative Beziehung annehmen. |
| SDLC-, Operating-Model- und Toolchain-Unterlagen | Kein passender Eintrag für die lokal bereitgestellten Dateien gefunden | Lokal vorhanden, aber nicht Teil des Repository-Commits und nicht im Quellenregister | Für Phase 0 unregistriert und außerhalb des Piloten. Keine Inhalte oder Dateinamen in das öffentliche Manifest übernehmen. |

`ARCH-SDD-REQ-001` ist ein weiterer registrierter, sanitierter Architektur-Anforderungsauszug (`review`), aber keine der fehlenden SDLC-, Enterprise-Operating-Model- oder Toolchain-Quellen. Eine Aufnahme in den Pilot erfordert eine dokumentierte Scope-Entscheidung und darf nicht aus dem ähnlichen Thema abgeleitet werden.

**Angenommener Pilotumfang:** Phase 1 darf ausschließlich mit den bereinigten
Auszügen `DSCB-STD-REQ-001` und `PRA-STD-REQ-001` sowie synthetischen Fixtures
strukturelle und deterministische Mechanik demonstrieren. Die ebenfalls
registrierten Auszüge `DEVSECOPS-POL-REQ-001` und `ARCH-SDD-REQ-001` sind nicht
Teil dieses Umfangs. Die fünf lokal bereitgestellten Dateien bleiben
unregistriert und außerhalb des Piloten. Diese Eingrenzung belegt weder
Vollständigkeit noch die Qualität eines semantischen Reviews der
Originaldokumente.

### 3.2 Phasen, Abhängigkeiten und Abnahmetore

Jede Phase wird separat umgesetzt, geprüft und in einem eigenen PR dokumentiert. Spätere Phasen werden nicht durch erfolgreiche frühere Phasen vorweggenommen.

| Phase | Arbeitspakete | Lieferumfang und Abnahmetor | Voraussetzung / ausdrückliche Grenze |
| --- | --- | --- | --- |
| **0 — Inventar und Design** | A | Aktueller Commit-/Datei-Abgleich; Quellmanifest mit Register-ID, Pfad, Status, Version und Hash; Quellen- und Eigentümer-Mapping; ADR mit Autoritäts-, Vertraulichkeits-, Datenfluss- und Viewergrenzen; offene Entscheidungen protokolliert. | Keine Quellpromotion, semantischen Läufe, Workflow-Enforcement-Änderung oder Viewer-Veröffentlichung. Fehlende Dokumente werden als fehlend geführt, nicht ersetzt oder erraten. |
| **1 — Doc-as-Code und deterministischer Kern** | B, C, D; formale Teile von F und G | Reproduzierbarer Import der freigegebenen bereinigten/synthetischen Eingaben; Schema, stabile Tabellen-IDs, Requirement-Stärkekennzeichnungen und vorläufige ID-Referenzen; DCR-001 bis DCR-009 oder dokumentierte Delegation; JSON-/Markdown-Report; synthetische Negativtests; bestehende Repo-Validierung. | Kein externer Modellaufruf. Semantischer Status bleibt `not_run`. Keine automatische Änderung des Quellenregisters, Candidate-Derivation, freigegebene Baseline-Änderung oder zusätzliche blockierende CI-Regel. |
| **2 — Belegbarer semantischer Pilot** | E, E.1–E.4; semantische Teile von F und H | Finding-Validator, kuratierter Testfallkatalog, getrennte Beleg-/Interpretations-/Entscheidungszustände und begrenzter Pilotreport. | Beginnt erst nach expliziter Freigabe des konkreten Quellenumfangs, Datenflusses, Providers/Modells, Aufbewahrung und zulässiger Zitate. Ohne diese Freigabe: `not_run` oder `blocked`; Phase 1 bleibt separat abnehmbar. |
| **3 — Sichere Viewer-Projektion** | I | Read-only-Adapter, lokale Vorschau, redigierte Projektion, Allowlist- und Confidential-Canary-Tests sowie Viewer-Regressionen. | Keine Veröffentlichung oder Deployment. Ohne vorhandenen Zugriffsschutz werden interne Vollansichten nicht gebaut oder in den öffentlichen Viewer projiziert. Nur ausdrücklich freigegebene öffentliche Felder dürfen erscheinen. |
| **4 — Review-Betrieb und Rolloutentscheidung** | J; Abschluss von H | Finding-Kontinuität, Trigger-/Scope-Matrix, Konfigurationsversionierung, manifestbasiertes Baseline-Paket, menschliche Pilotbewertung und dokumentierte Rolloutentscheidung. | Ein vollständiger Sechser-Satz ist nur möglich, wenn die fehlenden Originale oder autorisierten Auszüge verfügbar, registriert, klassifiziert und freigegeben sind. Ohne menschliche Bewertung bleibt Rollout `pending`; es entsteht keine normative Freigabe. |

**PR-Reihenfolge:** Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4. Eine Phase kann auf einem vorgelagerten PR aufbauen; kein PR darf Ergebnisse oder Freigaben späterer Phasen als bereits erreicht darstellen. Relevante Änderungen an den akzeptierten Lifecycle-Fingerprints aus `model/governance/lifecycle/operating-acceptance/00000001.json` bleiben ausgeschlossen und benötigen einen separat versionierten Folgeprozess.

## 4. Dokumentenumfang und Quellenverantwortung

Die folgende Zuordnung ist ein zu bestätigender Vorschlag. Existierende Governance-Hierarchie und Entscheidungen haben Vorrang; Konflikte als Finding erfassen.

| Dokumentklasse | Vorgeschlagener maßgeblicher Inhalt |
| --- | --- |
| Policy | Grundsätze und verbindliche Leitplanken |
| Control Baseline | Kontrollanforderungen und erforderliche Nachweise |
| Platform Reference Architecture | Plattformstruktur und Architekturvorgaben |
| SDLC | Aktivitäten, Übergänge, Ergebnisse und Gate-Kriterien |
| Operating Model | Rollen, Entscheidungsrechte und Zusammenarbeit |
| Toolchain Reference Architecture | Toolchain-Fähigkeiten, Schnittstellen und technische Umsetzung |

Mögliche externe Inputs, jeweils aktuelle verfügbare Fassung prüfen:

- DevSecOps Policy, Review Integrated v2;
- DevSecOps Control Baseline, Reviewer Comments v0.3;
- DevSecOps Platform Reference Architecture, Reviewer Comments v0.4;
- Software Development Process DevSecOps V5, Activity/RACI/Artifacts;
- Software Industrialisation Enterprise Operating Model, revised extended scope;
- Enterprise SDLC Toolchain Reference Architecture v0.4.

Dateinamen sind Suchhinweise, keine Freigabe- oder Versionsnachweise. Importinventar muss tatsächlichen Dateinamen, Version, Quellenstatus, Hash und Verfügbarkeit festhalten. Nicht stillschweigend eine ältere Version verwenden.

Die Liste der sechs externen Inputs ist ein Such- und Zielinventar. Für Phase 0
werden die verfügbaren registrierten Eingaben über das Manifest belegt. Die
fünf zusätzlich lokal bereitgestellten Dateien sind zwar im Maintainer-Checkout
vorhanden, bleiben aber unregistriert und außerhalb des Piloten. Sie werden
nicht im Repository-Manifestsnapshot aufgeführt. Bestehende
Repository-Dokumente ähnlichen Titels dürfen nicht automatisch als Ersatz
gemappt werden.

## 5. Zielarchitektur

### 5.1 Doc-as-Code

Markdown mit stabilem Frontmatter als bearbeitbare Quelle verwenden, sobald die Migration bestätigt ist. Originaldatei und Konvertierung bleiben nachvollziehbar. Pro Dokument explizit festhalten, ob DOCX oder Markdown derzeit die maßgebliche Bearbeitungsquelle ist; keine doppelte unklare Autorität.

Frontmatter beziehungsweise kompatibles Register enthält Dokument-ID, Titel, Version, Status, Owner, Sprache, Governance-Domänen, Quellenreferenz, Quellhash und Konvertierungsinformationen. Bestehendes Register als maßgebliche Registrierungsstelle erhalten; doppelte Metadaten auf Übereinstimmung prüfen.

Stabile IDs für Anforderungen, Rollen, Begriffe, Aktivitäten, Gates und Artefakte einführen. IDs dürfen nicht allein aus Zeilennummern oder veränderlichem Aussagewortlaut entstehen. Quellenreferenzen enthalten Dokument-ID, Abschnitt/Anker, Quellhash und optional Zeilenbereich des geprüften Standes.

### 5.2 Beziehungsmodell

Ein schema-validiertes YAML-/JSON-Modell im Repository nutzen. Eine zusätzliche Graphdatenbank ist für dieses Workpackage nicht erforderlich.

Beziehungen mindestens: `defines`, `references`, `implements`, `verified_by`, `evidenced_by`, `owned_by`, `depends_on`. Jede Beziehung hat Typ, Quell- und Ziel-ID sowie nachvollziehbare Herkunft. `candidate`-/KI-vorgeschlagene Beziehungen getrennt von bestätigten Beziehungen halten.

Gemeinsamen Rollen-/Begriffskatalog und eine Themen-zu-Quelle-Zuordnung einführen oder vorhandene Modelle erweitern. Synonyme und zugelassene lokale Rollenprofile explizit modellieren. Keine fachliche Äquivalenz allein aus Namensähnlichkeit ableiten.

### 5.3 Verantwortlichkeiten

- Intake Agent: Input klassifizieren, registrieren, Änderungen erkennen und Konsistenzreview auslösen.
- Document Consistency Reviewer: deterministische Ergebnisse auswerten, semantische Konflikte untersuchen und Findings/Optionen vorbereiten.
- Menschlicher Dokument-/Governance-Owner: fachliche Autorität, Konfliktauflösung, Quellenpromotion und normative Änderung entscheiden.

Reviewer als modellneutrale Rolle und Skill integrieren; Provideradapter gemäß bestehender Architektur ergänzen. Agentenregistrierung ist kein Nachweis eines ausgeführten Reviews.

## 6. Arbeitspakete

### A. Bestandsaufnahme und Design

1. Aktuellen Commit, vorhandene Modelle, Agenten, Tests und CI untersuchen.
2. Verfügbare reale Quellen inventarisieren und Dokumentengrenzen bestätigen.
3. Kleine ADR mit Architektur, Autoritätsmodell, Reviewgrenzen und Wiederverwendung vorhandener Komponenten erstellen.
4. Implementierungsplan und eventuell notwendige Entscheidungen dokumentieren.

### B. Konvertierung und Migration

1. Reproduzierbaren Import für DOCX und bestehendes Markdown implementieren; Dependencies und Befehle dokumentieren.
2. Überschriften, Tabellen, Listen, Links, relevante Bilder und Quellbezüge erhalten. Komplexe Elemente mit Verlustwarnung erfassen.
3. Kommentare, Änderungsmarkierungen und offene Entscheidungsmarker separat nachvollziehbar erhalten. Tracked Changes nicht stillschweigend annehmen oder verwerfen; nicht unterstützte Elemente ausdrücklich melden.
4. Konvertierungsmanifest erzeugen: Quellhash, Toolversion, Behandlung von Kommentaren/Revisionen, Warnungen und geprüfte Elemente.
5. Originale nach Repository-Vertraulichkeitsregeln aufbewahren. Private Eingaben außerhalb öffentlicher beziehungsweise veröffentlichter Dokumentationspfade halten. Exporter auf unbeabsichtigte Offenlegung prüfen.
6. Pilotkonvertierung und Qualitätscheck durchführen; vollständige Migration nur für tatsächlich verfügbare Quellen ausweisen.

### C. Struktur und Beziehungen

1. Schema für IDs, Referenzen, Rollen, Begriffe, Themenverantwortung und Beziehungen implementieren.
2. Reale bestehende IDs übernehmen; sonst stabile neue IDs und eine dokumentierte Mapping-Tabelle erstellen.
3. Beziehungen auf Quellenstellen zurückführen. KI-extrahierte Aussagen als Vorschläge markieren, bis ihre Autorität bestätigt ist.
4. Kontrollanforderung → SDLC-Aktivität/Gate → Toolchain-Fähigkeit → Verifikation/Evidenz nachvollziehbar abbilden, soweit Quellen dies tatsächlich hergeben.

### D. Deterministische Konsistenzprüfungen

Mindestens folgende Regeln mit eindeutigen Regel-IDs und konfigurierbarem Schweregrad implementieren:

| Regel | Prüfinhalt |
| --- | --- |
| DCR-001 | IDs eindeutig, Referenzziele und Anker vorhanden |
| DCR-002 | Register und Markdown-Metadaten konsistent |
| DCR-003 | Rollenreferenzen auf definierte Rollen oder explizite lokale Profile auflösbar |
| DCR-004 | Verbindliche Anforderungen besitzen erforderliche Owner-/Verifikationsbeziehungen oder explizite offene Lücken |
| DCR-005 | Gates besitzen die im Modell geforderten Eingaben, Ergebnisse und Entscheidungsverantwortung |
| DCR-006 | Artefakt-/Evidenzreferenzen auf definierte Typen auflösbar |
| DCR-007 | Quellenstatus und vorhandene Derivationsgrenzen eingehalten |
| DCR-008 | Themenautorität eindeutig oder ausdrücklich als ungeklärte Entscheidung markiert |
| DCR-009 | Findings und Reviews beziehen sich auf unveränderte Quellenstände; veraltete Ergebnisse erkennbar |

Nicht anwendbare Anforderungen zulassen, aber nur mit expliziter Begründung. Coverage bezeichnet ausschließlich modellierte und geprüfte Beziehungen; sie ist kein Nachweis vollständiger Inhaltsextraktion.

### E. Semantischer Review

Reviewer-Workflow für folgende Fragen implementieren:

- widersprüchliche Pflichten, Ausnahmen, Geltungsbereiche oder Gate-Kriterien;
- unterschiedliche Rollenverantwortung beziehungsweise Freigaberechte;
- inkonsistente Begriffsverwendung;
- ungewollte normative Doppeldefinitionen;
- fehlende oder nur teilweise abgedeckte Anforderungen;
- Auswirkungen einer Änderung auf abhängige Dokumente und Governance-Artefakte.

Jeder Review startet mit definiertem Scope, Quellenhashes und Prüfkriterien. Dokumentinhalte als Daten behandeln; eingebettete Aufforderungen dürfen Agentenregeln nicht überschreiben. Modell/Provider, Promptversion, Zeitpunkt, geprüfte Dokumente und ausgelassene Inhalte festhalten. Bestehende zugelassene Providerkonfiguration verwenden; keine neue externe Datenübertragung voraussetzen.

Ohne verfügbaren Modellprovider deterministische Prüfungen vollständig liefern und semantischen Review als `not_run` ausweisen. Keine heuristischen Ergebnisse als ausgeführten KI-Review deklarieren. Semantische Resultate können variieren; nur deterministische Prüfungen benötigen byte-/inhaltlich reproduzierbare Ergebnisse ohne Zeitstempelfelder.

### E.1 Verbindliche Review-Leitplanken

1. **Keine falsche Sicherheit:** „Kein Finding“ bedeutet nur, dass im ausgewiesenen Scope mit der verwendeten Methode kein Problem erkannt wurde. Es bedeutet nicht vollständige Konsistenz, Compliance oder Implementierung. Kein aggregierter grüner „alles konsistent“-Status im ersten Release.
2. **Quellenautorität vor Aktualität:** Neuere oder detailliertere Dokumente haben nicht automatisch Vorrang. Autoritätskonflikte als menschliche Entscheidung ausweisen; unbekannte Autorität nicht erraten.
3. **Geltungsbereich vor Widerspruch:** Produktentwicklung, Factory, Safety, Security, Cloud/Fog/Edge, Lifecycle-Zustand, Produktprofil und Ausnahmen berücksichtigen. Ein bestätigter Widerspruch benötigt unvereinbare Aussagen im selben anwendbaren Kontext. Bei fehlendem Kontext als potenziellen Konflikt beziehungsweise Klärungsbedarf kennzeichnen.
4. **Normative Stärke erhalten:** Pflicht, Empfehlung, Erlaubnis, Verbot und offene Entscheidung getrennt erfassen. Keine Umwandlung von Empfehlungen zu Pflichten durch Konvertierung, Extraktion oder Lösungsvorschläge.
5. **Konvertierungsqualität als Vorbedingung:** Inhaltsbereiche mit Verlustwarnungen oder ungeklärten Revisionen nicht als vollständig geprüft ausweisen. Insbesondere RACI-Tabellen, zusammengeführte Zellen, Kommentare und Entscheidungsmarker mit der Originalquelle abgleichen.
6. **Keine stille Harmonisierung:** Reviewer meldet Konflikt, Optionen und Auswirkungen. Widersprüche nicht automatisch umformulieren oder normative Autorität durch eine neue Formulierung ersetzen.
7. **Prüflücken sichtbar:** Fehlende Quellen, abgeschnittene Modellkontexte, ausgelassene Tabellen, nicht unterstützte Inhalte und Providerfehler mindern die Review-Abdeckung und müssen im Ergebnis sichtbar sein.

### E.2 Fachliche Richtigkeit der Beziehungen

Eine schema-gültige Beziehung ist noch kein fachlicher Abdeckungsnachweis. Für wesentliche `implements`, `verified_by` und `evidenced_by`-Beziehungen zusätzlich prüfen:

- Deckt das Ziel die tatsächliche Verpflichtung einschließlich Geltungsbereich und normativer Stärke ab?
- Ist die Abdeckung vollständig, teilweise, nicht gegeben oder nicht beurteilt?
- Prüft die referenzierte Verifikation die Anforderung tatsächlich oder nur einen ähnlichen Sachverhalt?
- Ist die Evidenz geeignet, aktuell und für den relevanten Quellen-/Implementierungsstand anwendbar?

Beziehungsprüfung mit Quellenstellen, Begründung, Bewertungsmethode und gegebenenfalls menschlichem Bestätiger dokumentieren. Technische Linkgültigkeit, fachliche Abdeckungsbewertung und menschliche Bestätigung sind separate Felder. Unbestätigte KI-Zuordnungen dürfen nicht als bestätigte Coverage gezählt werden. Menschliche Bestätigung ersetzt keinen technischen Verifikationsnachweis.

### E.3 Dokumentenkonsistenz und Implementierungsabdeckung trennen

Zwei voneinander unabhängige Reviewdimensionen liefern:

| Dimension | Fragestellung | Nachweis |
| --- | --- | --- |
| Dokumentenkonsistenz | Stimmen anwendbare Anforderungen, Rollen und Begriffe zwischen den Quellen überein? | Quellenvergleich und fachlich bewertete Beziehungen |
| Implementierungsabdeckung | Sind akzeptierte Anforderungen durch Policies, Schemas, Templates, Workflows oder andere Governance-Artefakte umgesetzt und verifiziert? | Artefaktreferenz, geprüfter Commit/Hash, Test beziehungsweise geeignete Evidenz |

Bidirektional prüfen: akzeptierte Anforderungen ohne hinreichende Umsetzung sowie ausführbare Governance-Regeln ohne akzeptierte Quellenbasis. Vorhandene Lineage-/Impact-/Validierungsmechanismen wiederverwenden. Eine Implementierungsreferenz allein belegt weder korrekte Durchsetzung noch erfolgreichen Betrieb; diese Nachweisgrenzen im Report nennen.

Fehlt eine geeignete Evidenz, Implementierungsabdeckung als `not_assessed`, `partial` oder `unverified` ausweisen, nicht als erfüllt. Teilbewertung und fehlende Nachweise mit Begründung festhalten. Umsetzung und Verifikation bleiben getrennt; keine Implementierungsänderung oder Baseline-Freigabe allein durch diesen Review. Dieser Umfang umfasst die Governance-Artefakte im Repository, nicht automatisch sämtliche Produkt-/Consumer-Repositories.

### E.4 Halluzinationskontrolle — verbindlicher Implementierungsumfang

Halluzinationen als erwartbaren Fehlerfall behandeln. Gute Prompts, niedrige Temperatur, Konfidenzwerte oder ein zweiter Modellaufruf sind keine Garantie für Richtigkeit. Unbelegte KI-Aussagen dürfen weder als bestätigte Fehler noch als Governance-Anforderungen übernommen werden.

#### Geschlossener Quellenumfang und Aussagearten

- Review nur gegen das explizite, versionierte Quellenmanifest ausführen. Keine stillschweigende Ergänzung aus Modellwissen oder Internetquellen. Externe Kriterien benötigen eine separat registrierte Quelle und einen autorisierten Scope.
- Quellenfakt, Interpretation und Lösungsvorschlag im Output getrennt kennzeichnen. Vorschläge besitzen keine normative Autorität.
- Fehlende Rollen, Pflichten, Beziehungen oder Entscheidungen nicht erfinden. `not_assessable` und `context_missing` als zulässige Bewertungszustände unterstützen.
- Modellkonfidenz ist eine Selbsteinschätzung, kein Richtigkeitsnachweis und kein Freigabekriterium.

#### Belege und Finding-Validator

Zwischen Modellantwort und entscheidungsfähigem Reviewreport einen deterministischen Finding-Validator implementieren. Für positive Quellenbehauptungen sind Quellen-ID, Hash, Anker beziehungsweise geprüfter Textbereich und kurzer Originalauszug erforderlich. Bei Konflikten beide Aussagen belegen; Paraphrasen separat führen.

Validator prüft mindestens Schema, IDs, Zulässigkeit der Quelle im Reviewmanifest, Hash, Referenzauflösung und Übereinstimmung des Originalauszugs mit dem referenzierten Textbereich. Nur dokumentierte nicht-semantische Normalisierung, etwa Zeilenenden, zulassen. Keine unscharfe Textähnlichkeit zur Bestätigung erfundener oder veränderter Zitate nutzen; Negationen und Modalverben unverändert erhalten.

Belegstatus getrennt vom Finding-Lifecycle führen, beispielsweise `valid`, `invalid`, `stale`, `incomplete`. Ungültige, veraltete oder unvollständige Belege führen in einen sichtbaren Quarantäne-/Klärungsbereich, nicht in bestätigte Findings oder erfüllte Coverage. Rohantwort und Ablehnungsgrund nach geltender Vertraulichkeits-/Aufbewahrungspraxis nachvollziehbar halten; sensible Inhalte nicht in öffentliche Logs schreiben.

Ein technisch valider Beleg bestätigt nur die Herkunft des Textes. Er bestätigt nicht die Interpretation. Fachliche Akzeptanz bleibt separat und erfordert die dokumentierte menschliche Entscheidung. Bei optionaler Zweitprüfung beide Reviews als zusätzliche Hinweise behandeln, nicht als unabhängigen Beweis.

#### Konflikt- und Lückenbehauptungen

Jedes Konflikt-Finding muss erläutern, warum dieselbe Anwendbarkeit vorliegt, welche Verpflichtungen unvereinbar sind und welche Ausnahmen beziehungsweise Hierarchieregeln berücksichtigt wurden. Bei unklarem Kontext nur potenziellen Konflikt melden.

Für Lücken gibt es keinen zitierbaren Beleg einer Abwesenheit. Stattdessen zugrunde liegende Erwartung belegen und Such-/Prüfscope, untersuchte Quellenstände, Methode, Suchbegriffe oder relevante Beziehungen und Prüflücken ausweisen. Bei unvollständigem Scope ausschließlich „im geprüften Umfang nicht gefunden“, nicht „existiert nicht“. Auch bei vollständig untersuchtem Scope Aussage auf diesen Quellenbestand begrenzen.

#### Betriebs- und Entscheidungsgrenzen

Providerfehler, Parserfehler, Kontextkürzungen und verworfene Findings explizit ausweisen. Belegprüfung darf technisch die Annahme eines KI-Findings verweigern, ohne dadurch ein neues blockierendes Deployment-Gate zu schaffen. Keine automatische Reparatur, Quellenpromotion oder Freigabe aus der Modellantwort. Menschliche Bestätigung und erneute Quellenprüfung bleiben erforderlich.

### F. Findings und Reports

Maschinenlesbaren JSON-Report und lesbaren Markdown-Report erzeugen. Finding mindestens:

- stabile Finding-ID, Regel/Reviewkategorie und Ursprung (`deterministic` oder `semantic`);
- Schweregrad, Konfidenz bei semantischen Findings und Bearbeitungsstatus;
- präzise Aussage über den Konflikt oder die Lücke;
- betroffene IDs, Quellenhashes und exakte Abschnitts-/Ankerreferenzen;
- beide Fundstellen bei einem Widerspruch beziehungsweise explizit benannter fehlender Gegenbeleg;
- Begründung, Auswirkung, Lösungsvorschlag und zuständiger Owner;
- Entscheidung, Entscheider und Entscheidungsbegründung, soweit vorhanden.

Statusmodell etwa: `open`, `triaged`, `accepted_for_resolution`, `resolved`, `false_positive`, `accepted_exception`. Ausnahmen brauchen Scope, Begründung und gemäß bestehender Governance gegebenenfalls Ablaufdatum. `resolved` nur nach erneuter Prüfung am geänderten Quellenstand. Fehlende/veraltete Reviews bleiben sichtbar.

Reports sollen getrennt anzeigen: deterministische Fehler, semantische Findings, offene Entscheidungen, nicht geprüfte Inhalte, modellierte Coverage und Review-Aktualität. Beabsichtigte erklärende Wiederholungen sind nicht automatisch Fehler.

Reportstruktur muss mindestens die getrennten Bereiche `formal_validation`, `semantic_review`, `human_decisions` und `implementation_coverage` enthalten. Je Bereich Scope, Aktualität, Ergebnis und nicht geprüfte Anteile ausweisen; Ausführungsstatus von Findings und fachlicher Annahme trennen. Bei Coverage Zähler, Nenner, betrachtete Population und unbestätigte Beziehungen angeben. Auch ein befundfreier Report enthält die Einschränkungen aus E.1.

### G. Änderungsauswirkungen und CI

1. Full-Review-Modus für den gesamten registrierten Satz implementieren.
2. Incremental-Modus mit explizitem Base-/Head-Commit implementieren: geänderte Dokumente plus relevante Abhängigkeiten und Referenzierer prüfen.
3. Änderungen an Rollen-/Begriffskatalog, Themenautorität, Schema oder unvollständigem Beziehungsmodell müssen den Scope konservativ erweitern; erforderlichenfalls Full Review. Löschungen und Umbenennungen berücksichtigen.
4. Bestehende CI um Reports ergänzen. Im ersten Release neue inhaltliche/semantische Regeln report-only betreiben; bestehende Sicherheits- und Candidate-Derivationssperren erhalten.
5. Modellprovider-Ausfälle dürfen keine grüne semantische Prüfung erzeugen. Kosten-/Größenlimits und ausgelassene Inhalte dokumentieren.
6. Keine neue zeitgesteuerte Automation erforderlich. Wiederkehrende Ausführung als dokumentierte Option beschreiben.

### H. Pilot, Dokumentation und Übergabe

Der erste deterministische Pilot in Phase 1 verwendet ausschließlich die im Register vorhandenen bereinigten Anforderungsauszüge `DSCB-STD-REQ-001` und `PRA-STD-REQ-001` sowie ausdrücklich synthetische Fixtures. Das ist ein begrenzter Test mit registrierten Auszügen, keine Konvertierung oder fachliche Prüfung der zurückgehaltenen Originale. Die Auswahl weiterer Quellen ist im Phase-0-Entscheidungsprotokoll festzuhalten.

Ein semantischer Pilot mit zwei bis drei zusammenhängenden Quellen ist Phase 2
und setzt voraus, dass die tatsächlichen Quellenstände, Nutzungsfreigaben und
ein zugelassener Provider feststehen. Lokal vorhandene, aber unregistrierte
Dateien sind bis zu einer separaten Intake- und Scope-Entscheidung
`not_authorized` für den Pilot; vorhandene ähnlich benannte Repository-
Dokumente ersetzen keine Quelle.

Erst nach der menschlich bewerteten Pilotentscheidung in Phase 4 wird der Umfang eines vollständigen Sechser-Satzes festgelegt. Die Infrastruktur kann dessen Verarbeitung vorbereiten; eine vollständige Konvertierung oder Prüfung darf nur für tatsächlich verfügbare, registrierte und freigegebene Quellen behauptet werden. Reale Originale, bereinigte Auszüge und synthetische Nachweise sind in Manifesten und Reports strikt unterscheidbar.

Liefere Bedienanleitung mit Import, Full Review, Incremental Review, Finding-Triage, erneuter Prüfung, Providerkonfiguration und Grenzen. Erkläre, wann Markdown zur maßgeblichen Bearbeitungsquelle wird und wie spätere Word-Exporte entstehen können. Ein vollständiges Corporate-DOCX-Exportsystem ist kein Pflichtumfang dieses Workpackages.

### I. Viewer-Integration des Document Consistency Reviews

Den bestehenden Repository-Viewer erweitern, keinen zweiten Viewer aufbauen. Vor Implementierung aktuelle Dateien, Datenprojektionen, Build-/Publikationspfade und Zugriffsschutz untersuchen. Bestehende Navigation und Gestaltung wiederverwenden. Diese Erweiterung ist Bestandteil desselben Implementierungsauftrags; Veröffentlichung oder Deployment ist weiterhin nicht autorisiert.

#### Architektur und Datenvertrag

Reviewausführung verbleibt bei Agenten/CLI/CI. Der Viewer konsumiert ausschließlich versionierte, schema-validierte und für die jeweilige Zielgruppe freigegebene Datenprojektionen. Keine Modellaufrufe, Secrets, Quellenpromotion, Finding-Entscheidungen oder schreibenden Governance-Aktionen im Browser. Triage erfolgt über den vorhandenen versionierten Prozess; der Viewer darf zulässige Links zu diesem Prozess anbieten.

Viewerprojektion enthält Schema-Version, Review-ID, geprüften Commit, aktuelle Referenzstände, Quellenhashes, Erzeugungszeitpunkt, Scope, Ausführungsstatus, Belegstatus und menschlichen Entscheidungsstatus. Bestehende Reportformate wiederverwenden beziehungsweise über einen dokumentierten Adapter projizieren. Aggregationen dürfen Quarantäne-Findings nicht als bestätigte Fehler zählen und unbestätigte Beziehungen nicht als bestätigte Coverage ausweisen.

#### Pflichtansichten

| Ansicht | Pflichtinhalt |
| --- | --- |
| Review-Übersicht | Formale Prüfung, semantischer Review, offene menschliche Entscheidungen und Implementierungsabdeckung getrennt; jeweils Scope, Aktualität und Prüflücken |
| Dokumentenübersicht | Dokument-ID, zulässiger Titel, Version, Quellenstatus, letzter Review und zugehöriger Quellenstand |
| Finding-Liste | Filter nach Dokument, Kategorie, Schweregrad, Owner, Lifecycle und Belegstatus; stabile Detail-Links |
| Konfliktdetail | Beide Aussagen nebeneinander mit zulässigen Originalauszügen, Fundstellen, Geltungsbereich, Begründung, Vorschlag und Entscheidungsstatus |
| Abdeckungsmatrix | Anforderung → Aktivität/Gate → Toolchain-Fähigkeit → Verifikation/Evidenz; fehlende, teilweise und unbestätigte Beziehungen sichtbar |
| Beleg-/Prüfqualität | `valid`, `invalid`, `stale`, `incomplete`, Quarantäne, nicht ausgeführte Prüfungen und nicht beurteilbare Bereiche klar unterscheidbar |

Detailansichten auf kleinen Bildschirmen lesbar stapeln. Filter und Navigation per Tastatur bedienbar machen; Zustände nicht ausschließlich durch Farben vermitteln. Große Datenmengen begrenzen/paginieren, ohne Prüfumfang oder Summen irreführend zu verändern. Sichtbare Definitionen für Kennzahlen und deren Zähler/Nenner anbieten.

#### Aktualität und Fehlerzustände

Aktualität aus dem Vergleich geprüfter Quellen-/Artefakthashes mit einem aktuellen Manifest des jeweiligen Builds beziehungsweise Snapshots ableiten, nicht allein aus dem Alter eines Zeitstempels. Bei Quellenänderung Review sichtbar als veraltet markieren. Ohne aktuellen Vergleichsstand ist Aktualität `unknown`, nicht aktuell. Ein statischer Viewer kann nur den Zustand seines publizierten Snapshots kennen; dies ausdrücklich anzeigen.

Fehlende Reports, ungültiges Schema, abgebrochene Reviews, Providerfehler und leere zulässige Projektionen benötigen eigene verständliche Zustände. „Keine Findings“ unterscheidet sich von „nicht geprüft“, „Daten fehlen“ und „Inhalte aus Vertraulichkeitsgründen nicht angezeigt“. Kein pauschaler grüner Gesamtstatus.

#### Vertraulichkeit und sichere Veröffentlichung

Interne Vollprojektion und öffentlich bereinigte Projektion technisch getrennt erzeugen. Öffentlich ausschließlich explizit freigegebene Felder per Allowlist exportieren; unbekannte Klassifizierung standardmäßig nicht veröffentlichen. Auch Titel, Owner, Pfade, Links, Konfliktbeschreibungen, Lösungsvorschläge, Metadaten und Kennzahlen können vertraulich sein.

Vertrauliche Daten nicht nur im UI verbergen: Sie dürfen in öffentlichen JSON-Dateien, HTML, JavaScript-Bundles, Downloads, Suchindizes, Source Maps oder Build-Artefakten nicht enthalten sein. Originalauszüge nur in dafür freigegebenen internen Ausgaben beziehungsweise ausdrücklich freigegebenen öffentlichen Quellen anzeigen. Öffentliche Quarantäneansichten dürfen keine ungeprüften Rohmodellantworten veröffentlichen. Projektionsfreigabe bedeutet Publikationsfreigabe der Daten, keine fachliche Bestätigung des Findings.

Interne Vollansichten nur über bereits vorhandenen wirksamen Zugriffsschutz oder lokal bereitstellen. Wenn kein geschützter interner Betrieb existiert, diesen als Voraussetzung melden; keine neue Authentifizierungslösung oder öffentliche Vollansicht stillschweigend einführen. Quellen-/Modelltexte als untrusted Daten rendern: HTML escapen beziehungsweise nach bestehender sicherer Markdown-Regel sanitizen, gefährliche URL-Schemata verwerfen. Freigegebene Fundstellen müssen zum geprüften Stand führen, nicht stillschweigend auf veränderte aktuelle Inhalte.

#### Viewer-Tests und Übergabe

Fixtures für gültigen, veralteten, unvollständigen und nicht ausgeführten Review sowie Quarantäne und redigierte Daten bereitstellen. Adapter-/Aggregationstests und UI-Smoke-Tests für Navigation, Filter, Details, mobile Darstellung und Fehlerzustände ergänzen. Veröffentlichungsschutz mit eindeutigen synthetischen Confidential-Canaries über sämtliche tatsächlich erzeugten öffentlichen Dateien testen; UI-Verbergen allein ist kein bestandener Test. HTML-/Link-Injection-Negativtest hinzufügen. Screenshots beziehungsweise reproduzierbare lokale Vorschau und genaue Start-/Build-Befehle liefern. Bestehende Viewerfunktionen regressionsprüfen.

### J. Review-Betrieb und Baseline-Management

#### Zuständigkeiten und Autoritätsmatrix

Eine versionierte Betriebsbeschreibung mit Dokument-Ownern, zuständiger Reviewfunktion, Triage-Verantwortung und Eskalationsweg liefern. Rollen aus dem bestehenden Governance-Modell verwenden; keine Personen oder neuen Entscheidungsgremien erfinden.

Die Themen-zu-Quelle-Matrix aus Abschnitt 4 ist ein Vorschlag bis zur dokumentierten fachlichen Bestätigung. Bestätiger, Datum, Scope und Entscheidung referenzieren. Unbestätigte Zuordnungen erlauben technische Pilotierung, aber keine automatische fachliche Vorrangentscheidung.

Für jedes akzeptierte Finding Owner, Priorität, Bearbeitungsentscheidung, nächste Aktion und gegebenenfalls Zieltermin beziehungsweise explizit offenen Termin erfassen. Konflikte zwischen Dokument-Ownern an die vorhandene zuständige Governance-Instanz eskalieren. Konfigurierbare Triage-/Bearbeitungsziele vorbereiten; keine verbindlichen SLAs ohne Ownerentscheidung festlegen. Überfällige, nicht zugeordnete und entscheidungsbedürftige Findings im Report/Viewer sichtbar machen. Dieser Auftrag autorisiert keine automatischen Nachrichten an Personen.

#### Ausgangsstand und neue Verschlechterungen

Den ersten vollständigen Review als unveränderlichen Review-Ausgangsstand erfassen, getrennt von einer normativ freigegebenen Governance-Baseline. Bestehende offene Probleme werden dadurch weder akzeptiert noch unterdrückt.

Spätere Läufe unterscheiden `new`, `unchanged`, `worsened`, `resolved`, `reopened` und `not_reassessed`. Verschärfungen anhand dokumentierter Kriterien wie größerem Geltungsbereich, neuer betroffener Quelle oder begründet höherem Schweregrad bewerten. Nicht erneut geprüfte Findings dürfen nicht als gelöst gelten. Modell-/Promptwechsel als mögliche Ursache von Ergebnisänderungen sichtbar halten; nicht jede neue Modellbewertung als fachliche Verschlechterung darstellen.

#### Finding-Kontinuität und Fehlalarme

Persistente Finding-ID von Reviewlauf, Zeilennummer, Quellenhash und Modellwortlaut entkoppeln. Vorkommen je Lauf mit eigenen Belegen/Quellenständen referenzieren. Deterministische Findings anhand Regel-ID, stabiler Entitäten und Scope korrelieren. Semantische Zuordnungsvorschläge zu früheren Findings benötigen nachvollziehbare Kriterien; bei unsicherer Identität menschliche Triage statt stiller Zusammenführung.

Entscheidungen append-only beziehungsweise über bestehende versionierte Historie nachvollziehbar halten. Zusammenführungen und Aufteilungen über explizite Vorgänger-/Nachfolgerbeziehungen erhalten. `false_positive` und `accepted_exception` bleiben mit Begründung, Gültigkeitsscope und Quellenbezug sichtbar. Bei relevanten Quellen-, Geltungsbereichs-, Autoritäts- oder Regeländerungen erneut bewerten; keine globale dauerhafte Unterdrückung. Geänderte Entscheidungsgrundlagen machen die frühere Entscheidung prüfbedürftig, ohne ihre Historie zu löschen.

#### Review-Auslöser und Änderungskontrolle

Eine maschinenlesbare Trigger-/Scope-Matrix implementieren oder vorhandene Logik erweitern:

| Änderung | Erforderliche Reaktion |
| --- | --- |
| Quelldokument, Quellenstatus oder Implementierungsartefakt | Betroffene Quellen/Artefakte und Abhängigkeiten prüfen |
| Rollen, Begriffe, Beziehungen oder Themenautorität | Betroffenen Scope erweitern; bei unklarer Reichweite Full Review |
| Schema, Prüfregel, Extraktions-/Konvertierungslogik | Betroffene Nachweise invalidieren beziehungsweise neu prüfen; Regressionstests |
| Prompt, Modell oder Providerkonfiguration | Kuratierten Fallkatalog prüfen; vergleichbare Referenzläufe und Auswirkungen dokumentieren |

Quellenaktualität und Methodikaktualität getrennt anzeigen. Ein Methodikwechsel macht historische Nachweise nicht rückwirkend bedeutungslos, muss aber die Anwendbarkeit des früheren Ergebnisses transparent machen. Ohne vorhandene Modellkonfiguration oder Live-Provider erforderliche Vergleichsläufe als ausstehend deklarieren.

Reviewer-Konfiguration versionieren: Regeln, Prompts, Modell-/Providerkennung, verfügbare Modellversion, Parameter, Tool-/Schema-/Konverterversionen und Quellenmanifest. Provider ohne exakte Modellversion als Reproduzierbarkeitsgrenze dokumentieren. Änderungen durch normalen Repository-Review führen; gegen bekannte Fehler und Fehlalarme testen und wesentliche Bewertungsabweichungen begründen. Auf eine frühere Konfiguration zurückgehen können. Keine Behauptung identisch reproduzierbarer semantischer Ausgaben.

#### Geprüftes Baseline-Paket

Ein manifestbasiertes, schema-validiertes Paket bereitstellen, das die konkrete Kombination aus Dokumentversionen/-hashes, Beziehungsmodell, Autoritätsmatrix, Reviewkonfiguration, Reports, Belegvalidierungen, menschlichen Entscheidungen und offenen Ausnahmen festhält. Paket-ID, Commit und referenzierte Dateien prüfen. Paketänderung erzeugt eine neue Version; vergangene Pakete nicht überschreiben.

Paketstatus `candidate` oder `reviewed` ist keine normative Freigabe. Nur der bestehende menschliche Freigabeprozess darf einen Governance-Freigabestatus begründen. Freigabeentscheidung und verbleibende Einschränkungen referenzieren. Historische Betrachtung im Viewer als solchen Snapshot kennzeichnen; keine Darstellung als aktueller Livezustand. Vorhandene Release-/Evidence-Mechanismen wiederverwenden.

#### Gestaffelte Einführung und Nutzenbewertung

1. Phase 1 mit den in Abschnitt 3.1 konkret benannten bereinigten Auszügen und synthetischen Tests abschließen. Das ist kein Ersatz für einen Review der Originaldokumente.
2. Für Phase 2 Quellen, Provider und Datenfluss freigeben; Findings mit zuständigen Menschen als hilfreich, Fehlalarm, unklar oder nicht beurteilbar bewerten. Bekannte übersehene Fälle und Aufwand für Triage/Review erfassen.
3. Erst nach dokumentierter Pilotauswertung und Bestätigung der nötigen Quellen den realen vollständigen Satz und dessen operative Viewer-Nutzung planen. Viewer-Code und synthetische Vorschau können vorher in Phase 3 erstellt werden; die Entscheidung begrenzt den operativen Rollout. Fehlende Originale bleiben ein expliziter Blocker des Vollsatzes.

Pilotnachweis: beantwortet der Mechanismus nachvollziehbar „Welche Änderung betrifft welche anderen Dokumente und wo ist eine Entscheidung nötig?“ Auswertung enthält hilfreiche Findings/Fehlalarme mit Bezugsmenge, bekannte übersehene Fälle, Bearbeitungsaufwand, Ausführungszeit und soweit verfügbar Modellkosten. Unbekannte Fehler nicht als gemessene Erkennungsquote ausweisen. Rolloutkriterien gemeinsam mit Ownern festhalten; bei fehlender menschlicher Bewertung Infrastruktur vollständig liefern und Rollout als ausstehend melden. Keine zusätzlichen blockierenden inhaltlichen/semantischen Gates im ersten Release; bestehende technische Schutzmechanismen erhalten. Funktionsumfang nach diesem Workpackage stabil halten und weitere Änderungen aus Pilotbefunden ableiten.

## 7. Abnahmekriterien

Die folgenden Kriterien gelten für das Gesamtvorhaben und werden den Phasen aus Abschnitt 3.2 zugeordnet. Jedes Phasen-PR führt eine Abnahmematrix mit `pass`, `partial`, `blocked`, `not_run` oder `not_in_scope`, konkreten Nachweisen und offenen Punkten. Nicht erreichte Kriterien späterer Phasen bleiben offen; sie dürfen nicht durch bestandene Schema-, Unit- oder Validatorprüfungen als erfüllt gelten. Phase 1 ist ohne Provider und ohne vertrauliche Originale abnehmbar, wenn die hierfür definierten Kriterien bestanden sind und semantischer Review ausdrücklich `not_run` bleibt.

- [ ] Finding-Validator gemäß E.4 zwischen Modellantwort und Report implementiert; Quellenmanifest, Hash, Textbereich und Originalauszug deterministisch geprüft.
- [ ] Erfundenes Zitat, falsche Fundstelle, fremde Quelle und veralteter Hash werden erkannt und sichtbar quarantänisiert; keine bestätigte Coverage daraus.
- [ ] Quellenfakten, Interpretationen und Lösungsvorschläge sowie Belegstatus und menschliche Akzeptanz sind getrennt auswertbar.
- [ ] Reale Zitate mit unbegründeter Konfliktinterpretation werden nicht allein durch bestandene Belegprüfung fachlich bestätigt.
- [ ] Lückenbehauptungen enthalten Erwartungsbeleg, Suchscope und Grenzen; unvollständiger Scope erzeugt keine universelle Abwesenheitsbehauptung.
- [ ] `not_assessable`/`context_missing`, verworfene Findings und Provider-/Parserfehler im Report sichtbar; Modellkonfidenz ist kein Freigabekriterium.
- [ ] Review-Leitplanken E.1 in Workflow, Prompts und Reports umgesetzt; kein pauschaler grüner Konsistenz-/Compliance-Nachweis.
- [ ] Konflikte werden unter Quellenautorität, Geltungsbereich und normativer Stärke bewertet; ungeklärter Kontext bleibt sichtbar.
- [ ] Fachliche Beziehungsprüfung gemäß E.2 vorhanden: gültiger Link mit fachlich ungeeignetem Ziel wird als unzureichende Abdeckung erkannt.
- [ ] Linkgültigkeit, fachliche Abdeckung, menschliche Bestätigung und technische Verifikation sind getrennt auswertbar.
- [ ] Dokumentenkonsistenz und Implementierungsabdeckung gemäß E.3 getrennt ausgewiesen; fehlende Umsetzung und quellenlose ausführbare Regeln getestet.
- [ ] Policies/Templates ohne geeigneten Verifikationsnachweis werden nicht als nachweislich wirksame Durchsetzung dargestellt.
- [ ] Reports enthalten die vier getrennten Ergebnisbereiche mit Scope, Aktualität, Prüflücken und begründeter Coverage.
- [ ] Keine stille Harmonisierung; normative Konfliktauflösung erfordert nachvollziehbare menschliche Entscheidung.
- [ ] Bestehendes Quellenregister und Intake integriert; keine zweite widersprüchliche Autorität.
- [ ] Rolle/Skill und erforderliche Provideradapter des Reviewers vorhanden.
- [ ] Importworkflow reproduzierbar; Tabellen und offene Entscheidungen der Pilotquellen geprüft, Verluste dokumentiert.
- [ ] IDs über reine Textverschiebungen und Überschriftenumordnung stabil.
- [ ] Deterministische Regeln DCR-001 bis DCR-009 implementiert oder begründet an bestehende Regeln delegiert.
- [ ] Synthetische Fixtures mit kaputter Referenz, Rollenlücke, fehlender Verifikation und unzulässiger Candidate-Derivation werden erkannt.
- [ ] Gezielte semantische Pilotfälle mit widersprüchlicher Freigaberolle und Pflichten/Ausnahmen liefern nachvollziehbare Findings, wenn der Provider verfügbar ist; andernfalls ausstehende Abnahme explizit markieren.
- [ ] Beabsichtigte Wiederholungen und zulässige Synonyme werden differenziert behandelt.
- [ ] Full- und Incremental-Modus vorhanden; indirekte Auswirkungen, Löschungen, Umbenennungen und globale Modelländerungen getestet.
- [ ] Quellenänderungen machen alte Findings/Reviews sichtbar veraltet.
- [ ] Reports enthalten Scope, Quellenstand, Findings, offene Entscheidungen und nicht geprüfte Inhalte.
- [ ] Ohne Provider ist semantischer Status `not_run`; ohne Originale wird keine reale Migration behauptet.
- [ ] Keine unreviewte Quellenpromotion, normative Baseline-Änderung oder externe Veröffentlichung.
- [ ] Relevante vorhandene Validatoren und Tests bestanden; verbleibende Fehler transparent zugeordnet.
- [ ] Dokumentierte reale Pilotnachweise beziehungsweise genaue Input-Blocker und reproduzierbare synthetische Nachweise vorhanden.
- [ ] Bestehender Viewer gemäß Abschnitt I erweitert; Reviewausführung und schreibende Governance-Aktionen bleiben außerhalb des Viewers.
- [ ] Alle Pflichtansichten verfügbar, filterbar/verlinkbar und auf kleinen Bildschirmen sowie per Tastatur bedienbar.
- [ ] Quellen-/Artefaktänderungen erzeugen sichtbares `stale`; fehlendes Vergleichsmanifest erzeugt `unknown` statt falscher Aktualität.
- [ ] Keine Findings, nicht geprüft, Daten fehlen, Quarantäne und redigierte Inhalte eindeutig unterscheidbar; keine irreführenden bestätigten Summen.
- [ ] Öffentliche Allowlist-Projektion und interne Vollprojektion getrennt; Confidential-Canary-Test über öffentliche Builddateien bestanden.
- [ ] Sichere Text-/Markdown-/Linkdarstellung und Injection-Negativtests vorhanden; Fundstellen referenzieren den geprüften Stand.
- [ ] Viewer-Smoke-/Regressionstests und reproduzierbare lokale Vorschau dokumentiert; kein Deployment durch diesen Auftrag.
- [ ] Review-Betriebsbeschreibung und bestätigungsfähige Autoritätsmatrix vorhanden; unbestätigte Autorität wird nicht als Vorrangregel verwendet.
- [ ] Finding-Triage mit Owner, Priorität, nächster Aktion und Eskalationsweg modelliert; offene Zuständigkeiten und Termine sichtbar.
- [ ] Review-Ausgangsstand von normativer Baseline getrennt; neue/verschärfte Findings hervorgehoben, bestehende Probleme weiterhin sichtbar.
- [ ] Finding-IDs laufübergreifend stabil; Historie, Wiederöffnung, Zusammenführung/Aufteilung und scope-begrenzte Fehlalarmentscheidungen nachvollziehbar.
- [ ] Nicht erneut geprüfte Findings nicht als gelöst dargestellt; relevante Änderungen lösen Neubewertung früherer Entscheidungen aus.
- [ ] Trigger-/Scope-Matrix umfasst Quellen, Beziehungen, Autorität, Implementierung und Reviewmethodik; Quellen- und Methodikaktualität getrennt.
- [ ] Reviewer-Konfiguration versioniert, Regressionen geprüft und Rückkehr zur vorherigen Konfiguration dokumentiert; ausstehende Livevergleiche sichtbar.
- [ ] Schema-validiertes Baseline-Paket mit Manifest, Reports und Entscheidungen verfügbar; technische Prüfung erzeugt keine normative Freigabe.
- [ ] Pilotbewertung und Rolloutentscheidung dokumentiert oder ausdrücklich ausstehend; reale vollständige Einführung nicht fälschlich behauptet.

## 8. Teststrategie

Tests prüfen fachlich relevante Fehlerfälle statt nur Ausgabeformen zu spiegeln. Unit-Tests für Schemas, Referenzen, Finding-Lifecycle und Abhängigkeitsauflösung; Integrationstests für Import → Registrierung → Prüfung → Report. Negative Fixtures für Candidate-Grenzen und Dokument-Prompt-Injection. Konvertierung anhand repräsentativer Tabellen, Kommentare und Revisionen prüfen.

Semantische Tests verwenden einen kleinen kuratierten Fallkatalog mit erwarteten Konfliktkategorien und belegbaren Referenzen; keine exakte Formulierung oder vollständige Modellreproduzierbarkeit verlangen. Falls keine Live-Ausführung möglich ist, Testadapter und echte Laufnachweise unterscheiden.

Zusätzlicher verbindlicher Fallkatalog für v0.2:

| Fall | Erwartetes Verhalten |
| --- | --- |
| Widersprüchliche Freigaberollen im selben Kontext | Konflikt mit beiden Fundstellen und menschlichem Entscheidungsbedarf |
| Unterschiedliche Regeln für verschiedene freigegebene Profile | Kein bestätigter Widerspruch allein aus unterschiedlicher Formulierung |
| Empfehlung wird als Pflicht extrahiert | Verlust normativer Stärke erkannt |
| Formal gültiger Link auf eine fachlich ungeeignete Verifikation | Fachliche Abdeckung unzureichend; Linkprüfung kann trotzdem bestehen |
| Akzeptierte Anforderung ohne Umsetzung | Implementierungslücke, unabhängig vom Konsistenzresultat |
| Ausführbare Regel ohne akzeptierte Quellenbasis | Quellen-/Lineage-Lücke, keine automatische Legitimation |
| Vorhandene Policy ohne Wirksamkeitsnachweis | Umsetzung und Verifikation getrennt; Wirksamkeit nicht nachgewiesen |
| Verlust einer RACI-Zelle oder offener Revision | Konvertierungswarnung und betroffener Bereich nicht vollständig geprüft |
| Providerfehler oder abgeschnittener Kontext bei null Findings | Unvollständiger/nicht ausgeführter Review, kein grünes Gesamtergebnis |

Erkannte bekannte Fehler und Fehlalarme getrennt protokollieren. Kleine Pilotfallzahlen nicht als allgemeine statistische Zuverlässigkeit darstellen.

Verbindliche Halluzinations-Negativtests für v0.3:

| Fall | Erwartetes Verhalten |
| --- | --- |
| Erfundenes Zitat an existierendem Anker | Beleg `invalid`, Quarantäne mit Grund |
| Echtes Zitat aus anderer Quelle oder außerhalb des referenzierten Bereichs | Referenz-/Scopefehler, keine Belegannahme |
| Zitat mit entfernter Negation oder geändertem „sollte“/„muss“ | Textprüfung schlägt fehl |
| Valides Zitat mit altem Quellenhash | Beleg `stale`, erneute Prüfung erforderlich |
| Erfundenes Rollen-/Anforderungsziel | Nicht auflösbare ID, keine Aufnahme als Quellenfakt |
| Echtes Zitatpaar aus unterschiedlichen Geltungsbereichen | Kein bestätigter Konflikt allein aufgrund der Zitate |
| Lückenbehauptung bei fehlendem Dokument | Nur begrenztes „nicht gefunden“/nicht beurteilbar |
| Nicht registrierte externe Pflicht aus Modellwissen | Nicht als bestehende Governance-Anforderung akzeptiert |
| Zweites Modell stimmt unbelegter Aussage zu | Belegpflicht bleibt unverändert; keine Freigabe |
| Manipulierte Modellantwort bei fehlendem Provider | Testfixture klar von echtem Reviewlauf getrennt |

Tests für mechanische Belegprüfung ohne Live-Provider ausführbar machen. Tests der fachlichen Interpretation getrennt mit kuratierten Fällen und menschlich geprüften Erwartungen dokumentieren. Anzahl verworfener Aussagen berichtet die Belegprüfung, nicht die Gesamt-Halluzinationsrate.

Aktuelle Repository-Prüfungen aus AGENTS.md/CI übernehmen. Typische vorhandene Befehle:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

Neue Befehle und benötigte Dependencies in der Übergabe exakt angeben.

## 9. Scope-Grenzen

Zusätzliche Betriebs-Tests gemäß Abschnitt J: Wiederholung eines unveränderten Findings erhält seine ID; verschobene Zeilen erzeugen keinen neuen Konflikt; außerhalb des Incremental-Scope liegende Findings bleiben `not_reassessed`; geänderte Grundlagen öffnen Fehlalarm-/Ausnahmeentscheidungen zur Prüfung; zweifelhafte semantische Korrelation wird nicht automatisch zusammengeführt. Triggeränderungen, Konfigurations-Rollback und Manipulation/fehlende Dateien eines Baseline-Manifests testen. Baseline-Snapshot mit offenen Findings darf keinen Freigabestatus erhalten, nur weil sein Schema gültig ist.

- Keine automatische fachliche Freigabe oder Behebung normativer Konflikte.
- Lösungsvorschläge und mechanische Migration sind erlaubt; inhaltliche Entscheidungen bleiben als solche sichtbar.
- Keine neue Graphdatenbank, kein neues ALM-System und kein vollständiger Plattformumbau.
- Keine Behauptung vollständiger Compliance aus Coverage oder fehlenden Findings.
- Keine originalen vertraulichen Unternehmensdokumente in öffentliche Pfade/Reports übernehmen.
- Keine neuen blockierenden semantischen Gates im ersten Release.
- Kein Merge und keine Veröffentlichung durch diesen Auftrag.

## 10. Erwartete Abschlussübergabe von Codex

1. Implementierte Fähigkeiten und verwendete Repository-Komponenten.
2. Liste geänderter Dateien und ADR.
3. Tatsächlich importierte Quellen mit Version/Hash und verbleibenden Inputs.
4. Exakte Import-/Reviewbefehle sowie Beispielreports.
5. Test- und Pilotresultate, getrennt nach deterministisch, semantisch und nicht ausgeführt.
6. Offene fachliche Entscheidungen und Einschränkungen.
7. Branch beziehungsweise Draft-PR-Link mit reviewfähiger Beschreibung.
8. Review-Betriebsbeschreibung, Autoritätsmatrix, Ausgangsstand, Baseline-Manifest und Pilot-/Rolloutentscheidung einschließlich ausstehender menschlicher Bewertungen.

## 11. Direkt verwendbarer Startprompt

> Bereite Phase 1 von WP-DCR-001 in einem eigenen Änderungssatz vor. Phase 0 wurde auf Basis des Commits `a8fc36f3de7f33cd2a26dff94f9a28985e78d64f` angenommen. Verwende ausschließlich `DSCB-STD-REQ-001`, `PRA-STD-REQ-001` und synthetische Fixtures. Beziehe die fünf lokal bereitgestellten, unregistrierten Dateien nicht ein; kopiere oder veröffentliche keine ihrer Inhalte. Semantische Verarbeitung und Viewer bleiben aufgeschoben. Trenne Schema, Generator, deterministische Prüfungen und Tests von der Phase-0-Entscheidung. Führe spätere Phasen nur nach ihren jeweiligen Freigabetoren aus. Bewahre Quellenautorität und Candidate-Derivationsgrenzen. Keine automatische Quellenfreigabe, keine normative Konfliktentscheidung, kein Merge.
