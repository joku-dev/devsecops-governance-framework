"""Preserve explicit control outcomes; never infer them from gate summaries."""
from .adapter import strict_json
from .candidates import check_context, make_candidates
from .contracts import require, schema_validator


def adapt_devsecops(report_bytes, context, *, evaluated_at):
    check_context(report_bytes, context, evaluated_at=evaluated_at)
    report = strict_json(report_bytes)
    schema_validator("devsecops-source").validate(report)
    for field in ("event", "purpose", "release_context"):
        require(report["run_context"][field] == context[field], "Producer/context mismatch: " + field)
    require(report["run_context"].get("source") != "demo" or context["synthetic"] is True,
            "Demo report requires declared synthetic context")
    controls = report["controls"]
    ids = [c["control_id"] for c in controls]
    require(len(ids) == len(set(ids)), "Duplicate control IDs are ambiguous")
    for control in controls:
        require(control["control_id"].startswith("DSCB-" + control["level"] + "-REQ-"), "Control ID/level mismatch")
    expected = {status: sum(c["status"] == status for c in controls) for status in ("pass", "fail", "not_tested", "not_applicable")}
    expected.update(total_controls=len(controls), applicable_controls=len(controls)-expected["not_applicable"],
                    tested_controls=expected["pass"]+expected["fail"])
    require(report["summary"] == expected, "Summary differs from declared control rows")
    outcomes = [{"rule_id": c["control_id"], "result": c["status"], "source_pointer": f"/controls/{i}",
                 "source_messages": [c["message"]] if c.get("message") else []} for i, c in enumerate(controls)]
    return make_candidates(report_bytes, context, outcomes, evaluated_at=evaluated_at,
                           adapter_id="devsecops-control-candidates", source_contract="control-evaluation-report@1.0.0",
                           domain="devsecops", granularity="control")
