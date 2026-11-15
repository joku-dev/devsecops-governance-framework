---
goal_id: AXIOM-V2-FUNCTIONAL-PARITY-001
date: "2026-11-15"
status: in_progress
v1_reference: 6b557fefe295b58272d2271326576ca3a3687197
v2_start: b6e3b64951456b5878a98810d50ba17cbe89dfe0
branch: feat/axiom-v2-functional-parity
change_request: GCR-2026-186
consumer_reference: joku-dev/ha-CPsWMS
---

# AXIOM V2: vollständige technische Funktionsparität zu V1

Der Maintainer hat die autonome Umsetzung samt Prüfung mit `ha-CPsWMS` am
15. November 2026 beauftragt. Dies ist ein technischer Produktauftrag, keine
neue normative Quelle, Freigabe einzelner Anforderungen oder Betriebsabnahme.

## Verbindlicher Umfang

Die letzte V1 vor der Entkopplung ist der exakte Commit `6b557fe` oben. Ihre
22 katalogisierten Funktionsbereiche, ausführbaren Einstiegspunkte und
Betriebsabläufe bilden den Vergleichsumfang. Der V2-Ausgangspunkt `b6e3b64`
ist eine entkoppelte Grundlage, noch kein funktional gleichwertiger V1-Ersatz.

Jede Funktion erhält ein ausführbares, installiertes V2-Gegenstück mit
repräsentativem Positiv-/Negativnachweis. Dass eine Datei weiterhin im
Entwicklungscheckout liegt, ein Befehl auf ein Altskript umleitet oder nur
historische Ergebnisse gelesen werden können, zählt nicht als Funktionsparität.
Eine Funktion wird nicht ohne explizite Maintainer-Entscheidung ausgenommen.

Der Umfang schließt Quellen-/Anforderungs-Lifecycle und DCR, bisherige
DevSecOps- und Architekturprüfungen, alle vorhandenen L1-Auswertungsarten,
Evidenz-/Ergebnis-Intake, Trust/Replay/Attestierungen, Reporting/Graph/Viewer,
Baseline-/Dokumentpublikation, Agentenreviews, Findings-/Maßnahmen-Lifecycle
sowie Installation, Dienste, Updates, Sicherung und Wiederherstellung ein.
Technische Funktionen und ihre erforderliche menschliche/operative Autorität
werden getrennt nachgewiesen. Alte Zustimmungen werden nicht automatisch neu
gebunden; fehlende Live-Zugänge dürfen nicht als implementierte Fähigkeit oder
bestandene Abnahme erscheinen.

## Umsetzung

- Anbieterneutrale gemeinsame Fachimplementierung mit expliziten SCM-, CI-,
  Evidence-, Veröffentlichungs- und sonstigen Providergrenzen.
- Alte V1-Ausführungspfade bleiben im erhaltenen Rückfallstand; V2 benötigt
  eigene Implementierung, explizite Produktbefehle und vollständige Paketierung.
- Private, instanzgebundene Arbeitsbereiche für Vorschläge/Ergebnisse; keine
  unbemerkte Änderung der installierten Quelle, Baseline oder offiziellen Indizes.
- Modelle, Policies, veröffentlichte Pakete/Tags, historische Ergebnisse und die
  fingerprintgeschützte persönliche Pilotabnahme werden nicht still geändert.
- Reproduzierbare Mac-/Linux-Kandidaten mit eigenem Zustand und Werkzeugen;
  bestehende Dienste, Entwürfe und Schlüssel bleiben erhalten.

## Abnahme und Referenztest

Das Paritätsinventar bindet die ursprünglichen V1-Dateien/Versionen. Zuordnen,
Implementieren, Installieren und fachlich Verifizieren sind getrennte Zustände.
Abschluss erfordert alle Funktionsbereiche und Betriebsabläufe; ein implementierter
Teilbereich oder bloß bestandene bestehende Unit-Tests genügen nicht.

`ha-CPsWMS` wird mit identischem festgehaltenem Commit, physischen Evidenzdateien,
Baseline-/Tool-Pins, Auswertungszeit und Prüfungskontext durch V1 und V2 geprüft.
Die derzeit gelesene Main-Revision ist `5c3b5cb50d2260bfbde736c9ac80667271406d99`.
Neuere Referenzläufe werden separat mit exakter Run-/Attempt-/Commit-/Hash-Bindung
aufgenommen. Ein Replay alter realer Artefakte bleibt als Replay datiert; ein
synthetischer Test wird nicht als frischer Consumer-Lauf bezeichnet.

Verglichen werden Kontroll-/Gate-Abdeckung, Status, Findings, Begründungen,
Evidenzbezug, Trust und resultierende Projektionen. Erlaubte Unterschiede wie
Hostpfade/Zeitstempel werden eng dokumentiert; Findings und unbewertete Kontrollen
werden nicht weg-normalisiert. Die bisherige portable Fünf-Kontrollen-Ansicht
ersetzt nicht die weiteren V1-Prüfungen. Keine Evidenz wird erfunden und kein
Schutz-/Approval-Gate zur Erreichung gleicher Ergebnisse abgeschwächt.

Vor jedem kohärenten Commit erfolgen gepinnte Gesamtvalidierung, passende
End-to-End-/Negativprüfungen, strenger Dokumentationsbuild und revisionsgebundene
Review-Nachweise. Technische Lieferung sind reviewbare PRs und installierbare
Mac-/VM-Kandidaten mit einer vollständigen Paritätsbilanz. Erforderliche externe
Codeowner-/Governance-Freigaben bleiben sichtbar; unabhängige Arbeit läuft weiter.
