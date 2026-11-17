"""Private local-Git review planning and declared completion checks, without execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from lib import review_git, review_planning as logic
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.provider_ports import REVIEW_PLAN_PROFILES, review_plan_profile
from lib.result_assessments import identity, operator_bytes
from lib.result_bytes import safe_bytes, strict_json
from lib.result_snapshot_store import explicit_time
from lib.review_metadata_application import FLAGS
from lib.supplement_application import write_lock

MAX_JSON = 8 * 1024**2
MAX_RESULTS = 4 * 1024**2
MAX_OUTPUT = 8 * 1024**2


def wire(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


class ReviewPlanningContext:
    def __init__(self, instance_root, settings):
        self.instance = Path(instance_root).resolve(); private_directory(self.instance/'state')
        self.root = private_directory(self.instance/'state/review-planning')
        self.inputs = private_directory(self.root/'inputs'); self.artifacts = private_directory(self.root/'artifacts'); self.assessments = private_directory(self.root/'assessments')
        self.binding = {'node_id': settings['node_id'], 'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip(), 'runtime_source_digest': source_digest()}
        self.clean = not bool(git_read(ROOT, 'status', '--porcelain', '--untracked-files=all').strip())

    def assert_current(self):
        if source_digest() != self.binding['runtime_source_digest'] or git_read(ROOT, 'rev-parse', 'HEAD').decode().strip() != self.binding['source_revision']: raise ValueError('review_planning_program_changed')

    def input_data(self, input_id):
        root = self.inputs/identity(input_id)
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077: raise ValueError('private_review_planning_input_required')
        manifest = strict_json(safe_bytes(root/'manifest.json', limit=MAX_JSON))
        if set(manifest) != {'schema_version', 'operation', 'profile', 'plan_assessment_id', 'files'} or type(manifest['schema_version']) is not int or manifest['schema_version'] != 1 or canonical_digest(manifest) != input_id: raise ValueError('invalid_review_planning_manifest')
        if manifest['operation'] not in ('prepare', 'check'): raise ValueError('invalid_review_planning_operation')
        if (manifest['plan_assessment_id'] is None) != (manifest['operation'] == 'prepare'): raise ValueError('invalid_review_planning_parent')
        if manifest['plan_assessment_id'] is not None: identity(manifest['plan_assessment_id'])
        profile = review_plan_profile(manifest['profile']); blobs = root/'blobs'
        if blobs.is_symlink() or not blobs.is_dir() or blobs.stat().st_mode & 0o077: raise ValueError('private_review_planning_blobs_required')
        fixed = {'facts.json', 'goal.txt'} | ({'results.json'} if manifest['operation'] == 'check' else set())
        if {p.name for p in root.iterdir()} != fixed | {'manifest.json', 'blobs'}: raise ValueError('review_planning_input_members_changed')
        names = fixed | {'blobs/' + p.name for p in blobs.iterdir()}
        if not isinstance(manifest['files'], dict) or set(manifest['files']) != names or len(names) > 11003: raise ValueError('review_planning_input_members_changed')
        files = {}; total = 0
        for name, row in manifest['files'].items():
            if name not in fixed and not re.fullmatch(r'blobs/[a-f0-9]{64}\.bin', name): raise ValueError('invalid_review_planning_blob_name')
            limit = 65536 if name == 'goal.txt' else MAX_RESULTS if name == 'results.json' else MAX_JSON if name == 'facts.json' else review_git.MAX_FILE
            if not isinstance(row, dict) or set(row) != {'sha256', 'bytes'} or type(row['bytes']) is not int or not 0 <= row['bytes'] <= limit: raise ValueError('invalid_review_planning_input_length')
            raw = safe_bytes(root/name, limit=limit); total += len(raw)
            if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']: raise ValueError('review_planning_input_changed')
            if name.startswith('blobs/') and name != 'blobs/' + row['sha256'] + '.bin': raise ValueError('review_planning_blob_identity_changed')
            if total > review_git.MAX_TOTAL + 2*MAX_JSON: raise ValueError('review_planning_input_budget')
            files[name] = raw
        facts = strict_json(files['facts.json'])
        if not isinstance(facts.get('files'), dict): raise ValueError('invalid_review_planning_source_map')
        for row in facts['files'].values():
            if row is not None and (not isinstance(row, dict) or not isinstance(row.get('sha256'), str) or not re.fullmatch('[a-f0-9]{64}', row['sha256'])): raise ValueError('invalid_review_planning_source_map')
        raw_files = {name: files['blobs/' + row['sha256'] + '.bin'] for name, row in facts['files'].items() if row is not None}
        if set(files) - fixed != {'blobs/' + row['sha256'] + '.bin' for row in facts['files'].values() if row is not None}: raise ValueError('review_planning_blob_members_changed')
        review_git.validate(facts, raw_files, profile)
        return manifest, facts, raw_files, files['goal.txt'].decode('utf-8'), files.get('results.json')

    def capture_input(self, operation, profile, facts, raw_files, goal, results, parent):
        policy = review_plan_profile(profile); review_git.validate(facts, raw_files, policy)
        if operation not in ('prepare', 'check') or (operation == 'prepare') != (parent is None) or (operation == 'check') != (results is not None): raise ValueError('invalid_review_planning_capture')
        files = {'facts.json': wire(facts), 'goal.txt': goal.encode('utf-8')}
        if len(files['facts.json']) > MAX_JSON or len(files['goal.txt']) > 65536: raise ValueError('review_planning_input_budget')
        if results is not None:
            if not isinstance(results, bytes) or len(results) > MAX_RESULTS: raise ValueError('review_planning_results_budget')
            files['results.json'] = results
        for raw in raw_files.values(): files['blobs/' + hashlib.sha256(raw).hexdigest() + '.bin'] = raw
        manifest = {'schema_version': 1, 'operation': operation, 'profile': profile, 'plan_assessment_id': parent,
            'files': {n: {'bytes': len(v), 'sha256': hashlib.sha256(v).hexdigest()} for n, v in files.items()}}
        if len(wire(manifest)) > MAX_JSON: raise ValueError('review_planning_manifest_budget')
        input_id = canonical_digest(manifest); reserve(self.root, sum(map(len, files.values())) + MAX_JSON)
        with tempfile.TemporaryDirectory(prefix='.incoming-', dir=self.inputs) as temporary:
            staged = Path(temporary)/'data'; staged.mkdir(mode=0o700); (staged/'blobs').mkdir(mode=0o700)
            for name, raw in files.items(): path = staged/name; path.write_bytes(raw); path.chmod(0o600)
            atomic_json(staged/'manifest.json', manifest); self.assert_current()
            with write_lock(self.root):
                target = self.inputs/input_id
                if target.is_symlink(): raise ValueError('unsafe_review_planning_input')
                if not target.exists(): os.rename(staged, target)
                saved = self.input_data(input_id)
                if saved != (manifest, facts, raw_files, goal, results): raise ValueError('immutable_review_planning_input_conflict')
        return input_id

    def render(self, input_id):
        manifest, facts, raw, goal, results = self.input_data(input_id)
        value, dispatch = logic.plan(facts, raw, goal, review_plan_profile(manifest['profile']))
        ready = False
        if manifest['operation'] == 'prepare':
            files = {'review-plan.json': wire(value), 'review-results-template.json': wire(logic.results_template(value)),
                'review-dispatch.json': wire(dispatch), 'review-dispatch.md': logic.render_text(dispatch).encode()}
        else:
            parent = self.record(manifest['plan_assessment_id'])
            if parent['operation'] != 'prepare': raise ValueError('review_check_requires_prepared_plan')
            self.inspect(manifest['plan_assessment_id']); _, previous, old_raw, old_goal, _ = self.input_data(parent['input_id'])
            original, _ = logic.plan(previous, old_raw, old_goal, review_plan_profile(parent['profile']))
            if manifest['profile'] != parent['profile'] or value != original or facts['files'] != previous['files'] or facts['role_paths'] != previous['role_paths']:
                raise ValueError('review_plan_stale_target_revision_source_index_or_contract')
            report = logic.check_results(value, strict_json(results), read_json(ROOT/'schemas/axiom-v2-review-results.schema.json'))
            ready = report['eligible_for_human_review']; files = {'review-check.json': wire(report)}
        if any(len(raw) > MAX_OUTPUT for raw in files.values()): raise ValueError('review_planning_output_budget')
        return files, ready

    def record(self, assessment_id):
        assessment_id = identity(assessment_id); value = strict_json(safe_bytes(self.assessments/(assessment_id+'.json'), limit=MAX_JSON))
        try: Draft202012Validator(read_json(ROOT/'schemas/axiom-v2-review-planning.schema.json'), format_checker=FormatChecker()).validate(value)
        except ValidationError: raise ValueError('invalid_review_planning_assessment') from None
        if type(value['schema_version']) is not int or canonical_digest(value) != assessment_id or any(value[k] != v for k, v in self.binding.items()): raise ValueError('review_planning_binding_changed')
        explicit_time(value['assessed_at']); return value

    def inspect(self, assessment_id):
        value = self.record(assessment_id); manifest, _, _, _, _ = self.input_data(value['input_id'])
        if any(value[k] != manifest[k] for k in ('operation', 'profile', 'plan_assessment_id')): raise ValueError('review_planning_operation_changed')
        files, ready = self.render(value['input_id'])
        if ready != value['declared_ready'] or {n: {'sha256': hashlib.sha256(v).hexdigest(), 'bytes': len(v)} for n, v in files.items()} != value['files']: raise ValueError('review_planning_output_manifest_changed')
        root = self.artifacts/assessment_id
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077 or {p.name for p in root.iterdir()} != set(files): raise ValueError('review_planning_output_members_changed')
        for name, raw in files.items():
            if safe_bytes(root/name, limit=MAX_OUTPUT) != raw: raise ValueError('review_planning_output_changed')
        self.assert_current()
        return {**value, 'assessment_id': assessment_id, 'data_directory': str(root), 'retained_complete_outputs_reverified': True, 'target_current_state_rechecked': False}

    def create(self, operation, profile, facts, raw, goal, at, *, results=None, parent=None, verify_target=None):
        explicit_time(at); input_id = self.capture_input(operation, profile, facts, raw, goal, results, parent); files, ready = self.render(input_id)
        value = {'schema_version': 1, 'kind': 'local-git-review-planning', **self.binding, 'input_id': input_id,
            'operation': operation, 'profile': profile, 'plan_assessment_id': parent, 'assessed_at': at,
            'source_worktree_clean': self.clean, 'target_observation': 'local-git-at-command-execution',
            'assessment_time_source': 'operator', 'files': {n: {'sha256': hashlib.sha256(v).hexdigest(), 'bytes': len(v)} for n, v in files.items()},
            'mode': 'report-only', 'evidence_trust': 'unverified', 'declared_ready': ready, **FLAGS}
        assessment_id = canonical_digest(value); reserve(self.root, sum(map(len, files.values())) + MAX_JSON)
        with tempfile.TemporaryDirectory(prefix='.incoming-', dir=self.artifacts) as temporary:
            staged = Path(temporary)/'data'; staged.mkdir(mode=0o700)
            for name, data in files.items(): path = staged/name; path.write_bytes(data); path.chmod(0o600)
            self.assert_current()
            if verify_target is not None: verify_target()
            with write_lock(self.root):
                record = self.assessments/(assessment_id+'.json'); target = self.artifacts/assessment_id
                if record.is_symlink() or target.is_symlink(): raise ValueError('unsafe_review_planning_assessment')
                if record.exists():
                    if strict_json(safe_bytes(record, limit=MAX_JSON)) != value: raise ValueError('immutable_review_planning_assessment_conflict')
                else:
                    if target.exists(): raise ValueError('unrecorded_review_planning_artifact')
                    os.rename(staged, target); atomic_json(record, value)
        inspected = self.inspect(assessment_id)
        return {**inspected, 'target_current_state_rechecked': verify_target is not None}


def run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 review-plan', allow_abbrev=False); commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare'); prepare.add_argument('--repo', type=Path, required=True)
    base_selection = prepare.add_mutually_exclusive_group()
    base_selection.add_argument('--base-commit')
    base_selection.add_argument('--base-ref', help='Resolve this local Git reference to a frozen exact base commit.')
    prepare.add_argument('--goal-file', type=Path, required=True); prepare.add_argument('--path', action='append', default=[]); prepare.add_argument('--profile', choices=REVIEW_PLAN_PROFILES, required=True); prepare.add_argument('--at', required=True)
    check = commands.add_parser('check'); check.add_argument('--repo', type=Path, required=True); check.add_argument('--plan', required=True); check.add_argument('--results', type=Path, required=True); check.add_argument('--at', required=True)
    inspect = commands.add_parser('inspect'); inspect.add_argument('--assessment', required=True)
    args = parser.parse_args(arguments); app = ReviewPlanningContext(instance_root, settings)
    if args.command == 'inspect': print(json.dumps(app.inspect(args.assessment), sort_keys=True)); return 0
    target = args.repo.resolve()
    if app.instance.is_relative_to(target) or target.is_relative_to(app.root): raise ValueError('review_private_state_must_be_outside_target')
    results = None; parent = None
    if args.command == 'prepare':
        profile = args.profile; base = args.base_commit; paths = args.path; goal = operator_bytes(args.goal_file, limit=65536).decode('utf-8')
    else:
        parent = identity(args.plan); previous = app.inspect(parent)
        if previous['operation'] != 'prepare': raise ValueError('review_check_requires_prepared_plan')
        _, old, _, goal, _ = app.input_data(previous['input_id']); profile = previous['profile']; base = old['target_commit']; paths = old['changed_paths'] if old['selection_mode'] == 'explicit_paths' else []
        results = operator_bytes(args.results, limit=MAX_RESULTS)
    from lib.provider_ports import resolve_review_base
    policy = review_plan_profile(profile)
    reference = args.base_ref if args.command == 'prepare' else None
    if reference is not None: base = resolve_review_base(args.repo, reference, profile)
    facts, raw = review_git.capture(args.repo, base, paths, policy)
    def recheck():
        if reference is not None and resolve_review_base(args.repo, reference, profile) != base:
            raise ValueError('review_base_reference_changed_during_operation')
        if review_git.observe(args.repo, base, paths, policy) != (facts, raw): raise ValueError('review_target_changed_during_operation')
    value = app.create(args.command, profile, facts, raw, goal, args.at, results=results, parent=parent, verify_target=recheck)
    print(json.dumps(value, sort_keys=True)); return 1 if args.command == 'check' and not value['declared_ready'] else 0
