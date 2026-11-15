# GCR-2026-173 — Portable Runtime M1 candidate

## Auftrag und Klassifikation

Der Maintainer beauftragt am 15. November 2026 die Fortsetzung des
Portability-Plans auf Basis des freigegebenen Goal-PR #368. Die Umsetzung erfolgt
auf dessen Commit `bf9aa3045382963bcbe53eeb29e54a49823a8312`; PR #368 ist ein
separater Dokumentations-PR. Diese Lieferung ist ein überprüfbarer M1-Kandidat
und keine Aussage, dass das Gesamtgoal oder M2 abgeschlossen ist.

| Feld | Einordnung |
|---|---|
| Artefakte | Neue Runtime/Adapter mit versionierter Baseline-Kompatibilitätsmatrix, Kontext-/Profil-/Ergebnisschemas, CI-Einstiege, Regressionen und technische Dokumentation |
| Typ | Ausführbare Governance-Integration und Evidence-Verträge; technische Ableitung bestehender Baseline |
| Full Source Document Intake | Nein; keine neue normative Quelle und kein Register-/Quellenwechsel |
| Fachlicher Umfang | Pipeline-L1-Prüfumfang, fünf zugeordnete Controls; übrige Controls ausdrücklich nicht ausgewertet |
| Baseline/Policy | Bestehende checksum-geprüfte L1-v1.1.3-Paketdateien und Rego unverändert |
| Verhalten | Neuer optionaler versionierter Pfad; Findings report-only, Pflichtlücken/Toolfehler technisch unvollständig/fehlerhaft |
| Schnittstellen | Additive v1-Kontext-, Profil- und Ergebnisverträge; keine Änderung offizieller Status-/Trust-/Ledgerformate |
| Release | Runtime-Kandidat zur expliziten Adoption; keine Veröffentlichung, kein Tag und keine neue Baseline |
| Migration | Neue GitLab-/Bamboo-Quelltemplates benötigen vorbereitete Runtime, geprüfte Profile und echte Evidenz; alte gepinnte Stände bleiben reproduzierbar |
| Betriebswirkung | Keine Consumer-Konfiguration, VM, Credentials, Routing- oder Publisher-Aktivierung geändert |
| Reviews | Governance, DevSecOps, Policy, Evidence, Release; Repo Steward zuletzt als deklarierte Rollenperspektiven |

## Verhalten und Nachweise

Der neue gemeinsame Prüfer korrigiert im neuen Pfad die Erfolgsannahme bei
unbekanntem Pflichtkontext, ignorierten Scannerfehlern und bloß angefordertem
Blocking. Kontext, tatsächlicher Checkout, Artefaktdigests, Baseline und
Runtime sind getrennt gebunden. Synthetische Fixtures sind kein Live-Nachweis;
Trust bleibt unverified, die externe Merge-Durchsetzung nicht verifiziert.

[ADR-PORT-001](../../operations/planning/portable-governance-runtime-adr.md) und
die [Betriebs-/Integrationsanleitung](../../operations/adapters/portable-governance-runtime.md)
beschreiben CLI, Profile, Exitcodes, Plattformgrenzen und Migration.

Die Abnahme umfasst Vertrags-, Negativ-, native Adapter- und echte OPA-Tests,
Entscheidungsparität über drei Providerkontexte, die vorgeschriebene
Gesamtvalidierung sowie Diff-/Baseline-/Fingerprint- und Dokumentationsprüfung.
Fehlende reale GitLab-/Bamboo-Systeme verhindern keine lokale Prüfung; deren
Versionen, Syntaximport, native Run-/Artefaktprovenienz und Live-Durchsetzung
bleiben als konkrete externe Nachweise offen.

M2 muss gemeinsame Evidenzverifikation, providergebundene Persistenz/Migration,
zentrale Operationsadapter und VM-Integration einschließlich Recovery und
Kapazitätsmessungen liefern. Architektur-Governance bleibt geparkt. Dieser PR
beansprucht keine Betriebs-, Blocking- oder Kapazitätsfreigabe.
