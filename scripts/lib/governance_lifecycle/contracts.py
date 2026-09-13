"""CLG-01 record contracts and bounded synthetic example checks.

These checks prove consistency of fixtures, never human identity or live trust.
No state is written and no lifecycle state machine is implemented here.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from functools import lru_cache
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from lib.result_ledger import canonical_digest

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_BASE = "https://joku-dev.github.io/devsecops-governance-framework/schemas/"
KINDS = ("observation", "decision", "remediation", "closure", "event")
FORMAT_CHECKER = FormatChecker()


@FORMAT_CHECKER.checks("date-time", raises=(ValueError, TypeError))
def check_utc_timestamp(value):
    # jsonschema's optional RFC3339 extra is not in the pinned toolchain.
    # Enforce our narrower UTC contract without adding a dependency.
    return isinstance(value, str) and datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%dT%H:%M:%SZ") == value


class ContractError(ValueError):
    """A structural or offline consistency contract was violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


@lru_cache(maxsize=16)
def schema_validator(kind: str) -> Draft202012Validator:
    require(kind in (*KINDS, "profile", "transaction", "index", "decision-v0.2", "remediation-v0.2", "action-transaction", "action-index", "closure-v0.2", "closure-transaction", "closure-index"), "Unknown lifecycle schema kind")
    resources = []
    for path in sorted((ROOT / "schemas").glob("governance-lifecycle-*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        resources.append((SCHEMA_BASE + path.name, Resource.from_contents(schema)))
    trust = json.loads((ROOT / "schemas/evidence-trust-record.schema.json").read_text())
    resources.append((SCHEMA_BASE + "evidence-trust-record.schema.json", Resource.from_contents(trust)))
    registry = Registry().with_resources(resources)
    schema = json.loads((ROOT / "schemas" / f"governance-lifecycle-{kind}.schema.json").read_text())
    return Draft202012Validator(schema, registry=registry, format_checker=FORMAT_CHECKER)


def timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def finding_id(key: dict) -> str:
    return "finding:" + canonical_digest({"fingerprint_version": "1", "key": key})


def record_ref(record: dict) -> dict:
    return {"id": record["record_id"], "digest": canonical_digest(record)}


def versioned_ref(value: dict, id_field: str = "id") -> dict:
    return {"id": value[id_field], "version": value["version"], "digest": canonical_digest(value)}


def approval_target(record: dict) -> str:
    return canonical_digest({key: value for key, value in record.items() if key != "approval"})


def observation_identity(record: dict) -> str:
    """Delivery identity excludes receipt time and result bytes; conflicts stay visible."""
    return canonical_digest({"finding": record["finding"], "source_context": record["body"]["source_context"]})


def validate_record(record: dict) -> None:
    kind = record.get("record_type")
    schema_kind = kind + "-v0.2" if kind in ("decision", "remediation", "closure") and record.get("schema_version") == "0.2.0" else kind
    schema_validator(schema_kind).validate(record)
    require(record["finding"]["finding_id"] == finding_id(record["finding"]["key"]), "Finding fingerprint mismatch")
    body = record["body"]
    if kind in ("decision", "closure"):
        approval = record["approval"]
        require(approval["target_digest"] == approval_target(record), "Approval content binding mismatch")
        require(approval["finding_id"] == record["finding"]["finding_id"], "Approval scope mismatch")
        require(approval["expected_revision"] == body["expected_revision"], "Approval revision mismatch")
        role = "remediation_decider" if kind == "decision" else "closure_approver"
        require(approval["role"] == role, "Approval role mismatch")
        require(timestamp(approval["issued_at"]) <= timestamp(record["recorded_at"]), "Approval after recording")
    elif kind == "event":
        require(body["revision"] == body["expected_revision"] + 1, "Event revision must advance by one")
        require(timestamp(body["effective_at"]) <= timestamp(record["recorded_at"]), "Event effective time after recording")
    elif kind == "observation":
        require(timestamp(body["observed_at"]) <= timestamp(body["acceptance"]["evaluated_at"]) <= timestamp(record["recorded_at"]), "Observation time order")


def acceptance_statement(record: dict) -> dict:
    target = deepcopy(record)
    acceptance = target["body"].pop("acceptance")
    return {"environment": "synthetic", "observation_digest": canonical_digest(target),
            "assessment": {k: v for k, v in acceptance.items() if k != "proof_ref"}}


def fixture_resource(reference: dict, resources: dict[str, bytes]) -> bytes:
    uri = reference["uri"]
    require(uri.startswith("fixture://"), "Only fixture resources are supported; live verification is unavailable")
    require(uri in resources, "Missing fixture resource")
    content = resources[uri]
    require(hashlib.sha256(content).hexdigest() == reference["digest"], "Fixture digest mismatch")
    return content


def validate_test_profile(profile: dict) -> None:
    schema_validator("profile").validate(profile)


def validate_test_record(record: dict, profile: dict, resources: dict[str, bytes]) -> None:
    validate_test_profile(profile)
    validate_record(record)
    require(record["environment"] == "synthetic", "Live records cannot use the test verifier")
    require(record["profile_ref"] == versioned_ref(profile, "profile_id"), "Test profile binding mismatch")
    require(record["finding"]["key"]["repository_id"] == profile["repository_id"], "Test repository mismatch")
    if record["record_type"] in ("decision", "closure"):
        approval = record["approval"]
        binding = profile["role_binding"]
        require(approval["role_binding_ref"] == versioned_ref(binding), "Role binding mismatch")
        require(approval["subject_id"] == binding["assignments"][approval["role"]], "Subject not assigned to role")
        require(approval["channel"] == profile["approval_channel"], "Approval channel mismatch")
        proof = json.loads(fixture_resource(approval["proof_ref"], resources))
        expected = {k: v for k, v in approval.items() if k != "proof_ref"}
        require(proof == {"environment": "synthetic", "approval": expected}, "Synthetic approval proof mismatch")
    elif record["record_type"] == "remediation":
        fixture_resource(record["body"]["work_ref"], resources)
    elif record["record_type"] == "observation":
        body = record["body"]
        context = body["source_context"]
        require(context["kind"] in profile["allowed_contexts"], "Context not accepted by test profile")
        require(context["producer_id"] in profile["allowed_producers"], "Producer not accepted by test profile")
        require(context["repository_id"] == profile["repository_id"], "Source repository mismatch")
        require(body["acceptance"]["profile_ref"] == record["profile_ref"], "Acceptance profile mismatch")
        proof = json.loads(fixture_resource(body["acceptance"]["proof_ref"], resources))
        require(proof == acceptance_statement(record), "Synthetic acceptance proof mismatch")
        snapshot_bytes = fixture_resource(body["snapshot_ref"], resources)
        snapshot = json.loads(snapshot_bytes)
        report_schema = json.loads((ROOT / "schemas/governance-repository-security-report.schema.json").read_text())
        Draft202012Validator(report_schema, format_checker=FORMAT_CHECKER).validate(snapshot)
        require(snapshot["repository_id"] == context["repository_id"], "Snapshot repository mismatch")
        require(snapshot["observed_at"] == body["observed_at"], "Snapshot observation time mismatch")
        require(snapshot["profile_version"] == body["profile_version"], "Snapshot profile mismatch")
        criteria = [c for c in snapshot["criteria"] if c["id"] == record["finding"]["key"]["rule_id"]]
        require(len(criteria) == 1, "Snapshot must contain exactly one matching criterion")
        require(criteria[0]["key"] == body["rule_key"] and criteria[0]["status"] == body["result"], "Snapshot criterion mismatch")
        trust = body["trust"]
        source = trust["capture"]["source"]
        for key in ("repository_id", "commit_id", "run_id", "run_attempt"):
            require(source[key] == context[key], "Trust source context mismatch")
        subjects = trust["capture"]["subjects"]
        require(any(s["digest"] == body["snapshot_ref"]["digest"] and s["size_bytes"] == len(snapshot_bytes)
                    and s["evidence_ref"] == body["snapshot_ref"]["uri"] for s in subjects), "Trust subject does not bind snapshot")
        if body["acceptance"]["outcome"] == "accepted":
            check_test_trust(record, profile)


def check_test_trust(observation: dict, profile: dict) -> None:
    """Check asserted synthetic acceptance, without authenticating a producer."""
    body = observation["body"]
    trust = body["trust"]
    require(trust["assessment_status"] == "evaluated" and trust["effective_level"] in
            ("provenance_verified", "attested"), "Insufficient observation trust")
    checks = trust["checks"]
    require(len({c["id"] for c in checks}) == len(checks), "Duplicate trust check IDs")
    by_id = {c["id"]: c for c in checks}
    require(all(name in by_id and by_id[name]["result"] == "pass" and by_id[name]["evidence_refs"]
                for name in profile["required_checks"]), "Required trust check missing or not passed")
    observed, accepted, verified = (timestamp(value) for value in
        (body["observed_at"], body["acceptance"]["evaluated_at"], trust["verified_at"]))
    require(observed <= verified <= accepted, "Trust verification outside acceptance window")
    require(0 <= (accepted - observed).total_seconds() <= profile["maximum_age_seconds"],
            "Observation stale at acceptance")


def resolve_record(reference: dict, records: dict[str, dict], kind: str) -> dict:
    require(reference["id"] in records, "Missing referenced record")
    value = records[reference["id"]]
    require(value["record_type"] == kind and record_ref(value) == reference, "Record reference binding mismatch")
    return value


def check_closure_prerequisites(closure: dict, records: dict[str, dict], profile: dict,
                                resources: dict[str, bytes], *, as_of: str) -> None:
    """Check a synthetic closure packet, not ledger state, revocation history or authority."""
    validate_test_record(closure, profile, resources)
    require(closure["record_type"] == "closure", "Expected a closure")
    body = closure["body"]
    require(body["as_of"] == as_of, "Explicit as_of must match the closure content")
    now = timestamp(as_of)
    require(timestamp(closure["recorded_at"]) <= now, "Closure recorded after as_of")
    require(closure["approval"]["disposition"] == "approve", "Closure not approved")
    remediation = resolve_record(body["remediation_ref"], records, "remediation")
    decision = resolve_record(remediation["body"]["decision_ref"], records, "decision")
    failing = resolve_record(body["failing_observation_ref"], records, "observation")
    passing = resolve_record(body["passing_observation_ref"], records, "observation")
    for record in (remediation, decision, failing, passing):
        validate_test_record(record, profile, resources)
        require(record["finding"] == closure["finding"], "Closure finding/scope mismatch")
        require(timestamp(record["recorded_at"]) <= now, "Referenced record after as_of")
    require(decision["approval"]["disposition"] == "approve", "Remediation decision not approved")
    require(decision["body"]["observation_ref"] == record_ref(failing), "Decision concerns a different failure")
    require(remediation["body"]["action"] == decision["body"]["action"], "Remediation differs from authorized action")
    require(remediation["body"]["progress"] == "completed", "Remediation is not completed")
    require(failing["body"]["result"] == "fail" and passing["body"]["result"] == "pass", "Closure requires criterion FAIL and PASS")
    fail_time, pass_time = (timestamp(r["body"]["observed_at"]) for r in (failing, passing))
    require(fail_time < pass_time, "PASS must be newer than the failure")
    require(timestamp(remediation["recorded_at"]) <= pass_time <= timestamp(closure["approval"]["issued_at"]), "Closure evidence must follow remediation and precede approval")
    require(timestamp(decision["recorded_at"]) <= timestamp(remediation["recorded_at"]), "Remediation predates decision")
    require(decision["body"]["expected_revision"] < remediation["body"]["expected_revision"] < body["expected_revision"], "Closure packet revisions out of order")
    for key in ("profile_version", "policy_version", "source_schema"):
        require(failing["body"][key] == passing["body"][key], "Incompatible evidence versions")
    for observation in (failing, passing):
        require(observation["body"]["acceptance"]["outcome"] == "accepted", "Observation not accepted")
    trust = passing["body"]["trust"]
    require(pass_time <= timestamp(trust["verified_at"]) <= timestamp(closure["approval"]["issued_at"]), "Trust verification time outside closure window")
    require(0 <= (now - pass_time).total_seconds() <= profile["maximum_age_seconds"], "Closure evidence is stale or from the future")


def check_event_references(event: dict, records: dict[str, dict]) -> None:
    """Check one event's references; no append, concurrency control or projection."""
    validate_record(event)
    require(event["record_type"] == "event", "Expected an event")
    body = event["body"]
    if body["previous_event_ref"] is not None:
        previous = resolve_record(body["previous_event_ref"], records, "event")
        validate_record(previous)
        require(previous["finding"] == event["finding"] and previous["environment"] == event["environment"]
                and previous["profile_ref"] == event["profile_ref"], "Event predecessor scope mismatch")
        require(previous["body"]["revision"] == body["expected_revision"], "Event predecessor revision mismatch")
        require(timestamp(previous["recorded_at"]) <= timestamp(event["recorded_at"]), "Event predecessor recorded later")
    kinds = {"finding_opened": "observation", "observation_added": "observation",
             "decision_recorded": "decision", "remediation_recorded": "remediation",
             "finding_closed": "closure", "finding_reopened": "observation"}
    for reference in body["source_refs"]:
        if body["event_type"] == "clarification_required":
            require(reference["id"] in records, "Missing clarification source")
            kind = records[reference["id"]]["record_type"]
        else:
            kind = kinds[body["event_type"]]
        source = resolve_record(reference, records, kind)
        validate_record(source)
        require(source["finding"] == event["finding"] and source["environment"] == event["environment"]
                and source["profile_ref"] == event["profile_ref"], "Event source scope mismatch")
        require(timestamp(source["recorded_at"]) <= timestamp(event["recorded_at"]), "Event source recorded later")
        if body["event_type"] in ("finding_opened", "finding_reopened"):
            require(source["body"]["result"] == "fail" and source["body"]["acceptance"]["outcome"] == "accepted", "Opening requires accepted criterion FAIL")
