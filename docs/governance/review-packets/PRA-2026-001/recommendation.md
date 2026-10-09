# PRA-2026-001: Fachliche Review-Empfehlung

## Entscheidungsrahmen

Diese Empfehlung dispositioniert alle 56 Einträge aus `PRA-STD-REQ-001`.
Sie ist noch keine menschliche Entscheidung und autorisiert weder eine
GRQ-Aktivierung noch eine Artefaktübernahme. Maßgeblich waren in dieser
Reihenfolge:

1. der normative Source-Text,
2. bereits aktive kanonische DSCB-Requirements,
3. `model/traceability/control-to-platform.yaml`,
4. `model/platform/platform-capabilities.yaml`,
5. die vorhandene Evidenzzuordnung,
6. Textähnlichkeit nur als Suchhinweis.

Der freigegebene PRA-Auszug bleibt unverändert und ist weiterhin durch
`730f3a1f5875ec76f3d032c9f620630fc68846d4722c28803b16c8ab50902d3b`
gebunden.

## Zusammenfassung

| Empfehlung | Anzahl | Wirkung |
|---|---:|---|
| Aktivierung und Plattformübernahme empfohlen | 16 | Requirement entscheiden, GRQ aktivieren und bestätigte Plattformzuordnung eintragen |
| Teilabdeckung | 12 | Requirement kann fachlich entschieden werden; Artefaktübernahme bleibt bis zur Lückenschließung ausgesetzt |
| Keine bestätigte Implementierung | 6 | In dieser implementierungsorientierten Welle offen lassen |
| Korrigieren oder ablehnen | 12 | Keine Aktivierung aus dem aktuellen Source-Text |
| Als unterstützendes Modell erhalten | 10 | Nicht als eigenständiges GRQ aktivieren |

## 1. Empfohlene erste Aktivierungswelle

Für diese 16 Einträge ist eine bestehende Umsetzung fachlich ausreichend
belegt. `runtime_enforcement` bleibt `none`; autorisiert wird zunächst nur der
Artefakttyp `platform`.

| Source Requirement | Requirement-Empfehlung | Kanonisches Ziel | Bestätigte Plattformfähigkeiten | Gleichwertigkeit |
|---|---|---|---|---|
| `REQ-008` | `duplicate` | `GRQ-000019` | `central_iam` | equivalent |
| `REQ-009` | `extend` | `GRQ-000019` | `rbac` | equivalent |
| `REQ-010` | `duplicate` | `GRQ-000002` | `approved_version_control` | equivalent |
| `REQ-011` | `duplicate` | kanonisches Ziel von `REQ-009` | `rbac` | equivalent |
| `REQ-012` | `extend` | `GRQ-000003` | `code_review`, `branch_protection` | equivalent |
| `REQ-013` | `duplicate` | `GRQ-000007` | `automated_pipeline_execution` | equivalent |
| `REQ-015` | `extend` | `GRQ-000032` | `version_controlled_build_configuration` | equivalent |
| `REQ-020` | `duplicate` | `GRQ-000011` | `artifact_repository_integrity` | equivalent |
| `REQ-022` | `extend` | `GRQ-000011` | `checksum_or_digest_records`, `signature_verification` | equivalent |
| `REQ-023` | `duplicate` | `GRQ-000013` | `release_approval_workflow` | equivalent |
| `REQ-024` | `extend` | `GRQ-000016` | `deployment_logging` | equivalent |
| `REQ-025` | `duplicate` | `GRQ-000015` | `machine_readable_evidence_generation` | equivalent |
| `REQ-026` | `extend` | `GRQ-000015` | `evidence_repository` | equivalent |
| `REQ-028` | `duplicate` | `GRQ-000016` | `security_event_generation`, `operational_logging` | equivalent |
| `REQ-029` | `extend` | `GRQ-000030` | `monitoring_integration`, `incident_record_repository` | equivalent |
| `REQ-037` | `new` | neues PRA-GRQ | `required_platform_level` der Controls und `required_from` der Capabilities | equivalent |

Bei `REQ-011` wird zuerst `REQ-009` entschieden und aktiviert. Anschließend
wird `REQ-011` auf dasselbe kanonische Ziel aufgelöst, damit keine zweite
RBAC-Anforderung entsteht.

## 2. Teilweise implementiert

Diese zwölf Anforderungen besitzen passende Fähigkeiten, deren gegenwärtiges
Modell aber nicht die gesamte normative Aussage beweist. Sie erhalten noch
keinen effektiven Requirement-to-Artifact-Eintrag.

| Source Requirement | Vorhandene Abdeckung | Fehlende oder unklare Abdeckung |
|---|---|---|
| `REQ-007` | zentrale und sichere Entwicklungsumgebung | Kennzeichnung und Governance der genehmigten Umgebung |
| `REQ-014` | automatisierte Pipeline und Build-Protokolle | vollständiger Nachweis eines kontrollierten und auditierbaren Ausführungskontexts |
| `REQ-016` | mehrere Scan-Fähigkeiten | explizite Integration und Ausführung innerhalb der Pipeline |
| `REQ-017` | Signing, Provenance, Dependency- und Integrity-Fähigkeiten | die sehr breite Supply-Chain-Integritätsaussage ist nicht atomar abgedeckt |
| `REQ-018` | Policy Gate Engine und automatisierte Checks | Abgrenzung von „technically feasible“ und vollständiger Automatisierungsumfang |
| `REQ-019` | Artefaktintegrität und Metadaten | ausdrückliche Eigenschaft eines genehmigten Artefakt-Repositorys |
| `REQ-021` | genehmigte Dependency-Repositories und Proxy | explizite Überwachung der Repositories |
| `REQ-027` | Evidence Repository, Reporting und Evidence Graph | vollständiger Nachweis interner und externer Audit-Unterstützung |
| `REQ-038` | Level-Metadaten | technische Validierung, dass ein niedrigeres als das erforderliche Level ausgeschlossen wird |
| `REQ-049` | Waiver Registry und Level-Modell | formale Kopplung zwischen Ausnahme, Level und unverzichtbaren Capabilities |
| `REQ-053` | `governance_workflow` | ausdrücklicher Genehmiger und Trigger bei baseline-relevanten Plattformänderungen |
| `REQ-055` | `release_blocking`, `waiver_registry` | vollständige Produktionsfreigabeentscheidung und formale Waiver-Verknüpfung |

## 3. Keine bestätigte bestehende Implementierung

Diese sechs Anforderungen bleiben in der ersten Welle offen. Die vorhandenen
Texttreffer sind kein Implementierungsnachweis.

| Source Requirement | Grund |
|---|---|
| `REQ-001` | Breites Plattformziel ohne atomare oder messbare Modellrepräsentation |
| `REQ-002` | Versionsverbindlichkeit ist Dokument-Governance, keine vorhandene Plattformfähigkeit |
| `REQ-003` | Konformität domänenspezifischer Varianten ist im aktuellen Plattformmodell nicht repräsentiert |
| `REQ-030` | Aufbewahrungsfristen und regulatorische Retention fehlen im Plattformmodell |
| `REQ-048` | Mindestlevel für klassifizierte, air-gapped und eingeschränkte Varianten wird nicht modelliert |
| `REQ-051` | Die geforderte logische Architekturgleichheit der Varianten wird nicht maschinenlesbar abgebildet |

## 4. Korrigieren oder ablehnen

Diese zwölf Einträge dürfen in ihrer aktuellen Form nicht aktiviert werden.

| Source Requirement | Empfehlung | Grund |
|---|---|---|
| `REQ-004` | correction required | Einleitung einer fehlenden Layer-Liste |
| `REQ-005` | reject | Abschnittsüberschrift |
| `REQ-006` | correction required | Einleitung einer fehlenden Capability-Liste |
| `REQ-031` | correction required | „They“ besitzt kein eigenständiges Bezugsobjekt |
| `REQ-032` | correction required | „It“ besitzt kein eigenständiges Bezugsobjekt |
| `REQ-039` | reject | Tabellenkopf |
| `REQ-044` | correction required | „It“ besitzt kein eigenständiges Bezugsobjekt |
| `REQ-045` | reject | Tabellenkopf |
| `REQ-050` | correction required | Einleitung einer fehlenden Variantenliste |
| `REQ-052` | correction required | Einleitung einer fehlenden Verantwortlichkeitsliste |
| `REQ-054` | correction required | Einleitung einer fehlenden Verifikationsliste |
| `REQ-056` | correction required | Einleitung einer fehlenden Dokumentenliste |

Eine Korrektur erfolgt über eine neue versionierte Source- oder Requirement-
Revision. Der freigegebene Originalauszug wird nicht überschrieben.

## 5. Unterstützende Modell- und Traceability-Daten

Diese zehn Einträge enthalten wertvolle Architektur- oder Zuordnungsdaten,
sind aber keine eigenständigen atomaren Requirements. Sie bleiben als
Source-Evidenz und werden nicht als GRQ aktiviert.

| Source Requirement | Verwendung |
|---|---|
| `REQ-033` | Beschreibung von PRA-Level 1 |
| `REQ-034` | Beschreibung von PRA-Level 2 |
| `REQ-035` | Beschreibung von PRA-Level 3 |
| `REQ-036` | Capability-Beschreibung für End-to-End Traceability |
| `REQ-040` | erklärende Tabellenzeile für Level 1 |
| `REQ-041` | Minimum Capability Matrix für Source Control |
| `REQ-042` | Minimum Capability Matrix für Evidence and Traceability |
| `REQ-043` | Einleitung der Traceability-Sicht |
| `REQ-046` | konkrete Allokation für `DSCB-L1-REQ-001` |
| `REQ-047` | konkrete Allokation für `DSCB-L3-REQ-009` |

Die fachlichen Inhalte von `REQ-046` und `REQ-047` sind bereits im
Control-to-Platform-Modell repräsentiert. Ihre Source-IDs bleiben als
Lineage-Evidenz erhalten.

## Empfohlene menschliche Entscheidung

Der Platform Owner sollte jetzt ausschließlich Folgendes bestätigen:

1. die 16 Einträge der ersten Welle mit den angegebenen Requirement-
   Klassifikationen;
2. deren aufgeführte Plattformzuordnungen als gleichwertig;
3. die Zurückstellung der zwölf Teilabdeckungen und sechs nicht implementierten
   Anforderungen;
4. die Korrektur beziehungsweise Ablehnung der zwölf strukturell ungeeigneten
   Einträge;
5. die Behandlung der zehn beschreibenden Einträge als unterstützende
   Source-Evidenz ohne GRQ-Aktivierung.

Diese Entscheidung verändert weder OPA-Policies noch den Blocking-Modus.
