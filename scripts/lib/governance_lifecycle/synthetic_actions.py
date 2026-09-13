"""Explicit synthetic consent/progress fixtures. Not a human-authentication adapter."""
from copy import deepcopy
import hashlib

from .adapter import json_bytes
from .contracts import approval_target, record_ref, versioned_ref
from .decisions import progress_statement


def resource(value):
    data = json_bytes(value)
    digest = hashlib.sha256(data).hexdigest()
    uri = "fixture://action-" + digest + ".json"
    return {"uri": uri, "digest": digest}, {uri: data}


def decision_packet(profile, observation, *, record_id, revision, at, case_id, disposition="approve", previous=None):
    work, resources = resource({"environment": "synthetic", "case_id": case_id, "work_item": "Synthetic remediation work"})
    plan = {"remediation_id": case_id, "owner_id": "test-human:remediation-owner", "target_at": "2026-09-14T12:00:00Z",
            "action": "Investigate and restore the synthetic GRS-002 review requirement.", "work_ref": work}
    body = {"expected_revision": revision, "purpose": "remediate", "observation_ref": record_ref(observation),
            "action": plan["action"], "rationale": "Synthetic consent only.", "remediation_plan": plan}
    if previous:
        body["supersedes_ref"] = record_ref(previous)
        if disposition == "revoke":
            body.update({k: deepcopy(previous["body"][k]) for k in ("observation_ref", "action", "remediation_plan")})
            work = previous["body"]["remediation_plan"]["work_ref"]
            _, resources = resource({"environment": "synthetic", "case_id": body["remediation_plan"]["remediation_id"], "work_item": "Synthetic remediation work"})
    record = {"schema_version": "0.2.0", "record_type": "decision", "record_id": record_id,
              "environment": "synthetic", "profile_ref": versioned_ref(profile, "profile_id"),
              "finding": deepcopy(observation["finding"]), "recorded_at": at, "body": body}
    binding = profile["role_binding"]
    approval = {"target_digest": approval_target(record), "finding_id": record["finding"]["finding_id"],
                "expected_revision": revision, "subject_id": binding["assignments"]["remediation_decider"],
                "subject_type": "human", "role": "remediation_decider", "role_binding_ref": versioned_ref(binding),
                "channel": "synthetic_fixture", "issued_at": at, "disposition": disposition}
    proof, proof_resources = resource({"environment": "synthetic", "approval": deepcopy(approval)})
    approval["proof_ref"] = proof
    record["approval"] = approval
    resources.update(proof_resources)
    return record, resources


def remediation_packet(decision, decision_resources, *, record_id, revision, at, progress="planned", previous=None):
    body = {**deepcopy(decision["body"]["remediation_plan"]), "expected_revision": revision,
            "decision_ref": record_ref(decision), "progress": progress}
    if previous:
        body["supersedes_ref"] = record_ref(previous)
    record = {"schema_version": "0.2.0", "record_type": "remediation", "record_id": record_id,
              "environment": "synthetic", "profile_ref": deepcopy(decision["profile_ref"]),
              "finding": deepcopy(decision["finding"]), "recorded_at": at, "body": body}
    proof, resources = resource(progress_statement(record))
    body["progress_evidence_ref"] = proof
    uri = body["work_ref"]["uri"]
    resources[uri] = decision_resources[uri]
    return record, resources
