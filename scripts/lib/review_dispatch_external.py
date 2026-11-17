"""Retained original local-file effects with explicit, durable partial-write recovery."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib import review_dispatch as logic, review_planning
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.provider_ports import (review_dispatch_profile, dispatch_file_profile,
    capture_dispatch_source, observe_dispatch_source, validate_dispatch_source,
    capture_dispatch_files, validate_dispatch_files, apply_dispatch_files, verify_dispatch_file_outputs)
from lib.result_assessments import identity
from lib.result_bytes import safe_bytes, strict_json
from lib.review_dispatch_application import PROFILE, MAX_JSON, MAX_OUTPUT, derive, descriptor
from lib.review_metadata_application import FLAGS
from lib.supplement_application import write_lock

FILE_PROFILE = 'legacy-local-dispatch-files-v1'
MAX_MATERIAL = 256 * 1024**2
FIXED = {'before-state.bin', 'before-log.bin', 'after-state.bin', 'after-log.bin', 'stdout.bin', 'source.json'}


def checked(value, definition):
    contract = read_json(ROOT / 'schemas/axiom-v2-review-dispatch-external.schema.json')
    try:
        Draft202012Validator({'$ref': '#/$defs/' + definition, '$defs': contract['$defs']},
                             format_checker=FormatChecker()).validate(value)
    except ValidationError: raise ValueError('invalid_external_dispatch_' + definition) from None


def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def durable_json(path, value):
    atomic_json(path, value)
    directory = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(directory)
    finally: os.close(directory)


class ExternalDispatchContext:
    def __init__(self, instance_root, settings):
        self.instance = Path(instance_root).resolve(); private_directory(self.instance / 'state')
        self.root = private_directory(self.instance / 'state/review-dispatch-external')
        self.plans = private_directory(self.root / 'plans'); self.executions = private_directory(self.root / 'executions')
        self.binding = {'node_id': settings['node_id'], 'runtime_source_digest': source_digest(),
                        'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()}
        self.clean = not bool(git_read(ROOT, 'status', '--porcelain', '--untracked-files=all').strip())
        self.forbidden = (self.instance, ROOT)

    def assert_current(self):
        if (source_digest() != self.binding['runtime_source_digest']
                or git_read(ROOT, 'rev-parse', 'HEAD').decode().strip() != self.binding['source_revision']):
            raise ValueError('external_dispatch_product_changed')

    def material(self, identifier):
        root = self.plans / identity(identifier)
        if (any(p.is_symlink() for p in (root, *root.parents)) or not root.is_dir()
                or root.stat().st_mode & 0o077): raise ValueError('private_external_dispatch_plan_required')
        names = set()
        for path in root.iterdir():
            if path.name not in ('record.json', 'blobs'): raise ValueError('external_dispatch_plan_members_changed')
            names.add(path.name)
        if names != {'record.json', 'blobs'}:
            raise ValueError('external_dispatch_plan_members_changed')
        if (root / 'record.json').stat().st_mode & 0o077: raise ValueError('private_external_dispatch_record_required')
        value = strict_json(safe_bytes(root / 'record.json', limit=MAX_JSON)); checked(value, 'plan')
        if canonical_digest(value) != identifier: raise ValueError('external_dispatch_plan_changed')
        if any(value[key] != expected for key, expected in self.binding.items()):
            raise ValueError('external_dispatch_node_runtime_or_source_changed')
        blobs = root / 'blobs'
        if blobs.is_symlink() or not blobs.is_dir() or blobs.stat().st_mode & 0o077:
            raise ValueError('private_external_dispatch_blobs_required')
        rows = value['files']; expected = {row['sha256'] for row in rows.values()}
        members = set()
        for path in blobs.iterdir():
            if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
                raise ValueError('private_external_dispatch_blob_required')
            members.add(path.name)
            if len(members) > 410: raise ValueError('external_dispatch_material_budget')
        if members != expected: raise ValueError('external_dispatch_blob_members_changed')
        files = {}; total = 0
        for name, row in rows.items():
            if name not in FIXED and not re.fullmatch(r'contracts/[a-f0-9]{64}\.bin', name):
                raise ValueError('unexpected_external_dispatch_file')
            limit = logic.MAX_STATE if name.endswith('state.bin') else MAX_JSON if name == 'source.json' else 1024**2 if name.startswith('contracts/') else logic.MAX_LOG
            raw = safe_bytes(blobs / identity(row['sha256']), limit=limit); total += len(raw)
            if total > MAX_MATERIAL: raise ValueError('external_dispatch_material_budget')
            if descriptor(raw) != row: raise ValueError('external_dispatch_material_changed')
            if name.startswith('contracts/') and name != 'contracts/' + row['sha256'] + '.bin':
                raise ValueError('external_dispatch_contract_blob_changed')
            files[name] = raw
        return value, files

    def render(self, value, files):
        request = value['request']; logic.checked_request(request)
        if value['profile'] != PROFILE or value['file_profile'] != FILE_PROFILE or value['native']['profile'] != FILE_PROFILE:
            raise ValueError('external_dispatch_profile_changed')
        before_state = files.get('before-state.bin'); before_log = files.get('before-log.bin')
        writes = validate_dispatch_files(value['native'], request, before_state, before_log, self.forbidden)
        dispatch = roles = None; expected = {}
        if value['native']['state']['present'] is True: expected['before-state.bin'] = before_state
        if value['native']['log']['present'] is True: expected['before-log.bin'] = before_log
        source = value['source']
        if source is not None:
            if request['action'] != 'dispatch' or source['repository_path'] != value['native']['repository_path']:
                raise ValueError('external_dispatch_source_changed')
            facts = strict_json(files['source.json']); rows = facts.get('files')
            if not isinstance(rows, dict) or len(rows) > 401: raise ValueError('invalid_external_dispatch_source')
            raw = {}
            for name, row in rows.items():
                if not isinstance(row, dict) or not isinstance(row.get('sha256'), str): raise ValueError('invalid_external_dispatch_source')
                blob = 'contracts/' + identity(row['sha256']) + '.bin'; raw[name] = files[blob]; expected[blob] = raw[name]
            roles, routing = validate_dispatch_source(facts, raw, PROFILE)
            if source['explicit_paths']:
                if facts['selection_mode'] != 'explicit_paths' or facts['changed_paths'] != source['explicit_paths']:
                    raise ValueError('external_dispatch_explicit_source_changed')
            elif facts['selection_mode'] != 'working_tree': raise ValueError('external_dispatch_working_source_changed')
            dispatch = review_planning.dispatch(facts['changed_paths'], roles, routing, review_dispatch_profile(PROFILE))
            expected['source.json'] = files['source.json']
        elif request['action'] == 'dispatch': raise ValueError('external_dispatch_source_required')
        result = derive(request, before_state, before_log, dispatch=dispatch, roles=roles)
        expected['stdout.bin'] = result['stdout']
        for key in ('state', 'log'):
            if result[key + '_bytes'] is not None: expected['after-' + key + '.bin'] = result[key + '_bytes']
        if expected != files: raise ValueError('external_dispatch_complete_outputs_changed')
        if value['effects'] != {'state_write': writes['state_write'], 'log_write': writes['log_write'],
                'event_appended': result['event'] is not None, 'provider_invoked': False}:
            raise ValueError('external_dispatch_effects_changed')
        return result

    def prepare(self, repository, usage_state, request, *, paths=None, base_ref=None,
                profile=PROFILE, file_profile=FILE_PROFILE, clock_provenance='explicit_operator_time'):
        review_dispatch_profile(profile); dispatch_file_profile(file_profile); logic.checked_request(request)
        repository = Path(repository).expanduser().absolute()
        if self.instance.is_relative_to(repository.resolve()) or repository.resolve().is_relative_to(self.root):
            raise ValueError('external_dispatch_private_state_must_be_outside_target')
        reserve(self.root, MAX_MATERIAL + MAX_JSON)
        facts = raw = source = dispatch = roles = None; files = {}
        if request['action'] == 'dispatch':
            facts, raw = capture_dispatch_source(repository, base_ref, paths or [], profile)
            roles, routing = validate_dispatch_source(facts, raw, profile)
            dispatch = review_planning.dispatch(facts['changed_paths'], roles, routing, review_dispatch_profile(profile))
        first = capture_dispatch_files(repository, usage_state, request, file_profile, forbidden_roots=self.forbidden)
        native, before_state, before_log = first
        result = derive(request, before_state, before_log, dispatch=dispatch, roles=roles)
        writes = validate_dispatch_files(native, request, before_state, before_log, self.forbidden)
        for name, item in [('before-state.bin', before_state), ('before-log.bin', before_log),
                ('after-state.bin', result['state_bytes']), ('after-log.bin', result['log_bytes']), ('stdout.bin', result['stdout'])]:
            if item is not None: files[name] = item
        if facts is not None:
            source = {'repository_path': native['repository_path'], 'base_ref': base_ref,
                      'explicit_paths': facts['changed_paths'] if paths else []}
            files['source.json'] = logic.wire(facts)
            for item in raw.values(): files['contracts/' + hashlib.sha256(item).hexdigest() + '.bin'] = item
        value = {'schema_version': 1, 'kind': 'external-review-dispatch-plan', **self.binding,
            'profile': profile, 'file_profile': file_profile, 'source_worktree_clean': self.clean,
            'request': deepcopy(request), 'clock_provenance': clock_provenance, 'usage_state': usage_state,
            'native': native, 'source': source, 'files': {name: descriptor(item) for name, item in files.items()},
            'effects': {'state_write': writes['state_write'], 'log_write': writes['log_write'],
                        'event_appended': result['event'] is not None, 'provider_invoked': False},
            'mode': 'report-only', 'evidence_trust': 'unverified', **FLAGS}
        checked(value, 'plan'); self.render(value, files)
        if len(logic.wire(value)) > MAX_JSON or sum(map(len, files.values())) > MAX_MATERIAL:
            raise ValueError('external_dispatch_plan_budget')
        identifier = canonical_digest(value)
        if capture_dispatch_files(repository, usage_state, request, file_profile, forbidden_roots=self.forbidden) != first:
            raise ValueError('external_dispatch_files_changed_during_prepare')
        if facts is not None and observe_dispatch_source(repository, base_ref, paths or [], profile) != (facts, raw):
            raise ValueError('external_dispatch_source_changed_during_prepare')
        self.assert_current()
        with tempfile.TemporaryDirectory(prefix='.incoming-', dir=self.plans) as temporary:
            staged = Path(temporary) / 'data'; staged.mkdir(mode=0o700); blobs = staged / 'blobs'; blobs.mkdir(mode=0o700)
            for item in files.values():
                path = blobs / hashlib.sha256(item).hexdigest(); path.write_bytes(item); path.chmod(0o600)
            atomic_json(staged / 'record.json', value)
            with write_lock(self.root):
                target = self.plans / identifier
                if target.is_symlink(): raise ValueError('unsafe_external_dispatch_plan')
                if not target.exists(): os.rename(staged, target)
                if self.material(identifier) != (value, files): raise ValueError('immutable_external_dispatch_plan_conflict')
        receipt = self.inspect(identifier); receipt['native_inputs_rechecked'] = True
        receipt['source_current_state_rechecked'] = facts is not None
        return receipt

    def execution(self, identifier):
        path = self.executions / (identity(identifier) + '.json')
        if not path.exists() and not path.is_symlink(): return None
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
            raise ValueError('private_external_dispatch_execution_required')
        value = strict_json(safe_bytes(path, limit=65536)); checked(value, 'execution')
        if value['assessment_id'] != identifier or any(value[key] != expected for key, expected in self.binding.items()):
            raise ValueError('external_dispatch_execution_binding_changed')
        return value

    def inspect(self, identifier):
        identifier = identity(identifier); value, files = self.material(identifier); self.render(value, files)
        execution = self.execution(identifier); self.assert_current()
        return {'schema_version': 1, 'assessment_id': identifier, **self.binding,
            'operation': value['request']['action'], 'assessed_at': value['request']['at'],
            'clock_provenance': value['clock_provenance'], 'effects': deepcopy(value['effects']),
            'execution_state': execution['state'] if execution else 'prepared',
            'abandoned_without_native_revert': bool(execution and execution['state'] == 'abandoned'),
            'abandonment': deepcopy(execution['abandonment']) if execution else None,
            'native_file_targets': {key: {'path': value['native'][key]['path'],
                'planned_write': value['effects'][key + '_write'], 'observed': value['native'][key]['observed'],
                'before_present': value['native'][key]['present'], 'before_sha256': value['native'][key]['sha256']}
                for key in ('state', 'log')},
            'retained_complete_outputs_reverified': True, 'native_inputs_rechecked': False,
            'native_outputs_rechecked': False, 'source_current_state_rechecked': False,
            'mode': 'report-only', 'evidence_trust': 'unverified', **FLAGS}

    def pending(self):
        path = self.root / 'pending.json'
        if not path.exists() and not path.is_symlink(): return []
        if path.is_symlink() or path.stat().st_mode & 0o077: raise ValueError('private_external_dispatch_pending_required')
        try: value = strict_json(safe_bytes(path, limit=65536))
        except FileNotFoundError: return []  # A concurrent completed operation removed its marker.
        checked(value, 'pending')
        if any(value[key] != expected for key, expected in self.binding.items()):
            raise ValueError('external_dispatch_pending_binding_changed')
        execution = self.execution(value['assessment_id'])
        return [value['assessment_id']] if execution is None or execution['state'] == 'applying' else []

    def clear_pending(self, identifier, *, only_if_matching=False):
        path = self.root / 'pending.json'
        if not path.exists(): return
        value = strict_json(safe_bytes(path, limit=65536)); checked(value, 'pending')
        if value['assessment_id'] != identifier:
            if only_if_matching: return
            raise ValueError('external_dispatch_pending_identity_changed')
        path.unlink()
        directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try: os.fsync(directory)
        finally: os.close(directory)

    def persist_material(self, identifier):
        """Persist the complete intent and its directory links before native effects.

        A durable journal referring to unsynced blobs cannot support recovery.
        Repeat this bounded barrier on admission, including a plan left visible
        by an earlier failed sync. Preparation alone has no native effects.
        """
        value, files = self.material(identifier)
        root = self.plans / identity(identifier)
        for path in [root / 'record.json', *sorted((root / 'blobs').iterdir())]:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try: os.fsync(descriptor)
            finally: os.close(descriptor)
        for path in (root / 'blobs', root, self.plans, self.executions,
                     self.root, self.root.parent, self.instance):
            descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try: os.fsync(descriptor)
            finally: os.close(descriptor)
        if self.material(identifier) != (value, files):
            raise ValueError('external_dispatch_material_changed_during_sync')

    def apply(self, identifier):
        identifier = identity(identifier)
        with write_lock(self.root):
            value, files = self.material(identifier); self.render(value, files); execution = self.execution(identifier)
            if any(other != identifier for other in self.pending()):
                raise ValueError('external_dispatch_pending_operation_requires_recovery')
            if execution is not None and execution['state'] == 'abandoned':
                raise ValueError('external_dispatch_abandoned_operation')
            rows = [{'kind': key, 'before': value['native'][key], 'before_raw': files.get('before-' + key + '.bin'),
                     'after_raw': files['after-' + key + '.bin']} for key in ('log', 'state') if value['effects'][key + '_write']]
            self.assert_current()
            if execution is not None and execution['state'] == 'applied':
                verify_dispatch_file_outputs(rows, FILE_PROFILE, forbidden_roots=self.forbidden)
                self.clear_pending(identifier, only_if_matching=True)
                receipt = self.inspect(identifier); receipt['native_outputs_rechecked'] = True; receipt['idempotent_apply'] = True
                return receipt
            if execution is None:
                snapshot, state, log = capture_dispatch_files(value['native']['repository_path'], value['usage_state'],
                    value['request'], FILE_PROFILE, forbidden_roots=self.forbidden)
                if snapshot != value['native'] or state != files.get('before-state.bin') or log != files.get('before-log.bin'):
                    raise ValueError('external_dispatch_native_inputs_changed')
                source = value['source']
                if source is not None:
                    facts = strict_json(files['source.json']); raw = {name: files['contracts/' + row['sha256'] + '.bin'] for name, row in facts['files'].items()}
                    if observe_dispatch_source(source['repository_path'], source['base_ref'], source['explicit_paths'], PROFILE) != (facts, raw):
                        raise ValueError('external_dispatch_source_changed_before_apply')
                execution = {'schema_version': 1, 'kind': 'external-review-dispatch-execution', **self.binding,
                    'assessment_id': identifier, 'state': 'applying', 'started_at': now(), 'completed_at': None,
                    'result': None, 'abandonment': None, **FLAGS}
            def persist():
                self.assert_current(); checked(execution, 'execution')
                self.persist_material(identifier)
                pending = {'schema_version': 1, 'kind': 'external-review-dispatch-pending',
                           **self.binding, 'assessment_id': identifier}
                checked(pending, 'pending')
                durable_json(self.root / 'pending.json', pending)
                durable_json(self.executions / (identifier + '.json'), execution)
            result = apply_dispatch_files(rows, FILE_PROFILE, forbidden_roots=self.forbidden,
                allow_after=self.execution(identifier) is not None, before_write=persist)
            execution = {**execution, 'state': 'applied', 'completed_at': now(), 'result': result}
            checked(execution, 'execution'); durable_json(self.executions / (identifier + '.json'), execution)
            self.clear_pending(identifier)
            receipt = self.inspect(identifier); receipt['native_outputs_rechecked'] = True
            receipt['idempotent_apply'] = False; receipt['resumed_partial_operation'] = bool(result['already_desired'])
            return receipt

    def abandon(self, identifier, reason):
        """Release a local pending intent explicitly; never undo or certify file effects."""
        identifier = identity(identifier); logic.text(reason)
        if len(reason) > 2048: raise ValueError('external_dispatch_abandonment_budget')
        with write_lock(self.root):
            self.inspect(identifier); execution = self.execution(identifier); self.assert_current()
            if execution is not None and execution['state'] == 'applied':
                raise ValueError('external_dispatch_completed_cannot_abandon')
            if execution is not None and execution['state'] == 'abandoned':
                if execution['abandonment']['reason'] != reason: raise ValueError('external_dispatch_abandonment_conflict')
            else:
                execution = {'schema_version': 1, 'kind': 'external-review-dispatch-execution', **self.binding,
                    'assessment_id': identifier, 'state': 'abandoned',
                    'started_at': execution['started_at'] if execution else now(), 'completed_at': now(),
                    'result': None, 'abandonment': {'reason': reason, 'native_files_reverted': False,
                                                 'native_outputs_certified': False}, **FLAGS}
                checked(execution, 'execution'); durable_json(self.executions / (identifier + '.json'), execution)
            self.clear_pending(identifier, only_if_matching=True)
            return self.inspect(identifier)

    def stdout(self, identifier):
        value, files = self.material(identifier); self.render(value, files); return files['stdout.bin']
