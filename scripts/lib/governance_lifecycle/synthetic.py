"""Explicitly fabricated packets for tests/demo; not a source of real trust."""
from copy import deepcopy
import hashlib
import json

from .adapter import adapt_grs002, json_bytes
from .contracts import ROOT


def synthetic_packet(profile, *, result, observed_at, recorded_at, run_id, policy_version="0.1.0"):
    example = json.loads((ROOT / "docs/examples/governance-lifecycle/observation-fail.json").read_text())
    report = json.loads((ROOT / "tests/fixtures/governance-lifecycle/resources/synthetic-fail-report.json").read_text())
    report["observed_at"] = observed_at
    criterion = next(c for c in report["criteria"] if c["id"] == "GRS-002")
    criterion.update(status=result, observed=result == "pass")
    report["overall_status"] = "pass" if result == "pass" else "findings"
    count = len(report["criteria"])
    report["summary"].update({"pass": count - int(result == "fail"), "fail": int(result == "fail"),
                              "critical_failures": int(result == "fail")})
    report_bytes = json_bytes(report)
    digest = hashlib.sha256(report_bytes).hexdigest()
    uri = "fixture://report-" + digest + ".json"
    context = deepcopy(example["body"]["source_context"])
    context["run_id"] = run_id
    trust = deepcopy(example["body"]["trust"])
    trust["verified_at"] = observed_at
    for check in trust["checks"]:
        check["evidence_refs"] = [uri]
    capture = trust["capture"]
    capture["captured_at"] = observed_at
    capture["source"].update(run_id=run_id, source_uri=uri)
    capture["subjects"][0].update(evidence_ref=uri, digest=digest, size_bytes=len(report_bytes))
    for step in capture["custody"]:
        step.update(at=observed_at, source_uri=uri, output_refs=[uri])
    return adapt_grs002(report_bytes, context, trust, recorded_at=recorded_at,
                       profile=profile, policy_version=policy_version)
