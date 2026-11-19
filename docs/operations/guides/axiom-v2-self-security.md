# V2: Repository-Sicherheitsbewertung

Der neue Entwicklungskandidat ergänzt `self-security assess` und `inspect`.
Er übernimmt alle 16 bestehenden GRS-Kriterien, vollständige JSON-/Markdown-
Berichte, Prioritäten, Evidenzverweise und die optionale Befund-Rückgabe.
Diese Zuordnung ist in Arbeit. Sie bestätigt weder vollständige V2-Parität noch
Betriebsfreigabe. Veröffentlichung und Installation dieses neuen Kandidaten
benötigen ihre eigenen vollständigen Prüfungen.

## Eine vorhandene Beobachtung auswerten

```bash
./axiom-v2 self-security assess \
  --profile legacy-repository-self-security-v1 \
  --observation /absoluter/pfad/beobachtung.json \
  --output-json /privater/export/sicherheit.json \
  --output-md /privater/export/sicherheit.md \
  --format legacy
```

Ohne `--model` wird das unveränderte Produktmodell verwendet. Ein ausdrücklich
gewähltes YAML-Modell bleibt mit seinen Originalentscheidungen auswertbar.
`--observed-at` ersetzt bei vorhandenen Beobachtungen deren ursprüngliche Zeit
nicht. Es erfolgen weder API-Abfragen noch lokale Quell- oder Signaturprüfungen.
Die Angaben stammen aus der gelieferten Beobachtung und gewinnen keinen Trust
allein durch einen bestandenen Bericht. Insbesondere beschreiben die unverändert
übernommenen V1-Markdown-Formulierungen das ursprüngliche Erfassungsprofil;
sie beweisen bei importierten Angaben keine authentifizierte Live-Erfassung.

## Fakten lesend erfassen

```bash
./axiom-v2 self-security assess \
  --profile legacy-repository-self-security-v1 \
  --repository owner/repository \
  --source-worktree /absoluter/pfad/zur/produkt-arbeitskopie \
  --observed-at 2026-11-15T12:00:00Z
```

Der ausdrückliche Kompatibilitätsadapter fragt sieben GitHub-Endpunkte mit GET
ab: Metadaten, Main-Schutz, Signaturpflicht, Actions-Zulassung, Workflow-Rechte,
private Schwachstellenmeldungen und die tatsächlich auf Main anwendbaren Regeln.
Er arbeitet ohne Token oder mit einer expliziten privaten `--token-file`.
Umgebungs-Tokens und gespeicherte CLI-Anmeldungen werden nicht übernommen.
Die fehlende `--repository`-Angabe verwendet wie V1 den vom Adapter gelesenen
Repository-Kontext beziehungsweise den bisherigen Governance-Repository-Namen.
Der Transport ist auf `api.github.com`, sieben Abfragen, 30 Sekunden je Abfrage
und begrenzte Antwortbytes festgelegt; Weiterleitungen nehmen keine Credentials
mit. Fehler bleiben endpunktspezifische begrenzte Codes. Die ursprünglichen
ungefilterten `gh`-Fehlertexte werden nicht als identische Transportausgabe
behauptet. Fehlende administrative Fakten bleiben sichtbare Befunde.

Die lokale Quelle hat den exakten eigenen Produkt-Commit; aktuelle gewöhnliche
Daten dürfen abweichen. Der Adapter nimmt die passenden Workflow-Dateien,
CODEOWNERS und Dependabot-Konfiguration als Daten auf. Unbekannte Schreib-
Workflows bleiben unsicher; bekannte Publisher-Aufrufe mit `git push` gelten
nicht als sicherer Review-Weg. Drittanbieter-Actions brauchen weiterhin den
vollständigen SHA. Programme dieser Quelle werden nicht ausgeführt.
Die bestehende vollständige Release-Prüfung erfasst tatsächliche Git-Referenzen,
Signaturen, historische Integritätsmanifeste und Artefakte in einem getrennten
privaten Verifikationsbereich. Ein behauptetes Signaturergebnis genügt nicht.

Wie beim Original können API-Ziel und lokale Governance-Quelle unterschiedlich
sein. Das erzeugt einen ausdrücklich gemischten technischen Beobachtungsumfang,
keine vollständige Selbstbewertung eines beliebigen Consumers. Das Berichtlabel
stammt aus dem gewählten Modell. Für `ha-CPsWMS` bleiben die festgehaltenen
Kontroll- und Architekturvergleiche davon getrennt. Eine frei vorgegebene
Beobachtungszeit ist keine unabhängige Zeit- oder historische Schutzbestätigung;
der native Release-Beleg hält seine eigene tatsächliche Erfassungszeit fest.

## Ausgabe und Nachprüfung

Standardmäßig verweist die Ausgabe auf private vollständige Berichte und eine
`assessment_id`. `--format legacy` liefert die ursprüngliche Ergebniszeile.
Ohne explizite Exporte bleiben JSON, Markdown und Text im Instanzzustand.
Mit `--output-json` und `--output-md` erfolgen die lokalen Exporte in dieser
Reihenfolge. Exporte in Produkt, Instanz, geprüfte Quelle oder Token-Datei sowie
Symlinks und Spezialdateien werden zurückgewiesen. Diese Exporte sind keine
SCM-Veröffentlichung.

```bash
./axiom-v2 self-security inspect --id <assessment_id>
```

Vor jeder nativen API-Abfrage existiert ein dauerhaft geschriebenes Intent;
Antworten bleiben einzeln und in Reihenfolge erhalten. Der separate Release-
Beleg besitzt seine eigenen Eingaben und nativen Prozessnachweise. Die Inspektion
prüft Node, Runtime, Produktrevision, Eingangsdaten, genau sieben geordnete
Antworten und den vollständigen Release-Replay. Sie rekonstruiert alle Kriterien,
JSON, Markdown, Textausgabe und Rückgabe aus den gespeicherten Daten. Sie ruft
keine API auf und wiederholt keine native Signaturprüfung. Die ursprüngliche
JSON-Reihenfolge der Release-Berichte bleibt bei der Zusammensetzung erhalten.
Das ist erklärte Konsistenz, keine unabhängige Ausführungsattestierung.

| Rückgabe | Bedeutung |
| --- | --- |
| 0 | Vollständige Bewertung; Befunde bleiben standardmäßig report-only. |
| 1 | Befunde und ausdrücklich gewähltes `--fail-on-findings`. |
| 2 | Abgewiesene oder unvollständige Ausführung; kein erfolgreicher Leerbericht. |

Die privaten Datensätze liegen unter
`<instance>/state/self-security/operations/<assessment_id>/`. Unterbrochene
Versuche werden weder fortgesetzt noch automatisch wiederholt. Ein neuer
Aufruf erhält eine neue Identität. Parser-/Modellfehler behalten ihre typisierte
unvollständige Ausführung statt nachgebildeter historischer Tracebacks.
Für große Prüfungen muss auch `TMPDIR` auf einem ausreichend großen privaten
Arbeitsvolume liegen. Bestehende Speicherreserven bleiben wirksam.
Die Funktion ändert keine Schutzregeln, Statusindizes, Baselines oder akzeptierten
Lifecycle-Dateien und aktiviert keinen Publisher, Dienst oder KI-Provider.
