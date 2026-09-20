# 6 Herkunft und Fragen für die anwaltliche Prüfung

## 6.1 Zweck und Prüfauftrag

Dieses Paket erläutert die technische Problemstellung, eine konkrete ausführbare Lösung, ihre Systemgrenzen und die experimentellen Nachweise. Es soll die anwaltliche Beurteilung erleichtern, welche technischen Merkmale weiter untersucht werden sollen und welche zusätzlichen Informationen für eine mögliche Anmeldung erforderlich sind. Patentansprüche, Anmelder- und Erfinderbenennung sowie eine rechtliche Bewertung sind nicht Bestandteil des Pakets.

Die DPMA-Hinweise verlangen für eine Anmeldung eine hinreichend deutliche und vollständige technische Offenbarung und nennen unter anderem technische Beschreibung, Ansprüche und gegebenenfalls Zeichnungen als Bestandteile. Das vorliegende Paket ist dafür eine technische Arbeitsgrundlage; die Auswahl und endgültige Fassung der Anmeldeunterlagen obliegt der Beratung. [E7]

## 6.2 Dokumentierte Herkunft und Versionsfolge

Der Maintainer stellte das Arbeitsdokument `WP_STATE_COMMITMENT_AUTHORIZATION_BINDING.md` zur Verfügung und beauftragte anschließend einen begrenzten privaten Prototyp mit technischen Nachweisen. Das Arbeitsdokument trägt das Datum 19. September 2026. Dieses aufgedruckte Datum beweist für sich genommen keinen Entstehungszeitpunkt. Die Originaldatei bleibt unverändert im lokalen Arbeitsverzeichnis und ist nicht Teil des Quellcodeauszugs.

| Dokumentierter Stand | Bedeutung |
|---|---|
| `68849a1011097e9ad985844110b12c2dd7f18e3b` | Prototypcode, Tests und ursprüngliches Design; Quellstand des automatisierten Versuchspakets |
| `6d1a3bae5527223fb5af54677c902cbba07009f6` | Aufbewahrung automatisierter Versuche und Validierungsnachweise |
| `4dbc458872d39c113d8f0b978aab918eb0c6ce28` | Vorbereiteter persönlicher Antrag; Quellstand der persönlichen Ausführung |
| `56ed0c743121fddc9d117b69eb470493dff5046d` | Aufbewahrung des abgeschlossenen persönlichen Demonstrationsnachweises |

Der Agent hat Implementierung, Experimente und Erläuterungen auf Grundlage des Auftrags vorbereitet. Daraus wird keine rechtliche Zuordnung von Erfinderschaft oder Eigentum abgeleitet. Die vollständigen menschlichen Beiträge, deren Zeitpunkte und etwaige Rechtebindungen müssen vom Maintainer und den beteiligten Personen bestätigt werden.

## 6.3 Technische Fragen an die Beratung

- Welche Kombination aus M1 bis M7 beschreibt einen hinreichend konkreten technischen Gegenstand und welche Merkmale sind bereits in relevanten Veröffentlichungen verbunden?
- Welche Bedeutung hat die nachgewiesene Redundanz zwischen zusätzlichem History-Root und vorhandener Head-/Sequenzprüfung für eine mögliche Abgrenzung?
- Ist der getrennte State-Root in einer genau definierten Ausgestaltung technisch tragend, obwohl der Zustand deterministisch aus bereits gebundenen Eingaben abgeleitet wird?
- Welche Rolle spielt die Implementierungsbindung zusammen mit der erneuten Prüfung an der tatsächlichen lokalen Schreibgrenze?
- Soll eine mögliche Beschreibung auf die nachgewiesene lokale Ausführungsform begrenzt bleiben oder zusätzliche ausreichend ausgearbeitete Ausführungsformen enthalten?
- Welche weiteren Versuche wären für externe Effekte, einen realen späteren Widerruf oder eine konkrete Agentenintegration erforderlich?

## 6.4 Vom Maintainer zu ergänzende Angaben

Für die Beratung sind die vollständigen Namen und konkreten technischen Beiträge der beteiligten Menschen, die frühesten belastbaren Entstehungsunterlagen und mögliche arbeitsvertragliche oder sonstige Rechtebindungen noch zu klären. Das Paket füllt diese Angaben nicht stellvertretend aus.

Ebenfalls offen ist eine vollständige Übersicht früherer Offenlegungen. Zu prüfen sind frühere öffentliche Repositorystände, Releases, GitHub Pages, Vorträge, Präsentationen, Consumer-Integrationen sowie Weitergaben des Arbeitsdokuments. Der während der Prototypentwicklung bestätigte private Repositorystatus belegt nicht, dass keine relevante ältere Veröffentlichung existiert. Gesondert zu erfassen sind Inhalt, Datum, Empfänger und gegebenenfalls vereinbarte Vertraulichkeit einer Weitergabe.

Das dokumentierte Konzept und der Prototyp sollen als technische Nachweise erhalten bleiben. Eine Auswahl passender Länder, Fristen oder Anmeldeverfahren wird hier nicht vorweggenommen. Der Benutzer kann diese Fragen anhand des Pakets direkt mit seinem Patentanwalt klären.

## 6.5 Weitergabe und Vertraulichkeit

Die Dateien sind als vertraulich gekennzeichnet und bleiben außerhalb der Website-, Viewer- und Release-Verzeichnisse. Der Docs-Publisher des Repositorys wurde deaktiviert; ein zusätzlicher Confidential-Marker sperrt die Veröffentlichung dieses Forschungsbereichs. Die Prüfung der Sichtbarkeit ist eine Momentaufnahme und keine Garantie gegen jede spätere Fehlkonfiguration.

Das ZIP-Paket ist zur gezielten Weitergabe durch den Maintainer bestimmt. Es ist nicht verschlüsselt. Die Vertraulichkeitskennzeichnung ersetzt keine Zugriffskontrolle; für die Übermittlung kann der mit der Kanzlei vereinbarte geschützte Kanal verwendet werden. Der Agent hat keine Unterlagen an einen Patentanwalt oder einen anderen Empfänger versendet.

**[E7] DPMA Anmeldung eines Patents.** Offizielle Hinweise zu technischer Offenbarung und Anmeldeunterlagen; geprüft am 20. September 2026. https://www.dpma.de/patente/anmeldung/index.html
