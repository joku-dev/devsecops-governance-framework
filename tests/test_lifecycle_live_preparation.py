"""Pilot appointment consistency and immutable history are distinct from live consent."""
from copy import deepcopy
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ContractError, schema_validator, validate_test_profile
from lib.governance_lifecycle.live_preparation import (
    PREPARATION_PATH, effective_assignments, revision_ref, validate_bindings, validate_preparation,
)
from validate_governance_lifecycle_ledger import check_accepted_prefix


class LivePreparationTests(unittest.TestCase):
    def setUp(self):
        self.binding = strict_json((ROOT / PREPARATION_PATH / "role-bindings/00000001.json").read_bytes())
        self.profile = strict_json((ROOT / PREPARATION_PATH / "profiles/00000001.json").read_bytes())

    def test_confirmed_three_roles_are_separate_but_do_not_activate_runtime(self):
        result = validate_preparation()
        self.assertEqual(len(result["assignments"]), 3)
        self.assertEqual(set(result["assignments"].values()), {"github-user:81616324"})
        self.assertFalse(result["runtime_authorized"])
        self.assertFalse(result["binding"]["authorization"]["runtime_consent_proof"])
        self.assertIsNone(result["profile"]["operating_policy"]["maximum_age_seconds"])
        with self.assertRaises(ValidationError):
            validate_test_profile(self.profile)

    def test_multiple_roles_and_identity_mismatches_are_rejected(self):
        for mutate in (lambda r: r.update(multiple_roles_confirmed=False),
                       lambda r: r["subjects"][0].update(provider_user_id=42),
                       lambda r: r["subjects"].append(deepcopy(r["subjects"][0])),
                       lambda r: r["assignments"].update(closure_approver="github-user:42")):
            binding = deepcopy(self.binding); mutate(binding)
            with self.assertRaises(ContractError):
                validate_bindings([binding])

    def test_scope_widening_and_machine_or_consent_substitution_are_rejected(self):
        for mutate in (lambda r: r["scope"].update(repository_id="other/repo"),
                       lambda r: r["scope"].update(rule_id="GRS-003"),
                       lambda r: r["scope"].update(enforcement="blocking"),
                       lambda r: r["subjects"][0].update(provider="agent"),
                       lambda r: r["authorization"].update(runtime_consent_proof=True)):
            binding = deepcopy(self.binding); mutate(binding)
            with self.assertRaises(ValidationError):
                validate_bindings([binding])

    def test_withdrawal_removes_effective_appointments_and_keeps_original(self):
        withdrawn = deepcopy(self.binding)
        withdrawn.update(revision=2, previous_ref=revision_ref(self.binding), status="withdrawn")
        before = deepcopy(self.binding)
        self.assertEqual(effective_assignments([self.binding, withdrawn]), {})
        self.assertEqual(self.binding, before)
        for mutate in (lambda r: r.update(revision=3),
                       lambda r: r["previous_ref"].update(digest="0" * 64),
                       lambda r: r.update(recorded_at="2026-09-12T00:00:00Z")):
            bad = deepcopy(withdrawn); mutate(bad)
            with self.assertRaises(ContractError):
                validate_bindings([self.binding, bad])

    def test_preparation_cannot_enable_live_actions_or_assume_operating_values(self):
        for key in ("live_intake_enabled", "consent_intake_enabled", "official_publish_enabled"):
            profile = deepcopy(self.profile); profile[key] = True
            with self.assertRaises(ValidationError):
                schema_validator("live-profile-preparation").validate(profile)
        profile = deepcopy(self.profile); profile["operating_policy"]["maximum_age_seconds"] = 86400
        with self.assertRaises(ValidationError):
            schema_validator("live-profile-preparation").validate(profile)

    def test_profile_cannot_ignore_withdrawal_or_changed_binding_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); shutil.copytree(ROOT / PREPARATION_PATH, root / PREPARATION_PATH)
            binding_path = root / PREPARATION_PATH / "role-bindings/00000001.json"
            changed = deepcopy(self.binding); changed["subjects"][0]["display_name"] = "changed"
            binding_path.write_bytes(json_bytes(changed))
            with self.assertRaisesRegex(ContractError, "digest"):
                validate_preparation(root)
            binding_path.write_bytes(json_bytes(self.binding))
            withdrawn = deepcopy(self.binding); withdrawn.update(revision=2, previous_ref=revision_ref(self.binding), status="withdrawn")
            (binding_path.parent / "00000002.json").write_bytes(json_bytes(withdrawn))
            with self.assertRaisesRegex(ContractError, "latest role"):
                validate_preparation(root)
            profile2 = deepcopy(self.profile); profile2.update(revision=2, previous_ref=revision_ref(self.profile), role_binding_ref=revision_ref(withdrawn))
            (root / PREPARATION_PATH / "profiles/00000002.json").write_bytes(json_bytes(profile2))
            self.assertEqual(validate_preparation(root)["assignments"], {})

    def test_merge_prefix_protects_accepted_role_and_profile_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); shutil.copytree(ROOT / PREPARATION_PATH, root / PREPARATION_PATH)
            def git(*args):
                return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
            git("init"); git("config", "user.email", "test@example.invalid"); git("config", "user.name", "Test")
            git("add", "."); git("commit", "-m", "accepted preparation")
            base = git("rev-parse", "HEAD")
            self.assertEqual(check_accepted_prefix(root, base), 0)
            for name in ("role-bindings", "profiles"):
                path = root / PREPARATION_PATH / name / "00000001.json"
                before = path.read_bytes(); path.write_bytes(before + b" ")
                with self.assertRaisesRegex(ContractError, "new immutable revision"):
                    check_accepted_prefix(root, base)
                path.unlink()
                with self.assertRaisesRegex(ContractError, "deleted or replaced"):
                    check_accepted_prefix(root, base)
                path.write_bytes(before)


if __name__ == "__main__":
    unittest.main()
