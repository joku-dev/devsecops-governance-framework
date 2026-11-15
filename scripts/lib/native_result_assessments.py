"""Private node/source-bound native result capture and exact offline replay."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile

from lib import ci_bundle_storage as storage
from lib.candidate_workspace import private_directory
from lib.consumer_intake_store import atomic_json
from lib.portable.contracts import canonical_digest
from lib.provider_ports import general_result_capture, general_result_verify
from lib.result_assessments import ResultContext, identity, require_schema, strict_json, MAX_ASSESSMENT
from lib.supplement_application import safe_bytes, write_lock


class NativeResultContext(ResultContext):
    def __init__(self, instance_root, settings):
        super().__init__(instance_root, settings)
        self.root = private_directory(self.instance_root / 'state/results-native')
        self.raw = private_directory(self.root / 'raw')
        self.assessments = private_directory(self.root / 'assessments')

    def validate(self, value):
        require_schema(value, 'axiom-v2-native-result-assessment.schema.json')
        if any(value[key] != expected for key, expected in self.binding.items()):
            raise ValueError('native_result_node_runtime_or_source_changed')
        if len((json.dumps(value, sort_keys=True, indent=2) + '\n').encode()) > MAX_ASSESSMENT:
            raise ValueError('native_result_assessment_record_limit')
        if value['capture']['verified_at'] != value['assessed_at']:
            raise ValueError('native_result_verification_time_changed')

    def replay(self, value, *, root=None):
        self.validate(value)
        source = self.raw / identity(value['input_id']) if root is None else Path(root)
        verified = general_result_verify(value['provider'], source, value['input_id'],
                                        budget=value['storage_budget_bytes'])
        if (verified['repository'] != value['repository'] or verified['snapshots'] != value['snapshots']
                or verified['verified_at'] != value['assessed_at']):
            raise ValueError('native_result_assessment_differs_from_exact_sources')
        for snapshot in verified['snapshots'].values():
            require_schema(snapshot, 'axiom-v2-result-snapshot.schema.json')
        return value

    def create_native(self, provider, repository, run_id, attempt, credential, *, domain, options,
                      requests=100, budget=storage.DEFAULT_BUDGET):
        with tempfile.TemporaryDirectory(prefix='.incoming-native-', dir=self.raw) as temporary:
            staged = Path(temporary) / 'data'
            verified, input_id, capture = general_result_capture(provider, repository, run_id, attempt,
                credential, staged, domain=domain, options=options, request_budget=requests, storage_budget=budget)
            identity(input_id)
            value = {'schema_version': 1, 'kind': 'v1-compatible-native-result-assessment', **self.binding,
                'source_worktree_clean': self.clean, 'input_origin': 'native_reader', 'provider': provider,
                'input_id': input_id, 'repository': verified['repository'], 'snapshots': verified['snapshots'],
                'assessed_at': verified['verified_at'], 'capture': capture, 'storage_budget_bytes': budget,
                'mode': 'report-only', 'evidence_trust': 'unverified', 'official_acceptance': False,
                'production_approval': False, 'risk_acceptance': False, 'authority_transferred': False}
            self.replay(value, root=staged); self.assert_current()
            with write_lock(self.root):
                target = self.raw / input_id
                if target.is_symlink(): raise ValueError('unsafe_native_result_raw_store')
                if target.exists(): self.replay(value)
                else: os.rename(staged, target)
                assessment_id = canonical_digest(value)
                output = self.assessments / (assessment_id + '.json')
                if output.is_symlink(): raise ValueError('unsafe_native_result_assessment_store')
                if output.exists():
                    if strict_json(safe_bytes(output, limit=MAX_ASSESSMENT)) != value:
                        raise ValueError('immutable_native_result_assessment_conflict')
                else:
                    storage.reserve(self.root, len(json.dumps(value, sort_keys=True, indent=2).encode()) + 1)
                    atomic_json(output, value)
            self.remember(assessment_id, value)
            return assessment_id, deepcopy(value)
