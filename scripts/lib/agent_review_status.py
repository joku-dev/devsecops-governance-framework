"""Inspect PR review metadata with trusted code; never execute code from a PR."""
from __future__ import annotations

import html
import json
from pathlib import Path
import re
import tempfile

from jsonschema import ValidationError

from .agent_receipts import validate_receipt
from .agent_review import git_output
from .agent_routing import load_role_contracts, load_routing_contract, normalize_path, routing_reasons_for_contract

START = '<!-- agent-review-receipt:start -->'
END = '<!-- agent-review-receipt:end -->'
SHA = re.compile(r'^(?:[0-9a-f]{40}|[0-9a-f]{64})$')


def committed_scope(root: Path, base: str, head: str) -> tuple[str, list[str]]:
    if not SHA.fullmatch(base) or not SHA.fullmatch(head):
        raise ValueError('PR base and head must be full commit SHAs')
    for sha in (base, head):
        if git_output(root, 'rev-parse', '--verify', '--end-of-options', sha + '^{commit}').strip() != sha:
            raise ValueError('PR subject is not a commit')
    ancestor = git_output(root, 'merge-base', base, head).strip()
    paths = git_output(root, 'diff', '--name-only', '--no-renames', '-z', ancestor, head).split('\0')
    return ancestor, sorted(normalize_path(p) for p in paths if p)


def expected_reviews(root: Path, head: str, paths: list[str]) -> dict:
    """Only bounded regular YAML/skill files are read from the PR commit."""
    entries = git_output(root, 'ls-tree', '-r', '-z', head, '--', '.agents/roles', '.agents/skills', '.agents/routing').split('\0')
    wanted = []
    for entry in filter(None, entries):
        meta, name = entry.split('\t', 1)
        if (re.fullmatch(r'\.agents/roles/[a-z0-9-]+\.yaml', name)
            or re.fullmatch(r'\.agents/skills/[a-z0-9-]+/SKILL\.md', name)
            or name == '.agents/routing/governance-agent-routing.yaml'):
            mode, kind, sha = meta.split()
            if mode not in ('100644', '100755') or kind != 'blob':
                raise ValueError('Review contract inputs must be regular files')
            if int(git_output(root, 'cat-file', '-s', sha)) > 65536:
                raise ValueError('Review contract exceeds the 64 KiB input bound')
            wanted.append((name, sha))
    if len(wanted) > 200:
        raise ValueError('Too many review contract inputs')
    with tempfile.TemporaryDirectory() as directory:
        snapshot = Path(directory)
        for name, sha in wanted:
            path = snapshot / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(git_output(root, 'cat-file', 'blob', sha))
        roles = load_role_contracts(snapshot)
        routing = load_routing_contract(snapshot / '.agents/routing/governance-agent-routing.yaml', known_agents=roles)
        selected = routing_reasons_for_contract(paths, routing)
        return {'roles': sorted(set(selected) - {'repo-steward'}) + (['repo-steward'] if selected else []),
                'validations': sorted({cmd for role in selected for cmd in roles[role]['validations']})}


def receipt_block(receipt: dict) -> str:
    validate_receipt(receipt)
    return START + '\n```json\n' + json.dumps(receipt, sort_keys=True) + '\n```\n' + END


def parse_receipt(body: str) -> dict | None:
    if not isinstance(body, str) or len(body.encode()) > 1048576:
        raise ValueError('PR description exceeds input bounds')
    if START not in body and END not in body:
        return None
    if body.count(START) != 1 or body.count(END) != 1:
        raise ValueError('Expected exactly one receipt block')
    match = re.search(re.escape(START) + r'\s*```json\s*\n(.*?)\n```\s*' + re.escape(END), body, re.S)
    if not match or len(match.group(1).encode()) > 65536:
        raise ValueError('Receipt block is malformed or exceeds 64 KiB')
    receipt = json.loads(match.group(1))
    validate_receipt(receipt)
    return receipt


def inspect_pr(root: Path, event: dict) -> dict:
    pr = event.get('pull_request', {})
    base, head = pr.get('base', {}).get('sha', ''), pr.get('head', {}).get('sha', '')
    ancestor, paths = committed_scope(root, base, head)
    expected = expected_reviews(root, head, paths)
    previous = expected_reviews(root, base, paths)
    union = set(expected['roles']) | set(previous['roles'])
    expected = {'roles': sorted(union - {'repo-steward'}) + (['repo-steward'] if union else []),
                'validations': sorted(set(expected['validations']) | set(previous['validations']))}
    report = {'status': 'missing', 'head_commit': head, 'base_commit': ancestor,
              'changed_path_count': len(paths), 'required_roles': expected['roles'],
              'roles': [], 'diagnostics': [], 'enforcement': 'report_only',
              'evidence_kind': 'self_reported_review_evidence', 'independent_human_approval': False,
              'routing_basis': 'target_and_proposed_contract_union'}
    try:
        receipt = parse_receipt(pr.get('body') or '')
    except (ValueError, TypeError, KeyError, ValidationError):
        report.update(status='invalid', diagnostics=['Receipt JSON, schema, input bounds or integrity are invalid; private input is omitted.'])
        return report
    if receipt is None:
        report['diagnostics'] = ['No explicit review receipt is attached to this PR description.']
        return report
    report['roles'] = receipt['roles']
    if (receipt['head_commit'] != head or receipt['base_commit'] != ancestor
        or receipt['changed_paths'] != paths
        or [r['role_id'] for r in receipt['roles']] != expected['roles']
        or sorted(v['command'] for v in receipt['validations']) != expected['validations']):
        report.update(status='stale', diagnostics=['Receipt commit, scope, roles or validations do not match the PR revision.'])
    else:
        report['status'] = 'declared_complete' if receipt['eligible_for_human_review'] else 'incomplete'
        report['diagnostics'] = ['Metadata consistency checked; private role outputs, logs and execution identities are not authenticated.']
    return report


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
