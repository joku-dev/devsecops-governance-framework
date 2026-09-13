"""Synthetic consent/withdrawal and remediation acceptance; no live authorization."""
from copy import deepcopy
import base64

from .adapter import strict_json
from .contracts import (
    canonical_digest, check_event_references, fixture_resource, record_ref,
    require, resolve_record, schema_validator, timestamp, validate_test_record, versioned_ref,
)
from .kernel import current_revision, transaction_ref


def progress_statement(record):
    target = deepcopy(record)
    target["body"].pop("progress_evidence_ref", None)
    return {"environment": "synthetic", "remediation_record_digest": canonical_digest(target)}


def latest_approval(state, finding_id):
    approvals = [r for r in state["actions"].values() if r["record_type"] == "decision"
                 and r["finding"]["finding_id"] == finding_id and r["approval"]["disposition"] == "approve"]
    return approvals[-1] if approvals else None


def validate_decision(record, resources, state):
    body = record["body"]
    plan = body["remediation_plan"]
    observation = resolve_record(body["observation_ref"], state["observations"], "observation")
    require(observation["finding"] == record["finding"] and observation["profile_ref"] == record["profile_ref"],
            "Decision observation scope/profile mismatch")
    require(observation["body"]["result"] == "fail", "Decision must reference an accepted failure")
    require(body["action"] == plan["action"], "Decision action differs from the bound plan")
    if record["approval"]["disposition"] == "approve":
        require(timestamp(plan["target_at"]) >= timestamp(record["approval"]["issued_at"]), "Plan deadline predates consent")
    fixture_resource(plan["work_ref"], resources)
    fid = record["finding"]["finding_id"]
    latest = latest_approval(state, fid)
    predecessor = body.get("supersedes_ref")
    disposition = record["approval"]["disposition"]
    if disposition == "reject":
        require(predecessor is None, "A rejected proposal cannot supersede an approval")
        return
    if predecessor is not None:
        previous = resolve_record(predecessor, state["actions"], "decision")
        require(latest is not None and predecessor == record_ref(latest), "Supersession must name the latest approved decision")
        require(previous["finding"] == record["finding"] and previous["profile_ref"] == record["profile_ref"],
                "Supersession scope/profile mismatch")
    else:
        require(latest is None, "Replacement approval must reference its predecessor")
    if disposition == "revoke":
        require(latest is not None and state["decision_status"][latest["record_id"]] == "approved",
                "Only the currently active approval can be withdrawn")
        require(all(body[k] == latest["body"][k] for k in ("observation_ref", "action", "remediation_plan")),
                "Withdrawal must identify the unchanged approved plan")
    else:
        used = {r["body"]["remediation_plan"]["remediation_id"] for r in state["actions"].values()
                if r["record_type"] == "decision" and r["approval"]["disposition"] == "approve"}
        require(plan["remediation_id"] not in used, "Replacement approval requires a new remediation case")


def validate_remediation(record, resources, state):
    body = record["body"]
    decision = resolve_record(body["decision_ref"], state["actions"], "decision")
    require(state["decision_status"].get(decision["record_id"]) == "approved", "Remediation approval is not active")
    require(decision["finding"] == record["finding"] and decision["profile_ref"] == record["profile_ref"],
            "Remediation decision scope/profile mismatch")
    plan = decision["body"]["remediation_plan"]
    require(all(body[k] == value for k, value in plan.items()), "Remediation differs from the approved plan")
    require(timestamp(decision["recorded_at"]) <= timestamp(record["recorded_at"]), "Remediation predates decision")
    previous = state["remediation_heads"].get(body["remediation_id"])
    if previous is None:
        require("supersedes_ref" not in body and body["progress"] == "planned", "Initial remediation must be planned without a predecessor")
    else:
        require(body.get("supersedes_ref") == record_ref(previous), "Remediation predecessor is not the accepted latest revision")
        require(body["decision_ref"] == previous["body"]["decision_ref"], "Remediation updates cannot switch their authorization")
        next_progress = {"planned": "in_progress", "in_progress": "completed"}.get(previous["body"]["progress"])
        require(body["progress"] == next_progress, "Invalid remediation progress transition")
    proof = strict_json(fixture_resource(body["progress_evidence_ref"], resources))
    require(proof == progress_statement(record), "Synthetic progress proof mismatch")


def action_event(record, state):
    fid = record["finding"]["finding_id"]
    previous = state["events"][fid][-1]
    event_type = "decision_recorded" if record["record_type"] == "decision" else "remediation_recorded"
    effective_at = record["approval"]["issued_at"] if record["record_type"] == "decision" else record["recorded_at"]
    body = {"event_type": event_type, "revision": previous["body"]["revision"] + 1,
            "expected_revision": previous["body"]["revision"], "previous_event_ref": record_ref(previous),
            "effective_at": effective_at, "policy_version": previous["body"]["policy_version"],
            "source_refs": [record_ref(record)]}
    event = {"schema_version": "0.1.0", "record_type": "event", "environment": "synthetic",
             "profile_ref": record["profile_ref"], "finding": record["finding"],
             "recorded_at": record["recorded_at"], "body": body}
    event["record_id"] = "event:" + canonical_digest(event)
    records = {**state["observations"], **state["actions"], record["record_id"]: record,
               **{e["record_id"]: e for es in state["events"].values() for e in es}}
    check_event_references(event, records)
    return event


def prepare_action_transaction(record, resources, profile, state, *, expected_revision):
    require(record.get("record_type") in ("decision", "remediation") and record.get("schema_version") == "0.2.0",
            "CLG-03 accepts version 0.2.0 decisions/remediations only")
    validate_test_record(record, profile, resources)
    body = record["body"]
    if record["record_type"] == "decision":
        required_uris = {record["approval"]["proof_ref"]["uri"], body["remediation_plan"]["work_ref"]["uri"]}
    else:
        required_uris = {body["work_ref"]["uri"], body["progress_evidence_ref"]["uri"]}
    require(set(resources) == required_uris and len(resources) == 2, "Exactly the two bound action resources are required")
    if record["record_type"] == "decision":
        fixture_resource(body["remediation_plan"]["work_ref"], resources)
    else:
        fixture_resource(body["progress_evidence_ref"], resources)
    previous = state["actions"].get(record["record_id"])
    if previous:
        require(previous == record, "Action ID already binds different immutable content")
        # No new acceptance: in particular, retrying a revoked approval cannot reactivate it.
        return None
    fid = record["finding"]["finding_id"]
    revision = current_revision(state, fid)
    require(revision > 0, "An accepted open finding is required")
    require(type(expected_revision) is int and expected_revision == body["expected_revision"] == revision,
            "Stale expected finding revision")
    require(timestamp(record["recorded_at"]) >= timestamp(state["transactions"][-1]["recorded_at"]),
            "Action recording time predates accepted ledger head")
    if record["record_type"] == "decision":
        require(timestamp(record["approval"]["issued_at"]) >= timestamp(state["events"][fid][-1]["recorded_at"]),
                "Consent predates the accepted finding revision")
        validate_decision(record, resources, state)
    else:
        validate_remediation(record, resources, state)
    transaction = {"schema_version": "0.2.0", "environment": "synthetic", "sequence": len(state["transactions"]) + 1,
                   "previous_ref": transaction_ref(state["transactions"][-1]),
                   "profile_ref": versioned_ref(profile, "profile_id"), "recorded_at": record["recorded_at"],
                   "expected_revision": expected_revision, "outcome": "accepted",
                   "reason": "decision_recorded" if record["record_type"] == "decision" else "remediation_recorded",
                   "record": deepcopy(record),
                   "resources": {uri: base64.b64encode(data).decode("ascii") for uri, data in sorted(resources.items())},
                   "event": action_event(record, state)}
    transaction["transaction_id"] = "transaction:" + canonical_digest(transaction)
    schema_validator("action-transaction").validate(transaction)
    return transaction


def apply_action(transaction, state):
    record = transaction["record"]
    state["actions"][record["record_id"]] = record
    if record["record_type"] == "decision":
        disposition = record["approval"]["disposition"]
        predecessor = record["body"].get("supersedes_ref")
        if disposition == "revoke":
            state["decision_status"][predecessor["id"]] = "revoked"
        elif disposition == "approve" and predecessor and state["decision_status"][predecessor["id"]] == "approved":
            state["decision_status"][predecessor["id"]] = "superseded"
        state["decision_status"][record["record_id"]] = {"approve": "approved", "reject": "rejected", "revoke": "withdrawal_recorded"}[disposition]
    else:
        state["remediation_heads"][record["body"]["remediation_id"]] = record


def add_action_projection(index, state, as_of):
    index["schema_version"] = "0.2.0"
    index["counts"]["decisions"] = sum(r["record_type"] == "decision" for r in state["actions"].values())
    index["counts"]["remediations"] = sum(r["record_type"] == "remediation" for r in state["actions"].values())
    for finding in index["findings"]:
        fid = finding["finding_id"]
        decisions = [r for r in state["actions"].values() if r["record_type"] == "decision" and r["finding"]["finding_id"] == fid]
        active = [r for r in decisions if state["decision_status"][r["record_id"]] == "approved"]
        finding["active_decision_ref"] = record_ref(active[0]) if active else None
        finding["decision_records"] = [{"record_ref": record_ref(r), "disposition": r["approval"]["disposition"],
                                        "effective_status": state["decision_status"][r["record_id"]]} for r in decisions]
        cases = []
        for case_id, record in sorted(state["remediation_heads"].items()):
            if record["finding"]["finding_id"] != fid:
                continue
            body = record["body"]
            cases.append({"remediation_id": case_id, "latest_record_ref": record_ref(record),
                          "decision_ref": body["decision_ref"], "owner_id": body["owner_id"], "target_at": body["target_at"],
                          "progress": body["progress"], "authorization_status": state["decision_status"][body["decision_ref"]["id"]],
                          "overdue": body["progress"] != "completed" and timestamp(as_of) > timestamp(body["target_at"])})
        finding["remediation_cases"] = cases
