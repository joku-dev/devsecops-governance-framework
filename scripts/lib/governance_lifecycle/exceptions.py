"""Synthetic observation-bound risk acceptance. Never a waiver-based finding closure."""
import base64
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import re

from jsonschema import Draft202012Validator
import yaml

from .adapter import strict_json
from .contracts import (ROOT, FORMAT_CHECKER, approval_target, canonical_digest, check_event_references,
                        fixture_resource, record_ref, require, resolve_record, schema_validator,
                        timestamp, validate_test_record, versioned_ref)
from .kernel import current_revision, transaction_ref

EXCEPTION_PROFILE = ROOT / "model/governance/lifecycle/synthetic-exception-profile.json"


def exception_profile():
    profile = strict_json(EXCEPTION_PROFILE.read_bytes())
    schema_validator("exception-profile").validate(profile)
    require(hashlib.sha256(profile["authority_model"].encode()).hexdigest() == profile["source_digest"],
            "Exception authority snapshot digest mismatch")
    authorities = yaml.safe_load(profile["authority_model"])["authorities"]
    require(set(authorities) == set(profile["bindings"]), "Exception authority snapshot risk classes differ")
    for risk, binding in profile["bindings"].items():
        require(binding["authority"] == authorities[risk]["approval_authority"], "Exception authority snapshot binding mismatch")
        require(len(binding["subjects"]) == (2 if risk == "critical" else 1), "Joint critical authority requires two distinct test subjects")
    return profile


def read_waiver(record, resources):
    waiver = strict_json(fixture_resource(record["body"]["waiver_ref"], resources))
    schema = strict_json((ROOT / "schemas/waiver.schema.json").read_bytes())
    Draft202012Validator(schema, format_checker=FORMAT_CHECKER).validate(waiver)
    require(waiver.get("environment") == "synthetic", "Waiver must be explicitly synthetic")
    require(waiver["scope"] == record["finding"]["key"]["resource"] and waiver["object_id"] == record["finding"]["finding_id"],
            "Waiver scope/object mismatch")
    require(waiver["affected_requirements"] == ["GRS-002"], "Unsupported waiver requirement mapping")
    require(re.fullmatch(r"synthetic-waiver:[a-zA-Z0-9._-]+", waiver["id"]) is not None and bool(waiver["compensating_controls"])
            and all(str(c).strip() for c in waiver["compensating_controls"]), "Synthetic waiver identity and compensating controls required")
    return waiver


def transaction_resources(transaction):
    return {uri: base64.b64decode(data, validate=True) for uri, data in transaction["resources"].items()}


def prepare_exception_transaction(record, resources, profile, state, *, expected_revision):
    require(record.get("record_type") == "exception" and record.get("schema_version") == "0.1.0", "Unsupported exception record")
    validate_test_record(record, profile, resources)
    approval, body = record["approval"], record["body"]
    require(set(resources) == {approval["proof_ref"]["uri"], body["waiver_ref"]["uri"]} and len(resources) == 2,
            "Exactly waiver and consent fixture resources are required")
    bound_profile = exception_profile()
    waiver = read_waiver(record, resources)
    binding = bound_profile["bindings"][waiver["risk_classification"]]
    require(approval["exception_profile_ref"] == versioned_ref(bound_profile, "profile_id"), "Exception profile binding mismatch")
    require(approval["authority"] == waiver["approval_authority"] == binding["authority"], "Wrong waiver approval authority")
    require(approval["subjects"] == sorted(binding["subjects"]), "Waiver consent does not include exactly the assigned subjects")
    require(waiver["approved_by"] == ",".join(approval["subjects"]), "Waiver approved_by does not bind subjects")
    require(approval["target_digest"] == approval_target(record), "Exception content binding mismatch")
    require(approval["finding_id"] == record["finding"]["finding_id"] and approval["expected_revision"] == body["expected_revision"],
            "Exception approval scope/revision mismatch")
    require(timestamp(approval["issued_at"]) <= timestamp(record["recorded_at"]), "Exception consent after recording")
    proof = strict_json(fixture_resource(approval["proof_ref"], resources))
    require(proof == {"environment": "synthetic", "approval": {k: v for k, v in approval.items() if k != "proof_ref"}},
            "Synthetic exception consent proof mismatch")
    previous = state["exceptions"].get(record["record_id"])
    if previous is not None:
        require(previous == record, "Exception ID already binds different immutable content")
        return None
    fid = record["finding"]["finding_id"]
    revision = current_revision(state, fid)
    require(type(expected_revision) is int and expected_revision == body["expected_revision"] == revision and revision > 0,
            "Stale expected finding revision")
    require(timestamp(record["recorded_at"]) >= timestamp(state["transactions"][-1]["recorded_at"]), "Exception predates ledger head")
    require(timestamp(approval["issued_at"]) >= timestamp(state["events"][fid][-1]["recorded_at"]), "Exception consent predates finding head")
    covered = [resolve_record(ref, state["observations"], "observation") for ref in body["covered_observation_refs"]]
    require(all(r["finding"] == record["finding"] and r["profile_ref"] == record["profile_ref"]
                and r["body"]["result"] == "fail" for r in covered), "Coverage must bind accepted failures of this finding/profile")
    require(body["covered_observation_refs"] == sorted(body["covered_observation_refs"], key=lambda ref: ref["id"]), "Coverage references must be sorted")
    expires = (date.fromisoformat(waiver["expiry"]) + timedelta(days=1)).isoformat() + "T00:00:00Z"
    require(body["expires_at"] == expires and timestamp(body["valid_from"]) < timestamp(expires), "Waiver expiry mapping/window mismatch")
    disposition = approval["disposition"]
    predecessor = body.get("supersedes_ref")
    if disposition == "revoke":
        require(predecessor is not None, "Withdrawal requires original grant reference")
        grant = resolve_record(predecessor, state["exceptions"], "exception")
        require(grant["approval"]["disposition"] == "approve" and grant["record_id"] not in state["revoked_exceptions"],
                "Only a previously approved, not yet withdrawn grant can be revoked")
        require(grant["finding"] == record["finding"] and grant["profile_ref"] == record["profile_ref"]
                and all(body[k] == grant["body"][k] for k in ("waiver_ref", "covered_observation_refs", "valid_from", "expires_at")),
                "Withdrawal must bind unchanged grant scope/content")
    else:
        require(predecessor is None, "New approvals/rejections cannot rewrite a grant; renewal requires a new waiver")
        require(fid not in state["active_closures"], "Finding is closed; no new exception treatment")
        require(waiver["approved_on"] == approval["issued_at"][:10], "Waiver approval date differs from consent")
        require(waiver["status"] == ("approved" if disposition == "approve" else "rejected") and waiver["expired"] is False,
                "Waiver status differs from consent disposition")
        require(timestamp(body["valid_from"]) >= timestamp(record["recorded_at"]), "Exception cannot grant retroactive coverage")
        if disposition == "approve":
            require(timestamp(expires) > timestamp(record["recorded_at"]), "Exception already expired at acceptance")
            for existing in state["exceptions"].values():
                if existing["approval"]["disposition"] == "approve":
                    require(state["exception_waivers"][existing["record_id"]]["id"] != waiver["id"], "Renewal requires a fresh waiver ID")
            outstanding = outstanding_failures(state, fid)
            require(all(r["record_id"] in outstanding for r in covered), "Cannot grant coverage for a previous closed episode")
    previous_event = state["events"][fid][-1]
    event = {"schema_version": "0.2.0", "record_type": "event", "environment": "synthetic",
             "profile_ref": deepcopy(record["profile_ref"]), "finding": deepcopy(record["finding"]), "recorded_at": record["recorded_at"],
             "body": {"event_type": "exception_recorded", "revision": revision + 1, "expected_revision": revision,
                      "previous_event_ref": record_ref(previous_event), "effective_at": approval["issued_at"],
                      "policy_version": previous_event["body"]["policy_version"], "source_refs": [record_ref(record)]}}
    event["record_id"] = "event:" + canonical_digest(event)
    check_event_references(event, {record["record_id"]: record, previous_event["record_id"]: previous_event})
    tx = {"schema_version": "0.4.0", "environment": "synthetic", "sequence": len(state["transactions"]) + 1,
          "previous_ref": transaction_ref(state["transactions"][-1]), "profile_ref": versioned_ref(profile, "profile_id"),
          "recorded_at": record["recorded_at"], "expected_revision": revision, "outcome": "accepted", "reason": "exception_recorded",
          "record": deepcopy(record), "event": event,
          "resources": {uri: base64.b64encode(data).decode("ascii") for uri, data in sorted(resources.items())}}
    tx["transaction_id"] = "transaction:" + canonical_digest(tx)
    schema_validator("exception-transaction").validate(tx)
    return tx


def apply_exception(transaction, state):
    record = transaction["record"]
    state["exceptions"][record["record_id"]] = record
    state["exception_waivers"][record["record_id"]] = read_waiver(record, transaction_resources(transaction))
    if record["approval"]["disposition"] == "revoke":
        state["revoked_exceptions"].add(record["body"]["supersedes_ref"]["id"])


def outstanding_failures(state, fid):
    closures = [c for c in state["closures"].values() if c["finding"]["finding_id"] == fid]
    cutoff = state["observations"][closures[-1]["body"]["passing_observation_ref"]["id"]]["body"]["observed_at"] if closures else None
    return {r["record_id"]: r for r in state["observations"].values() if r["finding"]["finding_id"] == fid
            and r["body"]["result"] == "fail" and (cutoff is None or timestamp(r["body"]["observed_at"]) > timestamp(cutoff))}


def effective_exception_status(record, state, as_of):
    disposition = record["approval"]["disposition"]
    if disposition != "approve":
        return "rejected" if disposition == "reject" else "withdrawal_recorded"
    if record["record_id"] in state["revoked_exceptions"]:
        return "revoked"
    if timestamp(as_of) >= timestamp(record["body"]["expires_at"]):
        return "expired"
    return "scheduled" if timestamp(as_of) < timestamp(record["body"]["valid_from"]) else "active"


def add_exception_projection(index, state, as_of):
    # Supply a complete v0.4 projection even when this scenario has no remediation or closure yet.
    from .decisions import add_action_projection
    from .closure import add_closure_projection
    add_action_projection(index, state, as_of)
    add_closure_projection(index, state)
    index["schema_version"] = "0.4.0"
    index["counts"]["exceptions"] = len(state["exceptions"])
    for finding in index["findings"]:
        fid = finding["finding_id"]
        outstanding = outstanding_failures(state, fid)
        records, covered, ended = [], set(), set()
        for record in state["exceptions"].values():
            if record["finding"]["finding_id"] != fid:
                continue
            body = record["body"]
            status = effective_exception_status(record, state, as_of)
            ids = {ref["id"] for ref in body["covered_observation_refs"]}
            if status == "active": covered.update(ids & outstanding.keys())
            if status in ("expired", "revoked"): ended.update(ids & outstanding.keys())
            waiver = state["exception_waivers"][record["record_id"]]
            records.append({"record_ref": record_ref(record), "disposition": record["approval"]["disposition"],
                            "status": status, "valid_from": body["valid_from"], "expires_at": body["expires_at"],
                            "risk_classification": waiver["risk_classification"], "waiver_id": waiver["id"],
                            "covered_observation_refs": deepcopy(body["covered_observation_refs"])})
        uncovered = outstanding.keys() - covered
        finding["exception_treatment"] = {
            "coverage": "not_applicable" if not outstanding else "full" if not uncovered else "partial" if covered else "none",
            "covered_observation_refs": [record_ref(outstanding[i]) for i in sorted(covered)],
            "uncovered_observation_refs": [record_ref(outstanding[i]) for i in sorted(uncovered)],
            "renewed_decision_required": bool(ended - covered), "exception_records": records}
