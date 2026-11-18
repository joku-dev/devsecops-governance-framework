"""Retained V1 historical consistency over explicit data and capture adapters.

Historical outputs describe their original scope; they confer no operating
acceptance, personal consent or authority on the executing V2 node.
"""
import base64
from copy import deepcopy
_OMITTED = object()
OPERATING_PATH = 'model/governance/lifecycle/live-operating'
VALIDATION_LEDGER = 'governance/lifecycle/live-validation'
MAX_CAPTURE_BYTES = 25 * 1024 * 1024

class LifecycleAdmission:

    def __init__(self, root, context, *, path_factory):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.OPERATING_PATH = OPERATING_PATH
        self.VALIDATION_LEDGER = VALIDATION_LEDGER
        self.MAX_CAPTURE_BYTES = MAX_CAPTURE_BYTES

    def load_operating(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.path_factory(repo)
        directory = root / OPERATING_PATH
        self.context.contracts.require(directory.is_dir() and (not directory.is_symlink()) and ({p.name for p in directory.iterdir()} == {'00000001.json'}), 'Unexpected operating profile revision')
        self.context.contracts.require(not (directory / '00000001.json').is_symlink(), 'Operating profile must not be a symlink')
        profile = self.context.adapter.strict_json((directory / '00000001.json').read_bytes())
        self.context.contracts.schema_validator('pilot-operating').validate(profile)
        prepared = self.context.preparation.validate_preparation(root)
        self.context.contracts.require(profile['preparation_ref'] == self.context.preparation.revision_ref(prepared['profile']), 'Operating preparation revision differs')
        self.context.contracts.require(profile['role_binding_ref'] == self.context.preparation.revision_ref(prepared['binding']), 'Operating role revision differs')
        self.context.contracts.require(prepared['assignments'], 'Pilot appointments are withdrawn')
        return profile

    def replay_embedded(self, encoded):
        self.context.contracts.require(type(encoded) is dict and bool(encoded), 'Complete capture is required')
        files = {}
        for name, data in encoded.items():
            path = self.path_factory(name)
            self.context.contracts.require(type(name) is str and (not path.is_absolute()) and ('..' not in path.parts) and (str(path) == name), 'Unsafe capture member')
            self.context.contracts.require(type(data) is str and len(data) <= MAX_CAPTURE_BYTES * 2, 'Unsupported capture encoding')
            files[name] = base64.b64decode(data, validate=True)
        self.context.contracts.require(sum(map(len, files.values())) <= MAX_CAPTURE_BYTES, 'Capture exceeds supported size')
        return self.context.provider.replay_embedded(files)

    def origin_key(self, capture):
        source = capture['source']
        return self.context.contracts.canonical_digest({'repository_id': capture['repository_id'], 'commit_id': source['commit_id'], 'run_id': source['run_id'], 'run_attempt': source['run_attempt'], 'workflow_id': source['workflow_id'], 'workflow_path': source['workflow_path'], 'artifact_name': 'governance-repository-security', 'rule_id': 'GRS-002', 'resource': 'refs/heads/main'})

    def producer_fingerprint(self, capture):
        source = capture['source']
        return self.context.contracts.canonical_digest({k: source[k] for k in ('artifact_id', 'artifact_sha256', 'report_sha256', 'observed_at', 'source_profile_version', 'verified_file_digests')})

    def prepare_receipt(self, capture, encoded, profile, history, *, recorded_at, expected_sequence):
        self.context.contracts.schema_validator('pilot-operating').validate(profile)
        self.context.contracts.require(capture['profile_ref'] == profile['preparation_ref'], 'Capture preparation differs')
        key, digest = (self.origin_key(capture), self.producer_fingerprint(capture))
        prior = next((t for t in history if t['origin_key'] == key), None)
        reason = 'producer_conflict' if prior else 'verified_capture_within_operating_policy'
        if prior is None:
            prior = next((t for t in history if t['outcome'] == 'eligible_for_pilot' and t['source']['observed_at'] == capture['source']['observed_at'] and (t['criterion']['status'] != capture['criterion']['status'])), None)
            if prior:
                reason = 'ambiguous_time'
        if any((t['origin_key'] == key and t['producer_fingerprint'] == digest for t in history)):
            return None
        self.context.contracts.require(type(expected_sequence) is int and expected_sequence == len(history), 'Stale receipt sequence')
        age = (self.context.contracts.timestamp(recorded_at) - self.context.contracts.timestamp(capture['source']['observed_at'])).total_seconds()
        self.context.contracts.require(self.context.contracts.timestamp(capture['captured_at']) <= self.context.contracts.timestamp(recorded_at), 'Receipt predates capture')
        self.context.contracts.require(0 <= age <= profile['operating_policy']['maximum_age_seconds'], 'Evidence is future-dated or stale')
        self.context.contracts.require(not history or self.context.contracts.timestamp(recorded_at) >= self.context.contracts.timestamp(history[-1]['recorded_at']), 'Receipt clock regressed')
        receipt = {'schema_version': '0.1.0', 'record_type': 'lifecycle-pilot-eligibility-receipt', 'environment': 'live_pilot_validation', 'official_state': False, 'live_activation_approved': False, 'sequence': len(history) + 1, 'previous_ref': self.context.kernel.transaction_ref(history[-1]) if history else None, 'profile_ref': self.context.preparation.revision_ref(profile), 'recorded_at': recorded_at, 'expected_sequence': expected_sequence, 'origin_key': key, 'producer_fingerprint': digest, 'outcome': 'quarantined' if prior else 'eligible_for_pilot', 'reason': reason, 'conflicts_with': self.context.kernel.transaction_ref(prior) if prior else None, 'provider_authentication': 'new_receipt_requires_independent_PR_check', 'capture': deepcopy(encoded), 'criterion': deepcopy(capture['criterion']), 'source': deepcopy(capture['source']), 'age_seconds_at_receipt': int(age)}
        receipt['transaction_id'] = 'transaction:' + self.context.contracts.canonical_digest(receipt)
        self.context.contracts.schema_validator('pilot-receipt').validate(receipt)
        return receipt

    def replay_receipts(self, transactions, profile):
        history = []
        for transaction in transactions:
            self.context.contracts.schema_validator('pilot-receipt').validate(transaction)
            capture = self.replay_embedded(transaction['capture'])
            expected = self.prepare_receipt(capture, transaction['capture'], profile, history, recorded_at=transaction['recorded_at'], expected_sequence=transaction['expected_sequence'])
            self.context.contracts.require(expected is not None and transaction == expected, 'Receipt chain or eligibility proof differs')
            history.append(transaction)
        return history

    def project_receipts(self, transactions, profile):
        history = self.replay_receipts(transactions, profile)
        eligible = [t for t in history if t['outcome'] == 'eligible_for_pilot']
        conflicts = [t for t in history if t['outcome'] == 'quarantined']
        failures = [t for t in eligible if t['criterion']['status'] == 'fail']
        latest = max(eligible, key=lambda t: (t['source']['observed_at'], t['transaction_id'])) if eligible else None
        key = {'repository_id': profile['scope']['repository_id'], 'domain': 'governance_repository_security', 'rule_id': 'GRS-002', 'finding_type': 'criterion_failure', 'resource': 'refs/heads/main'}
        return {'schema_version': '0.1.0', 'index_type': 'lifecycle-live-pilot-validation', 'official_state': False, 'live_activation_approved': False, 'enforcement': 'report_only', 'profile_ref': self.context.preparation.revision_ref(profile), 'as_of': history[-1]['recorded_at'] if history else None, 'head_ref': self.context.kernel.transaction_ref(history[-1]) if history else None, 'counts': {'receipts': len(history), 'eligible': len(eligible), 'quarantined': len(conflicts), 'failures': len(failures)}, 'latest_criterion_result': latest['criterion']['status'] if latest else None, 'pilot_finding': {'finding_id': self.context.contracts.finding_id(key), 'state': 'needs_clarification' if conflicts else 'open', 'occurrences': len(failures), 'closure_supported': False} if failures else None, 'receipt_refs': [self.context.kernel.transaction_ref(t) for t in history], 'limitation': 'Eligibility validation only; personal decisions and LD-07 are required before operational lifecycle use'}
