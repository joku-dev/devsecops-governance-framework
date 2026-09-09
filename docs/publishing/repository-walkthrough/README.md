# Funktionsweise des Governance-Repositories

[PowerPoint herunterladen](files/repository-funktionsweise.pptx)

Diese Präsentation erklärt das Repository auf Deutsch in 16 Folien für etwa
20 Minuten. Sie eignet sich für Führungskräfte und technische Verantwortliche,
die den Ablauf und die Aufgabenverteilung verstehen möchten.

Die Folien behandeln die vier Architektur-Ebenen, Quellenaufnahme, Kontrollen,
ein konkretes SBOM-Beispiel, Baselines, Anwendungsläufe, Ergebnisaufnahme,
Review, Historie, Statusanzeige und Betriebsmodi. Sprechernotizen enthalten
Erläuterungen und Quellen zum festgehaltenen Stand
`80ba315e56828f5186303045cc2792b576396c26` vom 9. September 2026.

- [Folieninhalt und Sprechernotizen](presentation.md)
- [Redaktionelle Quelle](content.json)
- [Ergänzendes Whitepaper für die Geschäftsführung](../executive-briefing/README.md)

## Pflege

Änderungen beginnen in `content.json`. Die Präsentation entsteht mit
`scripts/publishing/build_repository_presentation.mjs` in der bereitgestellten
Artefaktumgebung. Der Builder verwendet die gleichen Umgebungsvariablen und den
gleichen privaten Finalisierungsablauf wie der
[Builder des Executive Briefings](../executive-briefing/README.md#pflege).
Der Aufruf erhält die redaktionelle JSON-Datei, ein privates Build-Verzeichnis
und einen neuen PPTX-Ausgabepfad innerhalb dessen übergeordneten Verzeichnisses.

`presentation.md` ist die lesbare redaktionelle Fassung und muss mit den
Folieninhalten, Sprechernotizen und Quellen übereinstimmen. Vor Veröffentlichung
alle finalen Folien rendern und visuell prüfen, den Inhaltsabgleich durchführen
und die freigegebene Ausgabedatei unverändert nach `files/` kopieren. Anschließend
die vollständige Repository-Validierung und den strengen MkDocs-Build ausführen.

Die Veröffentlichung ist ein abgeleitetes Kommunikationsartefakt gemäß
GCR-2026-055. Sie verändert keine Governance-Regeln oder Freigaben.
