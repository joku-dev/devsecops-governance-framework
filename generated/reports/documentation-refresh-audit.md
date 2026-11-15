# Dokumentationsabgleich nach Merge

Auslöser: PR #375: Add provider assurance candidates and portable migration recovery (`4fe95869face`)

## Ergebnis

- Lokale Markdown-Linkprüfung: 2 fehlende lokale Markdown-Zielpfade.
- `mkdocs build --strict`: passed.
- Der PR-Inhalt stammt aus der PR-Zusammenfassung und den geänderten Pfaden; fachliche Bedeutung und Querverweise benötigen menschliche Prüfung.

## Betroffene Implementierungspfade

- `.agents/routing/governance-agent-routing.yaml`
- `.github/workflows/codeql.yml`
- `.github/workflows/dependency-review.yml`
- `.github/workflows/devsecops-portable-v1.yml`
- `.github/workflows/governance-repository-security.yml`
- `.github/workflows/portable-capacity.yml`
- `.github/workflows/runtime-package.yml`
- `.github/workflows/vm-installation.yml`
- `pipeline-baseline/templates/bamboo/README.md`
- `pipeline-baseline/templates/bamboo/bamboo-specs/bamboo.yaml`
- `pipeline-baseline/templates/gitlab-ci/.gitlab-ci.yml`
- `pipeline-baseline/templates/portable/github-actions/consumer.yml`
- `schemas/intake-candidate-v1.schema.json`
- `schemas/portable-consumer-registry-v1.schema.json`
- `schemas/portable-consumer-service-v1.schema.json`
- `schemas/portable-context-v1.schema.json`
- `schemas/portable-intake-bundle-v2.schema.json`
- `schemas/portable-intake-policy-v2.schema.json`
- `schemas/portable-intake-receipt-v2.schema.json`
- `schemas/portable-profile-v1.schema.json`
- `schemas/portable-result-v1.schema.json`
- `schemas/provider-role-candidate-v1.schema.json`
- `schemas/runtime-package-v1.schema.json`
- `scripts/deploy_vm.py`
- `scripts/generate_portable_candidate_index.py`
- `scripts/governance_runtime.py`
- `scripts/intake_portable_evidence.py`
- `scripts/lib/consumer_intake_store.py`
- `scripts/lib/portable/__init__.py`
- `scripts/lib/portable/adapters.py`
- `scripts/lib/portable/contracts.py`
- `scripts/lib/portable/runtime.py`
- `scripts/lib/portable_intake/__init__.py`
- `scripts/lib/portable_intake/assurance.py`
- `scripts/lib/portable_intake/bundle.py`
- `scripts/lib/portable_intake/candidate_index.py`
- `scripts/lib/portable_intake/controller.py`
- `scripts/lib/portable_intake/operations.py`
- `scripts/lib/portable_intake/publisher.py`
- `scripts/lib/portable_intake/store.py`
- `scripts/lib/portable_intake/transport.py`
- `scripts/lib/runtime_package.py`
- `scripts/observe_provider_assurance.py`
- `scripts/package_governance_runtime.py`
- `scripts/portable_consumer_intake.py`
- `scripts/serve_governance_workbench.py`
- `scripts/workbench/consumer-view.js`

## Fehlende lokale Markdown-Ziele

- `README.md` → `/picture`
- `pipeline-baseline/templates/bamboo/README.md` → `../../../../docs/operations/adapters/portable-governance-runtime.md`

## Redaktionelle Prüfpunkte

- README-Einstieg und Funktionsumfang aktualisieren.
- Funktion fachlich im Katalog dem passenden Bereich zuordnen und Eingaben, Ablauf, Ergebnisse sowie Grenzen beschreiben.
- Technische Inventareinträge und Navigations-/Querverweise ergänzen.
- Prüfen, ob Foundation, Governance-, Demo-, Release- oder Consumer-Dokumentation betroffen ist.
