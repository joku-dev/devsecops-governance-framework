# Arbeitsablauf

1. Eine Anforderung oder ein Kapitel wird in einem Branch geändert.
2. Das Manifest bestimmt die verbindliche Reihenfolge der Publikation.
3. JSON-Schemas und Referenzprüfungen prüfen Struktur, Kennungen und Pfade.
4. Der Pull Request zeigt die fachlichen Änderungen und baut eine Vorschau.
5. Nach dem Review erzeugt dieselbe Werkzeugkette die freigegebenen Formate.
6. Provenienz und Prüfsummen verbinden jedes Ergebnis mit seinen Git-Quellen.

Neue Anforderungen erhalten die nächste freie Kennung und werden als eigener
Eintrag in `publication.yaml` ergänzt. Eine Kennung wird nach der Einführung
nicht für einen anderen Inhalt wiederverwendet.
