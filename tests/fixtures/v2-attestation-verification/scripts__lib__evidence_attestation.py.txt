"""Report-only public-key verification for the evidence attestation pilot."""

from __future__ import annotations

import base64
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile

import yaml


CHECK_IDS = [
    "trust_root_known",
    "attestation_signature_valid",
    "attestation_subject_matches",
    "attestation_context_matches",
]


def canonical_statement(statement: dict) -> bytes:
    return json.dumps(statement, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_trust_roots(path: Path) -> dict:
    registry = yaml.safe_load(path.read_text(encoding="utf-8"))
    if registry.get("status") != "pilot_report_only" or registry.get("enforcement") != "report_only":
        raise ValueError("The pilot accepts only a report-only trust-root registry")
    return registry


def _verify_ed25519(public_key_pem: str, statement: bytes, signature: str) -> tuple[bool, str]:
    try:
        signature_bytes = base64.b64decode(signature, validate=True)
    except (ValueError, TypeError) as exc:
        return False, f"Signature is not valid base64: {exc}"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        key_path, statement_path, signature_path = root / "key.pem", root / "statement.json", root / "signature.bin"
        key_path.write_text(public_key_pem, encoding="utf-8")
        statement_path.write_bytes(statement)
        signature_path.write_bytes(signature_bytes)
        try:
            completed = subprocess.run(
                ["openssl", "pkeyutl", "-verify", "-pubin", "-rawin", "-inkey", str(key_path),
                 "-in", str(statement_path), "-sigfile", str(signature_path)],
                capture_output=True, text=True, check=False,
            )
        except FileNotFoundError:
            return False, "OpenSSL is unavailable; signature verification was not performed."
    return completed.returncode == 0, "Ed25519 signature is valid." if completed.returncode == 0 else "Ed25519 signature is invalid."


def assess_attestation(*, attestation: dict, registry: dict, expected_context: dict,
                       expected_subject: dict, evaluated_at: str, attestation_ref: str,
                       current_effective_level: str = "integrity_verified") -> dict:
    """Verify authenticity while deliberately retaining the current effective Trust level."""
    roots = registry.get("roots", [])
    root = next((item for item in roots if item.get("key_id") == attestation.get("key_id")
                 and item.get("issuer") == attestation.get("issuer") and item.get("status") == "pilot"), None)
    checks = {check_id: {"id": check_id, "result": "not_evaluated", "reason": "Prerequisite check did not pass."}
              for check_id in CHECK_IDS}
    permitted = root is not None and attestation.get("statement", {}).get("repository_id") in root.get("permitted_repositories", [])
    checks["trust_root_known"] = {
        "id": "trust_root_known", "result": "pass" if permitted else "fail",
        "reason": "Pilot issuer, key, and repository scope are registered." if permitted else "Issuer, key, or repository scope is not registered.",
    }
    if permitted:
        valid, reason = _verify_ed25519(root["public_key_pem"], canonical_statement(attestation["statement"]), attestation["signature"])
        checks["attestation_signature_valid"] = {"id": "attestation_signature_valid", "result": "pass" if valid else "fail", "reason": reason}
    statement = attestation.get("statement", {})
    subject_matches = statement.get("subject") == expected_subject
    checks["attestation_subject_matches"] = {
        "id": "attestation_subject_matches", "result": "pass" if subject_matches else "fail",
        "reason": "Attested subject identifier and digest match the collected subject." if subject_matches else "Attested subject does not match the collected subject.",
    }
    actual_context = {key: statement.get(key) for key in ("repository_id", "commit_id", "run_id", "run_attempt", "artifact_name")}
    context_matches = actual_context == expected_context
    checks["attestation_context_matches"] = {
        "id": "attestation_context_matches", "result": "pass" if context_matches else "fail",
        "reason": "Repository, commit, run attempt, and artifact are bound to the attestation." if context_matches else "Attestation context differs from the authoritative collection context.",
    }
    ordered = [checks[item] for item in CHECK_IDS]
    passed = all(check["result"] == "pass" for check in ordered)
    return {
        "schema_version": "0.1.0", "assessment_type": "evidence-attestation-pilot", "enforcement": "report_only",
        "evaluated_at": evaluated_at, "attestation_ref": attestation_ref,
        "effective_level": current_effective_level, "candidate_level": "attested" if passed else "none",
        "status": "pass" if passed else "fail", "checks": ordered,
    }
