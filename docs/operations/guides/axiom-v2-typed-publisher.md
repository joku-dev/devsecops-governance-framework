# AXIOM V2 Typed-Evidence-Publisher

`typed-publisher publish/inspect/replay` erhält den vollständigen bisherigen
Einstieg `publish_typed_evidence_assurance_update.py` und dessen allgemeinen
operativen Publisher. Das ist ein Entwicklungsbaustein der Funktionsparität;
eine aktuelle vollständige Quell-, Installations- oder Betriebsabnahme wird damit
nicht behauptet.

## Ursprüngliche Erweiterung

Die Originalfunktion `configure()` ergänzt genau diese drei append-only Bereiche:

- `status/measured-security-results/`
- `status/measured-l1-results/`
- `status/control-evidence-assurance/`

Der Scope `typed-evidence` erhält diese drei Pfade zusätzlich zu seiner bisherigen
Allowlist. Existierende Ledger-Dateien dürfen weiterhin nicht geändert oder
entfernt werden. Der vollständige ursprüngliche Ablauf für Pfadauswahl, Symlink-
und Scope-Prüfung, Fetch, Vorfahrenprüfung, Branch, Staging, Commit, Push, PR,
Pipeline-Appends und drei Workflow-Dispatches bleibt erhalten. Auch die anderen
fünf ursprünglichen Scopes und deren gegebenenfalls nötige vollständige
Lifecycle-Gates bleiben verfügbar.

Die erweiterte Konfiguration gehört einer eigenen Publisher-Instanz. Sie verändert
weder die allgemeine Publisher-Konfiguration noch andere Instanzen. Wiederholtes
`configure()` behält die ursprünglichen Tupel-Erweiterungen innerhalb dieser
Instanz bei. Ganze Originalfunktionen und die vollständige finite native
Pfad-/Kommandoaufnahme werden gegen unveränderliche V1-Vergleichsdaten geprüft;
gewählte Source-Programme werden vom Produkt nicht geladen.

## Explizite Ausführung

```bash
axiom-v2 --instance /path/to/instance typed-publisher publish \
  --profile legacy-typed-evidence-publisher-v1 \
  --transport-profile legacy-typed-evidence-publisher-native-v1 \
  --source-worktree /path/to/standalone-clone \
  --scope typed-evidence --repository owner/repository \
  --run-id 123 --attempt 1 --workflow-ref refs/heads/main
```

Dieser Aufruf kann native Git- und Provider-Schreibzugriffe ausführen. Die
zulässige Source ist ein eigener gewöhnlicher Clone mit eindeutig gebundenem
Pull-/Push-Ziel. Geteilte Git-Verzeichnisse, implizite Source-/Instanzprogramme,
externe Filter/Include-Konfiguration und umgeleitete Schreibpfade werden nicht
zugelassen. Ein lokales Test-Remote benötigt ausdrücklich
`legacy-typed-evidence-publisher-local-test-v1` und `--local-origin-root`.

Die gewählte Legacy-Adapterfassung erhält den bisherigen GitHub-Akteur, genaue
PR-Texte und Umweltschlüssel sowie Governance CI, CodeQL und Repository Security
als drei Dispatches. Das Workflow-Ref bleibt eine deklarierte Eingabe und belegt
keinen geschützten Workflow oder eine Betriebsfreigabe. `--scope` ist wie beim
Original erforderlich. `--original-arguments` übernimmt als letzter Abschnitt
die ursprünglichen Parserargumente.

`--invocation configure` führt nur die ursprüngliche Konfiguration innerhalb des
gewählten Objekts aus. Es startet keine Git-/Provider-Operation. Die Nachprüfung
zeigt `configured_publisher_scope_rules`. Dieser Hilfsaufruf ist keine allgemeine
Simulation eines nachfolgenden nativen Publish.

`--output-file` und `--summary-file` wählen die ursprünglichen Append-Ziele. Native
Modi, Bytes, Returncodes und Teilfehler bleiben erhalten. `--native-temporaries`
betrifft die temporären Prüfschritte; deren privater Standardmodus macht einen
Git-Push oder Provider-Aufruf nicht zu einer Simulation.

## Nachprüfung

```bash
axiom-v2 --instance /path/to/instance typed-publisher inspect --record /path/from/record_root
axiom-v2 typed-publisher replay --record /path/from/record_root
```

`inspect` bindet den Nachweis an dieselbe Instanz. `replay` benötigt den gewählten
Source-Clone, Client und Ausgabedateien nicht mehr und wiederholt keine nativen
Aktionen. Der ganze ursprüngliche Ablauf einschließlich der gekapselten
Konfiguration wird aus gespeicherten Eingaben, Rohstreams und Beobachtungen
nachgerechnet; private Nachweisdateien bleiben notwendige Eingaben.

Nach einem späteren Fehler können ein Commit, Push oder PR bereits bestehen.
Unvollständige technische Aufnahmen liefern `2`, ohne ursprünglichen Erfolg,
automatischen Wiederanlauf oder Rollback zu erfinden. Konsistente gespeicherte
Bytes authentifizieren keinen Producer und beweisen keinen unabhängigen externen
Abschluss. Eine pausierte V2-Instanz aktiviert dadurch keinen Publisher-Dienst;
offizielle Annahme, persönliche Zustimmung und Betriebsautorität bleiben separat.
Die aktuelle vollständige Regression, gebundener Review, Signatur, installierte
Mac-/Linux-/Peer-Abnahme und feste ha-CPsWMS-Vergleiche stehen noch aus.
