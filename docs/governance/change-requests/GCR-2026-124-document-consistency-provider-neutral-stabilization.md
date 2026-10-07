# GCR-2026-124: Providerneutrale Stabilisierung des semantischen Reviews

## Zweck und Einordnung

Der schemaungültig abgewiesene Pilotlauf aus `GCR-2026-123` zeigte eine Lücke
zwischen providerseitig erzeugbarer strukturierter Ausgabe und dem
maßgeblichen Repositoryvertrag. Dieser Änderungssatz schließt diese technische
Lücke providerneutral. Er verändert keine Governance-Anforderung und führt
keinen Provider aus.

## Umsetzung

- Ein enges Provider-Projektionsschema vermeidet die im Pilot beobachteten
  inkompatiblen Schemaelemente `oneOf`, `uniqueItems` und `const`.
- Ein deterministischer Adapter ergänzt ausschließlich Laufmetadaten und
  überführt die Projektion in den unveränderten maßgeblichen Antwortvertrag.
- Die bekannte Verwechslung von `context_missing` beziehungsweise
  `not_assessable` mit dem Feld `applicability.status` wird nur bei
  widerspruchsfreier Bedeutung normalisiert und sichtbar protokolliert.
- Widersprüchliche Zustände, unbekannte Werte und mehrdeutige Suchscopes werden
  fail-closed verworfen.
- Die aktive Adapterkonfiguration `dcr-adapter-0001` ist providerneutral.
  Provider, Modell und Promptversion müssen bei jedem Lauf explizit gebunden
  werden; dadurch wird kein Provider freigegeben.

## Entscheidungsgrenze

Die Adapterausgabe bleibt untrusted. Erst der bestehende Repositoryvalidator
prüft das maßgebliche Schema, Manifest, Quellenhashes, Fundstellen und exakte
Kurzbelege. Normalisierung bestätigt weder Interpretation noch Finding.

Der Änderungssatz autorisiert keinen weiteren Live-Lauf, keine menschliche
Finding-Bestätigung, keine Veröffentlichung und keinen Rollout. Die
Rolloutentscheidung bleibt `pending`.

## Auswirkung

- Quellenregister und Quellenstatus: unverändert
- Controls, OPA und Architekturmarker: unverändert
- Released Baselines: unverändert
- Consumer-Repositories: unverändert
- Viewer und Veröffentlichung: unverändert
- Enforcement: report-only; kein neues Gate

## Rollen

- Governance Analyst: technische Folgearbeit aus dem Pilotbefund abgegrenzt.
- Repo Steward: fokussierter Änderungssatz und vollständige Validierung.
