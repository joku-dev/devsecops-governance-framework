# ADR-DCR-001 — Quellenidentität und Grenzen der Dokumentenprüfung

- **Status:** Phase 0 angenommen; Phase 1 nicht begonnen
- **Entscheidungsdatum:** 2026-10-07
- **Repository-Basis:** `a8fc36f3de7f33cd2a26dff94f9a28985e78d64f`
**Änderungsantrag:** [GCR-2026-116](../../governance/change-requests/GCR-2026-116-document-consistency-review.md)

## Entscheidung

1. **Quellenumfang:** Der Pilot startet mit den registrierten Auszügen
   `DSCB-STD-REQ-001` und `PRA-STD-REQ-001` sowie synthetischen Fixtures.
   Er prüft weder die vollständigen Originaldokumente noch leitet er Controls,
   Architekturmarker, Policies, Schemas oder Baselines daraus ab.
2. **Quellenregister:**
   `model/documents/source-document-register.yaml` bleibt das einzige
   maßgebliche Quellenregister. Das Phase-0-Manifest ist ein unveränderlicher
   Snapshot ausgewählter Registerdaten und Dateihashes, kein zweites Register.
3. **Lokale Dokumente:** Fünf zusätzlich lokal bereitgestellte Dateien bleiben
   unregistriert, lokal und außerhalb des Piloten. Sie werden nicht in das
   Manifest aufgenommen oder in Phase 0 inhaltlich ausgewertet.
4. **Routing:** Owner-Angaben dienen ausschließlich dazu, Reviews an die
   passenden Rollen weiterzuleiten. Sie bestätigen weder Quellenautorität noch
   eine fachliche oder normative Freigabe.
5. **Semantik und Provider:** Es findet kein semantischer Review und kein
   externer Provideraufruf statt. Ein semantischer Status bleibt `not_run`, bis
   Quellenumfang, Datenfluss, Provider, Aufbewahrung und zulässige Auszüge
   separat freigegeben sind.
6. **Viewer:** Phase 0 veröffentlicht keine Viewer-Ansicht und führt keine
   Quelleninhalte in eine öffentliche Projektion über.
7. **Phasengrenze:** Phase 0 umfasst Inventar, Entscheidungsprotokoll und
   Quellenmanifest. Schema, Generator, deterministische Prüfungen und Tests
   werden separat als Phase 1 vorgelegt.
8. **Lifecycle-Schutz:** Die in
   `model/governance/lifecycle/operating-acceptance/00000001.json`
   fingerprinteten Dateien bleiben unberührt.

## Aktueller Quellenstand

Die Repository-Basis ist Commit `a8fc36f3de7f33cd2a26dff94f9a28985e78d64f`.
Der Register-Snapshot hat SHA-256
`bbc54e21f2e33c0b7406ad33c0fe2084c5dfb6795b4bbdee1a11b883546c052a`.
Das maschinenlesbare Phase-0-Manifest bindet die beiden ausgewählten
Registereinträge an ihre Pfade, Status, Versionen, Owner-Routing und exakten
Dateihashes.

Die fünf lokalen Dateien sind im Maintainer-Checkout vorhanden, aber nicht
Bestandteil dieses Repository-Commits und nicht im Quellenregister. Für diese
Phase gilt daher: lokal vorhanden, nicht registriert, nicht autorisiert und
nicht im Pilotumfang. Ihre Inhalte und Dateinamen werden nicht in das
Repository-Manifestsnapshot übernommen.

## Konsequenzen und Grenzen

- Das Manifest belegt nur, welche registrierten Bytes ausgewählt wurden.
  Es belegt keine semantische Konsistenz, Quellenautorität, Umsetzung oder
  Compliance.
- Die Entscheidung nimmt Phase 0 ab, aber genehmigt keine der fünf lokalen
  Quellen und ändert keine bestehende Quellen- oder Baselinefreigabe.
- Phase 1 benötigt einen eigenen Änderungssatz und eine eigene Prüfung.
- Ein semantischer Pilot, Viewer-Integration, Quellenpromotion und
  Veröffentlichung bleiben separate spätere Entscheidungen.
