# Closed-Loop Governance: Umsetzungsplan

Stand: 12. September 2026. Geprüfter Ausgangspunkt: Repository-Commit
`5311182c220548474fcd90b04c38dc46b144937a`.

Status: Die Umsetzungsrichtung wurde vom Maintainer bestätigt. Dieses Dokument
plant die technische Umsetzung; die beschriebenen neuen Laufzeitfähigkeiten sind noch
nicht implementiert. Die Planung ist in
[GCR-2026-060](../../governance/change-requests/GCR-2026-060-closed-loop-governance-plan.md)
klassifiziert.

## Fortschritt CLG-01

Der [Vertragsstand 0.1.0](../evidence/governance-lifecycle-contract.md) enthält
additive Schemas, synthetische Beispiele und ausführbare Offline-Prüfungen.
Das [Entscheidungsblatt](../evidence/governance-lifecycle-pilot-decisions.md)
hält offene Live-Zuordnungen fest. Die vollständige Lifecycle-Laufzeit ist
weiterhin nicht implementiert. CLG-01 ist erst nach erfolgreicher Validierung
und Merge seines PRs abgeschlossen; danach folgt CLG-02 mit Kern und Adapter.

## Ziel und erster Pilot

Ein Finding soll durch einen vollständig nachvollziehbaren Ablauf geführt werden:

```text
Akzeptierte Beobachtung mit Fehler
  → Finding
  → nachgewiesene menschliche Entscheidung
  → zugeordnete Behebung
  → neue, passende Evidenz und erneute Bewertung
  → nachgewiesene menschliche Abschlussfreigabe
  → Abschluss
  → Wiedereröffnung bei einem tatsächlich neueren Fehler
```

Der erste Pilot verwendet das bestehende Self-Security-Kriterium **GRS-002**,
`pull_request_review_required`, für den Schutz von `main`. Das Modell
`model/controls/governance-repository-security.yaml` und
`scripts/assess_governance_repository_security.py` liefern dafür bereits
Kriterium-ID, Ergebnis, Profilversion, Repository und Beobachtungszeit.
Der [Self-Security-Betriebsleitfaden](../security/governance-repository-self-security.md)
beschreibt die heutige Auswertung.

Wir beginnen mit ausdrücklich synthetischen, schema-konformen Reports und einer
separaten Testidentität. Dabei wird kein echter Branchschutz abgeschaltet.
Anschließend folgt die Abnahme mit aktuell erfasster Evidenz und tatsächlich
zugeordneten Verantwortlichen. Ein fehlender oder bereits behobener Live-Fehler
wird nicht künstlich als offenes Finding angelegt. Die vollständige Fehlerfolge
bleibt in diesem Fall ein nachgewiesener Testlauf.

Der vorhandene Self-Security-Report allein ist noch kein vertrauenswürdiger
Lifecycle-Eingang: Sein Adapter muss zusätzlich den unveränderlichen Snapshot,
Digest, Erzeugungskontext und Akzeptanznachweis erfassen. Generierte aktuelle
Reports sind Ansichten und ersetzen diesen Nachweis nicht.

## Umsetzung in abnehmbaren Paketen

CLG-01 bis CLG-05 werden jeweils als eigener PR umgesetzt; Abhängigkeiten werden
in dieser Reihenfolge bearbeitet. Ein Paket ist fertig, wenn seine Abnahme
bestanden und der zugehörige PR nach den geltenden Repository-Regeln gemergt ist.

| Paket | Konkretes Ergebnis | Abnahme | Voraussetzung |
|---|---|---|---|
| **CLG-01: Verträge** | Lifecycle-Vertragsdokument, additive Schemas und gültige/ungültige Beispiele für Beobachtung, Entscheidung, Ereignis, Behebung und Abschluss; offene organisatorische Zuordnungen ausdrücklich markiert | Die untenstehenden Verträge und Testfälle sind eindeutig; Beispiele werden gegen die Schemas geprüft; Testfreigaben sind vom späteren Betriebsprofil unterscheidbar | Dieser Umsetzungsplan |
| **CLG-02: Finding und Ereignisse** | Deterministischer Kern, GRS-002-Adapter, unveränderliche Beobachtungen/Ereignisse und daraus erzeugter Finding-Index | Wiederholte Zustellung ist idempotent; Konflikte, veraltete Revisionen und verspätete Beobachtungen werden korrekt behandelt; Wiederaufbau ergibt denselben Index | CLG-01 |
| **CLG-03: Entscheidung und Behebung** | Validierter Intake menschlicher Entscheidungen, Bindung der Freigabe an Inhalt und Revision, Zuordnung einer Behebung mit Owner und Zieltermin | Unberechtigte, zurückgezogene oder nach Inhaltsänderung veraltete Freigaben werden abgewiesen; eine Bot-Aktion erzeugt keine menschliche Entscheidungsbefugnis | CLG-02 |
| **CLG-04: Abschluss und Pilotabnahme** | Evidenzgebundener Abschluss, Wiedereröffnung, kleiner JSON/Markdown-Bericht, ausführbares Pilot-Runbook und eng begrenzte Integration des Betriebs-Publishers | Vollständiger Ablauf und Negativfälle bestanden; Testlauf und Live-Beobachtung getrennt ausgewiesen; zuständige Menschen nehmen den Betriebsablauf ab | CLG-03; Betriebszuordnungen und Akzeptanzprofil für den Live-Anteil geklärt |
| **CLG-05: Befristete Ausnahmen** | Anbindung bestehender Waiver-/Exception-Verträge, Teilabdeckung, Ablauf, Widerruf und erneuter Entscheidungsbedarf | Teil-Waiver verdeckt keine Restabweichung; Ablauf funktioniert mit vorgegebenem Auswertungszeitpunkt; Risikobilligung zählt nicht als erfolgreiche Behebung | CLG-04; vorhandene Autoritäten und gegebenenfalls genehmigte Erweiterungen abgebildet |
| **CLG-06: Ausbau** | Weitere Ergebnisadapter, Viewer, Portfolio und belastbare Kennzahlen; anschließend optionale, modellneutrale KI-Unterstützung | Jeder Adapter weist Granularität und Kontext nach; Kennzahlen folgen den Ereignissen; Kernablauf funktioniert vollständig ohne LLM | CLG-05; Priorisierung anhand der Piloterfahrung |

CLG-01 bis CLG-04 bilden den ersten Meilenstein. CLG-06 ist ein nachgelagerter
Backlog, der vor seiner Umsetzung in einzelne Adapter-, Reporting- und
KI-Änderungen zerlegt wird. Umfang und Aufwand werden nach CLG-01 anhand der
festgelegten Verträge neu eingeschätzt; Kalendertermine sind noch nicht zugesagt.

## Verträge für CLG-01

### 1. Entscheidungsbefugnis und Freigabenachweis

Eine Freigabe referenziert mindestens die Entscheidung, ihren kanonischen
Inhaltsdigest, die erwartete Finding-Revision, den Geltungsbereich, die
authentifizierte Person, die einschlägige Rolle samt versionierter Zuordnung,
den Freigabezeitpunkt und den verifizierbaren Freigabenachweis. Änderungen an
freigegebenem Inhalt erfordern einen passenden neuen Nachweis. Ablehnung und
Widerruf werden als neue Datensätze behandelt.

Ein technischer PR-Merge und eine fachliche Governance-Entscheidung werden
getrennt geprüft. Ein Feld `decision_maker_type: human`, eine Git-Signatur oder
die Ausführung durch ein Werkzeug unter einem Benutzerkonto genügt allein
nicht. Der erste Adapter muss dokumentieren, welcher Freigabekanal die
Identität, Rolle, bewusste Zustimmung und Bindung an den Inhalt belegt. Eine
kleine, separat kontrollierte Rollenbindung ist als Pilotlösung möglich; ein
Enterprise-Verzeichnis ist keine Voraussetzung.

Für Waiver gilt bereits `model/waivers/waiver-authorities.yaml`:

| Risikoklasse | Bestehende Freigabeautorität |
|---|---|
| `low`, `medium` | DevSecOps Governance Board |
| `high_cybersecurity` | CISO |
| `high_safety` | Safety Authority |
| `critical` | CDO und CSCSO gemeinsam |

Diese Waiver-Zuständigkeiten werden nicht pauschal auf Behebungsentscheidungen
oder Abschlüsse übertragen. Die dafür berechtigten Rollen und realen Personen
sind vor dem Live-Intake zu bestätigen. Die Severity eines Findings ist nicht
automatisch seine Waiver-Risikoklasse. Neue verbindliche Zuständigkeiten oder
SLA-Vorgaben durchlaufen bei Bedarf den Source-Document-Intake und den
Governance-Change-Prozess. Die Beispielsfristen des ursprünglichen Workpackages
sind keine bereits genehmigte Betriebsvorgabe.

### 2. Identität, Ereignisse und Zustand

Der Finding-Fingerprint erhält eine Version und eine dokumentierte
Kanonisierung. Er umfasst mindestens Repository/Consumer, Domäne, Regel,
Finding-Typ und normalisierten Ressourcen-/Geltungsbereich. Beobachtungs-ID,
Finding-ID und Ereignis-ID sind unterschiedliche Identitäten. Profil- und
Policyversionen bleiben an der Beobachtung erhalten; ihre Vergleichbarkeit
wird ausdrücklich geprüft.

Akzeptierte Beobachtungen, Entscheidungen und Lifecycle-Ereignisse sind
unveränderliche Datensätze. Änderbare aktuelle Zustände sind ausschließlich
generierte Projektionen daraus. Konfigurationen liegen in versionierten
Modellen. Es gibt keine zweite, manuell gepflegte Finding-Wahrheit.

Ereignisse tragen Aggregat-ID, Revision/Vorgängerbezug, fachlichen Zeitpunkt,
Erfassungszeitpunkt, Schema-/Policyversionen und Quellenbezug. Schreiboperationen
prüfen die erwartete Revision gegen den aktuell akzeptierten Stand; zwei PRs
auf derselben Revision dürfen nicht unbemerkt beide wirksam werden. Die Prüfung
muss deshalb auch den späteren Merge-Stand absichern. Unsichere Kausalität oder
widersprüchliche Evidenz führt zu einem sichtbaren Klärungsbedarf.

Eine erneut gelieferte identische Beobachtung erhöht weder Ereigniszahl noch
Occurrence-Zähler. Eine neue unabhängige Beobachtung desselben Fehlers wird
dagegen am bestehenden Finding erfasst. Verspätet eingegangene ältere Fehler
bleiben in der Historie, ohne einen durch neuere passende Evidenz belegten
Abschluss aufzuheben. Laufende Auswertungen erhalten einen expliziten
`as_of`-Zeitpunkt; Replay greift nicht auf die aktuelle Uhrzeit zurück.

### 3. Ergebnisadapter und Evidenz

Für jeden Adapter werden unterstützte Eingabeschemata, Regel- und
Ressourcenidentität, Granularität, akzeptierter Kontext und Fehlerverhalten
beschrieben. Nur akzeptierte Mainline-, Release- oder ausdrücklich freigegebene
Kontexte beeinflussen den offiziellen Lifecycle. PR-, Branch-, Diagnose- und
Testdaten bleiben als solche erkennbar.

GRS-002 liefert ein konkretes Einzelkriterium. Ein DevSecOps-Summenergebnis mit
einem fehlgeschlagenen Gate liefert dagegen nicht automatisch einzelne
Control-Findings. Unbekannte Zuordnungen bleiben unbekannt und werden sichtbar;
ein LLM darf keine fehlenden Regel-IDs oder Freigaben rekonstruieren.

Trust wird gemäß `schemas/evidence-trust-record.schema.json` beschrieben:
`unverified`, `integrity_verified`, `provenance_verified`, `attested`. Die
Mindeststufe, erforderlichen Einzelprüfungen, erlaubten Quellen, Frischegrenzen
und Replay-Regeln des Piloten werden in CLG-01 als Akzeptanzprofil festgelegt
und vor Live-Nutzung bestätigt. Ein Gesamtlevel ersetzt keine Prüfung der
relevanten Checks; fehlende Nachweise erlauben keinen Abschluss.

### 4. Abschluss, Wiedereröffnung und Behandlung

Der erste Abschlussgrund ist erfolgreiche Behebung. Dazu gehören eine
passende Behebungsreferenz, neuere akzeptierte Evidenz für dieselbe Regel und
denselben Geltungsbereich, eine kompatible Baseline/Profil-/Policyversion,
bestandene Trust-/Frische-/Replay-Prüfungen sowie die befugte menschliche
Freigabe des konkreten Abschlusses. Ein abgeschlossenes Arbeitsticket, ein
Gesamt-PASS oder ein nicht erneut geprüftes Kriterium reicht nicht aus.

Eine neue akzeptierte Fehlerbeobachtung nach dem Abschluss öffnet das Finding
erneut; der frühere Abschluss bleibt historisch erhalten. Fachlich ältere oder
unvergleichbare Beobachtungen werden nicht allein aufgrund ihres späteren
Intake-Zeitpunkts als neuer Fehler behandelt.

Ab CLG-05 werden Finding-Zustand, Behebungsfortschritt und Ausnahmeabdeckung
getrennt projiziert. Behebung und gültiger Waiver können gleichzeitig bestehen.
Teilabdeckung lässt den übrigen Geltungsbereich offen. Risikobilligung ist eine
eigene, befristete Behandlung mit überprüfbarem Ablauf und eigener Zählung;
weitere Abschlussgründe brauchen jeweils einen eigenen Nachweisvertrag.

## Geplanter Dateiumfang

Die folgenden neuen Pfade sind Planungsvorschläge, keine bereits vorhandenen
Schnittstellen. CLG-01 legt die endgültigen Namen und Schemas fest.

| Bereich | Vorgeschlagener Ort / Wiederverwendung |
|---|---|
| Vertragsdokument | `docs/operations/evidence/governance-lifecycle-contract.md` |
| Neue additive Verträge | `schemas/governance-lifecycle-*.schema.json` |
| Versionierte Lifecycle-Konfiguration | `model/governance/lifecycle/` |
| Akzeptierte unveränderliche Datensätze | `governance/lifecycle/observations/`, `decisions/`, `events/` als getrennte Unterordner |
| Generierter aktueller Zustand | `status/governance-lifecycle-index.json` |
| Deterministischer Kern und Adapter | `scripts/lib/governance_lifecycle/` |
| Tests und synthetische Fälle | `tests/test_governance_lifecycle*.py`, `tests/fixtures/governance-lifecycle/` |
| Pilotanleitung und kleiner Bericht | `docs/demos/`, skripterzeugt unter `generated/reports/` |

Vorhandene Bausteine werden gezielt wiederverwendet: Digest-/Append-only-Muster
aus `scripts/lib/result_ledger.py`, vorhandene Evidence-Trust-Verträge,
`schemas/waiver.schema.json`, `schemas/architecture-exception.schema.json` und
der Aktionskatalog `architecture/remediation-actions.yaml`. Der Aktionskatalog
beschreibt Vorschläge; konkrete Behebungsfälle erhalten eigene Instanzen.

`scripts/publish_operational_update.py` unterstützt die neuen Pfade bisher
nicht. Seine Erweiterung benötigt einen eigenen eng begrenzten Schreibumfang.
Automatisierte Beobachtungen und vorgeschlagene Entscheidungen werden von
akzeptierten menschlichen Entscheidungen getrennt validiert. Ein Pfad in einer
Allowlist oder ein akzeptierter Bot-PR verleiht keine Entscheidungsbefugnis.

## Nachzuweisende Pilotfälle

| ID | Fall | Erwartetes Ergebnis |
|---|---|---|
| P01 | GRS-002 FAIL → gültige Entscheidung → Behebung → neue passende PASS-Evidenz → gültige Abschlussfreigabe | Ein Finding, vollständige Kette und begründeter Abschluss |
| P02 | Dieselbe Beobachtung wird erneut zugestellt | Keine doppelte Beobachtung, kein zusätzliches Ereignis und keine erhöhte Occurrence-Zahl |
| P03 | Zwei Änderungen erwarten dieselbe Revision | Zweite konkurrierende Änderung wird zurückgewiesen oder zur erneuten Prüfung vorgelegt |
| P04 | Eine ältere FAIL-Beobachtung trifft nach neuerem PASS und Abschluss ein | Historie ergänzt; Finding bleibt geschlossen |
| P05 | Eine tatsächlich neuere akzeptierte FAIL-Beobachtung trifft nach Abschluss ein | Dasselbe Finding wird wiedereröffnet; Abschlussgeschichte bleibt erhalten |
| P06 | Gesamt-PASS, anderes Repository/Scope, inkompatible Regelversion oder Kriterium nicht geprüft | Kein Abschluss aufgrund dieser Evidenz |
| P07 | Erforderlicher Trust-Check fehlt/schlägt fehl, Evidenz ist veraltet oder Replay ist konfliktbehaftet | Abschluss verweigert; Ursache sichtbar |
| P08 | Rolle fehlt, Zustimmung ist nur behauptet, Freigabe wurde widerrufen oder der Inhalt danach geändert | Entscheidung bzw. Abschluss wird nicht akzeptiert |
| P09 | Synthetischer oder nicht akzeptierter Branch-/PR-Report wird als Live-Evidenz eingereicht | Keine Wirkung auf den offiziellen Zustand |
| P10 | Ledger mit festem `as_of` vollständig neu projizieren | Gleiche fachliche Zustände und Kennzahlen; unveränderliche Ursprungsdaten |
| P11, ab CLG-05 | Teil-Waiver, parallele Behebung, Ablauf und Widerruf | Restabweichung sichtbar; Ausnahmeende erzeugt Entscheidungsbedarf; keine gezählte Behebung durch Risikobilligung |

## Nächster konkreter Arbeitsauftrag

**CLG-01 prüfen und abschließen:** Den Vertragsstand, die Schema-Gruppe,
Beispiele, Negativtests und das Entscheidungsblatt im eigenen PR prüfen.
Die ausführbare Abdeckung und noch ausstehenden Runtime-Prüfungen stehen im
[Vertragsdokument](../evidence/governance-lifecycle-contract.md).

**Nach dessen Merge CLG-02 umsetzen:** Deterministischen Finding-/Ereigniskern,
GRS-002-Adapter, unveränderliche Speicherung und daraus erzeugten Index bauen.
Abnahmefälle sind insbesondere persistente Idempotenz, Konflikte und
Merge-Revisionen sowie reproduzierbare Projektion mit festem `as_of`.
Synthetische Identitäten bleiben ausschließlich für Tests bestimmt;
ungeklärte Betriebszuordnungen bleiben ausdrücklich offen.

Der Maintainer koordiniert anschließend die Benennung der Entscheidungs- und
Abschlussverantwortlichen mit den zuständigen Governance-Rollen. Der technische
Vertragsentwurf und die Offline-Tests können schon vorher entstehen. Der
Live-Intake benötigt die dokumentierten Zuordnungen und den bestätigten
Freigabenachweis. Die Beispielsrollen im ursprünglichen Workpackage ersetzen
diese Klärung nicht.

Jeder Implementierungs-PR enthält die eigene Intake-/Impact-Klassifikation und
passende Tests. Vor dem Commit laufen
`./scripts/bootstrap_validation_env.sh` und `./scripts/validate_all.sh`; für
Dokumentation zusätzlich ein strikter MkDocs-Build. Reviewer werden nach den
[bestehenden Rollen](../../governance/governance-roles-and-agent-profiles.md)
zugeordnet: Governance-Analyse, Evidence/Intake und Repository-Pflege; bei
Waiver-, Architektur- oder OPA-Änderungen kommen die betroffenen Fachrollen hinzu.

Nach CLG-04 wird die Pilotabnahme dokumentiert und über den nächsten
Repository-Release entschieden. Dieser Plan selbst benötigt keinen Release.
Neue Lifecycle-Funktionen beginnen report-only. Bestehende Baselines,
Consumer-Einstellungen und Freigaberegeln werden in ihren eigenen geregelten
Änderungsverfahren behandelt.

## Bezug zum ursprünglichen Workpackage

Eingangsdokument: `WP_Closed_Loop_Governance_Decision_Remediation_Runtime.md`,
lokaler Entwurf mit 57 Arbeitspaketen; geprüft am 12. September 2026.
SHA-256: `8f53edbbac187f5225e1f792ee0b3ca367cb82fbfd9821b5beb3b072b0684a0b`.
Der Entwurf bleibt als Eingang erhalten; dieser Plan beschreibt die geprüfte
Umsetzungsreihenfolge und die Präzisierungen für den Piloten.

| Themen des Entwurfs | Einordnung in diesem Plan |
|---|---|
| WP-01–05, WP-08–13, WP-22–23, WP-29–32 | Verträge und Kern in CLG-01–04 |
| WP-04, WP-17, WP-26–27, WP-34–35, WP-54–56 | Autorität, Abschlussprüfung und Schreibgrenzen bereits im ersten Meilenstein; keine Abhängigkeit von einer neuen KI-Rolle |
| WP-06–07, WP-24, WP-48 | Befristete Ausnahmen in CLG-05 |
| WP-14–16, WP-18–21, WP-33, WP-40–41, WP-49 | Erweiterungsbacklog CLG-06; Kennzahlen und KI nach dem Kernnachweis, SLA-Fristen mit eigener fachlicher Entscheidung |
| WP-25, WP-28, WP-36–39, WP-42–47, WP-53 | Dokumentation, Tests, Betriebs- und Release-Prüfung begleiten jedes betroffene Paket |
| WP-50–52 | API-, Enterprise- und Föderationsthemen bleiben zukünftige Integrationsmöglichkeiten |
| WP-57 | Die Reihenfolge dieses Plans zieht den vollständigen Piloten vor breite Projektionen und KI-Unterstützung |
