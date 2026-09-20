# GitHub-Checks des privaten Draft-PRs

Beobachtet am 20. September 2026 für PR #176, Stand `6d1a3ba`.
Die lokalen Nachweise in diesem Verzeichnis bestanden; die GitHub-Checks waren
zu diesem Zeitpunkt nicht vollständig grün. Der PR bleibt deshalb ein Draft.

* [Dependency Review, Lauf 35504297952](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/35504297952):
  GitHub meldet, dass Dependency Review für dieses Repository nicht unterstützt
  wird, und verweist auf Dependency Graph/GitHub Advanced Security.
* [Consumer Lifecycle Guard, Lauf 35504297724](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/35504297724):
  Der bestehende Workflow erhält HTTP 404 beim Lesen der früheren
  Provider-Diskussion `issues/101`. Der verwendete CI-Zugriff muss separat geprüft
  werden; der erfolgreiche persönliche lokale API-Zugriff ersetzt dieses Secret
  nicht.
* Governance CI und CodeQL waren bei dieser Erfassung noch in Bearbeitung.
  Ein späteres Ergebnis ist unmittelbar am PR nachzusehen.

Diese Beobachtung ist keine Ausnahmegenehmigung für fehlgeschlagene Checks und
kein Grund, das Repository öffentlich zu machen. Die betreffenden bestehenden
Provider-/CI-Grenzen wurden für den Prototyp nicht abgeschwächt. Der Prototyp und
sein eigenständiger Evidence-Prüfer sind lokal ausführbar; sein erfolgreicher
Funktionsnachweis ist getrennt vom GitHub-Merge-Status zu bewerten.
