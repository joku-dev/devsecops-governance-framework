"""Conservative report-only assurance for each measured DevSecOps L1 control."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from lib.evidence_trust import evaluate_freshness, load_freshness_policy
from lib.measured_security import ROOT


PROFILE_ID = "control-evidence-assurance-v1"
PROFILE_PATH = ROOT / "model" / "evidence" / "control-evidence-assurance-profile.yaml"
POLICY_PATH = ROOT / "model" / "evidence" / "evidence-freshness-policies.yaml"
EVIDENCE_TYPES_PATH = ROOT / "model" / "evidence" / "evidence-types.yaml"
SCHEMA_PATH = ROOT / "schemas" / "control-evidence-assurance.schema.json"
RESULT_ROOT = ROOT / "status" / "control-evidence-assurance"
TRUST_LEVELS = ("unverified", "integrity_verified", "provenance_verified", "attested")
RESULTS = ("pass", "fail", "not_evaluated")


def canonical_digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def assurance_binding(item: dict) -> str:
    return canonical_digest({key: value for key, value in item.items() if key != "assurance_binding"})


def load_profile() -> dict:
    profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    expected = {f"DSCB-L1-REQ-{number:03}" for number in range(1, 17)}
    actual = [row.get("control_id") for row in profile.get("controls", [])]
    if profile.get("profile_id") != PROFILE_ID or set(actual) != expected or len(actual) != 16:
        raise ValueError("Control assurance profile must map every L1 control exactly once")
    policies = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    known_policies = {row["id"] for row in policies.get("policies", [])}
    unknown = {row.get("freshness_policy") for row in profile["controls"]} - known_policies
    if unknown:
        raise ValueError(f"Unknown assurance freshness policies: {sorted(unknown)}")
    evidence_types = yaml.safe_load(EVIDENCE_TYPES_PATH.read_text(encoding="utf-8"))
    type_rows = {row["id"]: row for row in evidence_types.get("evidence_types", [])}
    known_types = set(type_rows)
    unknown_types = {row.get("evidence_type") for row in profile["controls"]} - known_types
    if unknown_types:
        raise ValueError(f"Unknown assurance evidence types: {sorted(unknown_types)}")
    for row in profile["controls"]:
        if row["control_id"] not in type_rows[row["evidence_type"]].get("supports_requirements", []):
            raise ValueError(
                f"Evidence type {row['evidence_type']} does not support {row['control_id']}"
            )
        if row.get("typed_evidence_type") not in (None, "sbom", "vulnerability_scan"):
            raise ValueError(f"Unsupported typed evidence projection: {row['typed_evidence_type']}")
    return profile


def _check(trust: dict, check_id: str) -> dict:
    return next((row for row in trust.get("checks", []) if row.get("id") == check_id), {})


def _freshness_projection(check: dict, policy: dict, verified_at: str, reason: str | None = None) -> dict:
    result = {
        "result": check.get("result", "not_evaluated"),
        "policy_id": check.get("policy_id", policy["id"]),
        "policy_version": check.get("policy_version", policy["policy_version"]),
        "policy_status": check.get("policy_status", policy["policy_status"]),
        "produced_at": check.get("produced_at"),
        "evaluated_at": check.get("evaluated_at", verified_at),
        "reason": reason or check.get("reason", "Freshness could not be evaluated."),
    }
    for key in ("age_seconds", "maximum_age_seconds"):
        if key in check:
            result[key] = check[key]
    return result


def _generic_freshness(policy: dict, measured: dict, verified_at: str, *, subject_bound: bool) -> dict:
    mode = policy["evaluation_mode"]
    if mode == "release_candidate_bound":
        return _freshness_projection({}, policy, verified_at,
            "No exact release candidate and approval evidence is available for this control.")
    check = evaluate_freshness(
        policy,
        produced_at=measured["run"]["updated_at"],
        evaluated_at=verified_at,
        subject_bound=subject_bound if mode == "subject_bound" else None,
    )
    return _freshness_projection(check, policy, verified_at)


def _matching_typed(typed_snapshots: list[dict], measured: dict, evidence_type: str) -> dict | None:
    matches = [row for row in typed_snapshots
        if row.get("repository_id") == measured["repository_id"]
        and row.get("evidence_type") == evidence_type
        and row.get("pipeline", {}).get("pipeline_run_id") == measured["run"]["id"]
        and row.get("pipeline", {}).get("run_attempt") == measured["run"]["attempt"]
        and row.get("repository", {}).get("commit_id") == measured["run"]["commit"]]
    if len(matches) > 1:
        raise ValueError(f"Ambiguous typed evidence for {evidence_type} and run {measured['run']['id']}")
    return matches[0] if matches else None


def _present_item(profile: dict, control: dict, measured: dict, typed: dict | None, verified_at: str) -> dict:
    policy = load_freshness_policy(POLICY_PATH, profile["freshness_policy"])
    item = {
        "evidence_type": profile["evidence_type"],
        "status": "present",
        "required": True,
        "evidence_refs": list(control["evidence_refs"]),
        "effective_level": "integrity_verified",
        "content_integrity": "pass",
        "provenance": "pass",
        "freshness": _generic_freshness(policy, measured, verified_at, subject_bound=True),
        "replay": "not_evaluated",
        "custody": "not_evaluated",
        "attestation": "not_evaluated",
    }
    if typed is None:
        return item
    trust = typed["trust"]
    item["effective_level"] = trust["effective_level"]
    item["content_integrity"] = _check(trust, "content_digest_verified").get("result", "not_evaluated")
    provenance_checks = ("producer_run_resolved", "commit_matches_run", "artifact_belongs_to_run")
    provenance_results = [_check(trust, name).get("result", "not_evaluated") for name in provenance_checks]
    item["provenance"] = "pass" if all(value == "pass" for value in provenance_results) else (
        "fail" if "fail" in provenance_results else "not_evaluated")
    item["freshness"] = _freshness_projection(_check(trust, "freshness_evaluated"), policy, verified_at)
    item["replay"] = _check(trust, "replay_key_unique").get("result", "not_evaluated")
    item["custody"] = _check(trust, "custody_recorded").get("result", "not_evaluated")
    attestation = [_check(trust, name).get("result", "not_evaluated") for name in
        ("attestation_signature_valid", "attestation_issuer_trusted", "attestation_subject_matches")]
    item["attestation"] = "pass" if all(value == "pass" for value in attestation) else (
        "fail" if "fail" in attestation else "not_evaluated")
    if typed.get("_source_file"):
        item["typed_source_file"] = typed["_source_file"]
    return item


def _missing_item(profile: dict, measured: dict, verified_at: str, reason: str,
                  *, evidence_type: str = "unmet_control_evidence") -> dict:
    policy = load_freshness_policy(POLICY_PATH, profile["freshness_policy"])
    return {
        "evidence_type": evidence_type,
        "status": "missing",
        "required": True,
        "evidence_refs": [],
        "effective_level": "unverified",
        "content_integrity": "not_evaluated",
        "provenance": "not_evaluated",
        "freshness": _freshness_projection({}, policy, verified_at, reason),
        "replay": "not_evaluated",
        "custody": "not_evaluated",
        "attestation": "not_evaluated",
    }


def _coverage(assessment: str, principles: dict) -> str:
    if assessment in principles["complete_assessments"]:
        return "complete"
    if assessment in principles["partial_assessments"]:
        return "partial"
    if assessment in principles["missing_assessments"]:
        return "missing"
    raise ValueError(f"Unknown L1 assessment: {assessment}")


def build_assurance(measured: dict, typed_snapshots: list[dict], *, measured_source_file: str,
                    verified_at: str | None = None) -> dict:
    profile = load_profile()
    if (measured.get("result_type") != "measured-l1-assessment"
            or measured.get("repository_id") != profile["repository_id"]
            or measured.get("reference_baseline") != profile["baseline_ref"]):
        raise ValueError("Measured assessment is outside the assurance profile")
    typed_times = [row.get("trust", {}).get("verified_at") for row in typed_snapshots
                   if _matching_typed([row], measured, row.get("evidence_type", ""))]
    verified_at = verified_at or max((value for value in typed_times if value), default=None)
    if not verified_at:
        raise ValueError("A stable central verification timestamp is required")
    controls_by_id = {row["control_id"]: row for row in measured["controls"]}
    profile_by_id = {row["control_id"]: row for row in profile["controls"]}
    if set(controls_by_id) != set(profile_by_id):
        raise ValueError("Measured controls and assurance profile differ")
    controls = []
    for control_id in sorted(controls_by_id):
        control = controls_by_id[control_id]
        mapping = profile_by_id[control_id]
        coverage = _coverage(control["assessment"], profile["principles"])
        typed = _matching_typed(
            typed_snapshots,
            measured,
            mapping.get("typed_evidence_type", mapping["evidence_type"]),
        )
        evidence = []
        if control["evidence_refs"]:
            evidence.append(_present_item(mapping, control, measured, typed, verified_at))
        missing_scope = []
        if coverage != "complete":
            missing_scope = [control["remaining"]]
            evidence.append(_missing_item(
                mapping,
                measured,
                verified_at,
                control["remaining"],
                evidence_type=("unmet_control_evidence" if evidence else mapping["evidence_type"]),
            ))
        complete = coverage == "complete"
        present = next((row for row in evidence if row["status"] == "present"), None)
        if complete and present is None:
            raise ValueError(f"Complete control has no evidence: {control_id}")
        aggregate_freshness = deepcopy(present["freshness"] if complete else evidence[-1]["freshness"])
        controls.append({
            "control_id": control_id,
            "assessment": control["assessment"],
            "coverage": coverage,
            "effective_level": present["effective_level"] if complete else "unverified",
            "content_integrity": present["content_integrity"] if complete else "not_evaluated",
            "provenance": present["provenance"] if complete else "not_evaluated",
            "freshness": aggregate_freshness,
            "replay": present["replay"] if complete else "not_evaluated",
            "custody": present["custody"] if complete else "not_evaluated",
            "attestation": present["attestation"] if complete else "not_evaluated",
            "decision_context": mapping["decision_context"],
            "subject_binding": mapping["subject_binding"],
            "evidence": evidence,
            "missing_scope": missing_scope,
        })
    summary = {
        "total_controls": 16,
        "coverage": {key: Counter(row["coverage"] for row in controls)[key] for key in ("complete", "partial", "missing")},
        "trust_levels": {key: Counter(row["effective_level"] for row in controls)[key] for key in TRUST_LEVELS},
        "freshness": {key: Counter(row["freshness"]["result"] for row in controls)[key] for key in RESULTS},
    }
    result = {
        "schema_version": "1.0.0",
        "result_type": "control-evidence-assurance",
        "profile": PROFILE_ID,
        "repository_id": measured["repository_id"],
        "reference_baseline": measured["reference_baseline"],
        "run": deepcopy(measured["run"]),
        "verified_at": verified_at,
        "enforcement": "report-only",
        "official_compliance_result": False,
        "production_approval": False,
        "risk_acceptance": False,
        "source_assessment": {
            "result_type": measured["result_type"],
            "profile": measured["profile"],
            "evidence_binding": measured["evidence_binding"],
            "source_file": measured_source_file,
        },
        "controls": controls,
        "summary": summary,
    }
    result["assurance_binding"] = assurance_binding(result)
    validate_assurance(result)
    return result


def validate_assurance(item: dict) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(item)
    if item["assurance_binding"] != assurance_binding(item):
        raise ValueError("Control assurance binding changed")
    if {row["control_id"] for row in item["controls"]} != {f"DSCB-L1-REQ-{n:03}" for n in range(1, 17)}:
        raise ValueError("Control assurance must contain all L1 controls")
    controls = item["controls"]
    expected = {
        "total_controls": 16,
        "coverage": {key: Counter(row["coverage"] for row in controls)[key] for key in ("complete", "partial", "missing")},
        "trust_levels": {key: Counter(row["effective_level"] for row in controls)[key] for key in TRUST_LEVELS},
        "freshness": {key: Counter(row["freshness"]["result"] for row in controls)[key] for key in RESULTS},
    }
    if item["summary"] != expected:
        raise ValueError("Control assurance summary differs from controls")
    for control in controls:
        missing = [row for row in control["evidence"] if row["status"] == "missing"]
        if (control["coverage"] == "complete") != (not missing):
            raise ValueError(f"Control assurance coverage mismatch: {control['control_id']}")
        if missing and control["effective_level"] != "unverified":
            raise ValueError(f"Missing evidence did not downgrade control Trust: {control['control_id']}")
        if missing:
            dimensions = ("content_integrity", "provenance", "replay", "custody", "attestation")
            if any(control[key] != "not_evaluated" for key in dimensions):
                raise ValueError(f"Missing evidence produced a positive Trust dimension: {control['control_id']}")
            if control["freshness"]["result"] != "not_evaluated":
                raise ValueError(f"Missing evidence produced positive Freshness: {control['control_id']}")


def validate_assurance_source(item: dict, repository_root: Path = ROOT) -> None:
    """Verify that a stored assurance still points to its exact measured source."""
    source_path = repository_root / item["source_assessment"]["source_file"]
    try:
        source_path.resolve().relative_to(repository_root.resolve())
    except ValueError as exc:
        raise ValueError("Control assurance source escapes repository root") from exc
    if not source_path.is_file() or source_path.is_symlink():
        raise ValueError("Control assurance measured source is missing or unsafe")
    measured = json.loads(source_path.read_text(encoding="utf-8"))
    from lib.measured_l1 import validate_snapshot
    validate_snapshot(measured)
    expected = item["source_assessment"]
    if (measured["repository_id"] != item["repository_id"]
            or measured["reference_baseline"] != item["reference_baseline"]
            or measured["run"] != item["run"]
            or measured["result_type"] != expected["result_type"]
            or measured["profile"] != expected["profile"]
            or measured["evidence_binding"] != expected["evidence_binding"]):
        raise ValueError("Control assurance differs from its measured source")


def store_snapshot(root: Path, item: dict) -> Path:
    validate_assurance(item)
    path = root / item["repository_id"].replace("/", "__") / f"run-{item['run']['id']}-attempt-{item['run']['attempt']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != item:
            raise ValueError("Conflicting control assurance; historical snapshot preserved")
        return path
    path.write_text(json.dumps(item, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_snapshots(root: Path) -> list[dict]:
    items = []
    for path in sorted(root.rglob("*.json")) if root.exists() else []:
        item = json.loads(path.read_text(encoding="utf-8"))
        validate_assurance(item)
        expected = item["repository_id"].replace("/", "__") + f"/run-{item['run']['id']}-attempt-{item['run']['attempt']}.json"
        if path.is_symlink() or path.relative_to(root).as_posix() != expected:
            raise ValueError("Control assurance path/identity mismatch")
        items.append(item)
    return sorted(items, key=lambda row: (
        datetime.fromisoformat(row["run"]["created_at"].replace("Z", "+00:00")),
        int(row["run"]["id"]), row["run"]["attempt"]))
