# GCR-2026-155 — Nachvollziehbare Agentenarbeit und Review-Abschluss

## Anlass

Der Maintainer beauftragt die Professionalisierung der Agentennutzung. Der
produktive Dispatcher importierte Routing-Code aus Tests, überging gestagte
Änderungen in bestimmten Zuständen und deckte aktuelle Workbench-, Requirements-
und Adapter-Pfade unzureichend ab. Eine zweite verkürzte Prüfungsliste konnte von
den Rollenverträgen abweichen. Rollenwahl allein liefert keinen revisionsgebundenen
Ausführungsnachweis.

## Artifact Intake Classification

| Feld | Einordnung |
|---|---|
| Typ und Owner | Operational agent contracts, implementation, tests and documentation; Governance Platform Maintainers |
| Neue Artefakte | `.agents/review-protocol.yaml`, `scripts/lib/agent_routing.py`, `scripts/lib/agent_review.py`, Harness-Regressions und dieser GCR |
| Source Document Intake | no; keine normative Quelldatei oder Registeränderung |
| Governance-Effekt | Report-only review support; keine Änderung an OPA oder Consumer-Enforcement |
| Release-Klassifikation | Agentensystem-Änderung benötigt Release-Manager-Review (`candidate` im Router); keine neue Baseline oder Veröffentlichung |
| Evidenzvertrag | Privates operatives Review-Paket; keine Änderung akzeptierter Consumer-Evidenz |

## Umsetzung und Akzeptanz

1. Modellneutrale Rollen benennen ihren Skill ausdrücklich. Routing und
   Validierungen werden produktiv aus diesen Verträgen gelesen; Tests importieren
   die Produktionsbibliothek. Unbekannte Rollen, fehlende Skills und doppelte
   YAML-Schlüssel werden abgelehnt.
2. Aktuelle Requirements-, Plattform-, Workbench-, Viewer- und Provider-Pfade
   haben zuständige Spezialisten mit sichtbaren Auswahlgründen. Ein GCR allein
   ist kein Source Intake. Die Git-Menge umfasst gestagte und ungestagte
   Änderungen, neue/gelöschte Dateien und beide Umbenennungspfade.
3. Ein privater Plan bindet Aufgaben und Ergebnisse an HEAD, Index, Quellbytes,
   Dateimodi und Verträge. Rollenwahl bleibt `not_started`; tatsächliche Rollen-
   Perspektiven, Subagenten und Menschen werden als deklarierte Ausführungsart
   unterschieden. Modelle oder Subagenten werden nicht automatisch gestartet.
4. Der Abschluss verlangt alle Rollen, spezifische Ausgaben und Pfade,
   Prüfungsstatus mit Nachweisreferenz und abschließende Steward-Synthese.
   Fehlende/übersprungene Arbeit, neue Pfade, veraltete Bindungen und offene
   high/critical Findings verhindern vollständige Review-Evidenz.
5. Der Abschluss bestätigt nur deklarierte Evidenz. Er authentifiziert keine
   Identität und führt keine Prüfungsbefehle aus. Menschliche PR-Freigaben,
   Quellen-/Requirements-Entscheidungen, Releases und Blocking bleiben getrennt.

## Geschützte Bereiche und Migration

Quellen, Register, kanonische Anforderungen, fachliche Entscheidungen, OPA,
akzeptierte Statusdaten, Release-Pakete und Operating-Acceptance-Fingerprints
werden nicht geändert. Historische Usage-Ereignisse werden nicht umgeschrieben.
Bestehende Dispatch- und Usage-Flags bleiben verfügbar; JSON-Auswahlgründe sind
additiv. Validierungslisten werden vollständig aus den Rollen übernommen und
können deshalb mehr Einträge enthalten. Bisherige Test-Harness-Imports bleiben
als Kompatibilitätsoberfläche erhalten.

Codex- und Mistral-Adapter verweisen auf das gemeinsame Protokoll. Modell- und
Reasoning-Einstellungen bleiben erhalten. Für kleine erläuternde Änderungen
bleibt ein fokussierter Review ohne vollständiges Paket möglich. Es wird keine
neue CI-Freigabehürde eingerichtet.

## Validierung

Verhaltensregressionen prüfen Git-Scopes, Produktions-Routing ohne Testabhängigkeit,
Vertragsfehler, Stale-Erkennung, fehlende Ergebnisse, Rollen-Ausgaben, Steward-
Synthese und die Trennung von Review-Evidenz und menschlicher Freigabe.
Vor Commit: gepinnter Bootstrap, vollständiges `validate_all.sh`, MkDocs strict,
Skill-Validierung und ein lokaler Prepare/Check-Durchlauf mit tatsächlich
durchgeführten Rollen-Perspektiven. Ergebnisse werden im PR dokumentiert.


## Lokale Prüfergebnisse

Gepinnter Bootstrap und vollständiges `validate_all.sh` bestanden mit **833 Tests**.
Der Agent Harness umfasst **42 Tests**, darunter **23 neue Verhaltensregressionen**.
MkDocs strict und die Validierung des angepassten Repo-Steward-Skills bestanden.
Alle neun Codex-Adapter behalten ihre Rollen-, Modell- und Reasoning-Einstellungen.
Keine geänderte Datei ist an die bestehende Operating Acceptance gebunden.
Durch die Validierung erzeugte Berichtsänderungen werden ausgeschlossen.
Der private Prepare/Check-Durchlauf und die konkreten Review-Ergebnisse werden
zusätzlich im PR dokumentiert; er ist keine unabhängige menschliche Freigabe.
