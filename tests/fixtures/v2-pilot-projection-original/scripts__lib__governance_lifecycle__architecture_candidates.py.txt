"""Candidate gate outcomes from the current unversioned architecture report shape."""
from .adapter import strict_json
from .candidates import check_context, make_candidates
from .contracts import require, schema_validator

GATE_IDS = ("architecture_readiness", "integration_readiness", "operation_readiness", "release_readiness")


def adapt_architecture(report_bytes, context, *, evaluated_at):
    check_context(report_bytes, context, evaluated_at=evaluated_at)
    report = strict_json(report_bytes)
    require("schema_version" not in report, "Versioned architecture producer requires an explicit adapter revision")
    schema_validator("architecture-source").validate(report)
    gates = report["gates"]
    ids = [gate["id"] for gate in gates]
    require(len(ids) == len(set(ids)) and set(ids) == set(GATE_IDS), "Expected exactly the four supported architecture gates")
    require(context["commit_id"].startswith(report["target"]["commit"]), "Declared full commit conflicts with report target commit")
    for gate in gates:
        require(gate["status"] == ("findings" if gate["findings"] else "pass"), "Gate status contradicts finding messages")
        require(all(message.strip() for message in gate["findings"]), "Blank finding message is ambiguous")
    expected = {"gate_count": len(gates), "passed": sum(not gate["findings"] for gate in gates),
                "with_findings": sum(bool(gate["findings"]) for gate in gates),
                "finding_count": sum(len(gate["findings"]) for gate in gates)}
    require(report["summary"] == expected, "Architecture summary differs from explicit gate outcomes")
    outcomes = [{"rule_id": gate["id"], "result": gate["status"], "source_pointer": f"/gates/{i}",
                 "source_messages": gate["findings"]} for i, gate in enumerate(gates)]
    return make_candidates(report_bytes, context, outcomes, evaluated_at=evaluated_at,
                           adapter_id="architecture-gate-candidates", source_contract="architecture-gate-report@legacy-shape-v1",
                           domain="architecture", granularity="gate")
