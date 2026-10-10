# Lokale Prüfung und Erzeugung

Die Struktur kann ohne Pandoc geprüft werden:

```bash
python3 doc-as-code/scripts/build_publication.py --validate-only
```

Für den vollständigen Export müssen die in `doc-as-code/toolchain.env`
festgelegte Pandoc-Version und die dort konfigurierte PDF-Engine installiert
sein:

```bash
python3 doc-as-code/scripts/build_publication.py
```

Die Ergebnisse entstehen unter `build/doc-as-code/`. Neben HTML, DOCX und PDF
werden ein maschinenlesbarer Anforderungsindex und ein Provenienznachweis
erzeugt.
