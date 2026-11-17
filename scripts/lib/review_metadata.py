"""Pure declared review metadata; original V1 wire semantics, no review execution."""
from __future__ import annotations
from collections import Counter
import hashlib
import html
import json
import re
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from lib.result_bytes import strict_json

START = '<!-- agent-review-receipt:start -->'
END = '<!-- agent-review-receipt:end -->'

def digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()

def normalize_path(path: str) -> str:
    if not isinstance(path, str) or not path or "\x00" in path or "\\" in path:
        raise ValueError("Changed paths must be nonempty repository-relative POSIX paths")
    if path.startswith("/") or re.match(r"^[A-Za-z]:", path) or ".." in path.split("/"):
        raise ValueError(f"Path must stay inside the repository: {path!r}")
    normalized = "/".join(part for part in path.split("/") if part and part != ".")
    if not normalized:
        raise ValueError("Empty repository path")
    return normalized + ("/" if path.endswith("/") else "")

def validate_receipt(receipt: dict, schema: dict) -> None:
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(receipt)
    unsigned = {k: v for k, v in receipt.items() if k != "receipt_digest"}
    if receipt["receipt_digest"] != digest(unsigned):
        raise ValueError("Receipt digest mismatch")
    if receipt["receipt_id"] != digest({k: receipt[k] for k in ("plan_digest", "results_digest")}):
        raise ValueError("Receipt identity mismatch")
    if any(normalize_path(p) != p for p in receipt["changed_paths"]):
        raise ValueError("Receipt paths must be canonical repository paths")
    ids = [r["role_id"] for r in receipt["roles"]]
    if len(ids) != len(set(ids)) or ids[-1] != "repo-steward":
        raise ValueError("Receipt requires unique roles and final repo-steward")
    commands = [v["command"] for v in receipt["validations"]]
    if len(commands) != len(set(commands)):
        raise ValueError("Duplicate receipt validation")
    if any(r["execution_declared"] and r["status"] not in ("completed", "failed") for r in receipt["roles"]):
        raise ValueError("Pending or skipped roles cannot declare execution")
    if receipt["eligible_for_human_review"] and (
        any(r["status"] != "completed" or not r["execution_declared"] for r in receipt["roles"])
        or any(v["status"] != "passed" for v in receipt["validations"])
        or any(receipt["finding_counts"]["open"][s] for s in ("high", "critical"))
    ):
        raise ValueError("Receipt readiness contradicts its declared outcomes")

def summarize_review_usage(receipts: list[dict], schema: dict) -> dict:
    selected, executed, completed, kinds = Counter(), Counter(), Counter(), Counter()
    for receipt in receipts:
        validate_receipt(receipt, schema)
        for role in receipt["roles"]:
            selected[role["role_id"]] += 1
            if role["execution_declared"]:
                executed[role["role_id"]] += 1
                kinds[role["execution_kind"]] += 1
            if role["status"] == "completed":
                completed[role["role_id"]] += 1
    return {"receipt_count": len(receipts), "selected_roles": dict(selected),
            "declared_executed_roles": dict(executed), "completed_roles": dict(completed),
            "declared_execution_kinds": dict(kinds), "evidence_kind": "self_reported_review_evidence",
            "independent_human_approval": False}

def receipt_block(receipt: dict, schema: dict) -> str:
    validate_receipt(receipt, schema)
    return START + '\n```json\n' + json.dumps(receipt, sort_keys=True) + '\n```\n' + END

def parse_receipt(body: str, schema: dict) -> dict | None:
    if not isinstance(body, str) or len(body.encode()) > 1048576:
        raise ValueError('PR description exceeds input bounds')
    if START not in body and END not in body:
        return None
    if body.count(START) != 1 or body.count(END) != 1:
        raise ValueError('Expected exactly one receipt block')
    match = re.search(re.escape(START) + r'\s*```json\s*\n(.*?)\n```\s*' + re.escape(END), body, re.S)
    if not match or len(match.group(1).encode()) > 65536:
        raise ValueError('Receipt block is malformed or exceeds 64 KiB')
    receipt = strict_json(match.group(1))
    validate_receipt(receipt, schema)
    return receipt

def render_status(report: dict) -> str:
    def cell(value):
        return html.escape(str(value)).replace('|', '&#124;').replace('`', '&#96;').replace('\n', ' ').replace('\r', ' ')
    observed = {r['role_id']: r for r in report['roles']}
    lines = ['# Agent review status', '', '**Report-only — declared review metadata; no human approval.**', '',
             'Status: `' + cell(report['status']) + '`', '',
             'Reviewed PR head: `' + cell(report['head_commit']) + '`', '',
             '| Required role | Declared status | Execution kind |', '|---|---|---|']
    for role in report['required_roles']:
        row = observed.get(role, {})
        lines.append('| ' + cell(role) + ' | ' + cell(row.get('status', 'missing')) + ' | ' + cell(row.get('execution_kind', 'unknown')) + ' |')
    lines.extend(['', *('- ' + cell(d) for d in report['diagnostics']), ''])
    return '\n'.join(lines)


def parse_usage(raw, schema, *, max_events=10000):
    receipts=[];seen=set()
    for line in raw.decode('utf-8').splitlines():
        if not line.strip():continue
        if len(receipts)>=max_events:raise ValueError('review_receipt_event_budget')
        receipt=strict_json(line);validate_receipt(receipt,schema)
        if receipt['receipt_id'] in seen:raise ValueError('Duplicate receipt in review usage log')
        seen.add(receipt['receipt_id']);receipts.append(receipt)
    return receipts


def status_from_subject(event, subject, schema):
    """Original status logic on explicit operator-declared target/proposed scope."""
    if event['head_commit']!=subject['head_commit'] or event['base_commit']!=subject['target_commit']:
        raise ValueError('review_event_subject_revision_mismatch')
    paths=subject['changed_paths']
    if paths!=sorted(set(paths)) or any(normalize_path(p)!=p for p in paths):
        raise ValueError('review_subject_paths_not_canonical')
    union=set(subject['target']['roles'])|set(subject['proposed']['roles'])
    roles=sorted(union-{'repo-steward'})+(['repo-steward'] if union else [])
    validations=sorted(set(subject['target']['validations'])|set(subject['proposed']['validations']))
    report={'status':'missing','head_commit':subject['head_commit'],'base_commit':subject['merge_base_commit'],
            'changed_path_count':len(paths),'required_roles':roles,'roles':[],'diagnostics':[],
            'enforcement':'report_only','evidence_kind':'self_reported_review_evidence',
            'independent_human_approval':False,'routing_basis':'target_and_proposed_contract_union'}
    try:receipt=parse_receipt(event['description'],schema)
    except (ValueError,TypeError,KeyError,ValidationError):
        report.update(status='invalid',diagnostics=['Receipt JSON, schema, input bounds or integrity are invalid; private input is omitted.'])
        return report
    if receipt is None:
        report['diagnostics']=['No explicit review receipt is attached to this PR description.'];return report
    report['roles']=receipt['roles']
    if (receipt['head_commit']!=subject['head_commit'] or receipt['base_commit']!=subject['merge_base_commit']
        or receipt['changed_paths']!=paths or [r['role_id'] for r in receipt['roles']]!=roles
        or sorted(v['command'] for v in receipt['validations'])!=validations):
        report.update(status='stale',diagnostics=['Receipt commit, scope, roles or validations do not match the PR revision.'])
    else:
        report['status']='declared_complete' if receipt['eligible_for_human_review'] else 'incomplete'
        report['diagnostics']=['Metadata consistency checked; private role outputs, logs and execution identities are not authenticated.']
    return report
