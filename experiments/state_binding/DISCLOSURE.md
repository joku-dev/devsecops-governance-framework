# Vertraulichkeit, Herkunft und offene Offenlegungsprüfung

Stand: 20. September 2026. Diese Bestandsaufnahme ist keine vollständige
Recherche zu Veröffentlichungen oder Rechten.

## Während der Implementierung tatsächlich geprüft

| Gegenstand | Beobachtung |
|---|---|
| GitHub-Repository | API: `private=true`, `visibility=private` |
| GitHub Pages | Repository-API: `has_pages=false`; Pages-API: HTTP 404 |
| Bekannter Viewer-Endpunkt | Anonymer HEAD auf `https://joku-dev.github.io/devsecops-governance-framework/`: HTTP 404 |
| Docs-Publisher | API bestätigt `state=disabled_manually` nach Deaktivierung |
| Neuer Branch | Separater privater Prototyp-Branch auf dem bestehenden main-Stand |
| Automatische Veröffentlichung | Kein neuer Publikationsworkflow; Docs-Workflow ohne private Override-Option und mit Confidential-Marker-Sperre |
| Detailliertes Material | Außerhalb von `docs/`, `generated/`, `status/` und MkDocs-Ausgaben |

Diese Momentaufnahme belegt keine Löschung früherer Kopien, Caches, Forks oder
bereits geteilter Dokumente. Sichtbarkeitseinstellungen und Zugriffsrechte können
sich später ändern. Vor jedem Push wird der aktuelle private Status geprüft.

## Herkunft und Beiträge

Der Maintainer hat das Arbeitsdokument
`WP_STATE_COMMITMENT_AUTHORIZATION_BINDING.md` zur Analyse bereitgestellt und
anschließend die Umsetzung eines privaten, begrenzten Prototyps mit Nachweisen
für eine mögliche Patentanmeldung beauftragt. Das Dokument war beim Beginn
dieser Umsetzung untracked und wurde nicht verändert oder veröffentlicht.

Der Agent hat den begrenzten Versuchsvertrag, die Implementierung, Tests und
Dokumentation vorbereitet. Daraus werden keine Aussagen über rechtliche
Erfinderschaft oder Rechteinhaberschaft abgeleitet. Frühere technische Beiträge,
Entstehungsdaten und beteiligte Menschen müssen vom Maintainer ergänzt werden.
Git-Zeitstempel oder generierte Berichte ersetzen diese Bestätigung nicht.

## Noch offen — vor einer Anmeldung mit Beratung klären

* Welche relevanten Teile waren früher in diesem Repository, in Releases,
  GitHub Pages, Präsentationen oder Consumer-Repositories öffentlich?
* Welche technische Merkmalskombination war wann tatsächlich erkennbar?
* Wer hat welche technische Idee beigetragen; bestanden Arbeitsverhältnisse,
  Abtretungen oder andere Rechtebindungen?
* Wem wurde das Work Package außerhalb dieses privaten Kontexts zugänglich
  gemacht und unter welchen Vertraulichkeitsbedingungen?
* Welche bekannten Verfahren und Patentschriften stehen der Kombination nahe?

Eine Umstellung auf privat hebt eine frühere Offenlegung nicht rückwirkend auf.
Die Bewertung erfolgt mit Patentberatung anhand der konkreten Inhalte und Daten.
Automatische Tests können diese Fragen nicht entscheiden.
