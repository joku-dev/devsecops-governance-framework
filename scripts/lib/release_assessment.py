"""Original V1 release-readiness wire and renderer; pinned OPA, private diagnostics.

Approval flags in an operator input remain declarations and never confer authority.
"""
from lib.portable.contracts import ROOT
from lib.tool_integrity import require_opa, evaluate_query

def render_markdown(payload: dict, findings: list[str]) -> str:
    target = payload.get("target_repository", {})
    status = "PASS" if not findings else "FINDINGS"
    lines = [
        "# DevSecOps Governance Report",
        "",
        "## Target",
        "",
        f"- Repository: `{target.get('path', 'unknown')}`",
        f"- Commit: `{target.get('commit', 'unknown')}`",
        f"- Release ID: `{target.get('release_id', 'unknown')}`",
        "",
        "## Gate Summary",
        "",
        "| Gate | Status | Findings |",
        "|---|---:|---:|",
        f"| DevSecOps Release Readiness | {status} | {len(findings)} |",
        "",
        "## Findings",
        "",
    ]
    if not findings:
        lines.append("No findings.")
    else:
        for finding in findings:
            lines.append(f"- {finding}")
    return "\n".join(lines).rstrip() + "\n"

def evaluate(input_path, *, opa, payload):
    if not isinstance(payload.get('release_candidate'), bool):
        raise ValueError('explicit_release_candidate_required')
    for key in ('repository', 'evidence', 'artifact', 'pipeline', 'infrastructure', 'deployment', 'release'):
        if not isinstance(payload.get(key), dict):
            raise ValueError('release_input_mapping_required')
    for key in ('dependencies', 'vulnerabilities', 'waivers'):
        if not isinstance(payload.get(key), list) or any(not isinstance(row, dict) for row in payload[key]):
            raise ValueError('release_input_array_required')
    findings = evaluate_query(require_opa(opa), ROOT / 'policies/opa/devsecops_release_readiness.rego',
                              input_path, 'data.devsecops.release_readiness.deny')
    return {'target': payload.get('target_repository', {}),
        'gate': {'id': 'devsecops_release_readiness', 'status': 'pass' if not findings else 'findings',
                 'findings': findings}, 'summary': {'finding_count': len(findings)}}
