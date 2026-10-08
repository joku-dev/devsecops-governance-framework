# GCR-2026-127: Reproduzierbares semantisches Kataloglaufpaket

## Zweck

Der kuratierte Katalog aus GCR-2026-126 benötigt einen reproduzierbaren,
providerunabhängigen Ausführungsscope. Dieser Änderungssatz ergänzt einen
fail-closed Paketgenerator und einen versionierten Prompt für einen später
separat freizugebenden synthetischen Providerlauf.

## Paketgrenze

Das Provider-Eingabeverzeichnis enthält exakt sechs Dateien:

- zwei synthetische Quelldateien;
- das synthetische Quellenmanifest;
- den synthetischen Register-Snapshot;
- das Provider-Projektionsschema;
- den versionierten Prompt.

Der Erwartungskatalog wird nur per Hash an das Laufpaket gebunden und nicht in
das Provider-Eingabeverzeichnis kopiert. Damit erhält das Modell keine
Sollantworten. Quellen-, Register-, Manifest- und Kataloghashes werden vor der
Paketerstellung geprüft.

## Entscheidungsgrenze

Das Paket bleibt `prepared_not_run`. Provider und Modell müssen bei der
Ausführung explizit gebunden und erneut freigegeben werden. Die Vorbereitung
ruft keinen Provider auf, bestätigt kein Finding und ändert weder Rollout noch
Enforcement.

## Governance-Auswirkung

- ausschließlich synthetische Daten;
- keine realen Quellen oder Consumer-Repositories;
- keine Änderung an Controls, Architekturmarkern, OPA oder Baselines;
- kein neues blockierendes Gate;
- Rollout bleibt `pending`.
