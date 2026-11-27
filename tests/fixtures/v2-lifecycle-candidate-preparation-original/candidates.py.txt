"""Diagnostic normalization, deliberately outside accepted lifecycle contracts."""
from copy import deepcopy
import hashlib

from .contracts import canonical_digest, require, schema_validator, timestamp


def check_context(report_bytes, context, *, evaluated_at):
    schema_validator("candidate-context").validate(context)
    require(hashlib.sha256(report_bytes).hexdigest() == context["report_sha256"], "Report digest differs from declared context")
    require(timestamp(context["observed_at"]) <= timestamp(evaluated_at), "Observation time is after candidate evaluation")
    if context["synthetic"]:
        return "test"
    if context["event"] == "pull_request":
        return "pull_request"
    if context["event"] == "workflow_dispatch":
        return "manual"
    if context["event"] == "release":
        return "release"
    return "mainline" if context["branch"] == "main" else "branch"


def make_candidates(report_bytes, context, outcomes, *, evaluated_at, adapter_id, source_contract, domain, granularity):
    kind = check_context(report_bytes, context, evaluated_at=evaluated_at)
    results = []
    for outcome in outcomes:
        record = {"subject": {"repository_id": context["repository_id"], "domain": domain,
                              "rule_id": outcome["rule_id"], "resource": "repository"},
                  "granularity": granularity, "result": outcome["result"], "source_pointer": outcome["source_pointer"],
                  "source_messages": deepcopy(outcome.get("source_messages", []))}
        record["candidate_id"] = "candidate:" + canonical_digest({"adapter_id": adapter_id,
            "source_contract": source_contract, "context": context, "outcome": record})
        results.append(record)
    report = {"schema_version": "0.1.0", "record_type": "lifecycle-input-candidates", "environment": "diagnostic",
              "official_state": False, "enforcement": "report_only", "acceptance_status": "not_evaluated",
              "trust_status": "unverified", "evaluated_at": evaluated_at,
              "adapter": {"id": adapter_id, "version": "0.1.0", "source_contract": source_contract},
              "source": {"context": deepcopy(context), "declared_context_kind": kind, "size_bytes": len(report_bytes),
                         "age_seconds": int((timestamp(evaluated_at) - timestamp(context["observed_at"])).total_seconds())},
              "counts": {status: sum(r["result"] == status for r in results)
                         for status in ("pass", "fail", "not_tested", "not_applicable", "findings")},
              "candidates": results,
              "acceptance_gaps": ["producer_authentication", "baseline_and_policy_resolution", "approved_scope_and_trust_profile",
                                  "approved_freshness_and_replay_policy", "accountable_live_acceptance"]}
    schema_validator("candidates").validate(report)
    return report
