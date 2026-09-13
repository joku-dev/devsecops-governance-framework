"""Fabricate labelled waiver and consent fixtures; never authenticate live authority."""
from copy import deepcopy
from datetime import date, timedelta

from .contracts import approval_target, record_ref, versioned_ref
from .exceptions import exception_profile
from .synthetic_actions import resource


def exception_packet(profile, observations, *, record_id, revision, at, waiver_id="synthetic-waiver:demo",
                     risk="medium", expiry="2026-09-13", valid_from=None, disposition="approve", previous=None,
                     previous_resources=None):
    binding_profile = exception_profile()
    binding = binding_profile["bindings"][risk]
    subjects = sorted(binding["subjects"])
    finding = observations[0]["finding"]
    waiver = {"id": waiver_id, "environment": "synthetic", "scope": finding["key"]["resource"],
              "object_id": finding["finding_id"], "affected_requirements": ["GRS-002"], "risk_classification": risk,
              "justification": "Synthetic temporary risk acceptance for named observations only.",
              "compensating_controls": ["Synthetic manual review evidence retained."],
              "approval_authority": binding["authority"], "approved_by": ",".join(subjects), "approved_on": at[:10],
              "expiry": expiry, "expired": False, "status": "rejected" if disposition == "reject" else "approved"}
    waiver_ref, resources = resource(waiver)
    body = {"expected_revision": revision, "waiver_ref": waiver_ref,
            "covered_observation_refs": sorted((record_ref(r) for r in observations), key=lambda r: r["id"]),
            "valid_from": valid_from or at, "expires_at": (date.fromisoformat(expiry) + timedelta(days=1)).isoformat() + "T00:00:00Z"}
    if previous is not None:
        body = {**deepcopy(previous["body"]), "expected_revision": revision, "supersedes_ref": record_ref(previous)}
        uri = body["waiver_ref"]["uri"]
        resources = {uri: previous_resources[uri]}
    record = {"schema_version": "0.1.0", "record_type": "exception", "record_id": record_id, "environment": "synthetic",
              "profile_ref": versioned_ref(profile, "profile_id"), "finding": deepcopy(finding), "recorded_at": at, "body": body}
    approval = {"target_digest": approval_target(record), "finding_id": finding["finding_id"], "expected_revision": revision,
                "authority": binding["authority"], "subjects": subjects, "subject_type": "human",
                "exception_profile_ref": versioned_ref(binding_profile, "profile_id"), "channel": "synthetic_fixture",
                "issued_at": at, "disposition": disposition}
    proof, proof_resources = resource({"environment": "synthetic", "approval": deepcopy(approval)})
    approval["proof_ref"] = proof
    record["approval"] = approval
    resources.update(proof_resources)
    return record, resources
