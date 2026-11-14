# AXIOM auf einer Linux-VM installieren

## Umfang und Voraussetzungen

Das IaC-Profil installiert die vorhandene Engine und die private Workbench auf
einer bestehenden Ubuntu-24.04-VM (amd64 oder arm64). Ansible verwaltet Pakete,
einen unprivilegierten Dienstbenutzer, einen festen Git-Checkout, Laufzeiten pro
Commit, systemd und private Sicherungen. Die Ziel-VM wird erst nach Fertigstellung
des Prototyps eingerichtet. Dieses Dokument ist keine Behauptung einer bereits
erfolgten Installation auf Proxmox.

Der Controller benötigt Python 3.13, SSH und einen bestätigten Hostschlüssel.
`scripts/deploy_vm.sh` legt eine ignorierte `.venv-deployment` mit den gehashten
Paketen aus `requirements-deployment.lock` an. `ansible-core` ist auf 2.22.0
festgelegt. `AXIOM_DEPLOY_PYTHON` und `AXIOM_DEPLOY_VENV` erlauben andere Pfade,
aber keine andere Python-Minorversion. Für die Ziel-VM wird `/usr/bin/python3`
verwendet; dort ist kein Ansible-Controller erforderlich.

Es werden weder Proxmox-VMs noch Datenträger angelegt, vergrößert oder formatiert.
Docker, Kubernetes, SSO, mehrere gleichzeitige Dienstinstanzen, verteilte Worker
und eine Lastzusage für 1.000–2.000 Repositories gehören zu späteren Schritten.
Der Dienst startet keine Provider-, Consumer-, Intake- oder Veröffentlichungsjobs.
Die Engine-Werkzeuge stehen für ausdrücklich gestartete Aufgaben bereit;
schreibende Jobs verwenden separate Arbeitskopien unter `/srv/axiom/jobs`.
Node und die DOM-Entwicklungsabhängigkeiten gehören zur separaten UI-Validierung,
nicht zur Workbench-Laufzeit; Node-abhängige Python-Tests können auf einer reinen
VM-Laufzeit als übersprungen erscheinen.

## Private Konfiguration und ein Befehl

Die Beispielkonfiguration liegt unter `infra/ansible/config.example.json`. Kopiere
sie außerhalb des Checkouts und passe SSH-Identität und Zielhost an:

```bash
mkdir -p -m 700 ~/.config/axiom
cp infra/ansible/config.example.json ~/.config/axiom/vm.json
chmod 600 ~/.config/axiom/vm.json
```

Erlaubte Felder sind `host`, `user`, `ssh_port`, `identity_file` und `backup_root`.
Ohne `identity_file` verwendet SSH seine bestehende lokale Konfiguration.
Passwörter und weitere Ansible-Variablen werden in dieser Datei nicht akzeptiert.
SSH-Hostprüfung bleibt aktiv; ein unbekannter oder geänderter Hostschlüssel muss
vorher auf einem unabhängigen Weg geprüft und persönlich bestätigt werden.

```bash
./scripts/deploy_vm.sh check --config ~/.config/axiom/vm.json
./scripts/deploy_vm.sh install --config ~/.config/axiom/vm.json \
  --revision APPROVED_FULL_40_CHARACTER_COMMIT_SHA --ask-become-pass
./scripts/deploy_vm.sh status --config ~/.config/axiom/vm.json
```

`--ask-become-pass` fragt das sudo-Passwort einmalig ab. Es wird weder gespeichert
noch als Kommandoargument übergeben. Vorhandene passwortlose Berechtigungen können
verwendet werden; die Automatisierung richtet keine neuen sudo- oder SSH-Rechte ein.
Nach diesem initialen Zugang laufen die Schritte autonom. Die Veröffentlichung
eines Branches oder PRs führt keine Installation auf einer privaten VM aus.

`check` und `status` laufen mit Ansible-Prüfmodus und ausschließlich lesenden
Remote-Kommandos. `check` prüft Ubuntu, Dienststatus, Port und Speicher; es simuliert
keinen vollständigen ersten Paket-/Git-/systemd-Lauf. Controller-Toolchain,
private temporäre Dateien und lokale Laufprotokolle können dabei entstehen.
Aktivierungen werden auf einem Controller durch eine exklusive Sperrdatei
serialisiert; zusätzlich hält der Lauf auf der VM `/run/lock/axiom-deployment`.
Verwaiste Sperren erst nach Prüfung der alten Prozesse entfernen. So kann auch
ein zweiter Controller keinen laufenden Versionswechsel überholen.

## Dienst und Browserzugriff

Der verwaltete Checkout bleibt unter `/srv/axiom/repository`; Entwürfe liegen
unverändert relativ dazu unter `.local/governance-workbench`. Kein Update benutzt
`git clean`. Lokale Änderungen an der aktiven Arbeitskopie brechen Updates ab.
Laufzeiten und vorbereitete Checkouts sind nach Commit getrennt. Der Benutzer
`axiom` besitzt keine Login-Shell; der systemd-Dienst hat nur Schreibzugriff auf
private Entwürfe und temporäre Dateien. PR-Veröffentlichung bleibt deaktiviert.

Das ausdrücklich gewählte VM-Profil erlaubt einen persönlichen SSH-Tunnel für
einen Maintainer. Der Server bindet weiterhin nur an `127.0.0.1`, hier Port 8766.
Benutze auf beiden Tunnelenden denselben Port, damit die vorhandenen Host- und
Origin-Prüfungen gelten:

```bash
ssh -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:8766:127.0.0.1:8766 joku@192.168.200.252
```

Öffne `http://localhost:8766`. Der Hostname unterscheidet die VM-Sitzung von
einer lokalen Workbench unter `http://127.0.0.1:8765`; Browser-Cookies sind nicht
nach Port getrennt. Verwende dafür deinen persönlichen SSH-Zugang, der Forwarding
bereits erlaubt. Ein mit `restrict` eingerichteter Automatisierungsschlüssel wird
nicht erweitert. Ist der lokale Port belegt, beende den eigenen alten Tunnel;
die Automatisierung beendet keine fremden Prozesse und wählt keinen Ersatzport.

Der einmalig erzeugte Zugangsschlüssel liegt rootgeschützt in
`/etc/axiom/workbench.env` und bleibt über Updates erhalten. Zum Ablesen persönlich
auf der VM `sudo cat /etc/axiom/workbench.env` ausführen; den Wert nicht in Git,
URLs, Chat, Tickets oder Protokolle kopieren. Der Dienst erhält ihn über systemd,
ohne ihn beim Start zu drucken. Dies ist kein Mehrbenutzer-/Enterprise-Hosting.
Direkter LAN-/Internet-Zugriff und Reverse Proxies sind mit diesem Profil nicht
vorgesehen; dafür bleiben HTTPS, Identitäten, Rollen und eine eigene Abnahme nötig.

## Update, Sicherung und Rückkehr

```bash
./scripts/deploy_vm.sh update --config ~/.config/axiom/vm.json \
  --revision APPROVED_FULL_40_CHARACTER_COMMIT_SHA --ask-become-pass
./scripts/deploy_vm.sh rollback --config ~/.config/axiom/vm.json --ask-become-pass
```

Ein Update prüft den neuen Commit zuerst separat mit der gepinnten Toolchain und
`validate_all.sh`. Dessen privates Protokoll liegt in der versionsbezogenen
Laufzeit als `validation.log`; Originalausgaben werden nicht in Ansible-Antworten
übertragen. Danach wird der Dienst für eine konsistente Sicherung gestoppt.
Entwürfe, Schlüssel, Dienstkonfiguration und Versionsbeleg werden mit Größen und
SHA-256-Manifest in einer privaten ZIP-Datei gesichert. Die VM behält sie unter
`/var/backups/axiom`, der Controller unter `backup_root/backups` (Standard:
`~/.local/state/axiom-deployment/backups`). Inhalt und Transportprüfsumme müssen
auf beiden Seiten übereinstimmen, bevor die neue Version aktiv wird.

Der VM-Preflight reserviert 8 GiB zuzüglich 2 GiB Vorbereitungsbudget und zwei
unkomprimierten Kopien des Zustands. Auf dem Controller bleiben mindestens 1 GiB
plus zwei Archivgrößen frei. Archive sind auf 512 MiB Nutzinhalt begrenzt;
größere Bestände benötigen ein gesondertes Backup-Konzept. Sicherungen und alte
Laufzeiten werden nicht automatisch gelöscht. Sie enthalten private Originale
und Zugangsdaten und benötigen entsprechend geschützte Speicherung.

Nach Aktivierung werden echte Anmeldung, geschützte Datenabfrage und Logout
geprüft. Bei Fehlern wird die vorherige Code-/Laufzeitversion mit der alten
Dienstkonfiguration wiederhergestellt und erneut geprüft; der Lauf bleibt
fehlgeschlagen. Bei der ersten Installation ohne Vorgänger bleibt der Dienst
gestoppt und sein Autostart wird deaktiviert, bis die Installation ausdrücklich
wiederholt wird. Entwürfe werden dabei nie auf einen älteren Snapshot zurückgesetzt.
Inkompatible Datenmigrationen werden nicht automatisch vorgenommen.

`rollback` aktiviert den im privaten Versionsbeleg gespeicherten Vorgänger und
legt zuvor ebenfalls eine geprüfte Sicherung an. Ein identischer gesunder
Installationslauf erzeugt keine weitere Sicherung und startet den Dienst nicht
neu. Kurze servicebedingte Unterbrechungen beim Versionswechsel sind vorgesehen.
Lokal gespeicherte Statusmetadaten und Controller-Protokolle sind Betriebsbelege,
keine Governance-Ergebnisse oder Freigaben. Sie enthalten keine Schlüssel oder
Originalauszüge und werden nicht in öffentliche Ergebnisindizes aufgenommen.

Eine Wiederherstellung zunächst in ein **neues** privates Verzeichnis proben:

```bash
python3 scripts/lib/vm_deployment.py verify --archive /PRIVATE/BACKUP.zip
python3 scripts/lib/vm_deployment.py restore --archive /PRIVATE/BACKUP.zip \
  --destination /PRIVATE/NEW-RECOVERY-DIRECTORY
```

Die Wiederherstellung überschreibt keinen vorhandenen Pfad. Ein tatsächlicher
Ersatz des Live-Zustands bleibt ein bewusster Operator-Schritt bei gestopptem
Dienst. VM-Snapshots ersetzen die geprüfte Kopie außerhalb der VM nicht.

## Bestehende Entwürfe übernehmen

Stoppe vorher die lokale Workbench, damit nur vollständig gespeicherte Inhalte
übernommen werden. Wähle Entwurfs-IDs ausdrücklich aus:

```bash
./scripts/deploy_vm.sh import-drafts --config ~/.config/axiom/vm.json \
  --source .local/governance-workbench --draft-id SELECTED_32_CHARACTER_DRAFT_ID \
  --ask-become-pass
```

Mehrere `--draft-id` sind möglich. Der Befehl prüft IDs, vorhandene Upload-Hashes,
Archivmanifest und das installierte Draft-Schema. Vor dem Import wird der
VM-Zustand auf beiden Seiten gesichert. Eine Kollision lehnt die gesamte Auswahl
ab. Gespeicherte Draft-Dateien und Uploads bleiben bytegleich, Originale auf dem
Controller erhalten. Desktop-Laufzeiten, Schlüssel, Sitzungen und PR-Arbeitskopien
werden nicht kopiert. Vorhandene PR-Referenzen bleiben historische Metadaten;
PR-Publikation wird dadurch nicht eingeschaltet. Ungespeicherter Browsertext ist
kein Bestandteil des Imports. Unterschiedliche Commit-/Quellstände werden weiter
als veraltet angezeigt, nicht durch Umschreiben von Metadaten aktualisiert.

## Validierung und Lieferung

Unit-Tests prüfen Archive, Korruption, Pfad-/Symlink-Angriffe, Importkollisionen,
Schema-Grenzen und private Controller-Konfiguration. Der separate Workflow
`vm-installation.yml` benutzt ausschließlich einen wegwerfbaren Ubuntu-24.04-
Runner mit echtem systemd. Er prüft Neuinstallation, Idempotenz, Versionswechsel,
Rollback, absichtlich defekten Dienststart, Datenerhalt, Import, Sicherungs-
Wiederherstellung und Dienstneustart. Er besitzt keine privaten VM-Zugangsdaten.
Der Integrationstest darf niemals auf der späteren Ziel-VM laufen.

Die Abnahme umfasst außerdem die vollständige Repo-Validierung, DOM-Tests und
MkDocs strict. Die erste echte VM-Installation, ein VM-Neustart und der persönliche
Browserzugriff werden nach Fertigstellung des Prototyps gesondert nachgewiesen.
