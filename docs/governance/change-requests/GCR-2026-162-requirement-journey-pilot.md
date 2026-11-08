# GCR-2026-162 — Lesender Pilot für individuelle Anforderungswege

## Auftrag und Einordnung

Der Maintainer beauftragt am 8. November 2026 einen öffentlichen Viewer-Piloten
für sechs festgelegte Fälle. Die Änderung ist eine erklärende, lesende Projektion
bestehender Datensätze. Sie trifft keine normative Entscheidung und veröffentlicht
keine neue Baseline. Die Serverinstallation bleibt zurückgestellt.

## Umfang

Die bestehende Seite „Anforderung bis OPA“ erhält eine Pilot-Auswahl und
versioniert verlinkte Detailseiten mit fünf Phasen. Die Auswahl enthält
`GRQ-000003@rev1`, `GRQ-000001@rev1`, `GRQ-000048@rev1` sowie die historischen
Proposals `P0001`, `P0004` und `P0008` des Falls
`RLC-PRA-STD-REQ-001-MIGRATION`.

Die [Bedienungsanleitung](../../operations/guides/governance-viewer-app.md#einzelne-anforderungswege-pilot-mit-sechs-fallen)
beschreibt Darstellung, Datenquellen und Grenzen. Quellenregister, Lifecycle,
Katalog und Artefaktregister bleiben Autorität; die Projektion fügt keine
Verknüpfungen aus Textähnlichkeit oder Dateinamen hinzu. Quelldokumente werden
nur zur Hashprüfung gelesen, nicht zur Anforderungsextraktion.

Aktive, wirksame GRQ-Revisionen zeigen Katalogtext. Historische Proposals zeigen
nur Metadaten und Beleglinks, keine Reviewtexte oder privaten Notizen. Die zwei
RTA-Zuordnungen von `GRQ-000048@rev1` bleiben getrennt. Das Duplikat verweist auf
`GRQ-000019`, ohne eigene Aktivierung oder erfundene historische Zielrevision.
Der abgelehnte Vorschlag endet sichtbar, ohne allgemeine Nichtanwendbarkeit zu
behaupten. Veröffentlichung und Laufzeit bleiben ohne ausdrücklichen
Anforderungsnachweis „nicht verknüpft“.

## Geschützte Grenzen

Keine Änderungen an Quellenfreigaben, kanonischen Anforderungen, gespeicherten
Entscheidungen, Artefaktregister, OPA-Semantik, Enforcement, Betriebsabnahmen,
Statusindizes oder freigegebenen Baselines. Insbesondere bleiben die
fingerprintgebundenen Governance-Workflows und Validierungseinstiege unverändert.
Der zusätzliche Viewer-DOM-Job nutzt das vorhandene gepinnte Node/jsdom-Setup.
Er ersetzt keine bestehende CI und verändert keine Merge-Regel.

## Prüfung und Lieferung

Python-Regressionen prüfen alle sechs Fälle, exakte Revisionen,
Mehrfachzuordnungen, fehlende/mehrdeutige Daten, Aktivierungsbindungen und
abweichende Hashes. DOM-Regressionen prüfen Direktlinks, Browsernavigation,
Tastaturziele, Textdarstellung, unbekannte Kennungen, kompatible Alt-Daten und
sicheres Escaping. Der Browserdurchlauf prüft breite und schmale Darstellung.

Gepinnter Bootstrap, vollständige Repository-Validierung, Viewer-Generierung und
MkDocs strict sind vor Lieferung auszuführen. Die konkreten Ergebnisse und der
revisionsgebundene Review werden im fokussierten PR dokumentiert. Rollenprüfungen
durch den ausführenden Koordinator gelten als `role_lens`, nicht als unabhängige
Freigabe. Merge erst nach erfolgreicher CI und unabhängiger Freigabe; anschließend
wird der veröffentlichte Pilot geprüft. Die Auswahl aller weiteren Anforderungen
ist nicht Teil dieses GCR.
