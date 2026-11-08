"""Compatibility imports for historical agent-harness scenarios.

The implementation lives in the production library, not in the test harness.
"""
from scripts.lib.agent_routing import (
    AGENT_SYSTEM_PREFIXES, AGENT_VALIDATIONS, ARCHITECTURE_EVIDENCE_PREFIXES,
    CORE_AGENTS, DERIVED_GOVERNANCE_PREFIXES, EVIDENCE_CONTEXTS, REPO_STEWARD,
    ROOT, ROUTING_CONTRACT, ROUTING_RULES, RoutingRule, classify_release_impact,
    evaluate_scenario, has_forbidden_candidate_derivation, load_routing_rules,
    normalize_path, parse_inline_list, route_agents, validations_for_agents,
)
