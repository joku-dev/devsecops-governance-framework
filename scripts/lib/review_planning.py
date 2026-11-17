"""Pure revision-bound role planning from retained local facts and contracts."""
import hashlib
import json
from pathlib import PurePosixPath
import re
import yaml
from jsonschema import Draft202012Validator
from lib.review_metadata import digest, normalize_path

PROTOCOL = '.agents/review-protocol.yaml'
ROUTING = '.agents/routing/governance-agent-routing.yaml'
MAX_PATHS = 10000


class ContractLoader(yaml.SafeLoader):
    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent): raise ValueError('review_contract_alias_not_supported')
        return super().compose_node(parent, index)


def unique_mapping(loader, node, deep=False):
    result = {}
    for key, value in node.value:
        name = loader.construct_object(key, deep=deep)
        if not isinstance(name, str) or name in result: raise ValueError('review_contract_unique_string_keys_required')
        result[name] = loader.construct_object(value, deep=deep)
    return result


ContractLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def yaml_object(raw):
    if not isinstance(raw, bytes) or len(raw) > 1024**2: raise ValueError('review_contract_byte_budget')
    try:
        value = yaml.load(raw.decode('utf-8'), Loader=ContractLoader)
        if not isinstance(value, dict): raise ValueError('review_contract_object_required')
        json.dumps(value, allow_nan=False)
        return value
    except (yaml.YAMLError, UnicodeError, RecursionError, OverflowError, TypeError):
        raise ValueError('invalid_review_contract') from None


def strings(value):
    return isinstance(value, list) and bool(value) and all(isinstance(s, str) and s.strip() for s in value)


def canonical_paths(paths):
    if not isinstance(paths, list) or len(paths) > MAX_PATHS or any(not isinstance(p, str) or len(p.encode()) > 4096 or normalize_path(p) != p for p in paths):
        raise ValueError('invalid_review_paths')
    if paths != sorted(set(paths)): raise ValueError('review_paths_must_be_sorted_unique')
    return paths


def contracts(raw):
    roles = {}
    for name in sorted(raw):
        if not re.fullmatch(r'\.agents/roles/[a-z0-9]+(?:-[a-z0-9]+)*\.yaml', name): continue
        role = yaml_object(raw[name])
        if role.get('id') != PurePosixPath(name).stem: raise ValueError('invalid_review_role_identity')
        if any(not isinstance(role.get(k), str) or not role[k].strip() for k in ('id', 'name', 'description', 'source_of_truth', 'skill')):
            raise ValueError('invalid_review_role_fields')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', role['skill']): raise ValueError('invalid_review_skill')
        if '.agents/skills/' + role['skill'] + '/SKILL.md' not in raw: raise ValueError('review_skill_required')
        if any(not strings(role.get(k)) for k in ('primary_files', 'responsibilities', 'validations', 'output_contract')):
            raise ValueError('invalid_review_role_lists')
        roles[role['id']] = role
    if not 1 <= len(roles) <= 200 or 'repo-steward' not in roles: raise ValueError('review_steward_contract_required')
    routing = yaml_object(raw[ROUTING]); protocol = yaml_object(raw[PROTOCOL])
    always = routing.get('always_select')
    if not strings(always) or 'repo-steward' not in always or set(always) - roles.keys(): raise ValueError('invalid_review_always_select')
    rules = routing.get('rules')
    if not isinstance(rules, list) or not 1 <= len(rules) <= 2000: raise ValueError('invalid_review_routing_rules')
    prefixes = set()
    for rule in rules:
        if not isinstance(rule, dict): raise ValueError('invalid_review_routing_rule')
        prefix = rule.get('path_prefix')
        if not isinstance(prefix, str) or normalize_path(prefix) != prefix or prefix in prefixes: raise ValueError('invalid_review_routing_prefix')
        prefixes.add(prefix)
        if not strings(rule.get('agents')) or set(rule['agents']) - roles.keys(): raise ValueError('unknown_review_role')
    if 'fallback' in routing:
        fallback = routing['fallback']
        if not isinstance(fallback, dict) or not strings(fallback.get('path_prefixes')) or not strings(fallback.get('agents')) or set(fallback['agents']) - roles.keys():
            raise ValueError('invalid_review_fallback')
        if any(normalize_path(p) != p or not p.endswith('/') for p in fallback['path_prefixes']): raise ValueError('invalid_review_fallback_prefix')
    execution = protocol.get('execution', {})
    if not isinstance(execution, dict) or execution.get('final_role') != 'repo-steward' or execution.get('default_access') != 'read_only' or execution.get('default_mode') != 'role_lens':
        raise ValueError('read_only_final_steward_protocol_required')
    authority = protocol.get('authority')
    if authority != {'result_is': 'self_reported_review_evidence', 'independent_human_approval': False,
                     'source_or_requirement_approval': False, 'release_or_blocking_authorization': False}:
        raise ValueError('review_protocol_cannot_grant_authority')
    return roles, routing, protocol


def routing_reasons(paths, routing):
    reasons = {}
    if paths:
        for role in routing['always_select']: reasons.setdefault(role, set()).add('always_select')
    for path in paths:
        matched = False
        for rule in routing['rules']:
            if path.startswith(rule['path_prefix']):
                matched = True
                for role in rule['agents']: reasons.setdefault(role, set()).add(rule['path_prefix'])
        fallback = routing.get('fallback', {})
        if not matched and any(path.startswith(p) for p in fallback.get('path_prefixes', [])):
            for role in fallback['agents']: reasons.setdefault(role, set()).add('fallback: unclassified functional path')
    return {role: sorted(values) for role, values in sorted(reasons.items())}


def dispatch(paths, roles, routing, profile):
    canonical_paths(paths); reasons = routing_reasons(paths, routing)
    impact = ('released_baseline' if any(p.startswith('releases/') for p in paths) else
              'candidate' if any(p.startswith(tuple(profile['release_candidate_prefixes'])) for p in paths) else
              'governance_model' if any(p.startswith(tuple(profile['model_prefixes'])) for p in paths) else 'none')
    warnings = []
    if any(p.startswith(('docs/governance/source-documents/', 'model/documents/')) for p in paths) and any(p.startswith(('architecture/', 'model/controls/', 'policies/opa/', 'releases/', 'schemas/')) for p in paths):
        warnings.append('Derived governance artifact path changed; verify no candidate source was used before review.')
    if impact == 'released_baseline': warnings.append('Released baseline path changed; release-manager review is mandatory.')
    return {'changed_files': paths, 'selected_agents': sorted(reasons), 'release_impact': impact,
            'required_validations': sorted({command for role in reasons for command in roles[role]['validations']}),
            'warnings': warnings, 'selection_reasons': reasons}


def plan(facts, raw, goal, profile):
    if not isinstance(goal, str) or not goal.strip() or len(goal.encode()) > 65536: raise ValueError('review_goal_required_or_too_large')
    paths = canonical_paths(facts['changed_paths'])
    if not paths: raise ValueError('review_changed_paths_required')
    roles, routing, protocol = contracts(raw); selection = dispatch(paths, roles, routing, profile)
    final = 'repo-steward'; tasks = []; selected_contracts = set(profile['common_contracts'])
    selected_contracts.update(name for name in profile['optional_contracts'] if name in raw)
    for role_id in sorted(set(selection['selected_agents']) - {final}) + [final]:
        role = roles[role_id]; role_path = '.agents/roles/' + role_id + '.yaml'; skill_path = '.agents/skills/' + role['skill'] + '/SKILL.md'
        selected_contracts.update((role_path, skill_path)); optional = profile['optional_role_contract'].format(role=role_id)
        if optional in raw: selected_contracts.add(optional)
        tasks.append({'role_id': role_id, 'phase': 'final_review' if role_id == final else 'specialist_review',
            'role_contract': role_path, 'skill': skill_path, 'selection_reasons': selection['selection_reasons'][role_id],
            'scope': [path for path in paths if role_id in routing_reasons([path], routing)], 'access': 'read_only',
            'required_output': role['output_contract'], 'validations': role['validations']})
    fingerprint = lambda name: hashlib.sha256(raw[name]).hexdigest() if name in raw else None
    value = {'schema_version': '1.0.0', 'user_goal': goal.strip(), 'head_commit': facts['head_commit'],
        'base_commit': facts['merge_base_commit'], 'selection_mode': facts['selection_mode'],
        'execution_status': 'not_started', 'default_mode': protocol['execution']['default_mode'],
        'changed_files': paths, 'release_impact': selection['release_impact'],
        'source_fingerprints': {name: fingerprint(name) for name in paths},
        'index_entries': {name: facts['index_entries'][name] for name in paths},
        'source_modes': {name: facts['files'][name]['mode'] if facts['files'][name] is not None else None for name in paths},
        'contract_fingerprints': {name: fingerprint(name) for name in sorted(selected_contracts)},
        'required_validations': selection['required_validations'], 'reviews': tasks, 'authority': protocol['authority']}
    value['plan_digest'] = digest(value)
    return value, selection


def results_template(value):
    return {'plan_digest': value['plan_digest'], 'reviews': [
        {'role_id': task['role_id'], 'status': 'pending', 'execution_kind': 'role_lens', 'executor': '',
         'provider': '', 'model': None, 'summary': '', 'outputs': {key: '' for key in task['required_output']},
         'reviewed_paths': [], 'reviewed_roles': [], 'findings': []} for task in value['reviews']],
        'validations': [{'command': cmd, 'status': 'not_run', 'evidence': ''} for cmd in value['required_validations']]}


def check_results(value, results, schema):
    Draft202012Validator(schema).validate(results)
    if digest({k: v for k, v in value.items() if k != 'plan_digest'}) != value.get('plan_digest') or results['plan_digest'] != value['plan_digest']:
        raise ValueError('review_plan_result_digest_mismatch')
    ids = [task['role_id'] for task in value['reviews']]
    if [row['role_id'] for row in results['reviews']] != ids: raise ValueError('review_result_role_order_or_members_changed')
    if sorted(row['command'] for row in results['validations']) != value['required_validations']: raise ValueError('review_result_validations_changed')
    incomplete = []; findings = []
    for task, review in zip(value['reviews'], results['reviews']):
        if review['status'] != 'completed' or any(not review[k].strip() for k in ('executor', 'provider', 'summary')): incomplete.append('Incomplete role review: ' + review['role_id'])
        if set(review['outputs']) != set(task['required_output']) or any(not text.strip() for text in review['outputs'].values()): incomplete.append('Missing required role outputs: ' + review['role_id'])
        if sorted(review['reviewed_paths']) != sorted(task['scope']): incomplete.append('Unreviewed role scope: ' + review['role_id'])
        findings.extend({'role_id': review['role_id'], **finding} for finding in review['findings'])
    if set(results['reviews'][-1]['reviewed_roles']) != set(ids[:-1]): incomplete.append('Final repo-steward must explicitly account for all specialist reviews')
    for validation in results['validations']:
        if validation['status'] != 'passed' or not validation['evidence'].strip(): incomplete.append('Missing declared passing validation with evidence: ' + validation['command'])
    if any(f['status'] == 'open' and f['severity'] in ('high', 'critical') for f in findings): incomplete.append('Open high/critical findings require resolution')
    return {'eligible_for_human_review': not incomplete, 'scope': value['selection_mode'],
        'evidence_kind': 'self_reported_review_evidence', 'independent_human_approval': False, 'incomplete': incomplete, 'findings': findings}


def render_text(dispatch: dict) -> str:
    lines = [
        "Governance Agent Dispatch",
        "",
        "Changed files:",
    ]
    if dispatch["changed_files"]:
        lines.extend(f"- {path}" for path in dispatch["changed_files"])
    else:
        lines.append("- none")

    lines.extend(["", "Selected agents:"])
    if dispatch["selected_agents"]:
        lines.extend(f"- {agent}: {', '.join(dispatch['selection_reasons'][agent])}" for agent in dispatch["selected_agents"])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            f"Release impact: {dispatch['release_impact']}",
            "",
            "Required validation:",
        ]
    )
    if dispatch["required_validations"]:
        lines.extend(f"- {command}" for command in dispatch["required_validations"])
    else:
        lines.append("- none")

    if dispatch["warnings"]:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in dispatch["warnings"])

    return "\n".join(lines) + "\n"
