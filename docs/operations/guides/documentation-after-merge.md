# Dokumentation nach einem Merge aktualisieren

## Zweck

Der Workflow `Documentation Refresh` bereitet nach jedem Merge eines PRs mit
Implementierungspfaden einen Dokumentationsabgleich als Draft-PR vor. Er ergänzt
den README-Überblick, einen Eintrag im Funktionskatalog, die technischen Pfade
und einen Auditbericht. Die Änderungen werden nie direkt nach `main` geschrieben.

## Ablauf

1. Ein PR wird nach `main` gemergt. Der Workflow prüft, ob Implementierung in
   Skripten, Workflows, Modellen, Policies, Schemas, Architektur, Anwendungen,
   Pipeline-Baselines oder Agent-Konfiguration geändert wurde.
2. Für solche PRs übernimmt der Generator die nummerierte PR-Zusammenfassung
   und die geänderten Pfade. Bei rein dokumentarischen Änderungen endet der
   Lauf ohne Folge-PR; dadurch entsteht keine Rekursion.
3. Eine lokale Markdown-Linkprüfung und `mkdocs build --strict` laufen gegen
   den aktuellen Main-Stand. Ergebnisse und redaktionelle Prüfpunkte werden im
   Auditbericht festgehalten.
4. Der Workflow öffnet einen Draft-PR mit den vorgeschlagenen Dokumenten.
   Er startet erforderliche PR-Prüfungen über `workflow_dispatch`, da ein
   `GITHUB_TOKEN`-Push keine normalen `pull_request`-Läufe auslöst.
5. Ein Maintainer prüft die fachliche Zuordnung und ergänzt die Auswirkungen
   auf README, Katalog, Navigation und betroffene Betriebs- oder Governance-
   Dokumente. Erst ein menschlich freigegebener Merge veröffentlicht die
   Dokumentationsänderungen auf `main`.

## Grenzen

Der Generator leitet keine fachliche Bedeutung aus dem Code ab. Er verwendet
die PR-Zusammenfassung und Pfadlisten als redaktionellen Ausgangspunkt. Der
Katalogeintrag muss daher im Draft-PR einem passenden Funktionsbereich
zugeordnet und fachlich vervollständigt werden. Linkprüfung und MkDocs-Build
weisen formale Probleme nach; sie bestätigen keine semantische Vollständigkeit.
Der Workflow führt keinen Document Consistency Review und keine Governance-
Entscheidung aus.
