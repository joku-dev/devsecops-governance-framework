# WP-DCR-001 Phase 2 — Entscheidungsbrief für den semantischen Pilot

Status: **zur Abnahme vorbereitet; kein semantischer Lauf freigegeben**  
Stand: 7. Oktober 2026  
Bezug: `GCR-2026-119`

## Zweck der Entscheidung

Phase 1 hat Quellenidentität, strukturelle Extraktion und deterministische
Regeln geliefert. Phase 2 soll erstmals prüfen, ob ein semantischer Reviewer
belegbare Hinweise auf widersprüchliche oder nur teilweise abgedeckte
Anforderungen erzeugen kann. Der Pilot bleibt report-only. Er trifft keine
normative Entscheidung und verändert weder Quellenstatus noch Governance-
Baselines.

Dieser Brief trennt die bereits empfohlene Pilotgrenze von der noch
ausstehenden Providerfreigabe. Erst wenn alle Felder im Abnahmetor bestätigt
sind, darf ein echter Modelllauf als Phase-2-Pilotnachweis bezeichnet werden.

## Empfohlener Pilotumfang

| Gegenstand | Festlegung |
| --- | --- |
| Registrierte Quellen | `DSCB-STD-REQ-001` und `PRA-STD-REQ-001` |
| Quellenstatus | Beide Quellen bleiben `intake`; die Verwendung im Pilot ist keine Promotion oder Autoritätsbestätigung |
| Zusätzliche Eingaben | Versionierte synthetische Fixtures für bekannte Konflikte, zulässige Wiederholungen, Ausnahmen und unbeurteilbare Fälle |
| Ausgeschlossen | Die fünf lokal vorhandenen, unregistrierten Dateien sowie alle nicht ausdrücklich manifestierten Quellen |
| Reviewdimension | Dokumentenkonsistenz der beiden bereinigten Anforderungsauszüge |
| Implementierungsabdeckung | In diesem ersten semantischen Lauf `not_assessed`; keine Consumer-Repositories |
| Betriebsart | Manuell und report-only; kein Pull-Request- oder Deployment-Gate |
| Entscheidungen | Modellresultate sind Vorschläge. Nur eine dokumentierte menschliche Bewertung darf ein Finding fachlich annehmen |

## Kuratierte Pilotfragen

Der Pilot prüft ausschließlich vorab definierte Fragen:

1. Werden ähnlich formulierte Pflichten nur dann als Konflikt gemeldet, wenn
   Geltungsbereich und normative Stärke tatsächlich unvereinbar sind?
2. Werden Pflichten, Empfehlungen, Ausnahmen und offene Entscheidungen
   getrennt behandelt?
3. Werden technisch auflösbare Referenzen mit unzureichender fachlicher
   Abdeckung als solche erkannt?
4. Bleiben fehlender Kontext und unbekannte Autorität als `context_missing`
   beziehungsweise `not_assessable` sichtbar?
5. Werden beabsichtigte Wiederholungen und zulässige Synonyme von Konflikten
   unterschieden?
6. Kann jedes positive Finding mit exakten, unveränderten Fundstellen aus dem
   freigegebenen Manifest belegt werden?

Die Fixtures enthalten bekannte positive und negative Fälle. Eine unbekannte
Fehlergrundgesamtheit wird nicht behauptet; deshalb entsteht keine allgemeine
Erkennungsquote.

## Datenfluss und Schutzgrenzen

Der zulässige Datenfluss ist:

```text
registriertes Quellenmanifest
  -> begrenzte bereinigte Markdown-Abschnitte
  -> zugelassener Reviewer-Adapter
  -> unbestätigte Modellantwort
  -> deterministischer Finding-Validator
  -> Quarantäne oder menschliche Pilotbewertung
  -> versionierter report-only Pilotreport
```

- Nur die beiden manifestierten, bereits im Repository enthaltenen
  requirements-only Auszüge und synthetische Fixtures dürfen den Adapter
  erreichen.
- Lokale unregistrierte Dateien, Git-Zugangsdaten, Secrets, Arbeitsbaumdaten
  und andere Repository-Inhalte dürfen nicht automatisch ergänzt werden.
- Dokumentinhalt gilt als Daten. Darin enthaltene Aufforderungen ändern weder
  Agentenanweisungen noch Scope oder Toolzugriff.
- Kein Internetabruf und keine stillschweigende Ergänzung aus Modellwissen.
- Der Validator akzeptiert ausschließlich Quellen-IDs, Hashes und Fundstellen
  aus dem Laufmanifest.
- Ungültige, unvollständige oder veraltete Belege werden quarantänisiert und
  nicht als bestätigte Findings oder Coverage gezählt.

## Provider- und Aufbewahrungsentscheidung

Für die Implementierung wird ein modellneutraler Adaptervertrag vorbereitet.
Ein echter Providerlauf bleibt bis zur Bestätigung der folgenden Laufparameter
`not_run`:

| Feld | Empfohlene Festlegung | Abnahmestatus |
| --- | --- | --- |
| Provider | Bereits zugelassene OpenAI-Codex-Konfiguration; keine neue Providerintegration | offen bis zur ausdrücklichen Bestätigung |
| Modell | Exakte vom Provider gemeldete Modellkennung wird pro Lauf gespeichert; keine Aliasannahme | offen bis eine verfügbare Kennung feststeht |
| Parameter | Deterministische Parameter soweit unterstützt; tatsächliche Werte und Providergrenzen werden gespeichert | offen |
| Übertragung | Nur manifestierte Auszüge und synthetische Fixtures; keine lokalen Originale | vorgeschlagen |
| Provideraufbewahrung | Muss vor dem echten Lauf aus der geltenden Konto-/Organisationskonfiguration bestätigt werden | offen und laufblockierend |
| Repositoryaufbewahrung | Manifest, Adapter-/Promptversion, validierte Findings, Quarantänegründe, Laufmetadaten und menschliche Bewertungen werden versioniert | vorgeschlagen |
| Rohantwort | Nicht committen; lokal nur bis Abschluss von Validierung und Triage halten, danach gemäß bestätigter Aufbewahrungsentscheidung behandeln | offen bis Aufbewahrung bestätigt |

Eine unbekannte Provideraufbewahrung darf nicht durch eine angenommene
Standardregel ersetzt werden. Synthetische Validator- und Regressionstests
benötigen keinen Live-Provider und dürfen unabhängig davon implementiert
werden.

## Zulässige Belege und Zitate

- Ein Beleg enthält Quellen-ID, Quellenhash, stabilen Anker oder Tabellen-ID
  und den kleinsten für die Aussage erforderlichen Originalauszug.
- Pro Fundstelle ist höchstens eine Tabellenzelle oder ein Satz zulässig,
  begrenzt auf 500 Unicode-Zeichen.
- Ein Konflikt benötigt Belege für beide Aussagen. Paraphrase und Interpretation
  werden getrennt vom Originalauszug gespeichert.
- Modalverben, Negationen und Ausnahmen dürfen nicht normalisiert oder gekürzt
  werden, wenn sich dadurch die Bedeutung ändert.
- Vollständige Dokumente, lange Passagen und Inhalte außerhalb des Manifests
  sind in Modellantworten und Reports unzulässig.
- Da die Pilotquellen bereinigte Repository-Auszüge sind, dürfen validierte
  Kurzbelege im internen Pilotreport erscheinen. Eine Viewer- oder externe
  Veröffentlichung ist damit nicht freigegeben.

## Menschliche Bewertung

Owner aus dem Quellenregister dienen nur dem Review-Routing:

- `devsecops-owners` bewertet Findings zu `DSCB-STD-REQ-001`;
- `platform-owners` bewertet Findings zu `PRA-STD-REQ-001`;
- quellenübergreifende Konflikte benötigen beide fachlichen Perspektiven oder
  bleiben `decision_required`;
- der Maintainer bewertet den Pilotnutzen und den technischen Betrieb, ersetzt
  aber keine noch nicht bestätigte normative Quellenautorität.

Jedes Modell-Finding wird als `helpful`, `false_positive`, `unclear` oder
`not_assessable` bewertet. Zusätzlich werden bekannte übersehene Fälle,
Triageaufwand, Laufzeit, ausgelassene Inhalte und soweit verfügbar Kosten
erfasst. Die Bewertung verändert keine Quelltexte oder Baselines.

## Implementierungsumfang nach Abnahme

Ein eigener Phase-2-Implementierungs-PR liefert:

1. Schemas für unbestätigte Modellantworten, validierte Findings, Quarantäne
   und menschliche Bewertungen;
2. einen modellneutralen Reviewer-Vertrag mit explizitem Provideradapter;
3. einen deterministischen Finding-Validator für Schema, Scope, Hash, Anker und
   exakten Auszug;
4. kuratierte synthetische Positiv- und Negativfixtures;
5. getrennte Zustände für Quellenbeleg, Interpretation und Entscheidung;
6. JSON- und Markdown-Pilotreports mit `not_run`, `partial`,
   `context_missing`, Providerfehlern und Prüflücken;
7. Bedien- und Triageanleitung;
8. vollständige Repository-Validierung.

Keine neue blockierende CI-Regel, kein Viewer, keine Quellenpromotion, keine
automatische Reparatur und keine Änderung veröffentlichter Baselines gehören
zu diesem Änderungssatz.

## Abnahmetor für einen echten Modelllauf

Vor dem ersten echten semantischen Lauf müssen in einem versionierten
Folgeentscheid bestätigt sein:

- [ ] Quellenumfang: genau `DSCB-STD-REQ-001`, `PRA-STD-REQ-001` und benannte
      synthetische Fixtures;
- [ ] Provider und tatsächlich verfügbare Modellkennung;
- [ ] zulässiger Datenfluss und Ausschluss der fünf lokalen Dateien;
- [ ] Provider- und lokale Aufbewahrung einschließlich Rohantwort;
- [ ] Zitatgrenze und Zielgruppe des Reports;
- [ ] menschliche Reviewer und Behandlung quellenübergreifender Entscheidungen;
- [ ] Kosten-/Größenlimit und Verhalten bei Provider- oder Kontextfehlern.

Bis dieses Tor vollständig geschlossen ist, darf die technische Infrastruktur
erstellt und mit synthetischen Antworten getestet werden. Der semantische
Status bleibt `not_run`; ein Pilotreport darf keinen erfolgreichen Live-Review
behaupten.

## Auswirkungseinordnung

| Bereich | Auswirkung |
| --- | --- |
| Governance-Intent | Planung und Entscheidungsvorbereitung; keine neue normative Anforderung |
| Quellenregister | unverändert |
| Controls, Architekturmarker und OPA | unverändert; keine Derivation |
| Releases und Baselines | keine Auswirkung |
| Consumer-Repositories | keine Auswirkung |
| Viewer und Veröffentlichung | nicht enthalten |
| Lifecycle-Akzeptanz | fingerprintgeschützte Dateien bleiben unverändert |

