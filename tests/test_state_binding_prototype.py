"""Private prototype invariants, actual writes, evidence tampering and publication boundary."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.state_binding import prototype as p
from experiments.state_binding.run_experiments import run
from experiments.state_binding.verify_evidence import rebuild, verify


class StateBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
        self.root = p.initialize(self.directory / "experiment")
        p.record(self.root, "evidence", {"run": "test-1", "result": "fail"})

    def grant(self):
        return p.fixture_approve(self.root, p.prepare(self.root))

    def bytes(self):
        return {x.name: x.read_bytes() for x in (self.root / "ledger/transactions").glob("*.json")}

    def test_golden_canonical_vector_and_unsupported_values(self):
        self.assertEqual(p.digest({"text": "Größe", "n": None, "b": True, "a": []}),
                         "cac6aca28c4826ebd2cd9ec96cd0c16f4e5e6055975e840949ea0570841abdcd")
        self.assertNotEqual(p.digest(True), p.digest(1))
        for value in (1.0, float("nan"), {1: "not-a-string-key"}, {"a"}, (1,)):
            with self.subTest(value=repr(value)), self.assertRaises(p.Rejected):
                p.digest(value)
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":1.5}'):
            path = self.directory / "invalid.json"
            path.write_text(raw)
            with self.assertRaises(ValueError):
                p.read_json(path)

    def test_empty_history_and_note_distinguish_semantic_state(self):
        empty = p.history_payload([])
        self.assertIsNone(empty["head_ref"])
        self.assertEqual(empty["transaction_count"], 0)
        before = p.snapshot(self.root)
        p.record(self.root, "audit_note", "No semantic effect")
        after = p.snapshot(self.root)
        self.assertEqual(before["roots"]["state"], after["roots"]["state"])
        self.assertNotEqual(before["roots"]["history"], after["roots"]["history"])

    def test_published_file_contains_exact_artifact_and_replays_in_independent_verifier(self):
        grant = self.grant()
        tx = p.execute(self.root, grant)
        files = self.bytes()
        self.assertEqual(len(files), 2)
        self.assertIn(tx["event"]["body"]["artifact"]["content"], next(v.decode() for k, v in files.items() if k.startswith("00000002")))
        after = p.snapshot(self.root)
        self.assertEqual(after["state"], rebuild(after["transactions"]))
        with self.assertRaises(p.Rejected):
            p.execute(self.root, grant)
        self.assertEqual(files, self.bytes())

    def test_incompatible_contract_and_action_tamper_produce_no_write(self):
        original = self.grant()
        for mutation in (lambda r: r.update(version="0"), lambda r: r["action"].update(content="tampered"),
                         lambda r: r.update(unexpected=True), lambda r: r.pop("roots")):
            grant = deepcopy(original)
            mutation(grant["request"])
            before = self.bytes()
            with self.assertRaises(p.Rejected):
                p.execute(self.root, grant)
            self.assertEqual(self.bytes(), before)

    def test_raw_ledger_tamper_and_deletion_are_detected_against_retained_history(self):
        grant = self.grant()
        p.execute(self.root, grant)
        txs = p.snapshot(self.root)["transactions"]
        changed = deepcopy(txs)
        changed[0]["event"]["body"]["result"] = "pass"
        with self.assertRaises(p.Rejected):
            p.replay(changed)
        with self.assertRaises(ValueError):
            rebuild(changed)
        with self.assertRaises(p.Rejected):
            p.replay(txs[1:])
        # Tail truncation alone remains a valid prefix: a trusted retained anchor
        # is explicitly necessary, rather than claiming hashes prevent rollback.
        self.assertNotEqual(p.digest(p.history_payload(txs)), p.digest(p.history_payload(txs[:-1])))
        self.assertEqual(p.replay(txs[:-1])["revision"], 1)

    def test_direct_publication_or_revocation_cannot_use_observation_api(self):
        for kind in ("publish", "revoke", "arbitrary"):
            with self.assertRaises(p.Rejected):
                p.record(self.root, kind, {})

    def test_revocation_requires_provider_and_remains_effective_after_reapproval(self):
        grant = self.grant()
        p.execute(self.root, grant)
        p.record(self.root, "audit_note", "Later history")
        with self.assertRaisesRegex(p.Rejected, "revocation_provider"):
            p.revoke(self.root, grant)
        p.update_fixture_provider(self.root, grant, "revoked")
        p.revoke(self.root, grant)
        before = self.bytes()
        p.write_json(self.root / "provider.json", {p.digest(grant["request"]): grant["provider_statement"]})
        with self.assertRaisesRegex(p.Rejected, "authorization_revoked"):
            p.execute(self.root, grant)
        self.assertEqual(before, self.bytes())
        self.assertIsNone(p.snapshot(self.root)["state"]["publication"])

    def test_added_removed_changed_and_symlink_implementation_files(self):
        repo = self.directory / "source"
        for name in ("experiments/state_binding/engine.py", "scripts/lib/governance_lifecycle/example.py",
                     "scripts/lib/result_ledger.py", "scripts/lib/__init__.py", "requirements-validation.txt",
                     "requirements-validation.lock", "scripts/validation-toolchain.env"):
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("original")
        with patch.object(p, "REPO", repo):
            first = p.digest(p.implementation_payload(p.source_manifest()))
            file = repo / "experiments/state_binding/extra.py"
            file.write_text("new")
            second = p.digest(p.implementation_payload(p.source_manifest()))
            self.assertNotEqual(first, second)
            file.write_text("changed")
            self.assertNotEqual(second, p.digest(p.implementation_payload(p.source_manifest())))
            file.unlink()
            self.assertEqual(first, p.digest(p.implementation_payload(p.source_manifest())))
            file.symlink_to(repo / "requirements-validation.txt")
            with self.assertRaises(p.Rejected):
                p.source_manifest()

    def test_context_and_provider_cannot_escape_experiment(self):
        with self.assertRaises(p.Rejected):
            p.initialize(ROOT / "status/forbidden-prototype")
        grant = self.grant()
        path = self.root / "provider.json"
        path.unlink()
        path.symlink_to(self.directory / "outside.json")
        with self.assertRaises(p.Rejected):
            p.execute(self.root, grant)

    def test_runtime_has_no_clock_input_in_roots(self):
        before = p.snapshot(self.root)
        # Changing presentation-only files does not change commitments.
        (self.root / "report.txt").write_text("generated_at: 2099-01-01")
        self.assertEqual(before["roots"], p.snapshot(self.root)["roots"])

    def test_change_during_provider_check_and_missing_proof_prevent_publication(self):
        grant = self.grant()
        before = self.bytes()
        with self.assertRaisesRegex(p.Rejected, "no_proof"):
            p.execute(self.root, grant, personal_verifier=lambda g: None)
        self.assertEqual(before, self.bytes())

        def changed_provider_read(path):
            value = original_read(path)
            if path.name == "provider.json":
                p.write_json(self.root / "executor-config.json", {"media_type": "application/json"})
            return value

        original_read = p.read_json
        with patch.object(p, "read_json", side_effect=changed_provider_read):
            with self.assertRaisesRegex(p.Rejected, "context_changed_during"):
                p.execute(self.root, grant)
        self.assertEqual(before, self.bytes())

    def test_injected_capture_does_not_become_live_personal_proof(self):
        grant = self.grant()
        fake = {"request": {"request_type": "private-prototype-local-demo", "prototype_grant": grant,
                            "repository_id": "joku-dev/devsecops-governance-framework"},
                "capture_method": "injected_test_transport"}
        before = self.bytes()
        with self.assertRaisesRegex(p.Rejected, "capture_method"):
            p.execute(self.root, grant, personal_verifier=lambda g: fake)
        self.assertEqual(before, self.bytes())


class EvidenceBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name).resolve()
        cls.bundle = cls.base / "evidence"
        cls.report, cls.anchor = run(cls.bundle, include_comparison=False)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_all_experiments_and_two_process_race_verify_independently(self):
        self.assertTrue(self.report["passed"])
        result = verify(self.bundle, self.anchor)
        self.assertEqual(result["experiments"], 18)
        self.assertTrue(result["external_anchor_checked"])

    def test_archive_round_trip_and_manifest_anchor(self):
        archive = self.base / "evidence.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as output:
            for path in sorted(self.bundle.rglob("*")):
                if path.is_file():
                    output.write(path, path.relative_to(self.bundle).as_posix())
        self.assertTrue(verify(archive, self.anchor)["verified"])
        with self.assertRaisesRegex(ValueError, "anchor"):
            verify(archive, "0" * 64)

    def test_tampered_projection_rejected_even_with_recomputed_bundle_checksum(self):
        target = self.bundle / "cases/unchanged/after/snapshot.json"
        manifest_path = self.bundle / "MANIFEST.json"
        original, manifest_original = target.read_bytes(), manifest_path.read_bytes()
        try:
            value = json.loads(original)
            value["roots"]["state"] = "0" * 64
            p.write_json(target, value)
            with self.assertRaisesRegex(ValueError, "Checksum"):
                verify(self.bundle)
            manifest = json.loads(manifest_original)
            manifest["files"][target.relative_to(self.bundle).as_posix()] = hashlib.sha256(target.read_bytes()).hexdigest()
            p.write_json(manifest_path, manifest)
            with self.assertRaisesRegex(ValueError, "Root projection"):
                verify(self.bundle)
        finally:
            target.write_bytes(original)
            manifest_path.write_bytes(manifest_original)

    def test_archive_traversal_rejected(self):
        target = self.base / "unsafe.zip"
        with zipfile.ZipFile(target, "w") as output:
            output.writestr("../outside", "bad")
        with self.assertRaisesRegex(ValueError, "Unsafe archive"):
            verify(target)
        self.assertFalse((self.base / "outside").exists())

    def test_confidential_marker_blocks_publisher_and_private_override_removed(self):
        import yaml
        workflow = yaml.safe_load((ROOT / ".github/workflows/publish-docs.yml").read_text())
        job = workflow["jobs"]["publish-docs"]
        self.assertEqual(job["if"], "${{ github.event.repository.private == false }}")
        self.assertNotIn("publish_private_pages", json.dumps(workflow))
        step = next(s for s in job["steps"] if s["name"] == "Refuse publication of confidential research")
        process = subprocess.run(["bash", "-c", step["run"]], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("prevents public publication", process.stderr)


if __name__ == "__main__":
    unittest.main()
