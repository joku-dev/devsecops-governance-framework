from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


REPO_STEWARD = "repo-steward"
ROOT = Path(__file__).resolve().parents[2]
ROUTING_CONTRACT = ROOT / ".agents" / "routing" / "governance-agent-routing.yaml"

CORE_AGENTS = {
    "source-document-intake",
    "governance-analyst",
    "architecture-runtime-governance",
    "devsecops-baseline",
    "policy-as-code",
    "evidence-and-intake",
    "release-manager",
    "demo-readiness",
    REPO_STEWARD,
}

AGENT_VALIDATIONS = {
    "architecture-runtime-governance": {
        "python3 scripts/validate_runtime_governance.py",
    },
    "devsecops-baseline": {
        "python3 scripts/validate_governance_repo.py",
    },
    "evidence-and-intake": {
        "python3 scripts/validate_governance_repo.py",
        "python3 scripts/generate_status_viewer.py",
    },
    "release-manager": {
        "python3 scripts/validate_governance_repo.py",
        "python3 -m unittest discover -s tests",
    },
    "policy-as-code": {
        "opa check policies/opa",
        "python3 -m unittest discover -s tests",
    },
    "repo-steward": {
        "git diff --check",
    },
    "source-document-intake": {
        "python3 scripts/generate_source_document_intake_status.py",
        "python3 scripts/generate_source_document_intake_review_briefs.py",
        "python3 scripts/generate_source_document_requirement_delta.py",
        "python3 scripts/generate_governance_change_impact_report.py",
        "python3 scripts/validate_governance_repo.py",
    },
    "governance-analyst": {
        "python3 scripts/validate_governance_repo.py",
    },
    "demo-readiness": {
        "python3 scripts/run_demo.py",
        "python3 scripts/generate_status_viewer.py",
    },
}


@dataclass(frozen=True)
class RoutingRule:
    prefix: str
    agents: frozenset[str]


def parse_inline_list(value: str) -> frozenset[str]:
    stripped = value.strip()
    if not stripped.startswith("[") or not stripped.endswith("]"):
        raise ValueError(f"Expected inline YAML list, got: {value}")
    items = [item.strip() for item in stripped[1:-1].split(",") if item.strip()]
    return frozenset(items)


def load_routing_rules(path: Path = ROUTING_CONTRACT) -> tuple[RoutingRule, ...]:
    rules: list[RoutingRule] = []
    current_prefix: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- path_prefix:"):
            current_prefix = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("agents:"):
            if current_prefix is None:
                raise ValueError(f"agents entry without path_prefix in {path}")
            rules.append(RoutingRule(current_prefix, parse_inline_list(stripped.split(":", 1)[1])))
            current_prefix = None
    if not rules:
        raise ValueError(f"No routing rules found in {path}")
    return tuple(rules)


ROUTING_RULES = load_routing_rules()

DERIVED_GOVERNANCE_PREFIXES = (
    "architecture/",
    "model/controls/",
    "policies/opa/",
    "releases/",
    "schemas/",
)
ARCHITECTURE_EVIDENCE_PREFIXES = (
    "docs/operations/evidence/architecture-evidence",
    "docs/operations/evidence/application-repo-architecture",
    "pipeline-baseline/templates/app-architecture-evidence/",
    "scripts/collect_architecture_release_input.py",
    "scripts/generate_architecture_governance_report.py",
)
AGENT_SYSTEM_PREFIXES = (
    ".agents/routing/",
    ".agents/roles/",
    ".agents/skills/",
    ".agents/providers/",
    "tests/agent_harness/",
)
REPO_VALIDATION_PREFIXES = (
    "scripts/validate_governance_repo.py",
    "tests/test_repo_validation.py",
)

EVIDENCE_CONTEXTS = {"mainline", "branch", "pull_request", "manual"}


def normalize_path(path: str) -> str:
    normalized = path
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def route_agents(changed_files: list[str]) -> set[str]:
    selected: set[str] = set()
    normalized_paths = [normalize_path(path) for path in changed_files]
    for path in normalized_paths:
        for rule in ROUTING_RULES:
            if path.startswith(rule.prefix):
                selected.update(rule.agents)
    if normalized_paths:
        selected.add(REPO_STEWARD)
    return selected


def validations_for_agents(agents: set[str]) -> set[str]:
    validations: set[str] = set()
    for agent in agents:
        validations.update(AGENT_VALIDATIONS.get(agent, set()))
    return validations


def classify_release_impact(changed_files: list[str]) -> str:
    paths = [normalize_path(path) for path in changed_files]
    if any(path.startswith("releases/") for path in paths):
        return "released_baseline"
    if any(path.startswith(("policies/opa/", "schemas/", ".github/workflows/")) for path in paths):
        return "candidate"
    if any(path.startswith(ARCHITECTURE_EVIDENCE_PREFIXES) for path in paths):
        return "candidate"
    if any(path.startswith(AGENT_SYSTEM_PREFIXES) for path in paths):
        return "candidate"
    if any(path.startswith(REPO_VALIDATION_PREFIXES) for path in paths):
        return "candidate"
    if any(path.startswith(("architecture/", "model/controls/")) for path in paths):
        return "governance_model"
    return "none"


def has_forbidden_candidate_derivation(changed_files: list[str]) -> bool:
    paths = [normalize_path(path) for path in changed_files]
    return any(path.startswith(DERIVED_GOVERNANCE_PREFIXES) for path in paths)


def evaluate_scenario(scenario: dict) -> dict:
    changed_files = scenario.get("changed_files", [])
    agents = route_agents(changed_files)
    validations = validations_for_agents(agents)
    return {
        "selected_agents": sorted(agents),
        "required_validations": sorted(validations),
        "release_impact": classify_release_impact(changed_files),
        "candidate_derivation_detected": has_forbidden_candidate_derivation(changed_files),
    }
