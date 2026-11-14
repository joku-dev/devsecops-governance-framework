# GCR-2026-170 — Reproduzierbare Linux-VM-Installation

## Auftrag und Einordnung

Der Maintainer beauftragt am 14. November 2026 die Umsetzung des besprochenen
IaC-Plans in einem eigenen Branch. Gewählt sind Engine und Workbench auf einer
bestehenden Ubuntu-VM, persönlicher SSH-Tunnel, gezielter Start mit einem Befehl,
explizite Übernahme ausgewählter Entwürfe und Sicherungen auf VM und Controller.
Die Installation auf der Ziel-VM folgt nach Fertigstellung des Prototyps.

| Feld | Klassifikation |
|---|---|
| Artefakte | Ansible-Profil, Controller-Einstieg, private Archiv-/Import-Helfer, Tests, CI und Betriebsanleitung |
| Typ und Ziel | Betriebsautomation unter `infra/ansible/` und `scripts/`, Tests unter `tests/`, praktische Betriebsanleitung unter `docs/operations/guides/` |
| Owner | Repository Maintainer |
| Full Source Document Intake | Nein; keine neue normative Quelle oder Ableitung |
| Governance-Verhalten | Keine Änderung an Kontrolle, Quelle, Freigabe, Evidence Trust, Ergebnisindex oder Enforcement |
| Schnittstellen | Neue private Operator-CLI und Betriebsmetadaten; keine neue HTTP-API oder Änderung am Draft-Schema |
| Betriebsänderung | Explizites einzelnes Maintainer-VM-Profil mit Loopback und SSH-Tunnel; keine allgemeine Freigabe für Netzwerk-/Mehrbenutzerhosting |
| Release-Auswirkung | Keine Baseline-Veröffentlichung oder Änderung freigegebener Pakete |
| Validierung | Gepinnter Bootstrap/Gesamtvalidierung, private Archiv-/Import-Tests, echter systemd-Test auf isoliertem Ubuntu, DOM-Tests, MkDocs strict und revisionsgebundener Review |

Die Implementierung hält vorhandene Draft-Pfade stabil, bereitet neue Versionen
separat vor und aktiviert sie erst nach geprüften privaten Sicherungen an zwei
Orten. Schlüssel, Dateien und historische Kontextbindungen bleiben erhalten.
Fehlerhafte Aktivierungen werden als Fehler gemeldet; eine Rückkehr verändert
keine Entwurfsdaten. Betriebsprotokolle sind keine Consumer- oder Compliance-
Ergebnisse. Der neue CI-Workflow greift ausschließlich auf seinen eigenen
wegwerfbaren Runner zu, nicht auf private Hosts.

## Review und Grenzen

Governance Analysis, Evidence and Intake, DevSecOps Baseline und Release Management
werden als Rollenperspektiven geprüft; Repo Steward synthetisiert zuletzt.
Ein Koordinator dokumentiert tatsächliche Perspektiven als `role_lens`, nicht als
unabhängige Agenten- oder menschliche Freigaben. Private Review-Pakete bleiben
außerhalb des Checkouts. Quellen, freigegebene Baselines und alle Dateien der
bestehenden Operating Acceptance bleiben unverändert.

Proxmox-Provisionierung, Datenträgeränderungen, Container-Orchestrierung, SSO,
parallele Worker und Skalierungsnachweise für viele Repositories sind separate
Folgeschritte. Die neue Automatisierung autorisiert keine produktive Einführung
weiterer Governance-Piloten oder Providerläufe.
