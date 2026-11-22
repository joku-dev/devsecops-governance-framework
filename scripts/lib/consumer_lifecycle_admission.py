"""Complete original consumer lifecycle functions over explicit data/effect ports.

Retained source history is not this node's operating authority.
"""
from __future__ import annotations
from copy import deepcopy
from referencing import Registry, Resource
import base64, hashlib
_OMITTED = object()
_DEFAULT_FETCH = object()
VALIDATION_LEDGER = 'governance/consumer-lifecycle/observations'
MAX_CAPTURE_BYTES = 30 * 1024 * 1024

class ConsumerAdmission:

    def __init__(self, root, context, *, path_factory, profile, process=None, temporary=None, clock=None, validator_class=None, default_fetch=None, architecture=None, argument_parser=None, argv=(), description=None):
        self.root, self.context, self.Path, self.profile = (root, context, path_factory, profile)
        self.process, self.temporary, self.clock = (process, temporary, clock)
        self.validator_class, self.default_fetch, self.architecture = (validator_class, default_fetch, architecture)
        self.argument_parser, self.argv, self.description = (argument_parser, list(argv), description)
        self.positive_id = profile.positive_id
        self.VALIDATION_LEDGER = VALIDATION_LEDGER
        self.MAX_CAPTURE_BYTES = MAX_CAPTURE_BYTES

    def capture_files(self, directory):
        result = self.context.consumer_evidence.replay_capture(directory)
        root = self.Path(directory)
        files = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        self.context.contracts.require(sum(map(len, files.values())) <= self.MAX_CAPTURE_BYTES, 'Capture exceeds supported size')
        return (result, files)

    def replay_embedded(self, encoded):
        self.context.contracts.require(type(encoded) is dict and bool(encoded), 'Complete capture is required')
        files = {}
        for name, data in encoded.items():
            path = self.Path(name)
            self.context.contracts.require(type(name) is str and (not path.is_absolute()) and ('..' not in path.parts) and (str(path) == name), 'Unsafe capture member')
            self.context.contracts.require(type(data) is str and len(data) <= self.MAX_CAPTURE_BYTES * 2, 'Unsupported capture encoding')
            files[name] = base64.b64decode(data, validate=True)
        self.context.contracts.require(sum(map(len, files.values())) <= self.MAX_CAPTURE_BYTES, 'Capture exceeds supported size')
        with self.temporary.TemporaryDirectory() as temporary:
            root = self.Path(temporary)
            for name, data in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            return self.context.consumer_evidence.replay_capture(root)

    def origin_key(self, capture):
        source = capture['source']
        return self.context.contracts.canonical_digest({'repository_id': capture['repository_id'], 'commit_id': source['commit_id'], 'run_id': source['run_id'], 'run_attempt': source['run_attempt'], 'workflow_id': source['workflow_id'], 'workflow_path': source['workflow_path'], 'artifact_name': 'architecture-governance-evidence', 'rule_id': 'operation_readiness', 'resource': 'repository'})

    def producer_fingerprint(self, capture):
        source = capture['source']
        return self.context.contracts.canonical_digest({k: source[k] for k in ('artifact_id', 'artifact_sha256', 'report_sha256', 'observed_at', 'policy_revision', 'input_sha256', 'verified_file_digests')})

    def prepare_receipt(self, capture, encoded, profile, history, *, recorded_at, expected_sequence):
        self.context.consumer_contracts.schema_validator('pilot-operating').validate(profile)
        self.context.contracts.require(capture['profile_ref'] == self.context.preparation.revision_ref(profile), 'Capture preparation differs')
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
        self.context.consumer_contracts.schema_validator('pilot-receipt').validate(receipt)
        return receipt

    def replay_receipts(self, transactions, profile):
        history = []
        for transaction in transactions:
            self.context.consumer_contracts.schema_validator('pilot-receipt').validate(transaction)
            capture = self.replay_embedded(transaction['capture'])
            expected = self.prepare_receipt(capture, transaction['capture'], profile, history, recorded_at=transaction['recorded_at'], expected_sequence=transaction['expected_sequence'])
            self.context.contracts.require(expected is not None and transaction == expected, 'Receipt chain or eligibility proof differs')
            history.append(transaction)
        return history

    def append_capture(self, root, directory, profile, *, recorded_at, expected_sequence):
        capture, files = self.capture_files(directory)
        encoded = {p: base64.b64encode(b).decode('ascii') for p, b in sorted(files.items())}
        with self.context.store.writer_lock(root):
            history = self.replay_receipts(self.context.store.load_transactions(root), profile)
            receipt = self.prepare_receipt(capture, encoded, profile, history, recorded_at=recorded_at, expected_sequence=expected_sequence)
            if receipt is None:
                return {'outcome': 'duplicate', 'transaction_ref': None}
            self.context.store.publish_transaction(self.Path(root) / 'transactions', receipt)
            return {'outcome': receipt['outcome'], 'transaction_ref': self.context.kernel.transaction_ref(receipt)}

    def project_receipts(self, transactions, profile):
        history = self.replay_receipts(transactions, profile)
        eligible = [t for t in history if t['outcome'] == 'eligible_for_pilot']
        conflicts = [t for t in history if t['outcome'] == 'quarantined']
        failures = [t for t in eligible if t['criterion']['status'] == 'fail']
        latest = max(eligible, key=lambda t: (t['source']['observed_at'], t['transaction_id'])) if eligible else None
        key = {'repository_id': profile['scope']['repository_id'], 'domain': 'architecture', 'rule_id': 'operation_readiness', 'finding_type': 'gate_failure', 'resource': 'repository'}
        return {'schema_version': '0.1.0', 'index_type': 'consumer-lifecycle-observation-validation', 'official_state': False, 'live_activation_approved': False, 'enforcement': 'report_only', 'profile_ref': self.context.preparation.revision_ref(profile), 'as_of': history[-1]['recorded_at'] if history else None, 'head_ref': self.context.kernel.transaction_ref(history[-1]) if history else None, 'counts': {'receipts': len(history), 'eligible': len(eligible), 'quarantined': len(conflicts), 'failures': len(failures)}, 'latest_criterion_result': latest['criterion']['status'] if latest else None, 'pilot_finding': {'finding_id': self.context.contracts.finding_id(key), 'state': 'needs_clarification' if conflicts else 'open', 'occurrences': len(failures), 'closure_supported': False} if failures else None, 'receipt_refs': [self.context.kernel.transaction_ref(t) for t in history], 'limitation': 'Eligibility validation only; personal decisions and consumer operating acceptance are required before operational lifecycle use'}

    def verify_new_receipts(self, repo, base_ref):
        """Required PR check: obtain fresh provider bytes instead of trusting persisted claims."""
        root = self.Path(repo)
        profile = self.context.consumer_contracts.load_operating(root)
        old = set(self.process.check_output(['git', 'ls-tree', '-r', '--name-only', base_ref, '--', self.VALIDATION_LEDGER], cwd=root, text=True).splitlines())
        checked = 0
        for path in sorted((root / self.VALIDATION_LEDGER / 'transactions').glob('*.json')):
            if str(path.relative_to(root)) in old:
                continue
            receipt = self.context.adapter.strict_json(path.read_bytes())
            preflight = self.context.adapter.strict_json(base64.b64decode(receipt['capture']['preflight.json'], validate=True))
            self.context.contracts.require(preflight['capture']['method'] == self.profile.capture_method, 'New consumer observation requires actual provider capture')
            with self.temporary.TemporaryDirectory() as temporary:
                observed = self.context.consumer_evidence.collect_preflight(str(receipt['source']['run_id']), self.Path(temporary) / 'capture', repo_root=root)
            now = self.clock()
            self.context.contracts.require(self.origin_key(observed) == receipt['origin_key'] and self.producer_fingerprint(observed) == receipt['producer_fingerprint'], self.profile.literal('legacy_52a2d060d5b766a6'))
            age = (self.context.contracts.timestamp(now) - self.context.contracts.timestamp(observed['source']['observed_at'])).total_seconds()
            self.context.contracts.require(0 <= age <= profile['operating_policy']['maximum_age_seconds'], 'New receipt is stale at PR acceptance')
            self.context.contracts.require(self.context.contracts.timestamp(receipt['recorded_at']) <= self.context.contracts.timestamp(now), 'Receipt claims a future acceptance time')
            checked += 1
        return checked
