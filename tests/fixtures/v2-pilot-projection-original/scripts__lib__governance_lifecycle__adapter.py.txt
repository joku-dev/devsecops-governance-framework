"""GRS-002 adapter for explicitly synthetic report/trust packets only."""
from copy import deepcopy
import hashlib
import json

from jsonschema import Draft202012Validator

from .contracts import (
    ROOT, FORMAT_CHECKER, acceptance_statement, canonical_digest, finding_id,
    require, validate_test_profile, validate_test_record, versioned_ref,
)


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON member: " + key)
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("Non-JSON numeric constant: " + value)

    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid_constant)


def adapt_grs002(report_bytes, context, trust, *, recorded_at, profile, policy_version):
    """Preserve supplied synthetic trust assertions; never infer real provenance."""
    validate_test_profile(profile)
    require(context.get("kind") == "test", "Adapter supports synthetic test context only")
    require(context.get("repository_id") == profile["repository_id"], "Adapter repository mismatch")
    report = strict_json(report_bytes)
    schema = json.loads((ROOT / "schemas/governance-repository-security-report.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FORMAT_CHECKER).validate(report)
    require(report["observation"].get("synthetic") is True, "Report must be explicitly synthetic")
    require(report["repository_id"] == profile["repository_id"], "Report repository mismatch")
    criteria = [c for c in report["criteria"] if c["id"] == "GRS-002"]
    require(len(criteria) == 1 and criteria[0]["key"] == "pull_request_review_required",
            "Exactly one GRS-002 criterion is required")
    digest = hashlib.sha256(report_bytes).hexdigest()
    trust = deepcopy(trust)
    subjects = [s for s in trust["capture"]["subjects"] if s["id"] == "governance_repository_security_report"]
    require(len(subjects) == 1 and subjects[0]["digest"] == digest
            and subjects[0]["size_bytes"] == len(report_bytes), "Trust subject does not match raw report")
    uri = subjects[0]["evidence_ref"]
    require(uri.startswith("fixture://"), "Adapter cannot accept live evidence resources")
    require(trust["capture"]["source"]["workflow_name"] == context["producer_id"], "Trust producer mismatch")
    key = {"repository_id": report["repository_id"], "domain": "governance_repository_security",
           "rule_id": "GRS-002", "finding_type": "criterion_failure", "resource": "refs/heads/main"}
    finding = {"fingerprint_version": "1", "key": key, "finding_id": finding_id(key)}
    identity = {"finding": finding, "source_context": context, "snapshot_digest": digest,
                "profile_version": report["profile_version"], "policy_version": policy_version}
    record = {
        "schema_version": "0.1.0", "record_type": "observation",
        "record_id": "observation:" + canonical_digest(identity), "environment": "synthetic",
        "profile_ref": versioned_ref(profile, "profile_id"), "finding": finding, "recorded_at": recorded_at,
        "body": {"observed_at": report["observed_at"], "result": criteria[0]["status"],
                 "rule_key": "pull_request_review_required", "granularity": "criterion",
                 "profile_version": report["profile_version"], "policy_version": policy_version,
                 "source_schema": "governance-repository-security-report.schema.json@0.2.0",
                 "source_context": deepcopy(context), "snapshot_ref": {"uri": uri, "digest": digest},
                 "trust": trust, "acceptance": {
                     "evaluated_at": recorded_at, "profile_ref": versioned_ref(profile, "profile_id"),
                     "outcome": "accepted", "verifier_id": "synthetic-contract-verifier"}}
    }
    proof = json_bytes(acceptance_statement(record))
    proof_uri = "fixture://acceptance-" + hashlib.sha256(proof).hexdigest() + ".json"
    require(proof_uri != uri, "Report and proof resource URI collision")
    record["body"]["acceptance"]["proof_ref"] = {"uri": proof_uri, "digest": hashlib.sha256(proof).hexdigest()}
    resources = {uri: report_bytes, proof_uri: proof}
    validate_test_record(record, profile, resources)
    return record, resources
