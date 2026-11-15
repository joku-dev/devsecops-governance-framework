# AXIOM V2: geprüfter Installationskandidat

Der technische V2-Kandidat wurde am 15. November 2026 getrennt auf macOS ARM64
und Ubuntu 24.04 x86_64 installiert und geprüft. Er ist eine technische
PR-/Installationslieferung aus [GCR-2026-185](../../governance/change-requests/GCR-2026-185-axiom-v2-decoupling.md),
keine produktive Ablösung oder Übertragung bestehender Betriebsabnahmen.

## Geprüfte Identitäten

| Bindung | Wert |
| --- | --- |
| Implementierungscommit beider Pakete | `756a28eae43d6b649e624dd081360bfed249fc66` |
| Originaler Git-Tree | `ea2c878f5770892f15880e1ae51d88fb1fbe72af` |
| Gemeinsamer Runtime-Source-Digest | `e034765206a01a45b9a2b55a923d24b3bd146d4e1038aca40197f353a655ad4a` |
| Aktive Abhängigkeiten, 644 Dateien | `c4223d7bc5e77600e51a7ace36bc5aa9cc6cd69623870c9cd800232bc3627f4a` |
| Mac-Paket SHA-256 | `f72c6a6d8968f4a035720db6f5e7ae3de9a338ca7f514dea51e455436fe8c9c9` |
| Linux-Paket SHA-256 | `70e5e31043712f3ec73b608db7bf14a3dd840aa8eaf029314d80116c462699c2` |
| Kanonischer Digest der neun fachlichen Fixture-Ergebnisse | `d5ebce95ae3e393a784938dd33584ceb0ee7c4e23c8616ab7685d63cdb01d158` |

Die Pakete enthalten denselben Quellstand und plattformspezifische, geprüfte
OPA-Binärdateien und Wheels. Ein zweiter unabhängiger Mac-Build desselben
Commits ergab denselben Paket-Hash. Die spätere Dokumentation und der gespeicherte
Host-Test sind Ergänzungen zu diesem exakt bezeichneten Installationskandidaten;
sie werden nicht als neuer, bereits auf beiden Hosts installierter Commit ausgegeben.

Produktversion `2.0.0-candidate`, portable Verträge/Runtime `1.0.0` und
DevSecOps-Baseline `l1-baseline-v1.1.3` sind getrennte Versionsachsen.
Es wurde kein Baseline-Tag, Releasepaket oder fachliches Policy-Verhalten geändert.

## Tatsächlich ausgeführte Prüfungen

- Gepinnter Bootstrap und vollständige Repository-Validierung: 1.204 Tests,
  ein bestehender Skip, OPA- und beide Repository-Validatoren erfolgreich.
- Strenger MkDocs-Build erfolgreich; alle 24 fingerprintgeschützten Dateien
  der persönlichen V1-Pilotabnahme bytegleich.
- Auf jedem Host ein frischer privater Präfix, eigene offline installierte
  Python-Umgebung, eigene Instanzkennung, eigener Schlüssel und leere Daten.
- Exakter Original-Commit/Tree und saubere sparse Git-Quelle; 49 freigegebene
  Python-Dateien einschließlich Adapter und Installationsbibliotheken.
  Frühere V1-CLI- und Importfassaden fehlen physisch im aktiven Arbeitsbaum.
- Echter OPA-Lauf je Host für GitHub Actions, GitLab CI und Bamboo/Bitbucket-
  Vertragskontexte, jeweils PASS, kritischer Befund und fehlende Schutzfakten.
  Alle neun fachlichen Ergebnisse stimmen zwischen beiden Hosts überein.
- Echte Workbench-HTTP-Prüfung auf getrennten Loopback-Ports: Anmeldung,
  Zugriffsschutz, CSRF-Prüfung und Abmeldung. Der Schlüssel erschien nicht im Log.
- Collector leer und pausiert, Publisher inaktiv; erneuter Instanzaufruf nach
  Beenden der Workbench erfolgreich. Ein nachträglich eingefügtes Alt-Skript
  wird vor dem Collector-Start zurückgewiesen.
- Bestehende VM unverändert auf `adc4643`; ihre Workbench auf Port 8766
  antwortet weiterhin. Kein V2-Dienst wurde dauerhaft gestartet.

Die Kontexte und Artefakte des Hostvergleichs sind ausdrücklich synthetisch;
die Auswertung erfolgt mit dem echten gepinnten OPA und unveränderten Policies.
Sie sind keine neue Consumer-Compliance-Aussage, kein Live-Provider-Test und
keine vollständige Bewertung aller 16 L1-Kontrollen. Die Pipeline-Gate-Abdeckung
bleibt bei den vorhandenen fünf Kontrollen.

## Wiederholung und Betriebsgrenzen

Das [Installationsverfahren](../planning/axiom-v2-decoupling.md) erzeugt neue
Präfixe und aktiviert weder Dienste noch Sammlung. Nach dessen Abschluss kann
der gespeicherte Test aus einem vertrauenswürdigen Entwicklungscheckout mit
dem Python der frischen Installation aufgerufen werden:

```sh
"$V2_PREFIX/venv/bin/python" tests/acceptance/axiom_v2_host_smoke.py \
  "$V2_PREFIX" /private/operator/host-smoke.json
```

Der Test benötigt den eigenen freien Instanzport, erstellt private Fixture-Daten
und beendet seinen Workbench-Prozess. Für eine vollständige Wiederholung einen
neuen Installationspräfix verwenden. Die privaten Schlüssel, Rohbelege und
Rollenreview-Pakete werden nicht veröffentlicht.

Das [Inventar](../planning/axiom-v2-function-inventory.md) ordnet alle 22
Funktionsbereiche sowie Python-, Shell- und Node-Einstiege zu. Lokale
Autorenwerkzeuge bleiben im Entwicklungscheckout. Alte Live-Lifecycle-Pfade
bleiben im erhaltenen V1-Stand; persönliche Zustimmung, Rollen, Waiver,
Publisher-Zuständigkeit und Blocking werden nicht übernommen.

GitLab-, Bamboo- und Bitbucket-DC-Zielversionen und Instanzen bleiben offen.
Ihre echten API-, Credential-, Draft- und Betriebsabnahmen benötigen diese
externen Ziele. Der vorbereitete Code wird durch einen separaten PR und die
aktive GitHub-CODEOWNER-Regel geprüft. Weder Fixture-Erfolg noch ein
Koordinator-Rollenreview ersetzen diese menschliche Freigabe.
