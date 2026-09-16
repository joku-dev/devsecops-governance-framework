# Consumer-Lifecycle: verbindlicher Betriebsumfang

## Scope und bestätigte Rollen

Dieser Leitfaden gehört zur separaten Betriebsabnahme für genau
`joku-dev/governance-framework-demo-consumer`, Architektur-Gate
`operation_readiness`, Ressource `repository`. Betrieb: manuell und report-only.

Der Maintainer bestätigte im Gespräch ausdrücklich mit „ich bestätige“ die
Mehrfachrolle von `joku-dev` / GitHub-ID `81616324` für Entscheidung,
Evidenzabnahme, Abschluss und Rollenverwaltung. Er bestätigte außerdem den
begrenzten Nachweisumfang: Maßnahmenprotokoll und CI-lokale Funktionsdiagnosen
für das nicht deployte Demo. `model/governance/lifecycle/consumer-operation/roles.json`
hält diese Zuordnung fest. Sie ist keine persönliche Betriebs- oder Einzelaktions-
Erklärung im GitHub-Verifikationskanal und bescheinigt keine Produktionsreife.

## Quelle und Beobachtung

Zulässig sind abgeschlossene erfolgreiche `push`-Läufe auf `main`, ausschließlich
Versuch 1 des definierten Architektur-Workflows. Der Collector verifiziert
GitHub-Repository-ID, Workflow-ID/-Pfad, Fork-Herkunft, vollständigen Commit,
Artefaktzuordnung, Verfügbarkeit und SHA-256 des heruntergeladenen ZIP-Archivs.
Doppelte, unerwartete, verschlüsselte und unsichere ZIP-Mitglieder werden abgelehnt.
Vorher-/Nachher-Abfragen erkennen Änderungen während der Aufnahme.

Consumer-Workflow und Baseline-Dateien sind per Digest gebunden. Das annotierte
Baseline-Tag wird zu Commit `19e281d323eb69be26bdb2cbf4368caadfbccaa7` aufgelöst;
das Tagobjekt selbst gilt nicht als Policy-Commit. Schema und Report-Konsistenz
werden geprüft. Der ausgewählte Gate-Bericht wird mit der gespeicherten Policy
und dem tatsächlichen Release-Input unabhängig durch OPA neu berechnet.

Die Architekturquelle liefert Gate-Ergebnisse mit Nachrichten. `findings` wird
für genau dieses Gate zu `fail` normalisiert; `pass` bleibt `pass`. Es entstehen
keine getrennten B5/P11-Marker-Findings. Architektur-Ausnahmen werden in diesem
Piloten nicht angenommen. Die anderen drei Gates erzeugen keine Lifecycle-Fälle.

Die Quelle hat keinen eigenen signierten Beobachtungszeitpunkt. Der Pilot bindet
`observed_at` deshalb ausdrücklich an die GitHub-Artefakterstellung als Zeitpunkt
der verfügbaren Evidenz, nicht an einen behaupteten Produktionsmesszeitpunkt.
Maximales Evidenzalter: 24 Stunden; Zukunftsversatz: null. Ein exakter Replay
ist wirkungslos, auch nach Alterung. Widersprüchliche Inhalte derselben Herkunft
und zeitlich mehrdeutige Ergebnisse kommen in Quarantäne. Historie wird vollständig
aufbewahrt; keine automatische Löschung. Aufbewahrung am Pilotende erneut prüfen.

## Betriebsabnahme und persönliche Aktionen

`model/governance/lifecycle/consumer-operation/acceptance.json` bindet Scope,
Rollen, Implementierungsdateien und diesen Leitfaden. Die benannte Person prüft
und postet die vorbereitete Erklärung **selbst** im darin angegebenen zentralen
PR. Codex bereitet den Text vor und erfasst die GitHub-Antwort, postet jedoch
keine persönliche Erklärung stellvertretend.

Der Prüfer bindet Inhalt und Antragsdigest, GitHub-Nutzer-ID, PR, Zeit und
unveränderten Kommentar. Er verwirft App-/Bot-Erklärungen und Wiederverwendung
fremder Anträge. Änderungen, Löschung, Ablehnung oder Widerruf entziehen die
entsprechende Wirkung bei erneuter Erfassung. GitHub belegt die Kontoidentität;
persönliche Anwesenheit wird ausdrücklich selbst erklärt.

Jede Entscheidung, Fortschrittsmeldung und jeder Abschluss benötigt einen
separaten inhalts- und revisionsgebundenen Antrag unter
`model/governance/lifecycle/consumer-operation/action-requests/` und eine eigene
persönliche Erklärung. Der Kanaltest des zentralen Piloten verleiht dafür keine
Zustimmung. Die Gesprächsbestätigung wird nicht als GitHub-Erklärung ausgegeben.

- Entscheidung: tatsächlicher frischer Gate-Fehler, benannter Bearbeiter, konkrete
  Maßnahme mit Arbeitslink und Frist sowie exakter Evidenz-/Aktionsstand.
- Fortschritt: erst `in_progress`, danach `completed`, jeweils persönliche
  Erklärung mit konkreten Nachweisen im Evidenztext.
- Abschluss: vollständiger Fortschritt, neuester zulässiger frischer Gate-PASS
  nach dem Abschlusszeitpunkt und nach sämtlichen Fehlerbeobachtungen; eigene
  persönliche Abschlussfreigabe. PASS allein schließt keinen Fall.
- Widerruf: Entscheidung oder Abschluss gezielt widerrufen; Änderungen/Löschung
  persönlicher Voraussetzungen entziehen abhängige Wirkung. Rollenentzug
  deaktiviert weitere Freigaben. Wiederherstellung benötigt neue Version/Abnahme.
- Wiedereröffnung: Ein zeitlich neuer Gate-Fehler nach bestätigtem Abschluss
  öffnet den Fall wieder. Konflikte verhindern weitere Aktionsfreigaben.

## Ausführung und Veröffentlichung

Der Workflow **Consumer Lifecycle Update** auf `main` unterstützt:

| Operation | Eingabe | Wirkung |
|---|---|---|
| `acceptance` | Keine | Persönliche Betriebsabnahme oder deren Widerruf erfassen |
| `observe` | Echter Architektur-Run | Quelle prüfen und unveränderlichen Vorschlag anhängen |
| `action` | Bereits versionierter Consumer-Aktionsantrag | Persönliche Zustimmung nachprüfen und Aktionsvorschlag anhängen |
| `refresh` | Keine | Aktive Betriebsabnahme nachprüfen und gespeicherten Zustand projizieren |

Es gibt keinen Zeitplan. Ein `refresh` erneuert keine Beobachtung. Ein
permission-reduzierender Widerruf wird über `acceptance` beziehungsweise den
ursprünglichen Aktionsantrag erfasst. Die dargestellten Zustände folgen gespeicherten
Erfassungen; ein noch nicht erfasster Kommentar-Widerruf wird nicht als bereits
veröffentlicht dargestellt.

Alle Änderungen gelangen über einen begrenzten PR auf `main`. Der dedizierte
Publisher darf ausschließlich neue Consumer-Nachweise und die eigene Projektion
schreiben. Er prüft Herkunft, unveränderte Historie und Zustimmung erneut und
startet Governance CI, CodeQL, Self-Security sowie **Consumer Lifecycle Guard**.
Für repositoryübergreifende Artefaktabfragen verwendet er das konfigurierte
`GH_RESULT_INTAKE_TOKEN`; Branch- und PR-Schreibzugriffe nutzen `GITHUB_TOKEN`.
Vor der ersten Aufnahme muss `GH_RESULT_INTAKE_TOKEN` als Actions-Secret im
zentralen Repository hinterlegt sein. Der Token benötigt `Actions: read` und
`Contents: read` für Demo-Consumer und Governance-Repository; Schreibrechte
sind für diesen Lesezugriff nicht nötig. Das repositorygebundene `GITHUB_TOKEN`
ersetzt diese repositoryübergreifende Berechtigung nicht. Tokenwerte gehören
ausschließlich in die Secret-Verwaltung, nicht in PR-Kommentare oder Chat.
Für bestehende automatisierte Publisher startet der Guard zusätzlich nach
erfolgreicher manuell ausgelöster Governance CI auf derselben internen Branch-
Revision. Dieser Dispatcher führt keinen Code aus dem Quellbranch aus.
Der Guard muss als erforderliche Prüfung des geschützten `main` eingerichtet sein.
Vor aktiven Operationen und Veröffentlichungen wird diese GitHub-Einstellung
erneut geprüft: strikte Pflichtprüfung mit Bindung an die GitHub-Actions-App.
Er verifiziert neue Provider-Nachweise unabhängig, einschließlich aktiver
Voraussetzungen für neue Aktionen. Bei weitergelaufenem `main` ist der Vorschlag
abzugleichen und erneut zu prüfen. Es erfolgt kein automatisches Approven/Mergen.

Speicher: `governance/consumer-lifecycle/observations/`, `actions/` und
`acceptance/`. Dateien werden atomisch und exklusiv angehängt; bestehende Modelle,
Anträge und Nachweise dürfen nicht überschrieben oder entfernt werden.
Anzeige: `status/governance-consumer-lifecycle.json` und
`generated/reports/governance-consumer-lifecycle.md`. Consumer-Gesamtergebnisse
und der bisherige GRS-002-Pilot bleiben getrennte Zustände.

## Grenzen

Keine automatische Behebung, keine Live-Waiver, neue Blocking-Modi, Baseline-
Änderungen, weiteren Consumer oder Bitbucket-Betrieb. Der Runtime-Code ist ein
Repository-Pilot ohne neuen Baseline-Release. Implementierungsabweichung oder
Rollenentzug deaktiviert neue Freigaben; eine Nachfolgeversion benötigt eigene
Abnahme. Historische Diagnosekandidaten werden nicht rückwirkend angenommen.

Der echte Ausgangsbefund und die technischen Behebungsnachweise sind bereits
vorbereitet. Ihre erste zulässige Lifecycle-Aufnahme, persönlichen Einzelaktionen
und der tatsächliche Abschluss folgen erst nach dieser Betriebsabnahme.
