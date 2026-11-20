"""Explicit private security acquisition and raw nested record retention."""
import hashlib
from pathlib import Path
import re

from lib.operations_security import reconstruct
from lib.operations_sources import yaml_value
from lib.provider_ports import SELF_SECURITY_PROFILE
from lib.providers import operations_report_profile as profile
from lib.providers.operations_files import SECURITY_MODEL
from lib.providers.retained_security_files import capture
from lib.providers.sbom_export_storage import read_private
from lib.retained_security_tree import MAX_FILE


class NativeSecurity:
    def __init__(self, record, sources, context, *, source_worktree, token_file=None):
        self.record = record
        self.sources = sources
        self.context = context
        self.source_root = str(Path(source_worktree).absolute())
        self.token_file = token_file

    def blob(self, ref):
        if (not isinstance(ref, dict) or set(ref) != {'sha256', 'bytes'}
                or not isinstance(ref['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', ref['sha256'])
                or type(ref['bytes']) is not int or not 0 <= ref['bytes'] <= MAX_FILE):
            raise ValueError('operations_nested_blob_invalid')
        raw = read_private(self.record.blobs / ref['sha256'], MAX_FILE)
        if hashlib.sha256(raw).hexdigest() != ref['sha256'] or len(raw) != ref['bytes']:
            raise ValueError('operations_nested_blob_changed')
        return raw

    def pack(self, tree):
        return {'label': tree.label, 'directories': sorted(tree.directories),
                'files': {name: self.record.blob(raw) for name, raw in tree.files.items()}}

    def security(self, repository, observed_at):
        model = self.sources.read_bytes(SECURITY_MODEL)
        yaml_value(model)  # Preserve original model-read/parse before acquisition.
        arguments = {'repository': repository, 'observed_at': observed_at,
                     'source_root': self.source_root, 'model_sha256': hashlib.sha256(model).hexdigest()}

        def effect():
            from lib.result_assessments import identity
            try:
                operation, value = self.context.create(profile=SELF_SECURITY_PROFILE, repository=repository,
                    source_worktree=self.source_root, model_raw=model, observed_at=observed_at,
                    token_file=self.token_file, fail_on_findings=False)
                identity(operation)
                if value['execution'] != 'complete':
                    raise ValueError('operations_nested_security_incomplete')
                child = identity(value['release_assessment'])
                self.context.assert_current()
                security_tree = capture(self.context.operations / operation)
                release_context = self.context.releases()
                release_context.assert_current()
                release_tree = capture(release_context.operations / child)
                result = {'schema_version': 1, 'operation': operation, 'binding': self.context.binding,
                          'security': self.pack(security_tree), 'release_operation': child, 'release': self.pack(release_tree)}
                reconstruct(result, self.blob, binding=self.context.binding, repository=repository,
                            observed_at=observed_at, model_raw=model, source_root=self.source_root)
                self.context.assert_current()
                return result
            except Exception:
                # A child that cannot be completely retained/reconstructed may
                # leave a useful partial report, never a complete parent record.
                self.record.capture_incomplete = True
                raise

        value = self.record.perform('operations_security_child', arguments, effect)
        raw_report = reconstruct(value, self.blob, binding=self.context.binding, repository=repository,
                                 observed_at=observed_at, model_raw=model, source_root=self.source_root)
        return profile.native_security_error_projection(raw_report)


class RetainedSecurity:
    def __init__(self, calls, sources, *, binding, source_root):
        self.calls = calls
        self.sources = sources
        self.binding = binding
        self.source_root = source_root

    def security(self, repository, observed_at):
        model = self.sources.read_bytes(SECURITY_MODEL)
        yaml_value(model)
        arguments = {'repository': repository, 'observed_at': observed_at,
                     'source_root': self.source_root, 'model_sha256': hashlib.sha256(model).hexdigest()}
        value = self.calls.call('operations_security_child', arguments)
        raw_report = reconstruct(value, self.calls.blob, binding=self.binding, repository=repository,
                                 observed_at=observed_at, model_raw=model, source_root=self.source_root)
        return profile.native_security_error_projection(raw_report)
