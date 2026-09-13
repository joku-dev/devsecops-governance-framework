"""Isolated synthetic publisher allowlist, semantic validation and immutable Git prefix."""
from pathlib import Path
import shutil
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_governance_lifecycle_index import DEFAULT_PROFILE
from generate_governance_lifecycle_pilot import generate
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ContractError
from lib.governance_lifecycle.kernel import replay
from lib.governance_lifecycle.store import append_closure, append_observation, load_transactions
from lib.governance_lifecycle.synthetic import synthetic_packet
from publish_operational_update import publish, selected_paths
from validate_governance_lifecycle_ledger import check_accepted_prefix
import test_operational_review_publication as operational_tests
from test_governance_lifecycle_closure import seed, PILOT
import base64


class LifecyclePilotPublicationTests(unittest.TestCase):
    git = operational_tests.OperationalPublicationTests.git
    write = operational_tests.OperationalPublicationTests.write
    api = operational_tests.OperationalPublicationTests.api

    def setUp(self):
        operational_tests.OperationalPublicationTests.setUp(self)
        self.profile = strict_json(DEFAULT_PROFILE.read_bytes())
        self.ledger = self.root / "governance/lifecycle/synthetic-closure"
        seed(self.ledger)
        self.write("model/governance/lifecycle/synthetic-grs002-profile.json", DEFAULT_PROFILE.read_text())
        self.write(".gitignore", ".append.lock\n.pending-*\n")
        self.index = self.root / "status/governance-lifecycle-closure-index.json"
        self.report = self.root / "generated/reports/governance-lifecycle-pilot.md"
        self.generate()
        self.git("add", ".")
        self.git("commit", "-m", "Accept synthetic observation and work history")
        self.git("push", "origin", "main")
        self.base = self.git("rev-parse", "HEAD").strip()
        transaction = load_transactions(PILOT)[6]
        self.closure = transaction["record"]
        self.resources = {uri: base64.b64decode(data) for uri, data in transaction["resources"].items()}

    def generate(self):
        generate(self.ledger, self.index, self.report, as_of="2026-09-13T14:00:00Z")

    def append(self):
        append_closure(self.ledger, self.closure, self.resources, self.profile, expected_revision=6)
        self.generate()

    def publish(self):
        return publish(self.root, scope="lifecycle-synthetic", repository="owner/repo", run_id="123", attempt="1", api=self.api)

    def test_valid_closure_opens_only_review_branch_without_changing_main(self):
        self.append()
        self.publish()
        self.assertEqual(self.git("ls-remote", "origin", "refs/heads/main").split()[0], self.base)
        self.assertEqual(self.calls[0][1]["head"], "automation/lifecycle-synthetic/123-1")
        self.assertIn("fixture consent is not human authentication", self.calls[0][1]["body"])
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(check_accepted_prefix(self.root, self.base), 6)
        self.assertEqual(len(self.git("diff", "--name-only", self.base, "HEAD").splitlines()), 3)

    def test_stale_index_or_forged_report_is_rejected_before_publication(self):
        append_closure(self.ledger, self.closure, self.resources, self.profile, expected_revision=6)
        with self.assertRaisesRegex(ContractError, "differs"):
            self.publish()
        self.generate()
        self.report.write_text("This is live and approved.\n")
        with self.assertRaisesRegex(ContractError, "report differs"):
            self.publish()
        self.assertEqual(self.calls, [])

    def test_other_context_and_profile_changes_are_out_of_scope(self):
        for path in ("status/repository-results-index.json", "model/governance/lifecycle/synthetic-grs002-profile.json",
                     "governance/lifecycle/synthetic/transactions/new.json"):
            original = (self.root / path).read_bytes() if (self.root / path).exists() else None
            self.write(path, "{}\n")
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, "out-of-scope"):
                selected_paths(self.root, "lifecycle-synthetic")
            if original is None: (self.root / path).unlink()
            else: (self.root / path).write_bytes(original)

    def test_pilot_history_cannot_be_modified_or_deleted(self):
        path = sorted((self.ledger / "transactions").glob("*.json"))[0]
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        with self.assertRaisesRegex(ValueError, "append-only"):
            selected_paths(self.root, "lifecycle-synthetic")
        with self.assertRaisesRegex(ContractError, "modified"):
            check_accepted_prefix(self.root, self.base)
        path.unlink()
        with self.assertRaisesRegex(ContractError, "deleted"):
            check_accepted_prefix(self.root, self.base)

    def test_clean_git_merge_of_competing_closure_and_failure_is_rejected(self):
        self.git("checkout", "-b", "closure-proposal")
        self.append()
        self.git("add", ".")
        self.git("commit", "-m", "Propose closure")
        closure_head = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-b", "failure-proposal", self.base)
        packet = synthetic_packet(self.profile, result="fail", observed_at="2026-09-13T14:00:00Z",
                                  recorded_at="2026-09-13T14:00:00Z", run_id="competing-failure")
        append_observation(self.ledger, *packet, self.profile, expected_revision=6)
        # Commit only the transaction so Git merges cleanly; semantic replay must still reject the union.
        self.git("add", "governance/lifecycle/synthetic-closure")
        self.git("commit", "-m", "Propose new failure")
        replay(load_transactions(self.ledger), self.profile)
        self.git("merge", "--no-edit", "closure-proposal")
        self.assertEqual(check_accepted_prefix(self.root, closure_head), 7)
        with self.assertRaises(ContractError):
            replay(load_transactions(self.ledger), self.profile)


if __name__ == "__main__":
    unittest.main()
