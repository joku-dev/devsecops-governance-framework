---
goal_id: AXIOM-GOAL-PLATFORM-PORTABILITY-001
title: Plattformoffene AXIOM Governance Runtime
version: "1.2"
date: "2026-11-15"
language: de
status: ready_for_execution
repository: https://github.com/joku-dev/devsecops-governance-framework.git
analysis_reference_commit: 4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be
integrated_reference_commit: edf16239e9274dbc33f38f204ef80f58c989f969
change_request: GCR-2026-172
delivery: incremental_reviewable_pull_requests
default_new_integration_mode: report-only
default_vm_collection_mode: shadow
vm_analysis_references:
  installation_pr: 363
  installation_commit: 416432e013143b6942f887a5ac610991f2a111f6
  consumer_intake_pr: 364
  consumer_intake_commit: 944c6f813ebb387f36a77f92af50deabd278d957
---

# Codex-Auftrag: AXIOM plattformoffen weiterentwickeln

**Version 1.2:** Aktualisierte integrierte Ausgangslage, verbindlicher paralleler Mac-/VM-Betrieb, Kapazitätsziel für 1.000–2.000 Consumer-Repositories, konkrete Akzeptanzschutzgrenzen, erste Unterstützungsmatrix und getrennte Report-only-/Blocking-Abnahmen. Version 1.1 hat die VM einschließlich Collector, Publisher, Zustandsmigration, Update und Recovery in das Goal aufgenommen.

Dieses Dokument ist ein technischer Entwicklungsauftrag mit Governance-Auswirkungen, keine neue normative Quelle für Controls oder Baselines. Die Artefaktklassifikation und diese Überarbeitung sind in [GCR-2026-172](docs/governance/change-requests/GCR-2026-172-platform-portability-goal.md) festgehalten. `ready_for_execution` bezeichnet die Ausführungsgrundlage; es bestätigt weder erledigte Arbeitspakete noch eine Betriebsfreigabe.

## 1. Auftrag und erwartetes Ergebnis

Übernimm die technische Umsetzung dieses Goals autonom im Repository `joku-dev/devsecops-governance-framework`.

Entwickle AXIOM so weiter, dass GitHub Actions, GitLab CI und Bamboo dieselbe versionierte Governance-Runtime verwenden. Git-Host, CI-System, Evidenztransport und Ergebnisveröffentlichung müssen getrennt konfigurierbar sein. Controls, fachliche Gate-Entscheidungen und gemeinsame Evidenzprüfungen werden zentral implementiert. Die Plattformadapter beschaffen Anbieterinformationen und veröffentlichen Ergebnisse.

Beziehe die VM-Version von Anfang an als Betriebsprofil desselben Produkts ein. CI-Ausführung und VM-Dienste verwenden dieselben jeweils benötigten fachlichen Module, Verträge und Provideradapter aus einem kompatiblen versionierten Stand. Die Ergebnisse des Umbaus werden über diese gemeinsamen Komponenten und einen kontrollierten VM-Updatepfad übertragen. Es entsteht keine separat gepflegte VM-Implementierung der Governance-Logik.

Arbeite bis zu einem implementierten, getesteten, dokumentierten und reviewfähigen Änderungsstand. Eine weitere Analyse oder zusätzliche YAML-Vorlagen allein erfüllen den Auftrag nicht. Triff gewöhnliche Implementierungsentscheidungen selbst und arbeite die abhängigen Arbeitspakete ohne wiederholte Bestätigung ab.

Das Gesamtziel hat zwei separat überprüfbare Meilensteine:

| Meilenstein | Ergebnis |
| --- | --- |
| **M1: Portable Consumer-Ausführung** | Ein gemeinsamer ausführbarer Prüfpfad, versionierte Kontext-/Ergebnisverträge, funktionale Adapter für GitHub Actions, GitLab CI und Bamboo sowie nachgewiesene lokale Entscheidungsparität. |
| **M2: Entkoppelte Evidenz und zentrale Operations einschließlich VM** | Versionierte anbieterübergreifende Identitäten, gemeinsamer Evidence-Verifier, Provideradapter für Intake und zentrale SCM-/CI-Operationen sowie ein dokumentierter Migrationspfad für bestehende Integrationen. Die VM verwendet diese Bausteine; persistenter Zustand, reproduzierbares Update und Wiederherstellung sind integriert und repo-seitig geprüft. |

Setze M1 vor M2 um. Fahre anschließend mit den unabhängig ausführbaren Arbeiten von M2 fort. Ein fertiges M1 ist ein Zwischenstand und darf nicht als vollständige Plattformöffnung ausgegeben werden.

Echte Zielsysteme werden nur im tatsächlich verfügbaren und autorisierten Umfang verwendet. Fehlende Zugänge verhindern keine lokale Implementierung, Fixture-Tests, Vertragsprüfungen, Dokumentation oder PR-Vorbereitung. Sie bleiben als konkrete offene Live-Abnahmen bestehen.

## 2. Ausgangslage und Quellenstand

Die vorangegangene Analyse bezieht sich auf `main` am Commit `4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be`. Die integrierte Ausgangslage dieser Überarbeitung ist `edf16239e9274dbc33f38f204ef80f58c989f969`. Prüfe vor Beginn erneut den aktuellen Stand. Beide Referenzen sind keine Anweisung, einen neueren Repository-Stand zurückzusetzen.

Lies zuerst:

- `AGENTS.md` und weitere auf den Arbeitsumfang anwendbare Repository-Anweisungen.
- `docs/foundation/03_ARCHITECTURE_PRINCIPLES.md` und `docs/foundation/04_REFERENCE_ARCHITECTURE.md`.
- `docs/operations/adapters/cicd-platform-adapter-strategy.md`.
- `docs/operations/adapters/bitbucket-bamboo-governance-adapter.md`.
- `docs/operations/status/governance-lifecycle-current-state.md`.
- `docs/operations/status/blocking-mode-alignment.md`.
- `docs/operations/agents/how-to-run-agent-review.md` und `.agents/review-protocol.yaml`.
- Die aktuellen Release-Metadaten, Consumer-Pins und betroffenen Betriebs-/Akzeptanzprofile.
- Die VM-Anleitungen `docs/operations/guides/linux-vm-installation.md` und `docs/operations/guides/vm-consumer-intake.md` am jeweils aktuellen integrierten oder zugehörigen PR-Stand. [R14] [R16]

Folgende Befunde sind am Referenzstand belegt und vor Änderungen gezielt zu bestätigen:

| ID | Befund | Relevante Dateien |
| --- | --- | --- |
| F01 | Der gewünschte plattformneutrale Kern mit Plattformadaptern ist bereits als Zielarchitektur beschrieben. | `docs/operations/adapters/cicd-platform-adapter-strategy.md` [R1] |
| F02 | Im GitHub-Reusable-Workflow liegen Plattformabfragen, Evidenzerzeugung und fachliche Gate-Logik in Inline-Python. Im untersuchten Stand umfasst die Datei 479 Zeilen, davon 306 in drei Python-Blöcken einschließlich Leerzeilen. | `.github/workflows/devsecops-baseline-reusable.yml` [R2] |
| F03 | GitHub und der von Bamboo verwendete Starter-Generator behandeln unbekannten Direct-Push-Status unterschiedlich. Der Generator kann mit synthetischen Platzhalterdateien und unbekanntem Repository/Branch/Commit `pass` sowie `blocks_merge: true` erzeugen. | `scripts/generate_pipeline_evidence.py`, GitHub-Reusable-Workflow [R2] [R3] |
| F04 | Das Kontextschema kennt `gitlab-ci`; Kontextgenerator und Pipeline-Evidence-CLI unterstützen GitLab noch nicht. | `schemas/platform-context.schema.json`, `scripts/generate_platform_context.py` [R4] |
| F05 | Die GitLab-Consumer-Vorlage besteht aus Echo-Platzhaltern. Der separate Governance-Integrationscheck ist kein vollständiger Consumer-Baselinepfad. | `pipeline-baseline/templates/gitlab-ci/.gitlab-ci.yml`, `templates/ci/gitlab-ci-governance-check.yml` [R5] |
| F06 | Die Bamboo-Vorlage generiert für Wiring-Tests Security-Platzhalter; Branch-Schutzabfragen sind ausdrücklich nicht implementiert. Die genannte Bamboo-Version ist eine Template-Annahme, kein Live-Kompatibilitätsnachweis. | `pipeline-baseline/templates/bamboo/bamboo-specs/bamboo.yaml` [R6] |
| F07 | Ein neutraler Bundle-Import existiert. Er erzeugt Status-Snapshots, ist aber nicht gleichwertig mit der stärkeren GitHub-Herkunftsprüfung. | `scripts/intake_ci_artifact_bundle.py`, `scripts/intake_github_actions_run.py` [R7] |
| F08 | Trust-Schemas und Laufzeitcode begrenzen Repository-IDs auf zwei Pfadbestandteile. Replay-/Collection-Schlüssel unterscheiden Provider und Instanz nicht durchgängig. | `schemas/evidence-trust-record.schema.json`, `scripts/lib/evidence_trust.py`, `scripts/lib/result_ledger.py`, `scripts/lib/collection_attempts.py` [R8] |
| F09 | Teile von Intake, Lifecycle, Publikation und Viewer sind an GitHub-APIs, GitHub-Identitäten und feste URLs gebunden. | `scripts/lib/governance_lifecycle/consumer_evidence.py`, `scripts/publish_operational_update.py`, `scripts/generate_status_viewer.py` [R9] |
| F10 | Veröffentlichte Consumer-Wrapper pinnen historische Runtime-Commits. Änderungen am heutigen `main` sind nicht automatisch Änderungen der tatsächlich konsumierten Implementierung. | `.github/workflows/devsecops-baseline-l1-v1.1.3.yml`, `releases/`, Consumer-Konfiguration [R10] |
| F11 | Wiederverwendbare Unterstützung für gepinnte OPA-Versionen, Prüfsummen, Mirror und Offline-Installation ist vorhanden. | `scripts/install_validation_opa.py` [R11] |

Die Analyse enthielt drei erfolgreiche bestehende Plattformkontexttests und gezielte lokale Prüfungen. Sie war kein Live-Test einer GitLab-/Bamboo-Installation und keine erneute vollständige Repositoryvalidierung. Übernimm keine unbelegten Produktions- oder Kompatibilitätsaussagen.

### 2.1 Zusätzlich untersuchte VM-Stände

Die folgenden PR-Stände wurden am 14. November 2026 untersucht. Beide PRs waren zu diesem Zeitpunkt offen und als Draft markiert. Sie sind keine Aussage über eine bereits vorhandene Installation. Prüfe vor Umsetzung erneut Merge-Status, Head, Basis und eventuelle Nachfolger.

| Referenz | Untersuchte Revision | Abhängigkeit am Analysestand |
| --- | --- | --- |
| PR #363 — reproduzierbare Ubuntu-VM-Installation, Branch `feat/linux-vm-iac` [R13] | `416432e013143b6942f887a5ac610991f2a111f6` | Basierte auf `feat/workbench-guided-impact`; zugehörige Vorarbeit PR #362 berücksichtigen. |
| PR #364 — Consumer-Intake im VM-Schattenbetrieb, Branch `feat/vm-consumer-intake` [R15] | `944c6f813ebb387f36a77f92af50deabd278d957` | Basierte auf dem untersuchten Stand von PR #363. |

| ID | VM-Befund | Konsequenz für diesen Auftrag |
| --- | --- | --- |
| F12 | PR #363 installiert den vorhandenen Repository-Stand mit Ansible/systemd und einer an den Commit gebundenen virtuellen Umgebung; der private Workbench bleibt Teil derselben Anwendung. [R14] | Gemeinsame Runtime und VM-Paketierung zusammenführen; Installation weiterhin an eine exakte Revision binden. |
| F13 | Der VM-Collector verwendet bereits den bestehenden GitHub-Intake und gemeinsame Generatoren. Discovery, Authentifizierung und PR-Publikation sind noch GitHub-spezifisch. [R16] [R17] [R19] [R20] | Bestehende Wiederverwendung erhalten; Anbieterzugriffe an dieselben Adaptergrenzen führen. |
| F14 | Der untersuchte SQLite-Store verwendet numerische Run-IDs und Schlüssel ohne durchgängige Provider-/Instanzbindung. Rohcache, verifizierte Kandidaten und Batches sind weitere persistente Identitätsträger. [R17] [R18] | Versionierte Zustandsmigration und kollisionsfreie Schlüssel im gesamten Betriebszustand umsetzen. |
| F15 | Die VM prüft Anwendungsdrift und sperrt bei inkompatiblem Stand mit `application_update_required`. Schattenbetrieb und Routing führen die Übergabe zwischen CI- und VM-Intake. [R16] [R17] | Neue Module in den geprüften Ausführungsumfang aufnehmen; Sperre, Schattenabnahme und explizite Schreibhoheit erhalten. |

Die damalige Analyse der Draftstände enthielt keinen Nachweis einer Installation oder erfolgreichen Migration auf einer realen Ziel-VM. Diese historische Nachweisgrenze ist keine Aussage über den heutigen Installationsstand. Vorhandene Datenbestände, installierter Commit und aktiver Betriebsmodus sind im ausführenden Kontext festzustellen, soweit ein entsprechender lesender Zugang vorhanden ist. Fehlender VM-Zugang blockiert die repo-seitige Integration nicht.

### 2.2 Integrierte Ausgangslage der Version 1.2

Am Referenzstand `edf16239e9274dbc33f38f204ef80f58c989f969` sind PR #362 (Workbench), #363 (Linux-VM-IaC) und #364 (VM-Consumer-Intake) zusammengeführt. Die oben aufgeführten Draft-Commits bleiben historische Analysequellen. Die vorhandenen Installations-, Queue-, Credential-, Schattenbetriebs- und Recoveryfunktionen sind zu erhalten und gezielt zu erweitern.

Dieser Git-Stand belegt keine Aktualisierung einer laufenden VM. Erfasse in WP0 getrennt den integrierten Quellstand, die getestete Deploymentrevision und den tatsächlich beobachteten installierten Stand einschließlich Beobachtungszeit, Betriebsmodus und Nachweis. Ist letzterer nicht lesend feststellbar, bleibt er ausdrücklich unbekannt. Historische Testnachweise erfüllen neue Portabilitäts- oder Migrationskriterien nicht automatisch.

## 3. Umfang und Arbeitsbefugnis

### 3.1 Im Auftrag enthalten

- Aktuellen Stand prüfen, einen isolierten Branch beziehungsweise bei Bedarf einen Worktree anlegen und fremde lokale Änderungen erhalten.
- Gemeinsame Runtime, Verträge, Adapter, sinnvolle Regressionstests und Migrationsdokumentation implementieren.
- Funktionale Consumer-Vorlagen für GitHub Actions, GitLab CI und Bamboo erstellen.
- VM-Collector, VM-Publisher, bestehende SQLite-Persistenz und IaC auf die gemeinsamen Verträge ausrichten; Migrations-, Update- und Wiederherstellungspfade einschließlich isolierter Tests implementieren.
- Anbieterabhängige Zugriffe aus gemeinsam genutzter neuer Runtime-Logik herauslösen.
- Bestehende technische Schutzmaßnahmen und fachliche Anforderungen in den neuen Pfaden erhalten.
- Konfigurierbare interne Endpunkte und reproduzierbare Abhängigkeiten vorsehen.
- Revisiongebundene Reviews und die vorgeschriebenen Validierungen durchführen.
- Kohärente Commits erstellen, einen Arbeitsbranch pushen und überprüfbare Pull Requests bereitstellen, soweit der ausführende Codex-Kontext über die entsprechenden Rechte verfügt.
- Parallele Implementierung an Teilagenten delegieren, wenn der Koordinator vorher disjunkte Dateiverantwortung festlegt. Spezialistenreviews bleiben unabhängig von der jeweiligen Implementierung; der Repo Steward synthetisiert zuletzt.

### 3.2 Abgegrenzte Aktionen

Dieser Auftrag aktiviert keine neuen verpflichtenden Merge-Checks, kein Blocking für reale Consumer und keine neue produktive Lifecycle-Autorität. Er autorisiert keine Änderung historischer Releases, Tags, Signaturen oder akzeptierter Entscheidungen. Er enthält keinen automatischen Merge der erstellten PRs und keinen produktiven Rollout. Für die VM umfasst diese Grenze auch tatsächliche Installation oder Aktualisierung einer bestehenden Ziel-VM, Credentialwechsel, Umschalten der Intake-Schreibhoheit und Aktivieren des Publishers. Die Implementierung, isolierte Testinstallationen und konkrete Vorbereitung dieser Schritte sind Teil des Auftrags.

Implementiere diese Fähigkeiten und bereite ihre Anwendung konkret vor. Bestehende separate Autorisierungen aus der tatsächlichen Codex-Sitzung gelten weiter; fordere sie nicht erneut an. Für eine darüber hinaus erforderliche Aktion schließe zuerst alle unabhängig ausführbaren Arbeiten ab und benenne dann präzise die noch fehlende Entscheidung oder Zugangsmöglichkeit.

### 3.3 Ausgeschlossen

- Vollständiger Rewrite, neues Parallelprodukt oder pauschale Verzeichnisumsortierung.
- Austausch von OPA/Rego ohne einen nachgewiesenen, für dieses Goal relevanten Grund.
- Wiederaufnahme der geparkten Architektur-Governance-Themen, neue Architekturmarker oder Änderungen der Architecture-Baseline. Technische Modularisierung und unveränderte Regressionstests begründen keine solche Wiederaufnahme.
- Ersetzung von Git als Versionsverwaltung.
- Kopieren und unabhängiges Weiterentwickeln derselben Gate-Logik in mehreren CI-Dateien.
- Einführung eines zusätzlichen zentralen Dienstes, einer zusätzlichen Datenbank oder eines universellen Pipeline-Frameworks ohne belegte Notwendigkeit. Die Migration des bereits vorhandenen VM-SQLite-Stores ist ausdrücklich enthalten.
- Umbau von AIFORGE oder anderen Consumer-Repositories außerhalb explizit freigegebener Integrationstests.
- Umgehung von Prüfungen, Abnahmen oder Zugriffsbeschränkungen, um einen grünen Status zu erreichen.

## 4. Architekturvorgaben

### 4.1 Git-Host und CI sind unabhängige Achsen

GitHub/GitLab/Bitbucket sind SCM-Anbieter; GitHub Actions/GitLab CI/Bamboo sind Ausführungssysteme. Ein einzelner Wert `platform: bamboo` darf den SCM-Anbieter nicht implizit festlegen. Kombinationen wie GitLab plus Bamboo müssen durch Komposition unterstützt werden können. Behaupte keine Unterstützung jeder denkbaren Kombination ohne eine entsprechende Abnahme.

#### 4.1.1 Erste verbindliche Unterstützungsmatrix

| Profil | SCM | CI | Betriebs-/Versionsgrenze |
| --- | --- | --- | --- |
| GHA-01 | GitHub.com | GitHub Actions | Bestehender Referenzpfad; tatsächlich verwendete Runner-, Runtime- und API-Versionen dokumentieren. |
| GL-01 | GitLab | GitLab CI | Hostingform, installierte Version/Edition und Runner-Profil vor der jeweiligen Live-Abnahme erfassen; derzeit nicht bestätigt. |
| BB-01 | Bitbucket Data Center | Bamboo | Beide installierten Versionen und Agentprofil vor Live-Abnahme erfassen; vorhandene Templateversionen sind keine bestätigten Zielversionen. |

Diese drei Profile sind der erste Implementierungs- und lokale Prüfungsumfang. Nicht bestätigte Versionen werden als offen geführt und verhindern keine lokal prüfbare Implementierung gegen dokumentierte, explizit benannte API-Verträge. GitHub Enterprise Server, Bitbucket Cloud und weitere Kombinationen erhalten gesonderte Profile und Nachweise. Die in Abschnitt 4.1 geforderte Komponierbarkeit, beispielsweise GitLab mit Bamboo, bleibt eine Entwurfsanforderung; sie begründet keine zusätzliche Unterstützungszusage.

### 4.2 Klare Verantwortlichkeiten

| Baustein | Verantwortung | Nicht seine Verantwortung |
| --- | --- | --- |
| Governance-Kern | Controls, Policy-Auswertung, fachliche Findings, Waiver-Auswertung, kanonische Entscheidungen | Provider-API-Aufrufe, CI-Variablen, PR-/MR-Erstellung |
| SCM-Adapter | Repository-Identität, Branch-Regeln, Reviewbelege, Change-Request-Metadaten | Erfindung fachlicher Erfüllung bei fehlenden Daten |
| CI-Adapter | Ereignis, Run, Attempt, Job, geprüfter Stand und Statusabbildung | Eigene Baseline-/Gate-Implementierung |
| Evidence-Transportadapter | Rohartefakte und unabhängige Anbieterbelege beschaffen | Selbstdeklarierte Provenienz als verifiziert markieren |
| Gemeinsamer Verifier | Digests, Zuordnung, Baselinebindung, Freshness, Replay und Trust prüfen | Fachliche Governance-Entscheidung aus einem Trust-Level ableiten |
| Publikationsadapter | Check-/Build-Status, Artefakte, PR/MR und Links veröffentlichen | Entscheidungen neu berechnen oder Findings abschwächen |

Im gemeinsamen neuen Kern sind keine `GITHUB_*`-, `CI_*`- oder `bamboo_*`-Zugriffe, fest verdrahteten Anbieterhosts oder Provider-SDK-Abhängigkeiten zulässig. Führe passende Architekturprüfungen für die definierten Kerngrenzen ein. Historische Snapshots, veröffentlichte Pakete, vorhandene Legacyprofile und Dokumentationslinks sind keine zu entfernenden Laufzeitabhängigkeiten.

### 4.3 Bestehende Bausteine weiterverwenden

Nutze bestehende Python-/OPA-Module, Schema-Validierung, Append-only-Speicherung und Installer. Behalte sinnvolle alte CLI-Einstiege zunächst als Kompatibilitätswrapper. Neue Verzeichnisse richten sich nach klaren Verantwortlichkeiten; Dateiumzüge benötigen einen konkreten Nutzen.

Ziel ist ein modularer ausführbarer Kern. Ein versioniertes OCI-Image kann die Verteilung vereinfachen, darf aber nicht die einzige Möglichkeit sein, dieselbe Runtime auf vorbereiteten internen Agents zu starten.

### 4.4 Ein gemeinsamer Kern für CI- und VM-Betrieb

Die VM ist ein Betriebsprofil mit Workbench, periodischem Collector und Publisher. Sie ist kein weiterer CI-Anbieter. Trenne das System, aus dem Evidenz stammt, vom System, das sie einsammelt, verifiziert oder veröffentlicht.

| Bereich | Gemeinsamer Code und Vertrag | Verantwortung des VM-Betriebsprofils |
| --- | --- | --- |
| Governance und Evidenz | Fachliche Module, Kontextnormalisierung, Verifier, Ergebnis-/Report-Erzeugung | Aufruf derselben passenden Module aus dem installierten kompatiblen Stand |
| Provideranbindung | SCM-, CI-, Evidence- und Publikationsadapter | Konfigurierte Consumerprofile, Endpunkte und getrennte Zugangsdaten bereitstellen |
| Hintergrundverarbeitung | Identität, Fehler-/Retry-Vertrag, idempotente Verarbeitung | Timer, Worker, Sperren, persistente Queue, Recovery und begrenzte Verarbeitung |
| Bereitstellung | Versions-/Abhängigkeitsmanifest, exakte Baseline-/Runtime-/Adapterbindung | Ansible/systemd, Kandidatenprüfung, Aktivierung, Backup und Wiederherstellung |

`consumer_intake.py` und `consumer_publisher.py` orchestrieren den Dienstbetrieb. Sie enthalten keine unabhängig kopierte Governance-Auswertung oder Herkunftsprüfung. Der VM-Intake muss Consumer-Scans nicht erneut ausführen; er verarbeitet ihre Belege nach denselben Verifikationsregeln wie der entsprechende CI-Intake.

Binde fest verdrahtete Repository-, Workflow-, Branch-, Baseline- und Artefaktwerte an versionierte Consumerprofile. Native GitHub-Authentifizierung verbleibt im GitHub-Adapter; zusätzliche Provider erhalten ihre eigenen unterstützten Authentifizierungsverfahren. Die Herkunft eines Consumer-CI-Laufs bleibt erhalten. Ein auf der VM ausgeführter Publisher darf sich nicht als GitHub-Actions-Lauf ausgeben oder dafür eine Run-ID erfinden.

Ein Merge im zentralen Repository aktualisiert eine laufende VM nicht. Der dortige Anwendungsstand wird nur über den kontrollierten, revisionsgebundenen Bereitstellungspfad aktiviert. Die VM-Integration gehört zu M2 und ist keine optionale spätere Portierung.

### 4.5 Paralleler Mac- und VM-Betrieb

Mac und Ubuntu-VM verwenden denselben Produktpfad mit getrennten Checkouts, Laufzeitumgebungen, privaten Zuständen, Credentials und Backups. Die Workbench muss auf beiden Hosts gleichzeitig nutzbar bleiben. Nutze getrennte Browser-Hostnamen gemäß VM-Anleitung, damit Sessions trotz unterschiedlicher Ports nicht kollidieren. Entwürfe und operative Daten werden nicht automatisch zwischen Hosts synchronisiert; ein Import bleibt ein kontrollierter eigener Vorgang.

Bei gleichen normalisierten Eingaben, Baseline-/Runtime-/Adapterständen, Auswertungszeit und Referenzzustand müssen die fachlichen Ergebnisse übereinstimmen. Hostpfade und Betriebsmetadaten dürfen abweichen. Neue gemeinsame Python-Module dürfen im Mac-Profil keine Linux-/systemd-Laufzeit voraussetzen; solche Abhängigkeiten bleiben im VM-Betriebsprofil.

Pro Consumer/Domäne existiert genau eine aktive Veröffentlichungszuständigkeit. Im bestehenden Pilotübergang bleibt der Mac ohne aktiven Collector-Publisher; die VM bleibt bis zur gesonderten Umschaltung im Schattenbetrieb und der bisherige CI-Intake bleibt zuständig. Zwei laufende Workbenches oder lokale Sperrdateien begründen keine sichere Veröffentlichung von mehreren Hosts. Keine verteilte Sperrinfrastruktur allein für dieses Goal einführen.

## 5. Verbindliche Vertragsanforderungen

### 5.1 Kontext und Identität

Definiere einen versionierten normalisierten Vertrag. Er muss mindestens Folgendes ausdrücken:

| Bereich | Inhalt |
| --- | --- |
| SCM | Anbieter, Instanz/Issuer, native Repository-ID, lesbarer Pfad, kanonische Repository-URL |
| Change Request | Art und native ID, Quell-/Zielrepository, Quell-/Zielbranch, soweit für den Ereignistyp vorhanden |
| Revision | Source-/Head-Commit, Target-/Base-Commit, tatsächlich geprüfter Commit und Prüfmodus: Branch, Source-Head oder Merge-Ergebnis |
| CI | Anbieter und Instanz, Pipeline-/Run-/Job-Identität, Attempt, normalisierter Ereignistyp und unveränderter nativer Kontext als Referenz |
| Governance | Baseline-ID, exakte Revision/Digest, Runtime-Version/Digest, Adapterversion, ausgewählter Umfang |
| Fähigkeiten | Verfügbare, fehlende und nicht unterstützte Providerinformationen samt Erhebungsstatus und Herkunft |

Native IDs sind opake Werte. Keine generelle Integer-Annahme für Bamboo-Build-Keys. GitLab-Untergruppen sind zulässig. Fehlende IDs dürfen nicht durch erfundene Werte ersetzt werden. Optionale Felder sind abhängig vom Ereignistyp; ein normaler Branch-Build benötigt keine erfundene PR-/MR-ID.

Provider, Instanz und native Repositoryidentität müssen in Speicher-, Index-, Replay- und Collection-Resolution-Schlüsseln konsistent berücksichtigt werden. Namespaces allein sind keine globalen Identitäten. Definiere eine explizite Altformat-Zuordnung statt historischer Umnummerierung. Das gilt auch für VM-SQLite-Schlüssel, Queue, Watermarks, HTTP-/ETag-Caches, Rohcache-/Verified-Pfade, Batchmanifeste und PR-/MR-Reconciliation. Identitäten von Herkunftslauf und ausführendem VM-Dienst bleiben getrennt.

Normalisiere Ereignisse fachlich. Ein GitHub-`pull_request`-SHA kann ein Merge-Commit sein; GitLab-MR-SHA-Variablen unterscheiden sich nach Pipeline-Typ. Leite den geprüften Stand aus tatsächlichem Checkout und vertrauenswürdigem Laufkontext ab. Übersetze nicht lediglich Variablennamen. Branch-Namen wie `main` gehören in ein Profil und nicht als allgemeine Annahme in den Kern. [P1] [P2]

### 5.2 Entscheidung, Ausführung, Trust und Enforcement

Halte vier Aussagen getrennt:

1. Fachliches Ergebnis einschließlich einzelner Control-Ergebnisse und Findings.
2. Technischer Ausführungsstatus einschließlich unvollständiger oder fehlerhafter Auswertung.
3. Evidenzqualität und tatsächlich verifizierte Herkunft.
4. Gewünschter Durchsetzungsmodus und nachgewiesene externe Durchsetzung.

Verwende explizite Zustände für `pass`, `fail`, `not_evaluated`/`incomplete` und technische Fehler; begründe die endgültige Zuordnung zu bestehenden Statusmodellen. `not_applicable` benötigt eine fachliche Begründung. Nicht automatisierbare oder manuelle Controls dürfen nur entsprechend dem geltenden Vertrag behandelt werden; sie werden weder stillschweigend bestanden noch pauschal als technische Fehler gewertet.

Ein fehlendes erforderliches Faktum, eine fehlgeschlagene Pflichtprüfung oder eine unbekannte Pflichtfähigkeit darf keine erfolgreich nachgewiesene Freigabe erzeugen. `blocks_merge: true` darf nicht allein aus `mode: block-on-error` als Tatsachenbehauptung entstehen. Trenne beispielsweise `requested_enforcement` von `enforcement_observation`.

### 5.3 CLI und Exitcodes

Implementiere einen stabilen, dokumentierten CLI-Einstieg. Ein sinnvoller Entwurf ist `evaluate` für die Auswertung und `gate` für die nachgelagerte Modusabbildung. Die konkreten Namen sind im ersten Architekturentscheid festzulegen.

Der folgende Vertrag ist als Ausgangspunkt umzusetzen oder durch einen dokumentierten gleichwertigen Vertrag zu ersetzen:

| Operation/Fall | Erwartung |
| --- | --- |
| `evaluate`: Auswertung technisch vollständig, auch mit Findings | Kanonisches Ergebnis schreiben; Exitcode `0` bedeutet erfolgreiche Ausführung, nicht automatisch fachliches `pass`. |
| `evaluate`: ungültiger Input, fehlende Policy, Toolfehler oder unvollständige Pflichtauswertung | Explizite Fehlerdiagnose; Exitcode `2`; kein fachliches `pass`. |
| `gate`: technisch gültiges Ergebnis, `report-only` | Findings sichtbar; Exitcode `0`; keine behauptete Merge-Sperre. |
| `gate`: Blocking-Modus und vollständiges fachliches `pass` | Exitcode `0`. |
| `gate`: Blocking-Modus und fachliches `fail` | Exitcode `1`. |
| `gate`: fehlendes, ungültiges oder unvollständiges erforderliches Ergebnis | Exitcode `2`, unabhängig vom Berichtsmodus. |

Validiere Modi ausdrücklich. Ein unbekannter Modus darf nicht unbemerkt in Report-only fallen. Falls `waiver-required` übernommen wird, muss die Wirkung an den existierenden Waiver-Vertrag einschließlich Umfang, Autorität und Gültigkeit gebunden sein. Ein frei gesetztes Environment-Flag ist kein Waiver-Nachweis.

Sichere Ergebnis und Diagnosen auch bei Fehlern. Nutze die passende Always-/Finalisierungsmöglichkeit jedes CI-Systems. Eine fehlgeschlagene Veröffentlichung darf eine negative oder unbekannte Bewertung nicht in Erfolg umwandeln.

### 5.4 Evidence-Bundle und Verifikation

Ein versioniertes Bundle benötigt Kontext, Baseline-/Runtime-Identität, Ergebnis, Manifest, Dateien beziehungsweise belastbare Referenzen, Digests sowie getrennte Herkunftsbelege und Trust-Bewertung.

Prüfe mindestens Repository-/Run-Zuordnung, Commit-Bindung, Artefaktzugehörigkeit, Dateidigest, exakte Baselinebindung, Freshness und Replay. Sichere vorhandene Grenzen gegen unsichere Archive, Pfadtraversierung und doppelte oder uneindeutige Manifestmitglieder. Übergib eine explizite Auswertungszeit beziehungsweise Clock-Abhängigkeit, damit Freshness-Tests reproduzierbar sind.

Ein JSON-Feld `exists: true`, ein frei gesetzter Providername oder eine vorhandene ZIP-Datei beweist keine Herkunft. Ein lokaler Bundle-Import darf weiterhin nützlich sein, muss aber die tatsächlich nachgewiesene Trust-Stufe zeigen. Fehlende native Providerbelege bleiben sichtbar. Gleiches Trust-Level erfordert gleichwertige Prüfaussagen, nicht identische API-Antworten.

### 5.5 Persistenter VM-Zustand und sicherer Versionswechsel

Führe für `scripts/lib/consumer_intake_store.py` eine explizite Schemaversion sowie nachvollziehbare Migrationen ein. Neuinstallationen erhalten direkt das neue Schema; vorhandene Installationen werden nur mit geprüfter Kompatibilität übernommen. [R18]

- Ordne Altdaten anhand belegter Legacy-Konfiguration ihrem Provider, ihrer Instanz und ihrem Repository zu. Bei Mehrdeutigkeit halte die betroffene Migration oder Verarbeitung mit Diagnose an; erfinde keine Herkunft.
- Unterstütze opake Run-, Job- und Change-Request-IDs. Erhalte die Bedeutung von Domäne und Attempt in eindeutigen Identitäten. Derselbe native Wert auf verschiedenen Instanzen darf nicht zusammenfallen.
- Migriere den zusammengehörigen Zustand: Queue und Collection-Resolution, Cache und Watermarks, Rohbelege, verifizierte Kandidaten, akzeptierte Projektionen, eingefrorene Batches sowie deren Publikationszuordnung. Legacy-Pfade dürfen über eine explizite Zuordnung weiter lesbar bleiben.
- Erhalte historische Snapshotbytes, Digests und akzeptierte Entscheidungen. Verändere bereits veröffentlichte Batch-Identitäten, Branches oder PR-/MR-Zuordnungen nicht durch eine neue Schlüsselberechnung. Offene oder teilweise veröffentlichte Batches müssen nach einem Neustart eindeutig fortsetzbar oder ausdrücklich angehalten sein.
- Stoppe für eine Zustandsmigration betroffene schreibende Dienste kontrolliert. Erzeuge ein kohärentes Backup von SQLite und den zugehörigen Dateien mit überprüfbarem Manifest. Nutze für SQLite eine geeignete konsistente Sicherung, beispielsweise die vorhandene Backup-API; eine beliebige Dateikopie bei laufenden Schreibern genügt nicht.
- Prüfe vor Aktivierung, ob Runtime, Adapter, Schema und gespeicherte Daten zusammenpassen. Datenbankschritte müssen transaktional oder wiederanlaufsicher sein; dateiübergreifende Schritte benötigen eine nachvollziehbare Wiederaufnahme-/Recovery-Strategie.
- Ein Rollback auf älteren Code ist nur bei nachgewiesener Datenkompatibilität zulässig. Ein inkompatibles Downgrade benötigt einen dokumentierten und geprüften Restore-Pfad; sonst wird es vor Aktivierung angehalten. Nach dem Backup entstandene Evidenz und offene Publikationen müssen gesichert und abgeglichen werden, bevor älterer Zustand wieder aktiv wird.

### 5.6 VM-Modi, Schreibhoheit und Privilegien

`report-only` beschreibt den Governance-Durchsetzungsmodus. `shadow` beschreibt den Betriebsmodus des Collectors ohne aktive Veröffentlichung. Diese beiden Entscheidungen sind unabhängig und dürfen nicht in einem Flag zusammenfallen.

Erhalte beim bestehenden Pilotübergang die vorgeschriebene Schattenphase von mindestens 24 Stunden und mindestens einen nach ihrem Start erzeugten echten passenden Mainline-Lauf. Vergleiche Repository, Run/Attempt, geprüften Commit, Baseline, Verdict, Checks und Artefaktdigests zwischen den beiden Intake-Pfaden; reine Erfassungszeitstempel dürfen abweichen. Eine bereits bestandene GitHub-Schattenabnahme gilt nicht automatisch für neue Provider oder neue Herkunftsverträge. [R16]

Lokale Paritätstests verwenden dieselbe Verifikationspolicy, dieselbe explizite Auswertungszeit und denselben relevanten Referenzzustand einschließlich Replay-Historie. Beim realen Schattenvergleich werden invariant vergleichbare Ergebnisse getrennt von zeit- oder zustandsabhängigen Freshness-/Replay-Aussagen bewertet. Abweichungen dieser Aussagen benötigen eine nachvollziehbare Erklärung; sie dürfen weder durch Gleichsetzung verdeckt noch pauschal als Paritätsfehler gewertet werden.

Die Routingkonfiguration legt pro Consumer/Domäne fest, ob CI oder VM veröffentlichen darf. Ein getrennt geprüfter Routingwechsel und die Publisher-Aktivierung bleiben explizite Betriebsschritte. Schattenbetrieb darf weder PRs/MRs erzeugen noch den bisherigen Eigentümer verdrängen. Bewahre die vorhandenen Sperren, begrenzten Retries, eingefrorenen Batches und die serialisierte Publikation; im untersuchten VM-Pilot gelten höchstens 25 Ergebnisse je Batch und höchstens ein offener VM-PR. Verhindere Doppelveröffentlichung und automatisches Wiedereröffnen bewusst geschlossener Änderungsvorschläge. [R16] [R20]

Erhalte die Trennung von Reader- und Publisher-Zugangsdaten, systemd-Credentials und privaten Datenpfaden. Der Workbench liest nur die vorgesehene Projektion, nicht die Collector-Datenbank, Rohbelege oder Zugangsdaten. Collector und Publisher arbeiten in isolierten Arbeitsverzeichnissen und ändern nicht nebenläufig den aktiven Workbench-Checkout. Zugangsdaten bleiben außerhalb öffentlicher Evidenz, Reports und Repository-Inhalte. [R16]

### 5.7 Kapazitätsziel und Nachweisgrenzen

Berücksichtige 1.000–2.000 Consumer-Repositories bei Consumerprofilen, Provider-/Instanzidentitäten, Queue-Verarbeitung, API-Budgets und begrenzten Arbeitsmengen. Ein einzelner Pilot oder ein Paginierungstest mit 2.000 Läufen beweist diese Repositoryanzahl nicht.

Lege in WP0 ein versioniertes Lastprofil mit Repositoryanzahl, Läufen je Repository und Zeitfenster, Rerun-Anteil, Artefaktgrößen, Aufbewahrung, Provider-/Instanzverteilung, Testhardware sowie benötigter Verarbeitungslatenz fest. Noch nicht belegte betriebliche Werte bleiben ausdrücklich offen; für lokale Tests gewählte synthetische Werte sind als solche kenntlich zu machen. Leite daraus messbare Grenzwerte für Durchsatz, Rückstau, API-Limits, Speicher und Wiederanlauf ab und kennzeichne, wer eine spätere betriebliche Kapazitätsfreigabe verantwortet.

Führe reproduzierbare synthetische Lasttests für 1.000 und 2.000 verschiedene Repositoryidentitäten einschließlich wiederholter Läufe, Neustart und API-Drosselung aus. Messe Verarbeitungsrate, Queue-Alter/-Tiefe, API-Aufwand, CPU-/Speicherspitzen, Plattenverbrauch und Recoveryzeit. Erhalte die begrenzte Verarbeitung und serialisierte Publikation; Tests publizieren nicht auf realen Zielsystemen. Dokumentiere Engpässe und Skalierungsfolgen, bevor zusätzliche Worker oder Infrastruktur vorgeschlagen werden.

Diese Vorbereitung und die lokalen Messungen gehören zum repo-seitigen M2-Abschluss. Eine Produktionszusage für 1.000–2.000 Repositories benötigt zusätzlich bestätigte Lastannahmen, vereinbarte Grenzwerte und passende reale Nachweise. Offene Lastannahmen werden als Lücke der Kapazitätsfreigabe ausgewiesen; sie rechtfertigen kein Ende der übrigen Implementierung.

## 6. Arbeitspakete und Abhängigkeiten

### WP0 — Arbeitsstand und Schutzgrenzen sichern

**Ergebnis:** kleiner aktueller Ausführungsplan und Inventar.

- Prüfe Branch, HEAD, lokale Änderungen, offene relevante PRs und aktuelle Repository-Anweisungen.
- Prüfe den aktuellen Stand der VM-PRs #363/#364 und ihrer Vorarbeiten einschließlich #362. Arbeite auf einem kompatiblen integrierten Stand oder mit nachvollziehbaren abhängigen PRs. Führe keinen automatischen Merge aus und setze die untersuchten Draftstände nicht mit `main` gleich.
- Erfasse die VM-Einstiege, Dienst-/Datenpfade, Zustandsversionen und Drift-Prüfungen. Bei vorhandenem lesendem Zugang dokumentiere installierten Commit und Betriebsmodus; ansonsten kennzeichne diese ausdrücklich als unbekannt.
- Erfasse die betroffenen Workflow-/Script-/Schema-Einstiege sowie tatsächliche Release- und Consumer-Pins.
- Unterscheide gepflegte Quellartefakte, generierte Dateien, unveränderliche Release-Snapshots und akzeptanzgebundene Pilotdateien.
- Erfasse anhand der wirksamen Operating-Acceptance-Manifeste jede betroffene fingerprintgebundene Datei und relevante Abhängigkeit. Insbesondere `scripts/lib/result_ledger.py` und `scripts/publish_operational_update.py` bleiben im bestehenden akzeptierten Pfad unverändert; plane erforderliche neue Funktionalität über additive versionierte Nachfolger. Eine neue gemeinsame Abhängigkeit darf den geschützten Pfad nicht indirekt umstellen. Benenne unvermeidbare Akzeptanzkonflikte, bevor Änderungen daran beginnen.
- Dokumentiere die erste Unterstützungsmatrix nach Abschnitt 4.1.1, die Mac-/VM-Betriebsgrenzen nach Abschnitt 4.5 und das Lastprofil einschließlich offener betrieblicher Grenzwerte nach Abschnitt 5.7.
- Erstelle eine knappe Baseline-/Runtime-/Adapter-Zuordnung. Behauptungen aus alten Dokumenten müssen mit Code und Pins abgeglichen werden.
- Prüfe vorhandene Validierung und dokumentiere relevante Vorfehler, damit neue Regressionen getrennt erkennbar sind.
- Halte Architekturentscheidungen im vorhandenen Repo-Format fest; führe kein paralleles Governance-System ein.

**Abnahme:** aktueller Ausgangsstand, Änderungsumfang, Schutzgrenzen und erste Testfälle sind eindeutig. Keine Änderung historischer Referenzen.

### WP1 — Versionierte Verträge definieren

**Abhängigkeit:** WP0.

- Setze Abschnitt 5 in kompatibel versionierte Schemas und gemeinsame Typen/Module um.
- Definiere Identität, Ereignisnormalisierung, Status, Fehlermodell, Fähigkeiten und Versionskompatibilität.
- Schließe VM-Schemaversion, Legacy-Zuordnung, Betriebsmodi und die Trennung zwischen Herkunftslauf und VM-Verarbeitung in die Verträge ein.
- Definiere die fachlichen Aussagen, die jeder Adapter liefern muss, sowie seine expliziten Grenzen.
- Erstelle synthetische, eindeutig markierte Referenzdaten für GitHub Actions, GitLab CI und Bamboo.
- Lege den Vergleichsmaßstab fest: Entscheidung und Findings müssen gleich sein; native IDs, Transport-URLs und Zeitstempel müssen nicht bytegleich sein.

**Abnahme:** gültige und ungültige Vertragsfälle sowie Altformat-Lesbarkeit sind durch echte Tests belegt.

### WP2 — Gemeinsame Runtime implementieren

**Abhängigkeit:** WP1.

- Charakterisiere das bisherige GitHub-Gate und den Starter-Generator für relevante Positiv-/Negativfälle.
- Extrahiere Collector-Orchestrierung, Bewertung, Report-Erzeugung und Exitcode-Abbildung in gemeinsame Module.
- Nutze diese fachlichen Module auch aus dem VM-Intake. Die bereits wiederverwendeten Intake-/Generatorpfade bleiben gemeinsam; systemd-, Queue- und Deploymentdetails bleiben im Betriebsprofil.
- Verwende vorhandene OPA-Regeln und Evaluatoren. Vermeide eine weitere parallele Implementierung derselben Control-Entscheidung.
- Trenne technische Extraktion von beabsichtigten semantischen Korrekturen in nachvollziehbare Commits.
- Korrigiere insbesondere unbekannten Pflichtkontext und selbstbehauptete Enforcement-Wirkung im neuen versionierten Pfad.
- Halte alte freigegebene Pfade reproduzierbar; führe für notwendige Änderungen an geschützten Einstiegspunkten einen versionierten Nachfolger ein.

**Abnahme:** lokale Ausführung ohne Providerzugang; eindeutige Exitcodes; erforderliche fehlende Fakten erzeugen keine erfolgreich nachgewiesene Freigabe.

### WP3 — GitHub als ersten Adapter anbinden

**Abhängigkeit:** WP2.

- Binde den neuen Workflowpfad an dieselbe Runtime; der Adapter enthält ausschließlich plattformspezifische Aufgaben.
- Erhebe GitHub-Metadaten über konfigurierbare Instanz-/API-Endpunkte und normalisiere den geprüften Commit korrekt.
- Sorge für Artefakte und Diagnosen auch bei Findings oder Fehlern.
- Halte Checks eindeutig und revisionsgebunden; Erfolg darf nicht auf eine andere oder veraltete Revision übertragen werden.
- Erhalte aktuelle Consumer-Pins und bestehende aktive Enforcement-Modi.

**Abnahme:** Vergleich mit charakterisiertem Verhalten; beabsichtigte Unterschiede separat dokumentiert; kein unbeabsichtigter Wechsel bestehender Consumer.

### WP4 — GitLab und Bamboo funktional anbinden

**Abhängigkeit:** WP2; parallele Arbeiten zu WP3 nur mit disjunkter Dateiverantwortung.

- Implementiere GitLab-Kontext einschließlich Untergruppen, MR-/Branch-Kontext und normalen beziehungsweise zusammengeführten Prüfrevisionen.
- Ersetze Echo-Vorlagen durch ausführbare Aufrufe der gemeinsamen Runtime.
- Stelle Bamboo auf denselben Prüfpfad um; Bamboo liefert CI-Daten, der konfigurierte SCM-Adapter liefert Repository-/Reviewdaten.
- Unterstütze GitLab als SCM und Bitbucket Data Center als relevanten SCM für den Bamboo-Pfad. Verwende explizite Fähigkeitsprofile, wo native Funktionen unterschiedlich sind.
- Entferne automatische Security-Platzhalter aus dem produktionsgeeigneten Pfad. Demo-Fixtures sind separat, explizit aktiviert und als synthetisch gekennzeichnet.
- Neue Consumer-Vorlagen starten in `report-only` und archivieren Ergebnisse zuverlässig.

**Abnahme:** M1 ist erreicht, wenn drei funktionale Adapter denselben lokalen Vertrags- und Paritätstest bestehen und echte Live-Lücken korrekt ausgewiesen sind. Das ist noch keine Live-Zertifizierung aller Plattformen.

### WP5 — Evidenzidentität, Verifier und Intake entkoppeln

**Abhängigkeit:** WP1–WP4.

- Implementiere die versionierte Provider-/Instanzidentität in Replay, Collection-Resolution, Speicherung und Indizes.
- Erweitere den neutralen Bundle-Pfad um gemeinsame Verifikation; bewahre Unterschiede zwischen deklarierter und verifizierter Evidenz.
- Trenne GitHub-spezifische Herkunftserhebung vom gemeinsamen Verifier und ergänze die vorgesehenen GitLab-/Bamboo-Pfade.
- Bewahre Rohbelege und Provenienzgrenzen. Ergänze Tests für Manipulation, falsche Bindung und fehlende Fähigkeit.
- Unterstütze alte und neue Datensatzversionen gemeinsam. Alte Evidence-Dateien, IDs und Entscheidungen werden nicht neu geschrieben.
- Implementiere die VM-Zustandsmigration nach Abschnitt 5.5 einschließlich SQLite, Caches, Dateipfaden und Publikationszuordnung. Prüfe vorhandene, leere, mehrdeutige und teilweise migrierte Zustände mit aussagekräftigen Fixtures.
- Prüfe die Parität des CI- und VM-Intakes mit identischen vertrauenswürdigen Eingaben, Baseline und kompatiblen Runtime-/Adapterversionen. Kontrolliere dabei Verifikationspolicy, Auswertungszeit und Referenzzustand nach Abschnitt 5.6.

**Abnahme:** Instanz-/Providerkollisionen ausgeschlossen; Untergruppen verarbeitet; negative Herkunftsfälle erkannt; historische Snapshots unverändert lesbar. VM-Neuinstallation, Zustandsupgrade und Wiederaufnahme nach Migrationsfehler sind geprüft.

### WP6 — Zentrale Operations an Adaptergrenzen führen

**Abhängigkeit:** WP5.

- Trenne in betroffenen zentralen Pfaden lokale Git-Arbeit, SCM-PR/MR-Publikation, CI-Trigger, Statusausgabe und Artefakttransport.
- Verwende `publish_operational_update.py` als Referenz für die bestehende Publikationsgrenze; der fingerprintgebundene Einstieg bleibt unverändert. Implementiere neue Publikationspfade als additive versionierte Nachfolger und führe neue Intake-Einstiege sowie Viewer-/Run-Links an die Adaptergrenzen. Erhalte akzeptierte Legacyprofile einschließlich ihrer Abhängigkeiten bis zu einer gesonderten versionierten Abnahme.
- Beziehe `scripts/lib/consumer_github.py`, `scripts/lib/consumer_intake.py`, `scripts/lib/consumer_publisher.py` und die Consumer-Routingkonfiguration ein. Überführe Discovery, Herkunftserhebung und PR-/MR-Publikation in die vorgesehenen gemeinsamen Provideradapter.
- Erhalte im VM-Pfad Schattenmodus, explizite Schreibhoheit, Sperren, Retry-Grenzen, Batch-Freeze und Reconciliation. Fertige wie fehlgeschlagene Consumer-Läufe müssen entsprechend dem fachlichen Vertrag behandelbar bleiben; ein negatives Governance-Ergebnis ist kein Grund, die Evidenz zu verwerfen.
- Trenne anbieterspezifische Self-Security-Erhebung vom gemeinsamen Assessment; bilde gleichwertige Fähigkeiten explizit ab.
- Führe neue Providerprofile für Lifecycle-/Reviewbelege ein, soweit repo-seitig möglich. Erhalte bestehende akzeptierte GitHub-Profile unverändert.
- Verwende für neue Identitäten eine explizite Issuer-/Subject-Bindung. Ein Anbietername allein ist keine Rollen- oder Freigabeautorität.
- Dokumentiere konkrete Legacygrenzen, die aufgrund akzeptierter Profile bestehen bleiben. Diese dürfen nicht als vollständig migriert bezeichnet werden.

**Abnahme:** unterstützte neue Operationspfade haben klare Adaptergrenzen und Vertragstests. Live-Autorität wird nicht durch Code, Schemaerweiterung oder synthetischen Test erzeugt.

### WP7 — Reproduzierbare Verteilung und VM-Betrieb integrieren

**Abhängigkeit:** parallel ab WP2; vor M2-Abschluss integrieren.

- Definiere ein Runtime-/Baseline-Manifest mit exakten Versionen und Digests sowie Kompatibilitätsprüfung.
- Nutze die vorhandenen verifizierten OPA-Installationsbausteine. Ersetze ungepinnte `latest`-/Upgrade-Pfade in den neuen Integrationen.
- Mache interne Paket-, Image-, Baseline- und Artefaktquellen konfigurierbar.
- Unterscheide internen Onlinebetrieb und vollständig vorbereiteten Offlinebetrieb. Ein Mirror mit öffentlichem Fallback erfüllt keine Offline-Zusage.
- Prüfe Auswertung ohne externe Netzabhängigkeit, nachdem die benötigten Pakete bereitgestellt sind.
- Prüfe den parallelen Mac-/VM-Betrieb nach Abschnitt 4.5 einschließlich gleicher fachlicher Ergebnisse, getrennter Sessions/Zustände/Credentials und eindeutiger Veröffentlichungszuständigkeit. Führe die reproduzierbaren Kapazitätsmessungen nach Abschnitt 5.7 durch und dokumentiere offene Produktionsgrenzen.
- Dokumentiere getrennt erforderliche Scanner-Images und aktualisierbare Sicherheitsdatenbanken.
- Integriere die neue Runtime in die bestehenden VM-Einstiege `scripts/deploy_vm.sh`, `scripts/deploy_vm.py`, `scripts/lib/vm_deployment.py` und die Ansible-/systemd-Konfiguration. Kandidatenprüfung und Aktivierung beziehen sich auf denselben exakten Commit beziehungsweise nachgewiesen vollständigen Paketdigest. [R14] [R21]
- Erweitere den Drift-/Kompatibilitätsvergleich um sämtliche neuen Core-/Adapterpakete, Profile, Schemas und relevanten Abhängigkeiten. Bei abweichendem Anwendungsstand bleibt `application_update_required` wirksam. Ein Datenabgleich darf keine neue Anwendungsversion beiläufig ausführen oder aktivieren. [R17]
- Bereite Neuinstallation und Update einer vorhandenen VM vor: Kandidat und Abhängigkeiten prüfen, Dienste geordnet anhalten, zusammengehörige Zustände sichern, gegebenenfalls migrieren, exakt geprüften Stand aktivieren und Funktionsprüfung durchführen. Erhalte vorhandene VM-/Controller-Sicherungen und deren Prüfsummen. [R14] [R16] [R21]
- Prüfe Wiederanlauf und fehlgeschlagene Aktivierung einschließlich Workbench-Anmeldung, Datenzugriff, Abmeldung und Collector-/Publisher-Zustand. Erhalte private Drafts und Credentials; ein Code-Rollback setzt sie nicht stillschweigend zurück.
- Behandle ein Downgrade auf eine Runtime ohne Collector ausdrücklich: betroffene Timer/Dienste deaktivieren, Zustand erhalten und Kompatibilität beziehungsweise Restore vorab prüfen. Führe keinen automatischen Wechsel der Intake-Schreibhoheit durch.
- Erstelle ein ausführbares Update-/Recovery-Runbook mit Vorbedingungen, Versionsmatrix, Backups, Wiederherstellungsprüfung und konkreten Aktivierungsschritten. Der reale Rollout bleibt ein gesonderter Betriebsschritt nach Abschnitt 3.2.

**Abnahme:** reproduzierbarer lokaler Start mit festgelegten Abhängigkeiten; dokumentierter interner Bereitstellungspfad; VM-Installation, Upgrade, Wiederanlauf und Recovery in einer isolierten geeigneten Testumgebung geprüft. Reale VM- und Offline-Abnahmen nur bei tatsächlich erfolgtem Test als geprüft kennzeichnen.

### WP8 — Gesamtvalidierung, Reviews und Übergabe

**Abhängigkeit:** alle vorangehenden Arbeitspakete.

- Führe die Akzeptanzmatrix aus Abschnitt 7 und die Repositoryvalidierung aus.
- Erstelle die geforderten revisiongebundenen Fachreviews. Spezialisten zuerst, Repo Steward zuletzt.
- Prüfe tatsächlich geänderte API-/CI-Syntax gegen die offiziellen Dokumentationen der Zielversionen. Die Quellen in Abschnitt 12 sind Ausgangspunkte; sie ersetzen keine Versionsprüfung.
- Halte veränderte Governance-Semantik, Migration, Rollback und offene externe Abnahmen nachvollziehbar fest.
- Weise die VM-Ergebnisse ausdrücklich aus: gemeinsame Module, Datenmigration, Drift-Sperre, Update-/Recovery-Nachweise, Schattenvergleich und weiterhin offene Live-Aktivierung. Ein isolierter Deploymenttest ist kein Nachweis einer aktualisierten Ziel-VM.
- Erstelle kohärente, abhängige PRs. Verknüpfe jeden PR mit Goal, WP, Vertrag und Testnachweis.
- Prüfe die für den PR verfügbaren CI-Ergebnisse und behebe eigene Regressionen. Bleibt eine externe Abhängigkeit, stelle einen konkret überprüfbaren Zwischenstand bereit und kennzeichne den offenen Abschluss.

**Abnahme:** M1/M2-Ergebnisse und Live-Reife sind getrennt nachvollziehbar; alle repo-seitig ausführbaren Arbeiten sind erledigt oder mit einem konkreten echten Blocker belegt.

## 7. Verbindliche Akzeptanz- und Testmatrix

Nutze bestehende Tests, wo sie die Aussage tatsächlich prüfen. Ergänze Tests für neue fachliche Risiken. Das Vorhandensein einer Datei, eines Strings oder eines Adapternamens reicht nicht als Funktionsnachweis.

| ID | Szenario | Erwartetes Ergebnis | Nachweisebene |
| --- | --- | --- | --- |
| AC01 | Identische fachliche Inputs und Baseline auf drei Adaptern | Gleiche kanonische Control-Ergebnisse, Findings und Entscheidung; bewusst variable Metadaten separat verglichen. | Lokal/Vertrag |
| AC02 | Fehlendes Repository, fehlender geprüfter Commit oder unbekannte Pflichtdaten | Keine erfolgreich nachgewiesene Freigabe; eindeutige Diagnose. | Lokal/Regression |
| AC03 | Synthetische Dateien, unbekannter Kontext und Bamboo-Modus `block-on-error` | Regression F03 behoben; kein verifiziertes `pass`, keine behauptete wirksame Merge-Sperre. | Lokal/Regression |
| AC04 | Fachliches Finding in Report-only und Blocking | Identische fachliche Entscheidung; unterschiedliche, dokumentierte Exitcode-Abbildung. | Lokal/Vertrag |
| AC05 | Ungültiges JSON, fehlende Policy, OPA-Fehler oder unbekannter Modus | Technischer Fehler; kein stilles Überspringen oder Erfolg. | Lokal/Negativ |
| AC06 | API nicht erreichbar, Zugriff verweigert oder Fähigkeit nicht unterstützt | Erhebungsstatus und fehlende Nachweise sichtbar; keine Erfolgsannahme. | Fixture und später live |
| AC07 | GitLab-Untergruppe und opaker Bamboo-Build-Key | Identität wird korrekt verarbeitet und wiedergefunden. | Lokal/Schema |
| AC08 | Gleichnamige Repositories/Runs auf zwei Providern oder Instanzen | Verschiedene Speicher-, Replay- und Resolution-Identitäten. | Lokal/Regression |
| AC09 | Source-Head gegenüber Merge-Ergebnis; neuer Commit nach erfolgreicher Prüfung | Ergebnis bleibt an den tatsächlich geprüften Stand gebunden; alter Status erfüllt keinen neuen Pflichtnachweis. | Lokal und live |
| AC10 | Manipuliertes Artefakt, falscher Commit oder falsche Baseline | Verifikation schlägt eindeutig fehl; Trust wird nicht erhöht. | Lokal/Negativ |
| AC11 | Fehlender Herkunftsbeleg, wiederholtes Bundle oder veraltete Evidenz | Definierte Trust-/Replay-/Freshness-Auswertung mit deterministischer Zeitbasis. | Lokal/Vertrag |
| AC12 | Historische Snapshots, Releases und akzeptierte Profile | Bytes unverändert; Leser/Projektionen bleiben kompatibel; Akzeptanz nicht stillschweigend erneuert. | Regression |
| AC13 | Gate-Finding, Toolfehler, Abbruch oder Publikationsfehler | Verfügbare Diagnosen erhalten; kein ersatzweises Erfolgsresultat. | Lokal und live |
| AC14 | Kern ohne Provider-Environment und ohne Anbieterzugang | Vollständige Auswertung normalisierter Eingaben möglich. | Lokal/Architektur |
| AC15 | Vorbereitete Runtime ohne Zugriff auf öffentliche Dienste | Auswertung funktioniert; nicht vorbereitete Abhängigkeiten führen zu klarer Fehlermeldung. | Lokal/offline; getrennt real |
| AC16 | Verbindliche Merge-Regel auf realem Git-Host bei gesonderter Blocking-Abnahme | Negatives, fehlendes oder veraltetes Pflichtresultat verhindert den Merge im autorisierten Testumfang; neue Regeln werden nicht allein für diesen Nachweis produktiv aktiviert. | Gesonderte Live-Blocking-Abnahme |
| AC17 | Manipulierter Consumer-Input oder geänderte untrusted Pipeline | Kann keine vertrauenswürdige Baseline, Provideridentität oder Freigabe selbst deklarieren. | Vertrag und Integration |
| AC18 | Identische Belege über CI- und VM-Intake bei gleicher Baseline, Verifikationspolicy, Auswertungszeit und Replay-Historie sowie kompatibler Runtime | Gleiche kanonische Verifikation, Control-Ergebnisse und Trust-Aussagen; Herkunftslauf und VM-Ausführung bleiben getrennt. Im realen Schattenvergleich zeit-/zustandsabhängige Aussagen gemäß Abschnitt 5.6 gesondert bewerten. | Lokal/Parität; später Schattenvergleich |
| AC19 | VM-Neuinstallation sowie Upgrade eines bestehenden Legacy-SQLite-/Dateizustands | Richtige Schemaversion und belegte Legacy-Zuordnung; Snapshotbytes, Digests, Entscheidungen, offene Batches und Publikationszuordnungen bleiben erhalten. Mehrdeutige Daten führen zum kontrollierten Halt. | Lokal/Migration |
| AC20 | Gleiche native IDs aus mehreren Providern/Instanzen, opake IDs und wiederholte Verarbeitung | Keine Kollision in Queue, Cache, Dateipfaden, Indizes oder Batches; Wiederaufnahme erzeugt keine zweite Publikation desselben Ergebnisses. | Lokal/Regression |
| AC21 | Neue oder geänderte Core-/Adapterdatei gegenüber installiertem VM-Stand | Drift führt vor Verarbeitung inkompatibler Daten zu `application_update_required`; erst ein kontrolliertes kompatibles Update hebt die Sperre auf. | Lokal und isolierte Integration |
| AC22 | VM-Update auf exakte Revision mit anschließendem Dienstneustart | Geprüfter Kandidat wird aktiviert; Workbench-Funktion, Collector-Zustand, private Drafts und ausstehende Verarbeitung bleiben erhalten; Backup und Wiederherstellung sind nachgewiesen. | Isolierte Ubuntu-/systemd-Integration |
| AC23 | Abbruch während Zustandsmigration, fehlerhafte Aktivierung und inkompatibles Downgrade | Wiederaufnahme oder geprüfter Restore funktioniert; inkompatibler alter Code wird nicht auf neuer Datenbank gestartet; keine verlorene Evidenz oder doppelte Publikation. | Fehler-/Recovery-Integration |
| AC24 | Schattenbetrieb, Routingwechsel und Neustart mit offenem Batch/PR/MR | Schattenmodus publiziert nicht; genau ein zuständiger Publisher; keine doppelte oder ungewollt wiedereröffnete Veröffentlichung. Bestehende Live-Schattenabnahme benötigt mindestens 24 Stunden und einen neuen passenden Lauf. | Lokal/Integration; Dauer und echter Lauf nur live |
| AC25 | VM-Berechtigungsgrenzen und neue Providerkonfiguration | Reader-/Publisher-Zugänge bleiben getrennt; Workbench liest nur seine Projektion; Collector verändert nicht den aktiven Checkout; Credentials erscheinen nicht in Evidenz/Reports. | Konfiguration und isolierte Integration |
| AC26 | Gleichzeitig laufende Mac- und VM-Workbench | Beide nutzbar; Sessions, Drafts, Credentials und Backups getrennt; keine automatische Synchronisation oder zweite aktive Veröffentlichungsinstanz. | Mac und isolierte Ubuntu-/systemd-Integration |
| AC27 | Gleiche normalisierte Eingaben auf Mac und VM | Gleiche fachliche Ergebnisse bei gleichen Versions-, Zeit- und Referenzzuständen; hostabhängige Metadaten getrennt. | Plattformübergreifende Parität |
| AC28 | 1.000 und 2.000 verschiedene Consumer-Repositories mit Reruns, Drosselung und Neustart | Identitäten bleiben getrennt; Verarbeitung bleibt begrenzt und wiederaufnehmbar. Durchsatz, Rückstau, API-Aufwand, Ressourcen und Recovery werden gegen das ausgewiesene Testlastprofil gemessen; keine Produktionszusage aus synthetischen Daten. | Lokale/isolierte synthetische Lasttests |
| AC29 | Umbau von Ledger-/Publikationspfaden mit bestehender Operating Acceptance | Betroffene Fingerprints erfasst; geschützte Dateien und akzeptierte Pfade unverändert. Neue Funktion über additive Nachfolger, keine indirekte Umstellung bestehender Akzeptanz. | Diff-/Fingerprint- und Regressionsprüfung |
| AC30 | Abnahme eines neuen Anbieterprofils im Report-only-Betrieb | Profil/Versionen und tatsächliche Live-Nachweise ausgewiesen; Findings sichtbar; fehlende Blocking-Abnahme wird separat geführt und verhindert keine ausdrücklich begrenzte Report-only-Freigabe. | Profilprüfung und gesonderte Live-Betriebsabnahme |

Melde keine vollständige Plattformunterstützung allein aufgrund synthetischer Fixtures. Für jede Kombination führe eine Matrix mit den unabhängigen Angaben `implementiert`, `lokal_geprüft`, `syntax_geprüft`, `live_geprüft` und `offen`, jeweils mit Revision, Systemversion/Edition, Testfall und Nachweis. Nicht alle fünf Angaben sind lineare Reifestufen. Ergänze für den VM-Betrieb installierte beziehungsweise getestete Revision, Zustandsversion, Betriebsmodus und Deploymentnachweis. Die Umsetzung einer Migration ist getrennt von ihrer Durchführung auf einer bestehenden Ziel-VM auszuweisen.

### 7.1 Getrennte Abschluss- und Freigabeentscheidungen

| Entscheidung | Erforderlicher Nachweis | Aussagegrenze |
| --- | --- | --- |
| Repo-seitiger Abschluss M1/M2 | Jeweils ausführbare Vertrags-, Regressions-, Paritäts-, Migrations-, Betriebs- und Lasttests; offene externe Abnahmen konkret benannt | Implementiert und lokal/isoliert verifiziert; keine Live-Freigabe |
| Operativer Report-only-Betrieb | Explizites Anbieterprofil mit Versionen, reale Ausführung und Evidence-Verifikation, Diagnosen sowie nötige Betriebs-/Recovery-Nachweise; VM-Schattenabnahme bei der jeweiligen Umschaltung | Findings sichtbar; keine zugesagte Merge-Sperre. VM-Publisher und Routing benötigen weiterhin die gesonderten Betriebsschritte. |
| Blocking-Freigabe | Zusätzlich passende Autorisierung, bestehende Blocking-Readiness-Kriterien und AC16 auf dem betreffenden Profil | Wirksame Durchsetzung nur im tatsächlich abgenommenen Umfang |
| Kapazitätsfreigabe 1.000–2.000 Repositories | Bestätigtes Lastprofil, vereinbarte Grenzwerte und passende reale Messungen nach Abschnitt 5.7 | Keine pauschale Übertragung auf andere Provider, Lasten oder Hardware |

AC16 ist kein Abschlusskriterium für repo-seitige Implementierung oder eine ausdrücklich begrenzte Report-only-Betriebsfreigabe. Fehlende Live-Nachweise bleiben offen und werden durch diese Trennung nicht als erfüllt gewertet.

## 8. Baseline-, Historien- und Migrationsregeln

- Baseline-Version, Runtime-Version und Adapter-Version sind getrennte, exakt auflösbare Größen.
- Unterscheide aktuelle Quellen, vorbereitete Releases und tatsächlich konsumierte veröffentlichte Stände.
- Ändere veröffentlichte Pakete, Tags und Signaturen nicht nachträglich. Erzeuge bei Bedarf neue Kandidaten mit klarer Herkunft; ihre produktive Veröffentlichung ist ein separater Schritt.
- Ändere eine bestehende Control-Bedeutung nicht stillschweigend während einer technischen Extraktion. Kennzeichne notwendige Korrekturen, Version und Auswirkungen ausdrücklich.
- Lies die tatsächlich fingerprintgebundenen Dateien der akzeptierten Piloten. Verwende additive Nachfolger, wenn ein Umbau bestehende Akzeptanz ungültig machen würde.
- Alte Evidenz und neue Evidenz bleiben unterscheidbar. Kein nachträgliches Hochstufen historischer Trust-Werte.
- Eine bestehende GitHub-Abnahme beweist keine GitLab-/Bamboo-Abnahme.
- Rollback bedeutet, Consumer auf den bisherigen vollständigen Runtime-/Baseline-/Adapter-Pin zurückzuführen. Neu entstandene Evidenz bleibt erhalten. Für die VM ist zusätzlich die Kompatibilität mit dem persistenten Zustand nach Abschnitt 5.5 nachzuweisen; ein Code-Pin allein reicht nicht.
- VM- und CI-Betrieb bleiben auf einem gemeinsamen Produktpfad. Untersuchte VM-Draft-PRs werden über ihren aktuellen kompatiblen Stand integriert; es entsteht kein dauerhaft abweichender VM-Fork.
- Ein neuer Runtime-Stand erneuert weder historische Schattenabnahmen noch die Autorisierung zur Übernahme der Intake-Schreibhoheit. Änderungen mit Auswirkung auf akzeptierte Fingerprints benötigen den dafür vorgesehenen Nachfolger-/Abnahmeweg.

## 9. Validierung und Agentenreview

Verwende die aktuell im Repository vorgeschriebenen Befehle. Am analysierten Stand sind dies vor einem relevanten Commit insbesondere:

```bash
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh
```

Die vollständige Validierung umfasst unter anderem OPA-Prüfung, Runtime-/Repo-Validierung, Evidence-Agent-Provenance und Python-Tests. Betroffene UI-/Viewer-Pfade benötigen ihre einschlägigen vorhandenen Tests. Passe den Validierungsumfang an reale Änderungen an, ohne vorgeschriebene Gates auszulassen.

Für die VM sind insbesondere die vorhandenen Tests in `tests/test_vm_deployment.py`, `tests/test_consumer_intake.py` und bei berührter Projektion `tests/workbench-consumers.test.cjs` einzubeziehen. Die Integrationsharnesses `tests/integration/run_vm_deployment.py` und `tests/integration/run_consumer_intake.py` am jeweiligen aktuellen Stand dienen als Ausgangspunkt. Erweitere sie um die konkreten Migrations-, Paritäts-, Drift- und Recovery-Risiken dieses Goals. [R14] [R16]

Deployment- und Recoverytests laufen in einer wegwerfbaren, geeigneten Ubuntu-/systemd-Testumgebung mit synthetischen Zugangsdaten und Testzustand. Starte solche potenziell verändernden Harnesses nicht auf der bestehenden Ziel-VM. Falls die ausführende Umgebung keine geeignete Integration unterstützt, führe die verfügbaren lokalen Tests aus, bereite den reproduzierbaren CI-Test vor und benenne die noch nicht ausgeführte Prüfung konkret. Ein Mock ersetzt keinen systemd-/Deploymentnachweis.

Behandle den Bootstrap als Vorbereitung mit Abhängigkeitszugriffen; seine bloße Ausführung ist kein Offline-Nachweis. Dokumentiere fehlende Tools, Netzwerkgrenzen und Vorfehler präzise. Entferne oder schwäche keine Prüfungen, um eine erfolgreiche Ausführung zu behaupten.

Nutze `scripts/dispatch_governance_agents.py` und die aktuelle Review-Anleitung für den revisiongebundenen Reviewplan. Die CLI benötigt beim Plan einen konkreten `--goal`; halte private Pläne und Ergebnisse außerhalb des Checkouts. Erzeuge den Plan nach relevanten HEAD-/Scope-/Vertragsänderungen erneut.

Unterscheide ausgewählte Rollen, tatsächlich ausgeführte Subagenten und menschliche Reviews. Ein Agentenreview ersetzt keine menschliche Freigabe, Release-Autorität oder Blocking-Autorisierung. Reiche bei offenen hohen oder kritischen Review-Findings keinen Stand als bereit zur Abnahme aus.

## 10. Autonome Arbeitsweise und konkrete Blocker

Arbeite nach dem Muster: aktuellen Stand prüfen, kleinsten kohärenten Schnitt implementieren, gezielt prüfen, abhängige Arbeiten fortsetzen, vollständig validieren, reviewen und als PR bereitstellen.

Entscheide Modulnamen, interne Hilfsfunktionen, Testorganisation und vergleichbare technische Details selbst. Vermeide wiederholte Rückfragen zu bereits festgelegten Zielen. Halte den Fortschritt in einem knappen WP-/Akzeptanzstatus fest, damit eine Fortsetzung ohne erneute Grundanalyse möglich ist.

Pausiere nur die betroffene Aktion, wenn ein echter Konflikt besteht: fehlende notwendige Identität oder Berechtigung, unvermeidbare Änderung historischer Akzeptanz, erforderliche neue produktive Durchsetzung oder eine nicht vom Auftrag gedeckte Veröffentlichung. Arbeite alle davon unabhängigen Pakete weiter ab.

Für jeden Blocker liefere:

1. Betroffenes WP und Akzeptanzkriterium.
2. Konkrete fehlende Information, Berechtigung oder Entscheidung.
3. Bereits implementierten und geprüften Umfang.
4. Kleinsten nächsten Schritt, mit dem der Blocker behoben wird.

Fehlende GitLab-/Bamboo- oder VM-Zugänge sind kein Grund, nach Architektur oder Stub-Adaptern aufzuhören. Sie sind ein Grund, Live-Abnahme offen zu lassen. Ist ein API-Vertrag unklar, prüfe offizielle Dokumentation oder markiere genau die betroffene Fähigkeit als offen; erfinde keine Endpunkte oder Nachweise.

## 11. Liefergegenstände und Definition of Done

### 11.1 Erwartete Liefergegenstände

- Implementierter gemeinsamer Runtime-Einstieg mit dokumentiertem Vertrag.
- Funktionale GitHub-Actions-, GitLab-CI- und Bamboo-Adapter/Vorlagen.
- Konfigurierbare SCM-Adapter für die in der Unterstützungsmatrix vorgesehenen GitHub-, GitLab- und Bitbucket-Data-Center-Pfade.
- Versionierte Kontext-, Identitäts-, Ergebnis- und Evidence-Verträge mit Altformatverträglichkeit.
- Gemeinsamer Evidence-Verifier und nachvollziehbar angebundene Transport-/Intake-Pfade.
- Entkoppelte neue zentrale Operationspfade und explizite Grenzen verbleibender Legacyprofile.
- Reproduzierbares Runtime-/Baseline-Paket beziehungsweise Manifest für interne Bereitstellung.
- Integriertes VM-Betriebsprofil mit gemeinsamem Core, konfigurierbaren Providern, versionsgebundenem Deployment und wirksamer Drift-Sperre.
- Versionierte VM-Zustandsmigration einschließlich Cache-/Batch-/Publikationszuordnung sowie geprüfter Backup-, Wiederanlauf- und Recovery-Pfade.
- VM-Update-/Rollback-Runbook, Kompatibilitätsmatrix und nachvollziehbarer Schatten-/Routing-/Publisher-Aktivierungsplan.
- Sinnvolle Vertrags-, Negativ-, Regressions- und Paritätstests.
- Architekturentscheidung, Integrationsanleitung, Migrations-/Rollback-Anleitung und aktuelle Unterstützungsmatrix im vorhandenen Dokumentationssystem.
- Reviewfähige Commits/PRs sowie eine Nachweismatrix für alle Akzeptanzkriterien.

### 11.2 Prüfliste für den repo-seitigen Abschluss

- [ ] WP0–WP8 sind abgeschlossen oder mit konkreten echten Blockern und erledigtem unabhängigem Umfang dokumentiert.
- [ ] Die neuen drei CI-Pfade verwenden dieselbe fachliche Bewertung und denselben Gate-Vertrag.
- [ ] M1 ist implementiert und lokal anhand AC01–AC07 sowie AC13/AC14 geprüft.
- [ ] M2 ist im beschriebenen repo-seitigen Umfang implementiert; AC08–AC12 und relevante Operationsprüfungen sind belegt.
- [ ] Die VM verwendet dieselben fachlichen Module und Adapterverträge; AC18–AC29 sind für die jeweils lokal beziehungsweise isoliert ausführbaren Ebenen belegt; AC30 bleibt bis zur jeweiligen Live-Betriebsabnahme offen.
- [ ] Versionierter Bestandsdatenpfad, Drift-Sperre, Update und Recovery sind implementiert; verbleibende echte Testblocker sind konkret dokumentiert.
- [ ] VM-PR-Abhängigkeiten und Zielrevision sind nachvollziehbar; reale Installation, Schattenabnahme, Eigentümerwechsel und Publisher-Aktivierung werden getrennt mit ihrem tatsächlichen Status geführt.
- [ ] Kein neuer Pflichtcheck/Blocking-Modus ist ohne passende gesonderte Autorisierung auf einem realen Consumer aktiviert.
- [ ] Historische Pakete, Evidenz, Signaturen und akzeptierte Profile sind erhalten.
- [ ] Erforderliche Validierungen und revisiongebundene Reviews sind aktuell; eigene Regressionen sind behoben.
- [ ] Interne Bereitstellung und Offline-Grenzen sind nachvollziehbar dokumentiert.
- [ ] Erste Unterstützungsmatrix und offene Versionen/Editionen sind ausgewiesen; Mac-/VM-Parität und getrennte Zustände sind geprüft.
- [ ] Lasttests für 1.000 und 2.000 Repositoryidentitäten sind ausgeführt; Testlastprofil, Messwerte und offene Produktionsgrenzen sind nachvollziehbar.
- [ ] Report-only-Betriebsfreigabe, Blocking-Abnahme und Kapazitätsfreigabe sind getrennt geführt; AC16 wird nur für Blocking beansprucht.
- [ ] Live-Abnahme ist je Kombination belegt oder konkret offen ausgewiesen.
- [ ] PR-Beschreibung und Abschlussbericht erklären Änderungen, Nutzen, Tests, Grenzen und nächsten Schritt.

Ein repo-seitig fertiger Stand mit offenen externen Abnahmen heißt **„implementiert und lokal verifiziert; Live-Abnahme offen“**. Eine **Report-only-Betriebsfreigabe** setzt die entsprechenden realen Nachweise nach Abschnitt 7.1 voraus und behauptet keine Merge-Sperre. Eine **Blocking-Freigabe** erfordert zusätzlich Autorisierung und wirksame Merge-Durchsetzung nach AC16. Eine **Kapazitätsfreigabe für 1.000–2.000 Repositories** benötigt ihren eigenen Lastnachweis. Jede Aussage nennt Profil, Versionen, Revision und Nachweisumfang. Ein Blocker macht das betreffende Akzeptanzkriterium nicht erfüllt.

### 11.3 Format des Abschlussberichts

1. Ergebnis je Meilenstein und wichtigste Architekturentscheidungen.
2. Commit-/PR-Links und betroffene Verträge.
3. Ausgeführte Tests mit konkreten Ergebnissen.
4. Unterstützungsmatrix mit Versions-/Editionsbezug und Nachweisgrenzen.
5. Beabsichtigte Verhaltensänderungen gegenüber dem Ausgangsstand.
6. Erhaltene historische/akzeptanzgebundene Grenzen.
7. Mac-/VM-Integrationsstand einschließlich Revisionen, Parität, getrennter Zustände, Datenkompatibilität, Update-/Recovery-Nachweisen und tatsächlichem Aktivierungsstatus.
   Weise zusätzlich Lastprofil, Messwerte für 1.000/2.000 Repositories und offene Kapazitätsgrenzen sowie Report-only- und Blocking-Freigaben getrennt aus.
8. Offene Punkte, echte Blocker und kleinster nächster Schritt.

## 12. Quellen und weiterführende Referenzen

### Repositoryquellen am analysierten Commit

Die folgenden Links belegen die Ausgangsbefunde. Für die Umsetzung ist zusätzlich der aktuelle Checkout maßgeblich.

- [R1: CI/CD Platform Adapter Strategy][R1]
- [R2: GitHub Reusable Baseline Workflow][R2]
- [R3: Pipeline-Evidence-Generator][R3]
- [R4: Plattformkontextgenerator][R4]
- [R5: GitLab-Consumer-Vorlage][R5]
- [R6: Bamboo-Specs-Vorlage][R6]
- [R7: Plattformneutraler Bundle-Import][R7]
- [R8: Replay-/Result-Ledger][R8]
- [R9: GitHub-gebundene Lifecycle-Evidenz][R9]
- [R10: Veröffentlichter L1-v1.1.3-Wrapper][R10]
- [R11: Verifizierter OPA-Installer][R11]
- [R12: Repository-Arbeitsregeln][R12]

### Zusätzlich untersuchte VM-Quellen

Die PR-Links beschreiben den Arbeitszusammenhang; die Dateilinks sind auf die oben genannten untersuchten Commits gebunden.

- [R13: PR #363 — Reproduzierbare Ubuntu-VM-Installation][R13]
- [R14: Installations-, Update- und Recovery-Anleitung am VM-Installationsstand][R14]
- [R15: PR #364 — Consumer-Intake auf der VM im Schattenbetrieb][R15]
- [R16: VM-Consumer-Intake, Schattenbetrieb, Routing und Backup][R16]
- [R17: VM-Intake-Orchestrierung und Drift-Prüfung][R17]
- [R18: Persistenter VM-Consumer-Store][R18]
- [R19: GitHub-Anbindung des VM-Collectors][R19]
- [R20: VM-Publisher und Batch-Reconciliation][R20]
- [R21: Revisionsgebundene VM-Aktivierung][R21]

### Offizielle Plattformdokumentation

- [P1: GitHub-Ereignisse und Commit-Semantik][P1]
- [P2: GitLab CI/CD predefined variables][P2]
- [P3: Bamboo und generische Git-Repositories][P3]
- [P4: Bitbucket Data Center — Merge Checks und Required Builds][P4]
- [P5: GitHub — Protected Branches][P5]
- [P6: GitLab — Offline Environments][P6]
- [P7: Bamboo YAML Specs][P7]
- [P8: GitLab — Merge Checks und Pipelines][P8]

Die Dokumentationsstände und verfügbaren Features sind gegen die tatsächlich eingesetzten Versionen und Editionen zu prüfen. Insbesondere sind GitHub.com und GitHub Enterprise Server sowie Bitbucket Cloud und Data Center getrennte Integrationsprofile.

[R1]: https://github.com/joku-dev/devsecops-governance-framework/blob/4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be/docs/operations/adapters/cicd-platform-adapter-strategy.md
[R2]: https://github.com/joku-dev/devsecops-governance-framework/blob/4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be/.github/workflows/devsecops-baseline-reusable.yml
[R3]: https://github.com/joku-dev/devsecops-governance-framework/blob/4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be/scripts/generate_pipeline_evidence.py
[R4]: https://github.com/joku-dev/devsecops-governance-framework/blob/4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be/scripts/generate_platform_context.py
[R5]: https://github.com/joku-dev/devsecops-governance-framework/blob/4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be/pipeline-baseline/templates/gitlab-ci/.gitlab-ci.yml
[R6]: https://github.com/joku-dev/devsecops-governance-framework/blob/4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be/pipeline-baseline/templates/bamboo/bamboo-specs/bamboo.yaml
[R7]: https://github.com/joku-dev/devsecops-governance-framework/blob/4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be/scripts/intake_ci_artifact_bundle.py
[R8]: https://github.com/joku-dev/devsecops-governance-framework/blob/4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be/scripts/lib/result_ledger.py
[R9]: https://github.com/joku-dev/devsecops-governance-framework/blob/4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be/scripts/lib/governance_lifecycle/consumer_evidence.py
[R10]: https://github.com/joku-dev/devsecops-governance-framework/blob/4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be/.github/workflows/devsecops-baseline-l1-v1.1.3.yml
[R11]: https://github.com/joku-dev/devsecops-governance-framework/blob/4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be/scripts/install_validation_opa.py
[R12]: https://github.com/joku-dev/devsecops-governance-framework/blob/4beaea7fdd8f7fb86ad1ed00fee8148568e1b3be/AGENTS.md
[R13]: https://github.com/joku-dev/devsecops-governance-framework/pull/363
[R14]: https://github.com/joku-dev/devsecops-governance-framework/blob/416432e013143b6942f887a5ac610991f2a111f6/docs/operations/guides/linux-vm-installation.md
[R15]: https://github.com/joku-dev/devsecops-governance-framework/pull/364
[R16]: https://github.com/joku-dev/devsecops-governance-framework/blob/944c6f813ebb387f36a77f92af50deabd278d957/docs/operations/guides/vm-consumer-intake.md
[R17]: https://github.com/joku-dev/devsecops-governance-framework/blob/944c6f813ebb387f36a77f92af50deabd278d957/scripts/lib/consumer_intake.py
[R18]: https://github.com/joku-dev/devsecops-governance-framework/blob/944c6f813ebb387f36a77f92af50deabd278d957/scripts/lib/consumer_intake_store.py
[R19]: https://github.com/joku-dev/devsecops-governance-framework/blob/944c6f813ebb387f36a77f92af50deabd278d957/scripts/lib/consumer_github.py
[R20]: https://github.com/joku-dev/devsecops-governance-framework/blob/944c6f813ebb387f36a77f92af50deabd278d957/scripts/lib/consumer_publisher.py
[R21]: https://github.com/joku-dev/devsecops-governance-framework/blob/944c6f813ebb387f36a77f92af50deabd278d957/infra/ansible/activate.yml
[P1]: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
[P2]: https://docs.gitlab.com/ci/variables/predefined_variables/
[P3]: https://confluence.atlassian.com/bamboo/git-289277007.html
[P4]: https://confluence.atlassian.com/bitbucketserver104/checks-for-merging-pull-requests-1822591164.html
[P5]: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
[P6]: https://docs.gitlab.com/user/application_security/offline_deployments/
[P7]: https://confluence.atlassian.com/bamboo1200/bamboo-specs-yaml-format-1680481857.html
[P8]: https://docs.gitlab.com/user/project/merge_requests/auto_merge/
