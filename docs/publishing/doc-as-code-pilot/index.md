# Doc-as-Code-Pilot

Diese Pilotpublikation zeigt, wie ein professionelles Dokument vollständig in
Git gepflegt und reproduzierbar als HTML, Word und PDF veröffentlicht wird.

Die publizierte Fassung wird aus
[`publication.yaml`](publication.yaml) erzeugt. Das Manifest legt die
Reihenfolge der Kapitel und der einzeln pflegbaren Anforderungen fest. Die
Dateien unter `requirements/`, zum Beispiel
[`DAC-REQ-001`](requirements/DAC-REQ-001.md), sind dadurch unabhängig änderbar,
bleiben aber Teil einer kontrollierten Gesamtpublikation.

Die Quellen dieser Seite und die Exportquellen haben unterschiedliche Aufgaben:
Diese Seite dient der Navigation in MkDocs. Das Manifest ist der technische
Einstiegspunkt für die Exportpipeline.

## Lokale Prüfung

```bash
python3 doc-as-code/scripts/build_publication.py --validate-only
```

## Lokaler Export

```bash
python3 doc-as-code/scripts/build_publication.py
```
