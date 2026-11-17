"""Finite original review-plan layout and release-classification compatibility."""
from copy import deepcopy

PROFILES = ('legacy-role-review-v1',)
POLICY = {
    'common_contracts': ['.agents/review-protocol.yaml', '.agents/routing/governance-agent-routing.yaml',
        'AGENTS.md', 'docs/governance/governance-roles-and-agent-profiles.md',
        'scripts/lib/agent_review.py', 'scripts/lib/agent_routing.py', 'scripts/dispatch_governance_agents.py'],
    'optional_contracts': ['.agents/execution-contract.yaml', '.agents/providers/codex/README.md'],
    'optional_role_contract': '.codex/agents/{role}.toml',
    'release_candidate_prefixes': ['policies/opa/', 'schemas/', '.github/workflows/',
        'docs/operations/evidence/architecture-evidence', 'docs/operations/evidence/application-repo-architecture',
        'pipeline-baseline/templates/app-architecture-evidence/', 'scripts/collect_architecture_release_input.py',
        'scripts/generate_architecture_governance_report.py', '.agents/', '.codex/agents/', '.github/codex/',
        'scripts/lib/agent_', 'scripts/dispatch_governance_agents.py', 'scripts/run_agent_reviews.py',
        'scripts/evaluate_agent_reviews.py', 'scripts/record_agent_review.py', 'scripts/report_agent_review_status.py',
        'tests/agent_harness/', 'scripts/validate_governance_repo.py', 'tests/test_repo_validation.py'],
    'model_prefixes': ['architecture/', 'model/controls/', 'model/platform/', 'model/traceability/',
        'model/evidence/', 'model/requirements/', 'model/governance/'],
}


def review_plan_profile(profile):
    if profile not in PROFILES: raise ValueError('unsupported_review_plan_profile')
    return deepcopy(POLICY)


def review_commit_profile(profile):
    if profile not in PROFILES: raise ValueError('unsupported_review_plan_profile')
    return {'roots': ['.agents/roles', '.agents/skills', '.agents/routing'],
        'patterns': [r'\.agents/roles/[a-z0-9-]+\.yaml', r'\.agents/skills/[a-z0-9-]+/SKILL\.md',
                     r'\.agents/routing/governance-agent-routing\.yaml'],
        'max_files': 200, 'max_file_bytes': 65536}
