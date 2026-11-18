# V2: öffentliche Artefakte auf vertrauliche Begriffe prüfen

Der lokale Befehl prüft Textdateien und UTF-8-Inhalte in `.docx`, `.xlsx` und
`.pptx`. Er meldet die Fundorte und verändert keine Eingaben. Er veröffentlicht
keine Dateien und speichert weder Suchbegriffe noch Dateiinhalte als Nachweise.

```bash
./axiom-v2 artifact-hygiene check \
  --profile legacy-public-artifact-hygiene-v1 \
  --forbidden-term VERTRAULICH \
  /absoluter/pfad/bericht.docx /absoluter/pfad/README.md
```

Weitere Begriffe können über weitere `--forbidden-term`-Optionen oder die
kommaseparierte Variable `PUBLIC_ARTIFACT_FORBIDDEN_TERMS` kommen. Die Variable
wird ausschließlich vom lokalen Adapter gelesen. Shell-Historie und die
Prozessliste können Befehlsargumente enthalten; echte vertrauliche Suchbegriffe
gehören deshalb in die passend geschützte Umgebung des Aufrufs.

Das explizite Profil erhält die gesamten ursprünglichen Ausgaben: Exit 0 bei
bestandener Prüfung; Exit 1 mit Fundorten oder `No forbidden terms configured`
auf stderr. Groß-/Kleinschreibung wird per Unicode-Casefold verglichen. Fehlende
Pfade und Verzeichnisse werden übersprungen, zählen aber wie im Original zur
angegebenen Pfadanzahl. Doppelte Pfade und Office-Mitgliedsnamen bleiben in der
ursprünglichen Reihenfolge erhalten. Ungültiges UTF-8 wird bei Textdateien
ignoriert; ungültige Office-Mitglieder werden übersprungen. Bei vom ZIP-Leser als
`BadZipFile` gemeldeten Format- oder CRC-Fehlern greift
der ursprüngliche Text-Fallback, auch nach vorherigen Funden. Andere ursprüngliche
Decoder-Ausnahmen sind damit nicht als erfolgreiches Ergebnis abgedeckt.

Der Produktkern erhält ausschließlich Texte und Begriffe. Der benannte lokale
Adapter liest Dateien, Office-Archive und die eine Umgebungsvariable. Er führt
keine Programme aus den geprüften Artefakten aus. Für die V2-Installation sind
eine gültige private Instanz und ihre unveränderten Produktdateien erforderlich.

Zusätzliche V2-Grenzen verhindern unbeschränkte lokale Eingaben: höchstens
1.024 Pfade, 16 MiB pro Datei oder ZIP-Mitglied, 2.048 Mitglieder pro Archiv,
8.192 Textorte und 1 MiB Ortsbezeichnungen. Das gemeinsame 64-MiB-Lesebudget
zählt Eingabe-, entpackte und erneut UTF-8-kodierte Textbytes. Es gibt höchstens
1.024 Begriffe mit zusammen 65.536 Zeichen nach Casefold, höchstens 4.096 Zeichen
pro CLI-Begriff und 65.536 Zeichen im Umgebungswert. Das Vergleichsbudget begrenzt
das Produkt aus gesamter Textlänge und Begriffanzahl auf 256 × 1024² Zeichen.
Pfad- und Mitgliedsnamen sind auf 4.096 Zeichen begrenzt. Namen mit C0-Steuerzeichen (U+0000 bis U+001F),
symbolische Links, Spezialdateien sowie verschlüsselte oder nicht unterstützte
ZIP-Mitglieder werden abgelehnt. Solche V2-Grenzen ergeben den strukturierten Fehler Exit 2;
sie sind keine ursprünglichen Hygiene-Befunde. Eine harte Prozess-Speichergrenze
wird für diesen lokalen Aufruf nicht behauptet.

Die fokussierten Tests vergleichen vollständige ursprüngliche Ausgaben und
Dateiverhalten. Ein erfolgreiches Ergebnis ersetzt weder Veröffentlichungserlaubnis
noch eine vollständige Prüfung auf Geheimnisse. Dieser Baustein bleibt in der
Paritätsmatrix in Arbeit, bis seine installierten Nachweise vorliegen.
