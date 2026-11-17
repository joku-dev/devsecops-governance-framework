"""Fingerprint-bound original review functions on real local Git; no target Python imports."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types
import uuid
from dataclasses import dataclass
import jsonschema
import yaml


class OriginalReview:
    def __init__(self, directory, metadata, repository):
        directory = Path(directory); metadata = Path(metadata); repository = Path(repository)
        contract = json.loads((directory/'contract.json').read_text())
        assert contract['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
        assert hashlib.sha256((directory/'dispatch.py.txt').read_bytes()).hexdigest() == contract['dispatch_sha256']
        for name, sha in contract['metadata_source_sha256'].items(): assert hashlib.sha256((metadata/name).read_bytes()).hexdigest() == sha
        self.package = '_original_review_' + uuid.uuid4().hex
        package = types.ModuleType(self.package); package.__path__ = []; sys.modules[self.package] = package
        self.modules = [self.package]
        def module(name):
            value = types.ModuleType(self.package + '.' + name); value.__package__ = self.package
            sys.modules[value.__name__] = value; self.modules.append(value.__name__)
            value.__dict__.update(Path=Path, json=json, hashlib=hashlib, subprocess=subprocess,
                jsonschema=jsonschema, yaml=yaml, re=__import__('re'), dataclass=dataclass,
                ROOT=repository, ROUTING_CONTRACT=repository/'.agents/routing/governance-agent-routing.yaml', REPO_STEWARD='repo-steward')
            return value
        def execute(target, path, names):
            tree = ast.parse(path.read_bytes()); selected = []
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names: selected.append(node)
                elif isinstance(node, ast.Assign) and any(isinstance(n, ast.Name) and n.id in names for n in node.targets): selected.append(node)
            assert len(selected) == len(names)
            exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), target.__dict__)
        routing = module('agent_routing')
        names = {'ContractLoader', '_unique_mapping', 'load_yaml', 'string_list', 'load_role_contracts', 'RoutingRule',
            'load_routing_contract', 'load_routing_rules', 'normalize_path', 'routing_reasons', 'routing_reasons_for_contract',
            'route_agents', 'validations_for_agents', 'classify_release_impact', 'has_forbidden_candidate_derivation',
            'evaluate_scenario', 'DERIVED_GOVERNANCE_PREFIXES', 'ARCHITECTURE_EVIDENCE_PREFIXES', 'AGENT_SYSTEM_PREFIXES', 'REPO_VALIDATION_PREFIXES'}
        execute(routing, metadata/'agent_routing.py.txt', names)
        routing.ContractLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, routing._unique_mapping)
        routing.ROLE_CONTRACTS = routing.load_role_contracts(); routing.CORE_AGENTS = set(routing.ROLE_CONTRACTS)
        routing.AGENT_VALIDATIONS = {name: set(role['validations']) for name, role in routing.ROLE_CONTRACTS.items()}
        routing.ROUTING_DATA = routing.load_routing_contract(); routing.ROUTING_RULES = routing.load_routing_rules()
        self.review = module('agent_review')
        for name in ('ROLE_CONTRACTS', 'load_yaml', 'normalize_path', 'routing_reasons'): self.review.__dict__[name] = routing.__dict__[name]
        execute(self.review, metadata/'agent_review.py.txt', {'git_output', 'changed_files', 'merge_base', 'fingerprint', 'digest', 'prepare_plan', 'results_template', 'RESULT_SCHEMA', 'check_results'})
        self.dispatch = module('dispatch')
        for name in ('evaluate_scenario', 'normalize_path', 'routing_reasons'): self.dispatch.__dict__[name] = routing.__dict__[name]
        execute(self.dispatch, directory/'dispatch.py.txt', {'build_dispatch', 'render_text', 'SOURCE_DOCUMENT_PREFIXES', 'DERIVED_GOVERNANCE_PREFIXES'})
        self.repository = repository

    def close(self):
        for name in reversed(self.modules): sys.modules.pop(name, None)

    def prepare(self, base, goal, paths=None):
        selected = paths if paths else self.review.changed_files(self.repository, base)
        dispatch = self.dispatch.build_dispatch(selected)
        plan = self.review.prepare_plan(self.repository, dispatch, goal, base_ref=base, explicit_paths=bool(paths))
        return plan, dispatch, self.review.results_template(plan), self.dispatch.render_text(dispatch)


def git(root, *arguments):
    import os
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1', GIT_AUTHOR_NAME='Parity Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
        GIT_COMMITTER_NAME='Parity Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid', GIT_AUTHOR_DATE='2026-11-15T12:00:00Z', GIT_COMMITTER_DATE='2026-11-15T12:00:00Z')
    return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', *map(str, arguments)], cwd=root, env=env, stderr=subprocess.PIPE).decode().strip()


def repository_from_files(root, files):
    root = Path(root); root.mkdir(mode=0o700)
    for name, row in sorted(files.items()):
        path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(row['bytes']); path.chmod(row['mode'])
    path = root/'docs/review-example.md'; path.parent.mkdir(exist_ok=True); path.write_text('original\n'); path.chmod(0o644)
    git(root, 'init', '-q', '-b', 'main'); git(root, 'add', '--all'); git(root, 'commit', '-qm', 'original review fixture')
    return git(root, 'rev-parse', 'HEAD')


def target_files(directory):
    directory = Path(directory); contract = json.loads((directory/'contract.json').read_text()); raw = (directory/'target-files.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == contract['target_files_sha256']
    value = json.loads(raw); assert value['v1_reference'] == contract['v1_reference']
    files = {}
    for name, row in value['files'].items():
        data = base64.b64decode(row['base64'], validate=True)
        assert hashlib.sha256(data).hexdigest() == row['sha256']
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data, usedforsecurity=False).hexdigest() == row['git_blob']
        files[name] = {'bytes': data, 'mode': row['mode']}
    return files


def declared_results(plan):
    """Synthetic declarations only; never evidence of actual review or validation."""
    value = {'plan_digest': plan['plan_digest'], 'reviews': [], 'validations': []}
    for task in plan['reviews']:
        value['reviews'].append({'role_id':task['role_id'], 'status':'completed', 'execution_kind':'role_lens',
            'executor':'synthetic fixture', 'provider':'synthetic fixture', 'model':None,
            'summary':'Synthetic declaration; no review execution', 'outputs':{k:'synthetic declared output' for k in task['required_output']},
            'reviewed_paths':task['scope'], 'reviewed_roles':[t['role_id'] for t in plan['reviews'][:-1]] if task['role_id']=='repo-steward' else [], 'findings':[]})
    value['validations'] = [{'command':command, 'status':'passed', 'evidence':'Synthetic declaration; not executed'} for command in plan['required_validations']]
    return value
