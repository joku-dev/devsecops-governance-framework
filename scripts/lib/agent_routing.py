"""Production routing from model-neutral role, skill and path contracts."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import yaml


REPO_STEWARD = "repo-steward"
ROOT = Path(__file__).resolve().parents[2]
ROUTING_CONTRACT = ROOT / ".agents" / "routing" / "governance-agent-routing.yaml"


class ContractLoader(yaml.SafeLoader):
    """Reject duplicate mapping keys rather than silently replacing role rules."""


def _unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in mapping:
            raise ValueError("Agent contracts require unique string mapping keys")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


ContractLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def load_yaml(path: Path) -> dict:
    try:
        return yaml.load(path.read_text(encoding="utf-8"), Loader=ContractLoader)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid agent contract {path}: {exc}") from exc


def string_list(values) -> bool:
    return isinstance(values, list) and bool(values) and all(isinstance(x, str) and x.strip() for x in values)


def load_role_contracts(root: Path = ROOT) -> dict[str, dict]:
    roles = {}
    for path in sorted((root / ".agents/roles").glob("*.yaml")):
        role = load_yaml(path)
        if not isinstance(role, dict) or role.get("id") != path.stem:
            raise ValueError(f"Invalid role identity: {path}")
        for field in ("id", "name", "description", "source_of_truth", "skill"):
            if not isinstance(role.get(field), str) or not role[field].strip():
                raise ValueError(f"{path}: missing {field}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", role["skill"]):
            raise ValueError(f"{path}: invalid skill identifier")
        skill = root / ".agents/skills" / role["skill"] / "SKILL.md"
        if not skill.is_file():
            raise ValueError(f"{path}: missing skill {skill}")
        for field in ("primary_files", "responsibilities", "validations", "output_contract"):
            values = role.get(field)
            if not string_list(values):
                raise ValueError(f"{path}: {field} must be a nonempty string list")
        roles[role["id"]] = role
    if REPO_STEWARD not in roles:
        raise ValueError("repo-steward role is required")
    return roles


ROLE_CONTRACTS = load_role_contracts()
CORE_AGENTS = set(ROLE_CONTRACTS)
AGENT_VALIDATIONS = {name: set(role["validations"]) for name, role in ROLE_CONTRACTS.items()}


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


def load_routing_contract(path: Path = ROUTING_CONTRACT, *, known_agents=None) -> dict:
    known_agents = CORE_AGENTS if known_agents is None else set(known_agents)
    data = load_yaml(path)
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list) or not data["rules"]:
        raise ValueError(f"No routing rules found in {path}")
    always = data.get("always_select")
    if not string_list(always) or REPO_STEWARD not in always or set(always) - known_agents:
        raise ValueError(f"{path}: always_select must include known repo-steward role")
    if "fallback" in data:
        fallback = data["fallback"]
        if not isinstance(fallback, dict) or not string_list(fallback.get("path_prefixes")) or not string_list(fallback.get("agents")) or set(fallback["agents"]) - known_agents:
            raise ValueError(f"{path}: invalid fallback routing")
        for prefix in fallback["path_prefixes"]:
            if normalize_path(prefix) != prefix or not prefix.endswith("/"):
                raise ValueError(f"{path}: fallback prefixes must be canonical directories")
    prefixes = set()
    for rule in data["rules"]:
        if not isinstance(rule, dict) or not isinstance(rule.get("path_prefix"), str):
            raise ValueError(f"{path}: rule requires path_prefix")
        prefix = rule["path_prefix"]
        if normalize_path(prefix) != prefix:
            raise ValueError(f"{path}: routing prefix is not canonical: {prefix}")
        if prefix in prefixes:
            raise ValueError(f"{path}: duplicate prefix {prefix}")
        prefixes.add(prefix)
        agents = rule.get("agents")
        if not string_list(agents) or set(agents) - known_agents:
            raise ValueError(f"{path}: unknown or empty role selection for {prefix}")
    return data


def load_routing_rules(path: Path = ROUTING_CONTRACT) -> tuple[RoutingRule, ...]:
    return tuple(RoutingRule(rule["path_prefix"], frozenset(rule["agents"])) for rule in load_routing_contract(path)["rules"])



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
    ".agents/",
    ".codex/agents/",
    ".github/codex/",
    "scripts/lib/agent_",
    "scripts/dispatch_governance_agents.py",
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
    if not isinstance(path, str) or not path or "\x00" in path or "\\" in path:
        raise ValueError("Changed paths must be nonempty repository-relative POSIX paths")
    if path.startswith("/") or re.match(r"^[A-Za-z]:", path) or ".." in path.split("/"):
        raise ValueError(f"Path must stay inside the repository: {path!r}")
    normalized = "/".join(part for part in path.split("/") if part and part != ".")
    if not normalized:
        raise ValueError("Empty repository path")
    return normalized + ("/" if path.endswith("/") else "")


# Load once, after path validation is available. Tests and CLI share this runtime.
ROUTING_DATA = load_routing_contract()
ROUTING_RULES = load_routing_rules()


def routing_reasons(changed_files: list[str]) -> dict[str, list[str]]:
    return routing_reasons_for_contract(changed_files, ROUTING_DATA, ROUTING_RULES)


def routing_reasons_for_contract(changed_files: list[str], data: dict, rules=None) -> dict[str, list[str]]:
    """Apply the same routing to a validated, data-only contract snapshot."""
    rules = rules if rules is not None else tuple(RoutingRule(r["path_prefix"], frozenset(r["agents"])) for r in data["rules"])
    paths = sorted({normalize_path(path) for path in changed_files})
    reasons: dict[str, set[str]] = {}
    if paths:
        for agent in data["always_select"]:
            reasons.setdefault(agent, set()).add("always_select")
    for path in paths:
        matched = False
        for rule in rules:
            if path.startswith(rule.prefix):
                matched = True
                for agent in rule.agents:
                    reasons.setdefault(agent, set()).add(rule.prefix)
        fallback = data.get("fallback", {})
        if not matched and any(path.startswith(prefix) for prefix in fallback.get("path_prefixes", [])):
            for agent in fallback["agents"]:
                reasons.setdefault(agent, set()).add("fallback: unclassified functional path")
    return {agent: sorted(values) for agent, values in sorted(reasons.items())}


def route_agents(changed_files: list[str]) -> set[str]:
    return set(routing_reasons(changed_files))


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
    if any(path.startswith(("architecture/", "model/controls/", "model/platform/", "model/traceability/",
                            "model/evidence/", "model/requirements/", "model/governance/")) for path in paths):
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
