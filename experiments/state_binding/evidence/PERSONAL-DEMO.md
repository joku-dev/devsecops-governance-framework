# Persönlicher Demonstrationslauf — vorbereitet, noch nicht ausgeführt

Der automatische Funktionsnachweis ist abgeschlossen. Dieser zusätzliche Schritt
prüft eine tatsächlich von der benannten Person abgegebene Erklärung.

1. Den vollständigen [Antrag](personal-demo-request.json) prüfen. Er bindet genau
   eine lokale Testpublikation, deren Kontext und Implementierungsdateien.
2. Bei Zustimmung den Inhalt der [vorbereiteten Erklärung](personal-demo-statement.txt)
   selbst als neuen Kommentar in den privaten
   [PR #176](https://github.com/joku-dev/devsecops-governance-framework/pull/176) kopieren.
3. Danach kann der folgende Befehl die Erklärung direkt bei GitHub prüfen und
   die gebundene lokale Testpublikation ausführen:

```bash
.venv-validation/bin/python experiments/state_binding/human_demo.py execute \
  --workspace experiments/state_binding/human-demo/session-1
```

Der Antrag erteilt keine Produktions-, Deployment-, Betriebsabnahme- oder
Patentfreigabe. Seine Beobachtungen und innere Fixture-Freigabe bleiben Testdaten.
Die zusätzliche persönliche Erklärung bindet deren tatsächlichen Demo-Effekt.
Codex erstellt oder postet diese Erklärung nicht im Namen der Person.

Benanntes Konto: `joku-dev`, GitHub-ID `81616324`.

Antragsdigest: `48a97c11dd0fe4f74806f95d2fcd2af019b097d3e129f0a18a9774654ec7ce88`.

Das lokale Workspace-Verzeichnis bleibt unverändert, bis die Erklärung geprüft
wird. Bei einer gebundenen Änderung muss ein neuer Antrag erzeugt und erklärt
werden. Die hier abgelegten Dateien sind nur der Review-Antrag und ein Textentwurf;
sie belegen noch keine abgegebene persönliche Erklärung.
