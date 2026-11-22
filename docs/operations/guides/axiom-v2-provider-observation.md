# AXIOM V2 Provider-Beobachtung

`provider-observation capture/inspect/replay` erhält den vollständigen bisherigen
Ablauf von `observe_provider_assurance.py`: Review-Beobachtungen für GitHub,
GitLab und Bitbucket Data Center sowie die bestehenden Sicherheitsbeobachtungen.
Die Ergebnisse bleiben Kandidaten. Sie übertragen weder persönliche Zustimmung
noch Rollenfreigaben, offizielle Annahme oder Betriebsautorität.

Die öffentliche Anbindung ist ein Entwicklungsstand. Die vollständige gepinnte
Regression, der gebundene Review und eine frische signierte Installations- und
Peer-Abnahme dieses Bausteins stehen noch aus. Seine Paritätszeile bleibt bis
zu diesen Nachweisen offen. Die akzeptierten Quellen und Baselines gelten weiter.

## Beobachtung starten

Die Argumente hinter `--` entsprechen dem bisherigen Programm. Verwende eine
eigene private Profildatei, eine separate Credential-Datei und ein neues
Ausgabeverzeichnis außerhalb von Produkt und Instanz:

```bash
axiom-v2 --instance /path/to/instance provider-observation capture \
  --profile legacy-provider-observation-v1 -- \
  reviews \
  --profile /private/path/provider-profile.json \
  --credential-file /private/path/read-token \
  --revision 0123456789abcdef0123456789abcdef01234567 \
  --change-id 7 \
  --output-root /private/path/new-observation
```

Das Provider-Profil enthält genau `scm`, `api_url`, `platform_version` und
`edition`. Version und Edition dürfen ausdrücklich unbekannt (`null`) sein.
API und SCM-Issuer müssen zusammenpassen. Beide Eingabedateien durchlaufen
die vollständige bisherige Privatdatei-Prüfung, einschließlich des bestehenden
systemd-ACL-Profils. Im normalen Benutzerbetrieb sind sie mit Modus `0600`
vorzubereiten. Der Token wird ausschließlich aus der Credential-Datei gelesen.

`security` ersetzt `reviews` für die Sicherheitsbeobachtung; `--change-id`
entfällt dann. GitHub behält seine enge ursprüngliche Abnahmebedingung: eigener
installierter Quellstand und angeforderte Revision stimmen überein, der relevante
Arbeitsbaum ist sauber, und die API bestätigt Main als passende Standardbranch.
Andernfalls bleiben die Kriterien sichtbar `not_proven`. GitLab und Bitbucket
erhalten ihre bisherigen eingeschränkten Sicherheitsfakten; fehlende fachliche
Äquivalenz wird nicht als bestandene Prüfung behandelt.

## Daten, Prozesse und Grenzen

Der SCM-Zugriff bleibt auf die ursprünglichen begrenzten HTTPS-GETs beschränkt.
TLS-Prüfung, Issuer-Bindung, Redirect-Schutz, Request-Budget und Pagination
bleiben erhalten. Es werden keine Provider-Reviews, PRs oder Einstellungen
geschrieben und keine KI-Provider gestartet.

Die Credential-Datei erhält eine getrennte, kurzlebige In-Memory-Capability.
Ihr gelesener Inhalt und dessen Digest gelangen nicht in die technischen
Nachweise. Reflektierte bekannte Tokenwerte führen zu einem technischen Abbruch.
Profildaten und Provider-Antworten sind dagegen vollständig gespeicherte Daten
der privaten Aufnahme. Die Dateien können personenbezogene Angaben enthalten.

Der GitHub-Sicherheitszweig verwendet die beiden ursprünglichen lokalen
Git-Leseabfragen. Der Adapter prüft zusätzlich Konfigurationsnamen und weist
externe Filter oder Includes zurück. Er speichert dabei keine Git-Konfigurations-
werte. Hooks, Fsmonitor, implizites Nachladen und Git-Umgebungsüberschreibungen
werden für diesen Port deaktiviert. Die vollständigen ursprünglichen Workflow-
und CODEOWNERS-Scanner bleiben erhalten.

Die Release-Prüfung läuft als eigener vollständiger privater Unterlauf mit
Quellrevision, Baum, Eingaben, Referenzen, einzeln protokollierten nativen Starts
und tatsächlichen Signaturprüfungen. Die Nachrechnung erhält alle Unterlauf-
dateien und Verzeichnisse, einschließlich leerer Verzeichnisse. Ein pauschaler
Release-Report ersetzt diesen Ablauf nicht. Die bestehenden Platzreserven und
Abbruchregeln gelten weiter.

Die benötigten eigenen `.github`-, Modell- und Release-Daten gehören bereits
zum Installationspaket. Fehlende physische Dateien werden nicht durch einen
Git-Blob-Fallback verdeckt. Produktdrift bleibt eine fehlgeschlagene Zulassung.

## Ausgaben und Nachrechnung

Der ursprüngliche Ablauf schreibt `candidate.json` und im `finally`-Schritt
`native-capture.json`. Beide behalten die gesamte ursprüngliche atomare
Schreibfolge einschließlich temporärer Dateien, Flush, Fsync, Chmod, Replace
und Fehlerbehandlung. Teilwirkungen bleiben in der Aufnahme sichtbar.

```bash
axiom-v2 --instance /path/to/instance provider-observation inspect --record /path/from/record_root
axiom-v2 provider-observation replay --record /path/from/record_root
```

`inspect` bindet an dieselbe Instanz. `replay` rekonstruiert den ursprünglichen
Ablauf aus den vollständigen privaten Nachweisen. Profil, Credential-Datei,
Ausgaben und API müssen dafür nicht mehr erreichbar sein. Es werden keine GETs,
Git-Abfragen, Signaturprogramme oder Dateischreibvorgänge erneut ausgeführt.
Der aktuelle zugelassene Produktcode bleibt für die Nachrechnung erforderlich.

Der Status unterscheidet einen vollständig erfassten ursprünglichen Fehler von
einer unvollständigen technischen Aufnahme. Ein ursprünglicher Parser-Exit `2`
kann daher `state: complete` mit `original_exit_code: 2` ergeben. Technische
Unvollständigkeit hat `state: incomplete` und keinen erfundenen ursprünglichen
Exit-Code. Credentials werden auch nach einem Journalfehler verworfen. Es gibt
keinen automatischen Wiederanlauf oder Rollback und keine Dienstaktivierung.
