# Dokumentationsabgleich nach Merge

Auslöser: PR #334: feat: add accountable governance agent review workflow (`dfd374cd2051`)

## Ergebnis

- Lokale Markdown-Linkprüfung: 1 fehlende lokale Markdown-Zielpfade.
- `mkdocs build --strict`: passed.
- Der PR-Inhalt stammt aus der PR-Zusammenfassung und den geänderten Pfaden; fachliche Bedeutung und Querverweise benötigen menschliche Prüfung.

## Betroffene Implementierungspfade

- `.agents/providers/mistral/governance-agent-dispatch.prompt.md`
- `.agents/providers/mistral/role-execution-contract.md`
- `.agents/review-protocol.yaml`
- `.agents/roles/architecture-runtime-governance.yaml`
- `.agents/roles/demo-readiness.yaml`
- `.agents/roles/devsecops-baseline.yaml`
- `.agents/roles/evidence-and-intake.yaml`
- `.agents/roles/governance-analyst.yaml`
- `.agents/roles/policy-as-code.yaml`
- `.agents/roles/release-manager.yaml`
- `.agents/roles/repo-steward.yaml`
- `.agents/roles/source-document-intake.yaml`
- `.agents/routing/governance-agent-routing.yaml`
- `.agents/skills/repo-steward/SKILL.md`
- `.codex/agents/architecture-runtime-governance.toml`
- `.codex/agents/demo-readiness.toml`
- `.codex/agents/devsecops-baseline.toml`
- `.codex/agents/evidence-and-intake.toml`
- `.codex/agents/governance-analyst.toml`
- `.codex/agents/policy-as-code.toml`
- `.codex/agents/release-manager.toml`
- `.codex/agents/repo-steward.toml`
- `.codex/agents/source-document-intake.toml`
- `scripts/dispatch_governance_agents.py`
- `scripts/lib/agent_review.py`
- `scripts/lib/agent_routing.py`

## Fehlende lokale Markdown-Ziele

- `README.md` → `/picture`

## Redaktionelle Prüfpunkte

- README-Einstieg und Funktionsumfang aktualisieren.
- Funktion fachlich im Katalog dem passenden Bereich zuordnen und Eingaben, Ablauf, Ergebnisse sowie Grenzen beschreiben.
- Technische Inventareinträge und Navigations-/Querverweise ergänzen.
- Prüfen, ob Foundation, Governance-, Demo-, Release- oder Consumer-Dokumentation betroffen ist.
