"""Fingerprint-bound original dispatcher recording functions; fixed test clock only."""
import ast
import argparse
from collections import Counter
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys


def load(directory, repository, roles, at):
    directory = Path(directory); repository = Path(repository)
    contract = json.loads((directory/'contract.json').read_text()); raw = (directory/'dispatch.py.txt').read_bytes()
    assert contract['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197' and hashlib.sha256(raw).hexdigest() == contract['dispatch_sha256']
    names = {'build_usage_event', 'append_usage_event', 'repo_relative', 'load_recording_state', 'save_recording_state', 'activate_recording', 'activate_continuous_recording', 'recording_usage_log', 'consume_recording_event', 'render_recording_status', 'load_usage_events', 'summarize_usage', 'render_usage_summary'}
    selected = [node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in selected} == names
    timestamp = datetime.fromisoformat(at.replace('Z', '+00:00')).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    values = {'Path': Path, 'Counter': Counter, 'json': json, 'ROOT': repository,
        'DEFAULT_USAGE_LOG': repository/'generated/agent-usage/agent-usage.jsonl',
        'SKILL_BY_AGENT': {name: role['skill'] for name, role in roles.items()}, 'now_utc': lambda: timestamp}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(directory/'dispatch.py.txt'), 'exec'), values)
    return values


def main(directory, repository, roles, at, arguments, dispatch):
    """Unchanged V1 main orchestration on explicit, already tested selection input.

    Actual Git selection/routing is covered by the independent planning oracle.
    Only build_dispatch is supplied here, to isolate original logging decisions.
    """
    values = load(directory, repository, roles, at)
    raw = (Path(directory) / 'dispatch.py.txt').read_bytes()
    selected = [node for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef)
                and node.name in ('parse_args', 'main', 'render_text')]
    assert len(selected) == 3
    values.update(argparse=argparse, sys=sys,
        DEFAULT_USAGE_STATE=Path(repository) / 'generated/agent-usage/recording-state.json',
        build_dispatch=lambda paths: deepcopy(dispatch), changed_files_from_git=lambda base: dispatch['changed_files'])
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(Path(directory) / 'dispatch.py.txt'), 'exec'), values)
    stdout = io.StringIO(); stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr): code = values['main'](arguments)
    return code, stdout.getvalue().encode(), stderr.getvalue().encode()
