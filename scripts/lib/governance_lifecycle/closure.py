"""Synthetic evidence-bound closure acceptance. No live authentication or waiver closure."""
import base64
from copy import deepcopy

from .adapter import strict_json
from .contracts import (
    canonical_digest, check_closure_prerequisites, check_event_references, fixture_resource,
    record_ref, require, resolve_record, schema_validator, timestamp, validate_test_record, versioned_ref,
)
from .kernel import current_revision, transaction_ref


def accepted_resources(state):
    resources = {}
    for transaction in state["transactions"]:
        if transaction["outcome"] == "accepted":
            for uri, content in transaction["resources"].items():
                data = base64.b64decode(content, validate=True)
                require(uri not in resources or resources[uri] == data, "Accepted resource URI changed content")
                resources[uri] = data
    return resources


def prepare_closure_transaction(record, resources, profile, state, *, expected_revision):
    require(record.get("record_type") == "closure" and record.get("schema_version") == "0.2.0",
            "Closure intake requires the synthetic 0.2.0 closure contract")
    validate_test_record(record, profile, resources)
    require(set(resources) == {record["approval"]["proof_ref"]["uri"]}, "Only the bound closure consent resource is accepted")
    strict_json(fixture_resource(record["approval"]["proof_ref"], resources))
    previous = state["closures"].get(record["record_id"])
    if previous is not None:
        require(previous == record, "Closure ID already binds different immutable content")
        return None
    fid = record["finding"]["finding_id"]
    body = record["body"]
    revision = current_revision(state, fid)
    require(type(expected_revision) is int and expected_revision == body["expected_revision"] == revision and revision > 0,
            "Stale expected finding revision")
    require(fid not in state["active_closures"], "Finding already closed")
    require(not any(t["observation"]["finding"]["finding_id"] == fid for t in state["conflicts"]),
            "Unresolved evidence conflict prevents closure")
    require(body["as_of"] == record["recorded_at"], "Closure as_of must equal acceptance recording time")
    require(timestamp(record["recorded_at"]) >= timestamp(state["transactions"][-1]["recorded_at"]),
            "Closure predates accepted ledger head")
    require(timestamp(record["approval"]["issued_at"]) >= timestamp(state["events"][fid][-1]["recorded_at"]),
            "Closure consent predates accepted finding revision")
    records = {**state["observations"], **state["actions"]}
    remediation = resolve_record(body["remediation_ref"], records, "remediation")
    require(state["remediation_heads"].get(remediation["body"]["remediation_id"]) == remediation,
            "Closure must reference latest remediation revision")
    decision = resolve_record(remediation["body"]["decision_ref"], records, "decision")
    require(state["decision_status"].get(decision["record_id"]) == "approved", "Closure remediation approval is not active")
    passing = resolve_record(body["passing_observation_ref"], records, "observation")
    observations = [r for r in state["observations"].values() if r["finding"]["finding_id"] == fid]
    latest = max(observations, key=lambda r: (r["body"]["observed_at"], r["record_id"]))
    require(latest == passing, "Closure must use the latest accepted observation")
    failures = [r for r in observations if r["body"]["result"] == "fail"]
    require(all(timestamp(r["body"]["observed_at"]) < timestamp(passing["body"]["observed_at"]) for r in failures),
            "PASS must follow every accepted failure")
    require(all(timestamp(r["body"]["observed_at"]) <= timestamp(remediation["recorded_at"]) for r in failures),
            "Remediation must follow every accepted failure")
    prior_closures = [c for c in state["closures"].values() if c["finding"]["finding_id"] == fid]
    if prior_closures:
        last = prior_closures[-1]
        require(timestamp(decision["recorded_at"]) > timestamp(last["recorded_at"]), "Reopened finding requires a new decision")
    evidence = accepted_resources(state)
    for uri, data in resources.items():
        require(uri not in evidence or evidence[uri] == data, "Closure resource shadows accepted evidence")
        evidence[uri] = data
    check_closure_prerequisites(record, records, profile, evidence, as_of=body["as_of"])
    previous_event = state["events"][fid][-1]
    event = {"schema_version": "0.1.0", "record_type": "event", "environment": "synthetic",
             "profile_ref": deepcopy(record["profile_ref"]), "finding": deepcopy(record["finding"]),
             "recorded_at": record["recorded_at"], "body": {
                 "event_type": "finding_closed", "revision": revision + 1, "expected_revision": revision,
                 "previous_event_ref": record_ref(previous_event), "effective_at": record["approval"]["issued_at"],
                 "policy_version": passing["body"]["policy_version"], "source_refs": [record_ref(record)]}}
    event["record_id"] = "event:" + canonical_digest(event)
    check_event_references(event, {**records, record["record_id"]: record, previous_event["record_id"]: previous_event})
    transaction = {"schema_version": "0.3.0", "environment": "synthetic", "sequence": len(state["transactions"]) + 1,
                   "previous_ref": transaction_ref(state["transactions"][-1]), "profile_ref": versioned_ref(profile, "profile_id"),
                   "recorded_at": record["recorded_at"], "expected_revision": revision, "outcome": "accepted",
                   "reason": "finding_closed", "record": deepcopy(record), "event": event,
                   "resources": {uri: base64.b64encode(data).decode("ascii") for uri, data in sorted(resources.items())}}
    transaction["transaction_id"] = "transaction:" + canonical_digest(transaction)
    schema_validator("closure-transaction").validate(transaction)
    return transaction


def reopens(observation, state):
    closed = state["active_closures"].get(observation["finding"]["finding_id"])
    if closed is None or observation["body"]["result"] != "fail":
        return False
    passing = state["observations"][closed["body"]["passing_observation_ref"]["id"]]
    return timestamp(observation["body"]["observed_at"]) > timestamp(passing["body"]["observed_at"])


def add_closure_projection(index, state):
    index["schema_version"] = "0.3.0"
    index["counts"]["closures"] = len(state["closures"])
    for finding in index["findings"]:
        fid = finding["finding_id"]
        closed = state["active_closures"].get(fid)
        finding["closure_supported"] = True
        finding["closure_refs"] = [record_ref(c) for c in state["closures"].values() if c["finding"]["finding_id"] == fid]
        finding["active_closure_ref"] = record_ref(closed) if closed and not finding["conflict_refs"] else None
        finding["reopen_count"] = sum(e["body"]["event_type"] == "finding_reopened" for e in state["events"][fid])
        if finding["active_closure_ref"] is not None:
            finding["state"] = "closed"
