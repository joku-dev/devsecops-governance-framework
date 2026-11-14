import tempfile
import unittest
from pathlib import Path

from tests.agent_harness.routing import REPO_STEWARD, ROUTING_CONTRACT, load_routing_rules, route_agents


class AgentRoutingTests(unittest.TestCase):
    def test_routing_matrix_selects_required_agents(self):
        cases = {
            ".agents/routing/governance-agent-routing.yaml": {
                "governance-analyst",
                "release-manager",
                REPO_STEWARD,
            },
            ".agents/providers/mistral/README.md": {
                "governance-analyst",
                "release-manager",
                REPO_STEWARD,
            },
            "tests/agent_harness/routing.py": {
                "governance-analyst",
                "release-manager",
                REPO_STEWARD,
            },
            "docs/governance/source-documents/new-source.md": {
                "source-document-intake",
                "governance-analyst",
                REPO_STEWARD,
            },
            "model/controls/dscb-l1.yaml": {
                "devsecops-baseline",
                "governance-analyst",
                REPO_STEWARD,
            },
            "architecture/review-gates.yaml": {
                "architecture-runtime-governance",
                "policy-as-code",
                REPO_STEWARD,
            },
            "docs/operations/evidence/architecture-evidence-type-taxonomy.md": {
                "architecture-runtime-governance",
                "evidence-and-intake",
                REPO_STEWARD,
            },
            "pipeline-baseline/templates/app-architecture-evidence/.governance/architecture/threat-model.json": {
                "architecture-runtime-governance",
                "evidence-and-intake",
                REPO_STEWARD,
            },
            "scripts/collect_architecture_release_input.py": {
                "architecture-runtime-governance",
                "evidence-and-intake",
                "release-manager",
                REPO_STEWARD,
            },
            "scripts/validate_governance_repo.py": {
                "governance-analyst",
                "release-manager",
                REPO_STEWARD,
            },
            "policies/opa/vulnerability_gate.rego": {
                "policy-as-code",
                "release-manager",
                REPO_STEWARD,
            },
            "schemas/governance-run-input.schema.json": {
                "evidence-and-intake",
                "release-manager",
                REPO_STEWARD,
            },
            "status/repository-results-index.json": {
                "evidence-and-intake",
                "demo-readiness",
                REPO_STEWARD,
            },
            "releases/l1/v1.1.3/checksums.txt": {
                "release-manager",
                REPO_STEWARD,
            },
            "pipeline-baseline/templates/bamboo/bamboo-specs.yml": {
                "devsecops-baseline",
                "release-manager",
                REPO_STEWARD,
            },
            "pipeline-baseline/templates/bitbucket/bitbucket-pipelines.yml": {
                "devsecops-baseline",
                "release-manager",
                REPO_STEWARD,
            },
            "templates/ci/gitlab-ci-governance-check.yml": {
                "devsecops-baseline",
                "release-manager",
                REPO_STEWARD,
            },
        }

        for path, expected_agents in cases.items():
            with self.subTest(path=path):
                self.assertEqual(route_agents([path]), expected_agents)

    def test_repo_steward_is_selected_for_every_meaningful_change(self):
        selected = route_agents(["README.md"])
        self.assertEqual(selected, {REPO_STEWARD})

    def test_implementation_paths_keep_domain_reviews_without_generated_changes(self):
        evidence = {"evidence-and-intake", "demo-readiness", REPO_STEWARD}
        analyst = {"evidence-and-intake", "governance-analyst", REPO_STEWARD}
        lifecycle = analyst | {"release-manager"}
        cases = {
            "docs/demos/demo-end-to-end-governance.md": {"demo-readiness", REPO_STEWARD},
            "docs/operations/status/current-governance-platform-state.md": evidence,
            "generated/current-main/ha-cpswms/result.json": evidence,
            "scripts/lib/viewer_app.py": evidence,
            "scripts/lib/viewer_technical.py": evidence,
            "scripts/lib/viewer_experience.py": evidence,
            "scripts/lib/requirement_journey_view.py": evidence | {"governance-analyst"},
            "scripts/lib/governance_requirement_lifecycle_view.py": evidence | {"governance-analyst"},
            "scripts/lib/consumer_lifecycle_next_step.py": evidence | {"governance-analyst"},
            "scripts/generate_status_viewer.py": evidence,
            "scripts/intake_governance_result.py": analyst,
            "scripts/intake_ci_artifact_bundle.py": analyst,
            "scripts/intake_lifecycle_pilot_action.py": analyst,
            "scripts/intake_architecture_github_actions_run.py": analyst | {"architecture-runtime-governance"},
            "scripts/generate_repository_results_index.py": evidence,
            "scripts/generate_architecture_results_index.py": evidence | {"architecture-runtime-governance"},
            "scripts/generate_typed_evidence_results_index.py": evidence,
            "scripts/lib/result_ledger.py": lifecycle,
            "scripts/lib/governance_lifecycle/kernel.py": lifecycle,
            "model/governance/lifecycle/consumer-operation/profile.json": lifecycle,
            "policies/opa/architecture_release_readiness.rego": {
                "architecture-runtime-governance", "policy-as-code", "release-manager", REPO_STEWARD},
        }
        for path, roles in cases.items():
            with self.subTest(path=path):
                self.assertEqual(route_agents([path]), roles)

    def test_domain_rules_do_not_overroute_unrelated_docs_scripts_or_policies(self):
        for path, expected in {
            "docs/publishing/article.md": {REPO_STEWARD},
            "scripts/unclassified.py": {"governance-analyst", REPO_STEWARD},
            "policies/opa/vulnerability_gate.rego": {"policy-as-code", "release-manager", REPO_STEWARD},
        }.items():
            with self.subTest(path=path):
                self.assertEqual(route_agents([path]), expected)

    def test_empty_change_set_selects_no_agents(self):
        self.assertEqual(route_agents([]), set())

    def test_routing_rules_are_loaded_from_model_neutral_contract(self):
        rules = load_routing_rules(ROUTING_CONTRACT)
        prefixes = {rule.prefix for rule in rules}

        self.assertIn("policies/opa/", prefixes)
        self.assertIn("docs/governance/source-documents/", prefixes)

    def test_routing_contract_parser_rejects_empty_rule_files(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "empty-routing.yaml"
            path.write_text("rules: []\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                load_routing_rules(path)
