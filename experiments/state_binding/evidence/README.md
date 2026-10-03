# Vertrauliche Versuchsnachweise

## Automatisierter Lauf 001

Code-Commit: `68849a1011097e9ad985844110b12c2dd7f18e3b` (signierter Entwicklungscommit).
Alle Implementierungsdateien des Versuchs stimmen mit diesem Commit überein.
Das Paket wurde aus einem unveränderten getrackten Arbeitsstand erzeugt.

- **18/18 Dateisystemversuche bestanden**, einschließlich zweier verschiedener Prozesse.
- **27/27 unveränderte Vergleichstests** des bisherigen Piloten bestanden.
- **640/640 Repository-Tests bestanden**; darunter 17 zusätzliche Prototyp-/Evidence-Tests.
- OPA/Runtime, Repository, Agent-Provenance und strikter MkDocs-Build bestanden.
- **83 geschützte Implementierungsdateien unverändert** gegenüber dem benannten main-Stand.
- Ergänzender persönlicher Demonstrationslauf: **erfolgreich durchgeführt**,
  separat dokumentiert in [PERSONAL-DEMO.md](PERSONAL-DEMO.md).
- Neuheit/Patentfähigkeit: **nicht bewertet**.

## Dateien

- [Versuchspaket](run-001.zip): Rohdaten, Vorher-/Nachher-Dateien, Ergebnisse,
  Quellmanifest, Versuchsbericht und Vergleichsprotokolle.
- [Unabhängige Prüfung](verification.json).
- [Validierungsnachweise](validation.json) mit Log- und Dateifingerprints.
- [Vollständiger erfolgreicher Testlauf](validation-final.log).
- [Erster Testlauf](validation-initial.log): dokumentiert den Fehler durch
  geerbte Commit-Signierung in einem temporären Test-Repository.
- [Dokumentationsbuild](docs-build.log).
- [Persönlicher Demonstrationslauf](PERSONAL-DEMO.md): echte GitHub-Erklärung,
  genau eine lokale Testpublikation, gespeicherter Replay und erneute Providerprüfung.
- [Separates persönliches Versuchspaket](personal-demo-001.zip) und
  [Prüfergebnis](personal-demo-verification.json).
- [Vollständige Repository-Validierung nach dem persönlichen Lauf](personal-demo-validation.log).
- [Separater GitHub-CI-Status](CI-LIMITATIONS.md).

Die erneute Validierung schaltete Signierung ausschließlich prozesslokal für
Fixture-Commits ab. Die gespeicherte Git-Konfiguration und die expliziten
Release-Tag-Signaturtests blieben unverändert. Ausgaben zu `owner/repo` in den
Testlogs stammen aus Test-Doubles; sie sind keine real eröffneten PRs.

## Paket prüfen

Vom Repository-Root aus:

```bash
python3 experiments/state_binding/verify_evidence.py \
  experiments/state_binding/evidence/run-001.zip \
  --expect-manifest-sha256 e8a903751e3e3f040371329f8f8ef2910376f72decd42a033f3620b50caf4628
```

Manifest SHA-256: `e8a903751e3e3f040371329f8f8ef2910376f72decd42a033f3620b50caf4628`

ZIP SHA-256: `919e299760d1f62d4345ff7a239ef7919c82d23c2c36732d9b8a1d7b665f29ea`

Der Prüfer benötigt nur die Python-Standardbibliothek und importiert den
Prototyp nicht. Ein separat aufbewahrter Manifest-Digest bindet das Paket;
Prüfsummen sind keine amtliche Zeitbestätigung. Die Quellen und Dateifingerprints
ermöglichen die Wiederholung gemäß der Anleitung im übergeordneten README.

## Aussagegrenze

Die Versuche weisen Funktionsverhalten im dokumentierten lokalen Modell nach.
Sie zeigen auch Redundanz zwischen History-Root und vorhandenen Head-Prüfungen.
Die als Weglassversuch zugelassenen Publikationen sind ausdrücklich ablatierte
Tests und keine produktiven Freigaben. Sämtliche automatisierten Erklärungen
bleiben synthetische Testdaten. Patentrecherche, Erfinderschaft und historische
Offenlegungen erfordern gesonderte Bewertung.
