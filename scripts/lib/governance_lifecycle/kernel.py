"""Deterministic synthetic lifecycle reduction; live authority is unavailable."""
from copy import deepcopy
import base64

from .contracts import (
    canonical_digest, check_event_references, observation_identity, record_ref,
    require, schema_validator, timestamp, validate_test_profile, validate_test_record, versioned_ref,
)


def producer_digest(observation):
    body = observation["body"]
    payload = {key: body[key] for key in (
        "observed_at", "result", "rule_key", "granularity", "profile_version",
        "policy_version", "source_schema", "source_context")}
    payload["snapshot_digest"] = body["snapshot_ref"]["digest"]
    return canonical_digest(payload)


def transaction_ref(transaction):
    return {"id": transaction["transaction_id"], "digest": canonical_digest(transaction)}


def transaction_name(transaction):
    return f'{transaction["sequence"]:08d}-{transaction["transaction_id"].split(":")[1]}.json'


def empty_state():
    return {"transactions": [], "observations": {}, "deliveries": {}, "events": {}, "conflicts": [],
            "actions": {}, "decision_status": {}, "remediation_heads": {}, "closures": {}, "active_closures": {}}


def current_revision(state, finding):
    events = state["events"].get(finding, [])
    return events[-1]["body"]["revision"] if events else 0


def classify(observation, state):
    identity = observation_identity(observation)
    prior = state["deliveries"].get(identity)
    if prior:
        if producer_digest(prior) != producer_digest(observation):
            return "producer_conflict"
        if canonical_digest(prior["body"]["trust"]) != canonical_digest(observation["body"]["trust"]):
            return "reassessment_required"
        return "duplicate"
    candidates = [r for r in state["observations"].values() if r["finding"] == observation["finding"]]
    body = observation["body"]
    for previous in candidates:
        other = previous["body"]
        if any(body[k] != other[k] for k in ("profile_version", "policy_version", "source_schema")):
            return "incompatible_version"
        if body["observed_at"] == other["observed_at"] and body["result"] != other["result"]:
            return "ambiguous_time"
    return "new_observation"


def make_event(observation, state, reason):
    fid = observation["finding"]["finding_id"]
    events = state["events"].get(fid, [])
    conflict = reason != "new_observation"
    if not events and (conflict or observation["body"]["result"] != "fail"):
        return None
    event_type = "clarification_required" if conflict else ("observation_added" if events else "finding_opened")
    if not conflict and state["active_closures"]:
        from .closure import reopens
        if reopens(observation, state):
            event_type = "finding_reopened"
    source = observation
    if conflict:
        # Quarantined input is retained in its transaction, not accepted as an event source.
        source = next(r for r in state["observations"].values() if r["finding"] == observation["finding"])
    body = {"event_type": event_type, "revision": len(events) + 1, "expected_revision": len(events),
            "previous_event_ref": record_ref(events[-1]) if events else None,
            "effective_at": observation["body"]["observed_at"],
            "policy_version": source["body"]["policy_version"], "source_refs": [record_ref(source)]}
    event = {"schema_version": "0.1.0", "record_type": "event", "environment": "synthetic",
             "profile_ref": observation["profile_ref"], "finding": observation["finding"],
             "recorded_at": observation["recorded_at"], "body": body}
    event["record_id"] = "event:" + canonical_digest(event)
    records = {**state["observations"], **{e["record_id"]: e for es in state["events"].values() for e in es}}
    if not conflict:
        records[observation["record_id"]] = observation
    check_event_references(event, records)
    return event


def prepare_transaction(observation, resources, profile, state, *, expected_revision):
    require(observation.get("record_type") == "observation", "CLG-02 accepts observations only")
    validate_test_record(observation, profile, resources)
    require(observation["body"]["acceptance"]["outcome"] == "accepted", "Observation is not accepted by the synthetic profile")
    required_uris = {observation["body"]["snapshot_ref"]["uri"], observation["body"]["acceptance"]["proof_ref"]["uri"]}
    require(set(resources) == required_uris and len(resources) == 2, "Exactly snapshot and acceptance resources are required")
    reason = classify(observation, state)
    if reason == "duplicate":
        return None
    # Repeated quarantined delivery also remains idempotent, without losing the first proof.
    for transaction in state["conflicts"]:
        other = transaction["observation"]
        if (observation_identity(other) == observation_identity(observation)
                and producer_digest(other) == producer_digest(observation)
                and canonical_digest(other["body"]["trust"]) == canonical_digest(observation["body"]["trust"])):
            return None
    fid = observation["finding"]["finding_id"]
    require(type(expected_revision) is int and expected_revision == current_revision(state, fid), "Stale expected finding revision")
    if state["transactions"]:
        require(timestamp(observation["recorded_at"]) >= timestamp(state["transactions"][-1]["recorded_at"]),
                "Recording time predates the accepted ledger head")
    if reason == "new_observation":
        require(observation["record_id"] not in state["observations"], "Observation ID reused for different producer context")
    event = make_event(observation, state, reason)
    transaction = {
        "schema_version": "0.1.0", "environment": "synthetic", "sequence": len(state["transactions"]) + 1,
        "previous_ref": transaction_ref(state["transactions"][-1]) if state["transactions"] else None,
        "profile_ref": versioned_ref(profile, "profile_id"), "recorded_at": observation["recorded_at"],
        "expected_revision": expected_revision, "outcome": "accepted" if reason == "new_observation" else "quarantined",
        "reason": reason, "observation": deepcopy(observation),
        "resources": {uri: base64.b64encode(data).decode("ascii") for uri, data in sorted(resources.items())},
        "event": event,
    }
    transaction["transaction_id"] = "transaction:" + canonical_digest(transaction)
    schema_validator("transaction").validate(transaction)
    return transaction


def apply_transaction(transaction, state):
    if transaction["schema_version"] == "0.3.0":
        record = transaction["record"]
        state["transactions"].append(transaction)
        state["closures"][record["record_id"]] = record
        fid = record["finding"]["finding_id"]
        state["active_closures"][fid] = record
        state["events"][fid].append(transaction["event"])
        return
    if transaction["schema_version"] == "0.2.0":
        from .decisions import apply_action
        state["transactions"].append(transaction)
        apply_action(transaction, state)
        fid = transaction["record"]["finding"]["finding_id"]
        state["events"].setdefault(fid, []).append(transaction["event"])
        return
    observation = transaction["observation"]
    state["transactions"].append(transaction)
    if transaction["outcome"] == "accepted":
        state["observations"][observation["record_id"]] = observation
        state["deliveries"][observation_identity(observation)] = observation
    else:
        state["conflicts"].append(transaction)
    if transaction["event"]:
        fid = observation["finding"]["finding_id"]
        state["events"].setdefault(fid, []).append(transaction["event"])
        if transaction["event"]["body"]["event_type"] == "finding_reopened":
            state["active_closures"].pop(fid)


def replay(transactions, profile):
    """Verify the complete ordered chain by regenerating each transaction, then reduce."""
    validate_test_profile(profile)
    state = empty_state()
    for transaction in transactions:
        action = transaction.get("schema_version") == "0.2.0"
        closure = transaction.get("schema_version") == "0.3.0"
        schema_validator("closure-transaction" if closure else "action-transaction" if action else "transaction").validate(transaction)
        resources = {uri: base64.b64decode(data, validate=True) for uri, data in transaction["resources"].items()}
        if closure:
            from .closure import prepare_closure_transaction
            expected = prepare_closure_transaction(transaction["record"], resources, profile, state,
                                                   expected_revision=transaction["expected_revision"])
        elif action:
            from .decisions import prepare_action_transaction
            expected = prepare_action_transaction(transaction["record"], resources, profile, state,
                                                  expected_revision=transaction["expected_revision"])
        else:
            expected = prepare_transaction(transaction["observation"], resources, profile, state,
                                           expected_revision=transaction["expected_revision"])
        require(expected is not None, "Duplicate lifecycle packet was persisted")
        require(transaction == expected, "Transaction chain, content, sequence or event mismatch")
        apply_transaction(transaction, state)
    return state


def project(transactions, profile, *, as_of):
    timestamp(as_of)
    replay(transactions, profile)  # Validate even records beyond the projection cut-off.
    visible = [tx for tx in transactions if timestamp(tx["recorded_at"]) <= timestamp(as_of)]
    state = replay(visible, profile)
    findings = []
    for fid, events in sorted(state["events"].items()):
        observations = [r for r in state["observations"].values() if r["finding"]["finding_id"] == fid]
        failures = [r for r in observations if r["body"]["result"] == "fail"]
        latest = max(observations, key=lambda r: (r["body"]["observed_at"], r["record_id"]))
        conflicts = [tx for tx in state["conflicts"] if tx["observation"]["finding"]["finding_id"] == fid]
        first_fail = min(failures, key=lambda r: (r["body"]["observed_at"], r["record_id"]))
        findings.append({"finding_id": fid, "identity": latest["finding"],
                         "state": "needs_clarification" if conflicts else "open",
                         "revision": current_revision(state, fid), "occurrences": len(failures),
                         "first_failure_ref": record_ref(first_fail), "latest_observation_ref": record_ref(latest),
                         "last_event_ref": record_ref(events[-1]), "evidence_status": latest["body"]["result"],
                         "observation_refs": sorted((record_ref(r) for r in observations), key=lambda r: r["id"]),
                         "conflict_refs": [transaction_ref(t) for t in conflicts], "closure_supported": False})
    index = {"schema_version": "0.1.0", "index_type": "governance-lifecycle-synthetic", "environment": "synthetic",
             "official_state": False, "enforcement": "report_only", "as_of": as_of,
             "profile_ref": versioned_ref(profile, "profile_id"),
             "ledger_head_ref": transaction_ref(visible[-1]) if visible else None,
             "counts": {"transactions": len(visible), "observations": len(state["observations"]),
                        "events": sum(len(es) for es in state["events"].values()),
                        "conflicts": len(state["conflicts"]), "findings": len(findings)},
             "findings": findings, "conflict_refs": [transaction_ref(tx) for tx in state["conflicts"]]}
    if state["actions"]:
        from .decisions import add_action_projection
        add_action_projection(index, state, as_of)
    if state["closures"]:
        from .closure import add_closure_projection
        add_closure_projection(index, state)
    schema_validator("closure-index" if state["closures"] else "action-index" if state["actions"] else "index").validate(index)
    return index
