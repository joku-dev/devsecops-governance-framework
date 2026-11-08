# Dokumentationsabgleich vom 7. November 2026

## Umfang und Quellen

Implementierungsstand: `ae423f34f75451b70b1ebffc71ea3683e4763c52` auf `main`.
Dieser erläuternde Abgleich konsolidiert die 14 unten genannten offenen
Dokumentationsentwürfe. Er beschreibt vorhandene Funktionen und korrigiert
Veröffentlichungsangaben. Er ist keine fachliche Requirements-Abnahme.

Die Prüfung verwendet den versionierten Code, Quellenregister, Lifecycle Cases,
Authority Ledger, akzeptierte Ergebnisindizes und Portfolio-Bericht. Remote-Tags
wurden mit `git ls-remote --tags` gelesen; die GitHub Releases API listete
v0.2.0 und v0.1.0 als veröffentlichte Adoption-Releases. Die Beobachtung löst
keinen Consumer-Lauf aus und ersetzt keine Evidenzaufnahme.

## Beschreibung des heutigen Systems

AXIOM verbindet kontrollierte Governance-Quellen, kanonische Anforderungen,
ausführbare Prüfungen und nachvollziehbare Evidenz. Der
[Funktionskatalog](../guides/repository-function-catalog.md) behält seine 22
Bereiche. Das [technische Inventar](../guides/repository-technical-function-inventory.md)
gleicht die vollständige Dateimenge der aufgeführten Implementierungsbereiche
gegen den genannten Commit ab: 165 Python-Dateien, 4 Shell-Dateien,
29 Workflows und 15 OPA-Module; weitere Skript-/Workbench-Dateien sind separat
aufgeführt. Dateilinks sind an diesen Commit gebunden.

Die private lokale [Review Workbench](../guides/governance-review-workbench.md)
führt durch Dokumentaufnahme, Anforderungsprüfung und Weitergabe. Registrierte
Dokumentversionen können ohne erneuten Upload vorbereitet werden. Nur explizit
deklarierte Anforderungen wie `DSCB-L1-REQ-001` werden aktuell extrahiert.
Fließtext und technische Extraktionszeilen-IDs erzeugen keine Anforderungen.
P1 setzt zusätzlich bestätigte `author_provided`-Provenienz voraus.

Prüfnotizen bleiben Vorschläge; der Fortschritt zählt Anforderungen mit Notiz.
Frühere Proposals und Entscheidungen stehen separat als Historie. Der
öffentliche Viewer zeigt lesende Projektionen. Quellenfreigabe, kanonische
Aktivierung, Zuordnung zu OPA, Baseline-Veröffentlichung und Blocking-Freigabe
bleiben getrennte Entscheidungen mit ihren bestehenden Verfahren.

## Abdeckung der offenen Dokumentationsentwürfe

Jeder Entwurf wird fachlich gegen den heutigen Code eingeordnet. Die
automatisch erzeugten Texte ersetzen teilweise dieselben Marker-Blöcke;
eine Merge-Reihenfolge allein würde keine konsistente Beschreibung ergeben.
Die Entwürfe bleiben bis zum Merge dieses Abgleichs offen und können danach
mit Verweis auf dessen PR als ersetzt geschlossen werden. Ihre Branches und
historischen Inhalte müssen dafür nicht gelöscht werden.

| Dokumentationsentwurf | Implementierungs-PR | Übernahme im konsolidierten Stand |
|---|---|---|
| [#332](https://github.com/joku-dev/devsecops-governance-framework/pull/332) | [#331](https://github.com/joku-dev/devsecops-governance-framework/pull/331) | Geführte Anforderungsprüfung, Originalkontext, Prüfnotizen, getrennte Historie, ZIP und reaktionsfähiger lokaler Server in Katalog, Architektur und Inventar |
| [#330](https://github.com/joku-dev/devsecops-governance-framework/pull/330) | [#326](https://github.com/joku-dev/devsecops-governance-framework/pull/326) | Explizite Deklarationen als einzige Extraktionsbasis und geführte Aufnahme in README, Katalog und Regelwerk |
| [#328](https://github.com/joku-dev/devsecops-governance-framework/pull/328) | [#292](https://github.com/joku-dev/devsecops-governance-framework/pull/292) | CodeQL-Aktualisierung; aktueller Workflow im Inventar, keine zusätzliche Governance-Funktion |
| [#327](https://github.com/joku-dev/devsecops-governance-framework/pull/327) | [#295](https://github.com/joku-dev/devsecops-governance-framework/pull/295) | Download-artifact-Aktualisierung; aktuelle betroffene Workflows im Inventar |
| [#304](https://github.com/joku-dev/devsecops-governance-framework/pull/304) | [#303](https://github.com/joku-dev/devsecops-governance-framework/pull/303) | Bereinigte PR-Arbeit ist Repository-Pflege; historische Evidenz bleibt erhalten, kein neuer Funktionsbereich |
| [#290](https://github.com/joku-dev/devsecops-governance-framework/pull/290) | [#289](https://github.com/joku-dev/devsecops-governance-framework/pull/289) | Explizite IDs vor Textähnlichkeit im Anforderungsvergleich; dokumentiert in Katalog und Workbench-Anleitung |
| [#288](https://github.com/joku-dev/devsecops-governance-framework/pull/288) | [#287](https://github.com/joku-dev/devsecops-governance-framework/pull/287) | Sanitisiert registrierte Quellen, direkte gegenüber gemeinsamen Ausgaben und erhaltene historische Release-Pfade im Katalog |
| [#286](https://github.com/joku-dev/devsecops-governance-framework/pull/286) | [#285](https://github.com/joku-dev/devsecops-governance-framework/pull/285) | Prozessführung übernommen; damalige P2-Fließtextableitung durch #326 abgelöst |
| [#284](https://github.com/joku-dev/devsecops-governance-framework/pull/284) | [#283](https://github.com/joku-dev/devsecops-governance-framework/pull/283) | Geführte Workbench-Aufnahme im aktuellen Ablauf konsolidiert |
| [#282](https://github.com/joku-dev/devsecops-governance-framework/pull/282) | [#281](https://github.com/joku-dev/devsecops-governance-framework/pull/281) | Authentifizierte lokale Workbench und Trennung vom öffentlichen Viewer in README, Architektur und Inventar |
| [#280](https://github.com/joku-dev/devsecops-governance-framework/pull/280) | [#278](https://github.com/joku-dev/devsecops-governance-framework/pull/278) | MD/DOCX/optionales PDF, Prozessprojektion und Freigabegrenzen beschrieben; alte P2-Aussagen abgelöst |
| [#277](https://github.com/joku-dev/devsecops-governance-framework/pull/277) | [#276](https://github.com/joku-dev/devsecops-governance-framework/pull/276) | P1-Provenienzgrenze erhalten; automatische P2-Ableitung durch #326 abgeschafft |
| [#274](https://github.com/joku-dev/devsecops-governance-framework/pull/274) | [#211](https://github.com/joku-dev/devsecops-governance-framework/pull/211) | Versionierte Baseline-Wrapper im aktuellen Inventar erfasst; keine erneute Änderung an Wrappern oder Consumer-Pins |
| [#248](https://github.com/joku-dev/devsecops-governance-framework/pull/248) | [#247](https://github.com/joku-dev/devsecops-governance-framework/pull/247) | Dependency Review mit aufgelösten Base-/Head-Referenzen im aktuellen Workflow erfasst |

## Datierte Zustände und Grenzen

Das Quellenregister enthält 15 Dokumente: 6 approved, 6 candidate und 3 review.
Die sechs erhaltenen Lifecycle Cases enthalten 867 Proposals, davon 84 mit
Entscheidung und 783 ohne Entscheidung. Diese historischen Zahlen sind keine
aktuelle Extraktionsmenge. DSCB besitzt 46 aktuell explizit deklarierte
Anforderungen; sein Lifecycle Case behält 55 Proposals, darunter 46 aktivierte
Entscheidungen und 9 offene historische Proposals. Der Abgleich verwirft oder
entscheidet keinen dieser Datensätze und ändert keine Quellprovenienz.

Die akzeptierten ha-CPsWMS-Ergebnisse bleiben vom 2. Oktober: DevSecOps
`36997125273` und Architektur `36997124090`. Der Portfolio-Bericht weist alle
drei Repositories als stale oder missing aus. Frische Repository-Tests erzeugen
keine neue Consumer-Evidenz. Detaillierte Zeit- und Pin-Bindungen stehen im
[Plattformstatus](current-governance-platform-state.md).

Die [Release-Übersicht](../../releases/index.md) unterscheidet veröffentlichte
Adoption-Releases, vorhandene Baseline-Tags und Consumer-Pins. v0.3.0 bleibt
vorbereitet und unveröffentlicht. Historische Release-Statements, Pakete und
Tags werden durch diese Korrektur nicht geändert.

## Kurzbeschreibung für GitHub About

> AXIOM Engineering Governance Runtime: controlled document intake, canonical requirements, executable governance checks and traceable evidence with human decision authority.

## Prüfung und Änderungsnachweis

[GCR-2026-154](../../governance/change-requests/GCR-2026-154-consolidated-repository-description.md)
klassifiziert den Abgleich als Dokumentation ohne Baseline- oder Release-Änderung.
Die Ausführung von Bootstrap, vollständiger Repository-Validierung, lokalem Demo
und strengem MkDocs-Build wird im zugehörigen PR mit dem konkreten Commit
protokolliert. Dieser Text beansprucht keine neue fachliche Abnahme.
