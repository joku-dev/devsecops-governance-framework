"""Behavioral regressions for real Git scopes and revision-bound review evidence."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.dispatch_governance_agents import build_dispatch
from scripts.lib import agent_routing
from scripts.lib.agent_review import changed_files, check_results, digest, prepare_plan, results_template


ROOT = Path(__file__).resolve().parents[2]


class ReviewExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / ".agents", self.root / ".agents")
        for name in ("AGENTS.md", "docs/governance/governance-roles-and-agent-profiles.md",
                     "scripts/lib/agent_review.py", "scripts/lib/agent_routing.py",
                     "scripts/dispatch_governance_agents.py"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        (self.root / "README.md").write_text("initial\n")
        self.git("init", "-b", "main")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-m", "fixture")
        (self.root / "README.md").write_text("changed\n")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, text=True, stderr=subprocess.DEVNULL)

    def plan(self, *, explicit=False, paths=None):
        paths = paths or changed_files(self.root)
        return prepare_plan(self.root, build_dispatch(paths), "Review a fixture change", explicit_paths=explicit)

    def completed(self, plan):
        results = results_template(plan)
        for task, review in zip(plan["reviews"], results["reviews"]):
            review.update(status="completed", executor="synthetic-test", provider="test", summary="Fixture review")
            review["outputs"] = {key: "Synthetic fixture only" for key in task["required_output"]}
            review["reviewed_paths"] = task["scope"]
        results["reviews"][-1]["reviewed_roles"] = [r["role_id"] for r in results["reviews"][:-1]]
        for validation in results["validations"]:
            validation.update(status="passed", evidence="synthetic fixture only")
        return results

    def test_pending_is_incomplete_and_complete_evidence_is_not_human_approval(self):
        plan = self.plan()
        self.assertEqual(plan["execution_status"], "not_started")
        self.assertFalse(check_results(self.root, plan, results_template(plan))["eligible_for_human_review"])
        report = check_results(self.root, plan, self.completed(plan))
        self.assertTrue(report["eligible_for_human_review"])
        self.assertFalse(report["independent_human_approval"])
        self.assertEqual(report["evidence_kind"], "self_reported_review_evidence")

    def test_staged_edit_undone_in_worktree_is_still_routed(self):
        self.git("add", "README.md")
        (self.root / "README.md").write_text("initial\n")
        self.assertEqual(changed_files(self.root), ["README.md"])

    def test_scope_includes_old_and_new_rename_paths_and_unicode_newline(self):
        self.git("mv", "README.md", "renamed.md")
        unusual = "Prüfung mit Leerzeichen\nweiter.md"
        (self.root / unusual).write_text("untracked")
        self.assertEqual(set(changed_files(self.root)), {"README.md", "renamed.md", unusual})

    def test_base_ref_uses_branch_merge_base_and_includes_local_edits(self):
        self.git("checkout", "-b", "feature")
        (self.root / "branch.md").write_text("branch")
        self.git("add", "branch.md")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-m", "branch")
        self.assertEqual(set(changed_files(self.root, "main")), {"README.md", "branch.md"})

    def test_changed_bytes_index_or_contract_make_review_stale(self):
        for mode in ("bytes", "index", "contract"):
            with self.subTest(mode=mode):
                plan = self.plan()
                result = self.completed(plan)
                if mode == "bytes":
                    (self.root / "README.md").write_text("changed again")
                elif mode == "index":
                    self.git("add", "README.md")
                else:
                    with (self.root / ".agents/review-protocol.yaml").open("a") as handle:
                        handle.write("\n# changed contract\n")
                with self.assertRaisesRegex(ValueError, "stale"):
                    check_results(self.root, plan, result)

    def test_new_path_invalidates_full_working_tree_plan(self):
        plan = self.plan()
        (self.root / "new.md").write_text("new")
        with self.assertRaisesRegex(ValueError, "scope is stale"):
            check_results(self.root, plan, self.completed(plan))

    def test_explicit_subset_is_named_and_never_claims_full_repository_coverage(self):
        plan = self.plan(explicit=True)
        (self.root / "unrelated.md").write_text("outside explicit scope")
        self.assertEqual(check_results(self.root, plan, self.completed(plan))["scope"], "explicit_paths")

    def test_skipped_review_failed_validation_and_open_high_findings_prevent_readiness(self):
        plan = self.plan()
        for case in ("skipped", "failed_validation", "high_finding"):
            result = self.completed(plan)
            if case == "skipped":
                result["reviews"][0]["status"] = "skipped"
            elif case == "failed_validation":
                result["validations"][0]["status"] = "failed"
            else:
                result["reviews"][0]["findings"] = [{"severity": "high", "path": "README.md", "issue": "fixture issue", "status": "open"}]
            self.assertFalse(check_results(self.root, plan, result)["eligible_for_human_review"], case)

    def test_missing_or_duplicate_roles_and_validations_rejected(self):
        plan = self.plan()
        for key in ("reviews", "validations"):
            for duplicate in (False, True):
                result = self.completed(plan)
                if duplicate:
                    result[key].append(deepcopy(result[key][0]))
                else:
                    result[key].pop()
                with self.assertRaises(ValueError):
                    check_results(self.root, plan, result)

    def test_missing_role_outputs_and_unreviewed_paths_are_incomplete(self):
        plan = self.plan()
        for key in ("outputs", "reviewed_paths"):
            result = self.completed(plan)
            result["reviews"][0][key] = {} if key == "outputs" else []
            self.assertFalse(check_results(self.root, plan, result)["eligible_for_human_review"])

    def test_rehashed_plan_cannot_drop_required_validations(self):
        plan = self.plan()
        plan["required_validations"] = []
        plan["plan_digest"] = digest({k: v for k, v in plan.items() if k != "plan_digest"})
        with self.assertRaises(ValueError):
            check_results(self.root, plan, self.completed(plan))

    def test_final_steward_must_account_for_specialist_reviews(self):
        plan = self.plan(explicit=True, paths=["model/requirements/catalog.yaml"])
        result = self.completed(plan)
        self.assertEqual(result["reviews"][-1]["role_id"], "repo-steward")
        self.assertTrue(check_results(self.root, plan, result)["eligible_for_human_review"])
        result["reviews"][-1]["reviewed_roles"] = []
        self.assertFalse(check_results(self.root, plan, result)["eligible_for_human_review"])
        result["reviews"].reverse()
        with self.assertRaisesRegex(ValueError, "repo-steward last"):
            check_results(self.root, plan, result)

    def test_deleted_file_is_bound_and_external_symlink_rejected(self):
        (self.root / "README.md").unlink()
        plan = self.plan()
        self.assertIsNone(plan["source_fingerprints"]["README.md"])
        self.assertTrue(check_results(self.root, plan, self.completed(plan))["eligible_for_human_review"])
        (self.root / "escape").symlink_to(ROOT / "README.md")
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.plan(explicit=True, paths=["escape"])

    def test_new_head_invalidates_even_byte_identical_review(self):
        plan = self.plan()
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "new head")
        with self.assertRaisesRegex(ValueError, "stale"):
            check_results(self.root, plan, self.completed(plan))

    def test_production_cli_without_tests_prepares_and_checks_private_packet(self):
        self.assertFalse((self.root / "tests").exists())
        usage = self.root / "generated/agent-usage"
        usage.mkdir(parents=True)
        state = usage / "recording-state.json"
        state.write_text(json.dumps({"active": True, "mode": "continuous", "usage_log": "generated/agent-usage/agent-usage.jsonl"}))
        original_state = state.read_bytes()
        with tempfile.TemporaryDirectory() as output_dir:
            plan_path, result_path = (Path(output_dir) / name for name in ("plan.json", "results.json"))
            command = [sys.executable, str(self.root / "scripts/dispatch_governance_agents.py")]
            prepare = [*command, "--goal", "Fixture review", "--plan-output", str(plan_path),
                       "--results-template", str(result_path), "README.md"]
            prepared = subprocess.run(prepare, capture_output=True, text=True)
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            self.assertEqual(state.read_bytes(), original_state)
            self.assertFalse((usage / "agent-usage.jsonl").exists())
            self.assertEqual(plan_path.stat().st_mode & 0o777, 0o600)
            check = [*command, "--check-review", str(plan_path), "--review-results", str(result_path)]
            self.assertEqual(subprocess.run(check, capture_output=True).returncode, 1)
            plan = json.loads(plan_path.read_text())
            result_path.write_text(json.dumps(self.completed(plan)))
            completed = subprocess.run(check, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertFalse(json.loads(completed.stdout)["independent_human_approval"])
            original = plan_path.read_bytes()
            self.assertEqual(subprocess.run(prepare, capture_output=True).returncode, 2)
            self.assertEqual(plan_path.read_bytes(), original)
            invalid = [*command, "--goal", "Fixture", "--plan-output", str(self.root / "private.json"), "README.md"]
            self.assertEqual(subprocess.run(invalid, capture_output=True).returncode, 2)
            self.assertFalse((self.root / "private.json").exists())


class ProductionRoutingTests(unittest.TestCase):
    def test_current_areas_have_specialists_and_selection_reasons(self):
        for path, expected in {
            "model/requirements/catalog.yaml": "governance-analyst",
            "model/platform/pra.yaml": "devsecops-baseline",
            "apps/governance-viewer/app.js": "evidence-and-intake",
            "scripts/workbench/app.js": "governance-analyst",
            ".codex/agents/repo-steward.toml": "release-manager",
            ".agents/execution-contract.yaml": "release-manager",
            "scripts/run_agent_reviews.py": "release-manager",
        }.items():
            dispatch = build_dispatch([path])
            self.assertIn(expected, dispatch["selected_agents"])
            self.assertTrue(dispatch["selection_reasons"][expected])

    def test_validations_come_from_role_contracts(self):
        for name, role in agent_routing.ROLE_CONTRACTS.items():
            self.assertEqual(agent_routing.validations_for_agents({name}), set(role["validations"]))
        self.assertIn("python3 scripts/validate_runtime_governance.py", build_dispatch(["README.md"])["required_validations"])

    def test_always_select_is_honored_from_neutral_contract(self):
        with patch.dict(agent_routing.ROUTING_DATA, {"always_select": ["repo-steward", "policy-as-code"]}):
            self.assertEqual(agent_routing.route_agents(["README.md"]), {"repo-steward", "policy-as-code"})

    def test_unclassified_functional_paths_have_visible_analyst_fallback(self):
        dispatch = build_dispatch(["scripts/new_unclassified_feature.py"])
        self.assertIn("governance-analyst", dispatch["selected_agents"])
        self.assertIn("fallback: unclassified functional path", dispatch["selection_reasons"]["governance-analyst"])
        self.assertEqual(build_dispatch(["model/requirements/catalog.yaml"])["release_impact"], "governance_model")

    def test_absolute_traversing_and_non_posix_paths_are_rejected(self):
        for path in ("/etc/passwd", "../model/controls/x", "model/../controls/x", "C:/repo/file", "model\\controls\\x", ""):
            with self.subTest(path=path), self.assertRaises(ValueError):
                agent_routing.route_agents([path])
        self.assertEqual(agent_routing.route_agents(["./model//controls/x"]), agent_routing.route_agents(["model/controls/x"]))

    def test_change_request_alone_is_not_a_source_intake(self):
        dispatch = build_dispatch(["docs/governance/change-requests/GCR-example.md", "policies/opa/x.rego"])
        self.assertNotIn("source-document-intake", dispatch["selected_agents"])
        self.assertFalse(dispatch["warnings"])

    def test_unknown_role_and_missing_skill_contract_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            routing = root / "routing.yaml"
            routing.write_text("always_select: [repo-steward]\nrules:\n  - path_prefix: docs/\n    agents: [unknown-role]\n")
            with self.assertRaises(ValueError):
                agent_routing.load_routing_rules(routing)
            shutil.copytree(ROOT / ".agents", root / ".agents")
            shutil.rmtree(root / ".agents/skills/repo-steward")
            with self.assertRaisesRegex(ValueError, "missing skill"):
                agent_routing.load_role_contracts(root)

    def test_duplicate_yaml_keys_and_uncanonical_prefix_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "routing.yaml"
            path.write_text("always_select: [repo-steward]\nalways_select: [policy-as-code]\nrules: []\n")
            with self.assertRaisesRegex(ValueError, "unique"):
                agent_routing.load_routing_rules(path)
            path.write_text("always_select: [repo-steward]\nrules:\n  - path_prefix: ./docs/\n    agents: [repo-steward]\n")
            with self.assertRaisesRegex(ValueError, "canonical"):
                agent_routing.load_routing_rules(path)
