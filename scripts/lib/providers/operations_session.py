"""Explicit source/credential/output selection for whole private operations runs."""
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import secrets
from types import SimpleNamespace

from lib.functional_parity import git_read
from lib.operations_collection import collect
from lib.operations_execution import FILES
from lib.operations_input_binding import check_bytes
from lib.operations_sources import text
from lib.portable.contracts import canonical_digest
from lib.portable.runtime import source_digest
from lib.providers import operations_report_profile as profile
from lib.providers.operations_files import NativeSources, held_root, raw_file
from lib.providers.operations_http import NativeBackend, ProviderReads
from lib.providers.operations_security import NativeSecurity
from lib.providers.sbom_export_native import Output
from lib.providers.sbom_export_storage import Record, normalized, owned_directory, read_private
from lib.providers.validation_worktree import signature
from lib.v2_source import active_fingerprints, selected_paths

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = profile.PRODUCT_INPUTS['schema']
CONFIG = profile.PRODUCT_INPUTS['config']
REQUIRED = frozenset(('scripts/lib/operations_application.py', 'scripts/lib/operations_ports.py',
    'scripts/lib/operations_execution.py', 'scripts/lib/operations_collection.py',
    'scripts/lib/operations_reporting.py', 'scripts/lib/operations_replay.py', 'scripts/lib/operations_input_binding.py',
    'scripts/lib/operations_output_replay.py', 'scripts/lib/operations_application_replay.py',
    'scripts/lib/operations_sources.py', 'scripts/lib/operations_security.py',
    'scripts/lib/retained_security.py', 'scripts/lib/retained_security_tree.py',
    'scripts/lib/providers/operations_session.py', 'scripts/lib/providers/operations_files.py',
    'scripts/lib/providers/operations_http.py', 'scripts/lib/providers/operations_http_worker.py',
    'scripts/lib/providers/operations_security.py', 'scripts/lib/providers/operations_report_profile.py',
    'scripts/lib/providers/retained_security_files.py', SCHEMA, CONFIG))


def capture_source(node, product_tree):
    if (not isinstance(node, dict) or set(node) != {'node_id', 'source_revision', 'runtime_source_digest'}
            or not all(isinstance(value, str) for value in node.values())
            or not re.fullmatch('[a-f0-9]{32}', node['node_id'])
            or not re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}', node['source_revision'])
            or not re.fullmatch('[a-f0-9]{64}', node['runtime_source_digest'])
            or not isinstance(product_tree, str) or not re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}', product_tree)):
        raise ValueError('operations_node_context_invalid')
    if node['runtime_source_digest'] != source_digest():
        raise ValueError('operations_runtime_generation_changed')
    if not REQUIRED <= set(selected_paths(ROOT)):
        raise ValueError('operations_execution_closure_not_registered')
    fingerprints = active_fingerprints(ROOT)
    return {'schema_version': 1, 'kind': 'own_registered_operations_source', 'source_root': str(ROOT),
            'active_fingerprints': fingerprints, 'source_digest': canonical_digest(fingerprints),
            'node_context': node, 'product_tree': product_tree, 'source_authentication_independent': False}


def input_bytes(path):
    path = normalized(path)
    with held_root(path.parent) as root:
        return raw_file(root, path.name)


class OperationsOutput(Output):
    NAMES = frozenset(FILES)


class Environment:
    def __init__(self, session):
        self.session = session
        self.record = session.record
        self.backend = None
        self.token = ''
        self.credential_signature = None

    def input(self, kind):
        label = self.session.request[kind + '_label']
        raw = self.record.perform('operations_input', {'kind': kind, 'label': label},
                                  lambda: input_bytes(label), encoding='bytes')
        check_bytes(kind, label, raw, self.session.source, profile.PRODUCT_INPUTS)
        return text(raw)

    def config_text(self):
        return self.input('config')

    def schema_text(self):
        return self.input('schema')

    def observation_text(self):
        return self.input('observation')

    def utc_now(self):
        value = self.record.perform('operations_clock', {}, lambda: datetime.now(timezone.utc).replace(microsecond=0).isoformat())
        return datetime.fromisoformat(value)

    def checkout_sha(self):
        value = self.record.perform('operations_checkout', {}, lambda: git_read(ROOT, 'rev-parse', 'HEAD').decode().strip())
        if value != self.session.node['source_revision']:
            raise ValueError('operations_product_revision_changed')
        return value

    def credential(self):
        path = self.session.credential_path
        if path is None:
            return ''
        before = signature(path.lstat())
        raw = read_private(path, 16384)
        if before != signature(path.lstat()):
            raise ValueError('operations_read_credential_changed')
        try:
            token = raw.decode('utf-8').strip()
        except UnicodeError:
            raise ValueError('operations_read_credential_invalid') from None
        if not token or any(ord(c) < 33 or ord(c) > 126 for c in token):
            raise ValueError('operations_read_credential_invalid')
        self.credential_signature = before
        return token

    def check_credential(self):
        if self.credential_signature is not None and signature(self.session.credential_path.lstat()) != self.credential_signature:
            raise ValueError('operations_read_credential_changed')

    def collect(self, config, now):
        if not self.session.request['live_admitted']:
            raise ValueError('operations_null_observation_requires_explicit_live_fallback')
        from lib.self_security_application import SecurityContext
        source = self.session.request['source_label']
        self.token = self.credential()
        self.backend = NativeBackend(self.record, self.token)
        reads = ProviderReads(self.backend, config['repository'], profile.workflow_queries(config))
        local = NativeSources(source, self.record, profile.INDEXES)
        context = SecurityContext(self.session.instance, self.session.settings)
        if context.binding != {**self.session.node, 'source_tree': self.session.source['product_tree']}:
            raise ValueError('operations_security_product_binding_changed')
        security = NativeSecurity(self.record, local, context, source_worktree=source,
                                  token_file=self.session.credential_path)
        environment = SimpleNamespace(main_reference=reads.main_reference, workflow_queries=profile.workflow_queries,
            workflow_runs=reads.workflow_runs, pull_requests=reads.pull_requests, registry=local.registry,
            index_domains=local.index_domains, index=local.index, records=local.records, security=security.security)
        try:
            return collect(config, now, environment)
        finally:
            self.check_credential()

    def clear(self):
        self.token = ''
        if self.backend is not None:
            self.backend.token = ''


class Session:
    def __init__(self, options, instance, settings):
        self.instance = owned_directory(instance)
        self.settings = settings
        self.node = {k: settings[k] for k in ('node_id', 'source_revision', 'runtime_source_digest')}
        self.source = capture_source(self.node, git_read(ROOT, 'rev-parse', 'HEAD^{tree}').decode().strip())
        if options.get('profile') != profile.PROFILE:
            raise ValueError('operations_profile_unsupported')
        observation = options.get('observation')
        fallback = options.get('allow_live_fallback', False)
        if type(fallback) is not bool:
            raise ValueError('operations_live_admission_invalid')
        if observation is not None and not fallback and any(options.get(key) is not None for key in ('source_worktree', 'token_file')):
            raise ValueError('operations_provided_observation_has_no_native_acquisition')
        live = observation is None or fallback
        if live and options.get('source_worktree') is None:
            raise ValueError('operations_explicit_source_worktree_required')
        if not live and fallback:
            raise ValueError('operations_live_admission_invalid')
        source = normalized(options['source_worktree']) if live else None
        config = normalized(options.get('config') or ROOT / CONFIG)
        observation = None if observation is None else normalized(observation)
        schema = normalized(ROOT / SCHEMA)
        self.credential_path = None if options.get('token_file') is None else normalized(options['token_file'])
        if self.credential_path is not None and self.credential_path in {config, schema, observation}:
            raise ValueError('operations_credential_overlaps_input')
        if options.get('as_of') is not None and not isinstance(options['as_of'], str):
            raise ValueError('operations_as_of_invalid')
        if self.instance == ROOT or self.instance.is_relative_to(ROOT) or ROOT.is_relative_to(self.instance):
            raise ValueError('operations_instance_outside_product_required')
        state = owned_directory(self.instance / 'state', True)
        state = owned_directory(state / 'operations-report', True)
        if os.statvfs(state).f_bavail * os.statvfs(state).f_frsize < 512 * 1024**2:
            raise ValueError('operations_free_space_reserve')
        output = normalized(options.get('output_directory') or state / 'artifacts' / secrets.token_hex(16))
        if output.is_relative_to(self.instance) and not output.is_relative_to(state / 'artifacts'):
            raise ValueError('operations_separate_export_instance_required')
        if source is not None and (output == source or output.is_relative_to(source) or source.is_relative_to(output)):
            raise ValueError('operations_separate_export_source_required')
        if any(output / name in {config, schema, observation, self.credential_path} for name in FILES):
            raise ValueError('operations_export_overlaps_input')
        self.request = {'schema_version': 1, 'profile': profile.PROFILE,
            'provided_observation': observation is not None, 'as_of': options.get('as_of'),
            'live_admitted': live, 'source_label': None if source is None else str(source),
            'credential_kind': 'none' if self.credential_path is None else 'explicit_private_file',
            'token_selected': self.credential_path is not None, 'token_value_retained': False,
            'config_label': str(config), 'schema_label': str(schema),
            'observation_label': None if observation is None else str(observation), 'output_label': str(output)}
        self.record = Record(owned_directory(state / 'records', True), self.request, self.source)
        self.output = OperationsOutput(self.record, output, source=ROOT, credential=self.credential_path)
        self.environment = Environment(self)

    def checkpoint(self):
        self.environment.check_credential()
        if capture_source(self.node, self.source['product_tree']) != self.source or git_read(ROOT, 'rev-parse', 'HEAD').decode().strip() != self.node['source_revision']:
            raise ValueError('operations_own_source_changed_during_operation')

    def close(self):
        self.environment.clear()
