# GitHub Reference Path

## Zweck

Der GitHub Reference Path ist die private, jederzeit testbare Referenzumgebung fuer dieses Governance-Repo.

Alle Erweiterungen fuer Firmenplattformen wie Bitbucket, Bamboo oder Jenkins muessen so gebaut werden, dass der bestehende GitHub-Pfad weiter funktioniert. GitHub ist damit nicht nur eine Beispielintegration, sondern die technische Referenzimplementierung fuer die End-to-End-Funktionalitaet.

## Referenzumgebung

| Bestandteil | Rolle |
|---|---|
| Governance-Repo | Zentrale Baselines, Policies, Schemas, Dokumentation, Status- und Evidence-Ablage. |
| GitHub Actions | Private Referenz-CI fuer Baseline-Ausfuehrung, Evidence-Erzeugung, Intake und Repo-Validierung. |
| `ha-CPsWMS` | Primaeres privates Applikationsrepo fuer reale End-to-End-Tests. |
| GitHub Pages | Referenzpfad fuer publizierte Governance-Dokumentation. |

## Architekturregel

GitHub bleibt der stabile Referenzpfad. Firmenplattformen werden als zusaetzliche Adapter ergaenzt.

Das bedeutet:

- GitHub Actions Workflows duerfen nicht durch Bamboo-, Bitbucket- oder Jenkins-spezifische Annahmen abhaengig gemacht werden.
- Gemeinsame Logik gehoert in neutrale Skripte, Schemas oder Datenmodelle.
- Plattformlogik gehoert in dedizierte Templates, Wrapper oder Adapter.
- Das normalisierte Evidence-JSON bleibt der verbindende Vertrag zwischen Applikationsrepo, Pipeline und Governance-Repo.
- `ha-CPsWMS` muss weiterhin als privater End-to-End-Testfall nutzbar bleiben.

## Was Stabil Bleiben Muss

Folgende Funktionen muessen nach jeder grundlegenden Aenderung weiterhin funktionieren:

1. Das Governance-Repo validiert seine strukturierten Quellen.
2. GitHub Actions kann die Governance-CI ausfuehren.
3. Ein Applikationsrepo kann die DevSecOps-Baseline per GitHub Actions nutzen.
4. Ein Applikationsrepo kann die Architektur-Governance per GitHub Actions nutzen.
5. Evidence wird maschinenlesbar erzeugt und in die vereinbarte JSON-Struktur ueberfuehrt.
6. Das Governance-Repo kann Evidence aufnehmen und Statusdateien aktualisieren.
7. Die Dokumentation kann mit MkDocs gebaut und ueber GitHub Pages publiziert werden.

## Definition Of Done Fuer Grundlegende Aenderungen

Eine grundlegende Aenderung am Governance-Kern ist erst fertig, wenn mindestens diese Nachweise vorliegen:

| Pruefung | Erwartung |
|---|---|
| Lokale Tests | `python3 -m pytest` ist erfolgreich. |
| Repo-Validierung | `python3 scripts/validate_governance_repo.py` ist erfolgreich. |
| Dokumentationsbuild | `mkdocs build --strict` ist erfolgreich, wenn Dokumentation oder Navigation geaendert wurde. |
| GitHub CI | Der Pull Request gegen `main` hat gruene GitHub Checks. |
| GitHub-Kompatibilitaet | Bestehende GitHub Actions Templates, Reusable Workflows und Intake-Skripte bleiben nutzbar. |

Bei Aenderungen an Pipeline-Templates, Evidence-Vertraegen oder Intake-Logik soll zusaetzlich ein End-to-End-Test mit `ha-CPsWMS` erfolgen.

Das konkrete Vorgehen ist im GitHub Reference Validation Runbook beschrieben:

```text
docs/operations/adapters/github-reference-validation-runbook.md
```

## Regeln Fuer Firmenadapter

Firmenadapter duerfen Plattformdetails kapseln, aber nicht den Governance-Kern veraendern.

Erlaubt:

- eigene Templates fuer Bamboo, Bitbucket Pipelines oder Jenkins
- Wrapper, die Plattformvariablen in das gemeinsame Evidence-Format uebersetzen
- normalisierte Plattformkontexte, wenn sie optional bleiben
- Dokumentation fuer Firmenplattformen als eigener Operations- oder Adapterpfad

Nicht erlaubt:

- GitHub-spezifische Funktionalitaet entfernen, um Firmenplattformen einfacher zu machen
- Evidence-Schemas ohne Rueckwaertskompatibilitaet brechen
- gemeinsame Skripte hart an Bamboo, Jenkins oder Bitbucket koppeln
- `ha-CPsWMS` als privaten Testpfad entwerten

## Praktischer Arbeitsmodus

Neue Arbeit wird in zwei Schichten gedacht:

| Schicht | Ziel |
|---|---|
| Governance-Kern | Plattformneutrale Regeln, Schemas, Evidence-Vertrag, Auswertung und Dokumentation. |
| Plattformadapter | GitHub Actions, Bamboo, Bitbucket oder Jenkins spezifische Ausfuehrung und Variablenuebersetzung. |

Der GitHub-Adapter ist die erste und wichtigste konkrete Implementierung. Weitere Adapter muessen sich daran messen lassen, ob sie denselben Governance-Kern und denselben Evidence-Vertrag verwenden koennen.
