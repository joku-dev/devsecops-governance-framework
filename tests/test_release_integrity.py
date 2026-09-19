from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.release_integrity import verify_release_integrity


class ReleaseIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Release Test")
        self.git("config", "user.email", "release-test@example.invalid")
        self.key = Path(self.temp.name) / "release-signing"
        subprocess.run(
            ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "release-test", "-f", str(self.key)],
            check=True,
        )
        self.git("config", "gpg.format", "ssh")
        self.git("config", "user.signingkey", str(self.key))
        self.git("config", "tag.gpgSign", "true")

        payload = self.root / "releases/test/payload.txt"
        payload.parent.mkdir(parents=True)
        payload.write_text("immutable release payload\n", encoding="utf-8")
        payload_digest = hashlib.sha256(payload.read_bytes()).hexdigest()
        checksums = self.root / "releases/test/checksums.sha256"
        checksums.write_text(f"{payload_digest}  releases/test/payload.txt\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "Release payload")

        self.legacy_tag = "legacy-baseline-v1"
        self.direct_tag = "direct-baseline-v2"
        self.git("-c", "tag.gpgSign=false", "tag", "-a", self.legacy_tag, "-m", "Legacy release")
        self.git("tag", "-s", self.direct_tag, "-m", "Direct signed release")

        public_key = self.key.with_suffix(".pub").read_text(encoding="utf-8").split()
        public_value = " ".join(public_key[:2])
        fingerprint = subprocess.check_output(
            ["ssh-keygen", "-lf", str(self.key.with_suffix('.pub'))], text=True
        ).split()[1]
        policy = {
            "schema_version": "0.1.0",
            "policy_id": "governance-release-signing",
            "repository_id": "example/repository",
            "status": "active_report_only",
            "enforcement": "report_only",
            "direct_signature": {
                "namespace": "git",
                "trusted_signers": [{
                    "principal": "release-test@example.invalid",
                    "github_login": "release-test",
                    "key_type": "ssh-ed25519",
                    "public_key": public_value,
                    "fingerprint": fingerprint,
                    "status": "active",
                    "valid_from": "2026-01-01T00:00:00Z",
                }],
            },
            "legacy_attestation": {
                "namespace": "governance-release-integrity-v1",
                "manifest": "releases/release-tag-integrity.json",
                "signature": "releases/release-tag-integrity.json.sig",
                "permitted_unsigned_tags": [self.legacy_tag],
            },
            "cutover": {
                "future_tags_require_direct_signature": True,
                "allow_new_legacy_tags": False,
            },
        }
        policy_path = self.root / "model/governance/release-signing-policy.yaml"
        policy_path.parent.mkdir(parents=True)
        policy_path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
        self.policy_path = policy_path

        manifest = {
            "schema_version": "0.1.0",
            "statement_type": "governance-release-tag-integrity",
            "repository_id": "example/repository",
            "issued_at": "2026-01-02T00:00:00Z",
            "signer_principal": "release-test@example.invalid",
            "purpose": "Test legacy integrity binding.",
            "legacy_tags": [{
                "tag_name": self.legacy_tag,
                "tag_object_sha": self.git("rev-parse", f"refs/tags/{self.legacy_tag}").strip(),
                "target_commit_sha": self.git("rev-list", "-n", "1", self.legacy_tag).strip(),
                "assurance_mode": "legacy_retrospective_attestation",
                "artifacts": [{
                    "path": "releases/test/checksums.sha256",
                    "role": "package_checksums",
                    "sha256": hashlib.sha256(checksums.read_bytes()).hexdigest(),
                }],
            }],
        }
        self.manifest_path = self.root / "releases/release-tag-integrity.json"
        self.manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        subprocess.run(
            [
                "ssh-keygen", "-Y", "sign", "-n", "governance-release-integrity-v1",
                "-f", str(self.key), str(self.manifest_path),
            ],
            check=True,
            capture_output=True,
        )

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.root, text=True, stderr=subprocess.PIPE
        )

    def verify(self):
        return verify_release_integrity(self.root, self.policy_path)

    def test_direct_and_legacy_verification_pass(self):
        result = self.verify()
        self.assertEqual(result["unverified_release_tags"], [])
        self.assertEqual(result["direct_verified_release_tags"], [self.direct_tag])
        self.assertEqual(result["legacy_manifest_verified_tags"], [self.legacy_tag])

    def test_manifest_tampering_invalidates_legacy_tag(self):
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["purpose"] = "Tampered after signing."
        self.manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        result = self.verify()
        self.assertIn(self.legacy_tag, result["unverified_release_tags"])
        self.assertTrue(any("signature is invalid" in item for item in result["verification_errors"]))

    def test_package_tampering_invalidates_legacy_tag(self):
        (self.root / "releases/test/payload.txt").write_text("tampered\n", encoding="utf-8")
        result = self.verify()
        self.assertIn(self.legacy_tag, result["unverified_release_tags"])
        self.assertTrue(any("Checksum mismatch" in item for item in result["verification_errors"]))

    def test_retargeted_legacy_tag_is_detected(self):
        (self.root / "later.txt").write_text("later\n", encoding="utf-8")
        self.git("add", "later.txt")
        self.git("commit", "-m", "Later commit")
        self.git("tag", "-d", self.legacy_tag)
        self.git("-c", "tag.gpgSign=false", "tag", "-a", self.legacy_tag, "-m", "Moved legacy tag")
        result = self.verify()
        self.assertIn(self.legacy_tag, result["unverified_release_tags"])
        self.assertTrue(any("differs from manifest" in item for item in result["verification_errors"]))

    def test_new_unsigned_release_tag_is_detected(self):
        new_tag = "new-baseline-v3"
        self.git("-c", "tag.gpgSign=false", "tag", "-a", new_tag, "-m", "Unsigned new release")
        result = self.verify()
        self.assertIn(new_tag, result["unverified_release_tags"])
        self.assertTrue(any("trusted direct signature required" in item for item in result["verification_errors"]))

    def test_mismatched_trusted_fingerprint_is_rejected(self):
        policy = yaml.safe_load(self.policy_path.read_text(encoding="utf-8"))
        policy["direct_signature"]["trusted_signers"][0]["fingerprint"] = "SHA256:wrong"
        self.policy_path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
