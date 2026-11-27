# AXIOM V2: Wiedergabe ohne Standardinstanz

Eine abgeschlossene Aufnahme kann mit dem zur Produktgeneration passenden
V2-Programm nachgerechnet werden, auch wenn die ursprüngliche Governance-Quelle
und die Standardinstanz nicht mehr vorhanden sind:

```bash
/path/to/installation/axiom-v2 pilot-update replay --record /path/to/record
```

Das gilt für die Befehle mit einer eigenen quellfreien `replay`-Operation.
Wiedergabe ist keine neue Erfassung, Veröffentlichung oder Betriebsfreigabe.
Die gespeicherte Anfrage, Produktgeneration, Beobachtungsreihenfolge und alle
verwendeten Blobs werden weiter geprüft. Fremde oder veränderte Produktdaten
werden dadurch nicht zulässig. Ein gültiger technischer Datensatz kann ein
ursprüngliches fachliches Fehlerergebnis enthalten.

Der installierte Starter verwendet seine Standardinstanz für Befehle, die eine
Instanz benötigen. Reine Wiedergabe und globale Prüfungen werden davor aufgelöst.
Eine fehlende oder beschädigte Standardinstanz verhindert deshalb keine reine
Wiedergabe. Ein gewöhnlicher Erfassungsbefehl darf dadurch weder eine neue Instanz
anlegen noch mit einer beschädigten Instanz fortfahren.

Eine ausdrücklich mit `--instance /path/to/node` gewählte Instanz bleibt bindend.
Sie wird wie bisher validiert; `inspect` weist Aufnahmen einer anderen Instanz
ab. Für die instanzfreie Wiedergabe wird diese Option weggelassen.

Die Korrektur betrifft die Instanzauswahl des Starters. Sie ändert weder
ursprüngliche Governance-Entscheidungen noch Eingabegrenzen, Autoritätsfelder,
Enforcement oder die vollständige äußere Python-Traceback-Darstellung. Die
[gemeinsame signierte Quell- und Installationsabnahme](../status/axiom-v2-goal-progress.md)
bleibt offen. Entwicklungsfixtures mit dem tatsächlichen Startertext ersetzen
keine installierte Abnahme des neuen signierten Pakets auf beiden Hosts.


## Versionsgebundene Installation

Der Installer verwendet den Startertext aus der aufgenommenen Paketversion,
nicht aus dem zufällig aktuell ausgecheckten Installer. Ältere Pakete ohne diese
Funktion behalten ihren bisherigen Starter und ihre ursprünglichen Grenzen.
Sie bekommen keine neue, für ihr Programm unbekannte Option vorgegeben.

Eine vorhandene, aber fehlerhafte Starterfunktion löst einen Installationsfehler
aus; es gibt keinen stillen Rückfall auf einen anderen Starter. Der Installer
schreibt seine Abschlussbestätigung erst nach erfolgreicher Erzeugung des
passenden Starters. Bestehende Installationen und Dienste werden nicht geändert.
