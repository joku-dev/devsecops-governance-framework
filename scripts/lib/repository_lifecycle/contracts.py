"""Original lifecycle consistency over an explicit retained data context.

Technical reference: V1 6b557f. Original records remain declared historical
facts; these checks never grant this node live approval, identity or consent.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from functools import lru_cache
import hashlib
import json
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from lib.result_ledger import canonical_digest
SCHEMA_BASE = 'https://joku-dev.github.io/devsecops-governance-framework/schemas/'
KINDS = ('observation', 'decision', 'remediation', 'closure', 'event')
FORMAT_CHECKER = FormatChecker()

class ContractError(ValueError):
    """A structural or offline consistency contract was violated."""

@FORMAT_CHECKER.checks('date-time', raises=(ValueError, TypeError))
def check_utc_timestamp(value):
    return isinstance(value, str) and datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').strftime('%Y-%m-%dT%H:%M:%SZ') == value

class LifecycleContracts:

    def __init__(self, root, context, *, validator_class, path_factory):
        self.root = root
        self.context = context
        self.validator_class = validator_class
        self.path_factory = path_factory
        self.canonical_digest = canonical_digest
        self.format_checker = FORMAT_CHECKER
        self.kinds = KINDS

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            raise ContractError(message)

    @lru_cache(maxsize=32)
    def schema_validator(self, kind: str) -> Draft202012Validator:
        self.require(kind in (*KINDS, 'profile', 'transaction', 'index', 'decision-v0.2', 'remediation-v0.2', 'action-transaction', 'action-index', 'closure-v0.2', 'closure-transaction', 'closure-index', 'exception', 'exception-profile', 'exception-transaction', 'exception-index', 'event-v0.2', 'overview', 'candidate-context', 'candidates', 'devsecops-source', 'architecture-source', 'pilot-role-binding', 'live-profile-preparation', 'pilot-operating', 'pilot-receipt', 'personal-channel-probe', 'pilot-action-request', 'pilot-action-receipt', 'operating-acceptance'), 'Unknown lifecycle schema kind')
        resources = []
        for path in sorted((self.root / 'schemas').glob('governance-lifecycle-*.schema.json')):
            schema = json.loads(path.read_text(encoding='utf-8'))
            self.validator_class.check_schema(schema)
            resources.append((SCHEMA_BASE + path.name, Resource.from_contents(schema)))
        trust = json.loads((self.root / 'schemas/evidence-trust-record.schema.json').read_text())
        resources.append((SCHEMA_BASE + 'evidence-trust-record.schema.json', Resource.from_contents(trust)))
        registry = Registry().with_resources(resources)
        schema = json.loads((self.root / 'schemas' / f'governance-lifecycle-{kind}.schema.json').read_text())
        return self.validator_class(schema, registry=registry, format_checker=FORMAT_CHECKER)

    def timestamp(self, value: str) -> datetime:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')

    def finding_id(self, key: dict) -> str:
        return 'finding:' + canonical_digest({'fingerprint_version': '1', 'key': key})

    def record_ref(self, record: dict) -> dict:
        return {'id': record['record_id'], 'digest': canonical_digest(record)}

    def versioned_ref(self, value: dict, id_field: str='id') -> dict:
        return {'id': value[id_field], 'version': value['version'], 'digest': canonical_digest(value)}

    def approval_target(self, record: dict) -> str:
        return canonical_digest({key: value for key, value in record.items() if key != 'approval'})

    def observation_identity(self, record: dict) -> str:
        """Delivery identity excludes receipt time and result bytes; conflicts stay visible."""
        return canonical_digest({'finding': record['finding'], 'source_context': record['body']['source_context']})

    def validate_record(self, record: dict) -> None:
        kind = record.get('record_type')
        schema_kind = kind + '-v0.2' if kind in ('decision', 'remediation', 'closure', 'event') and record.get('schema_version') == '0.2.0' else kind
        self.schema_validator(schema_kind).validate(record)
        self.require(record['finding']['finding_id'] == self.finding_id(record['finding']['key']), 'Finding fingerprint mismatch')
        body = record['body']
        if kind in ('decision', 'closure'):
            approval = record['approval']
            self.require(approval['target_digest'] == self.approval_target(record), 'Approval content binding mismatch')
            self.require(approval['finding_id'] == record['finding']['finding_id'], 'Approval scope mismatch')
            self.require(approval['expected_revision'] == body['expected_revision'], 'Approval revision mismatch')
            role = 'remediation_decider' if kind == 'decision' else 'closure_approver'
            self.require(approval['role'] == role, 'Approval role mismatch')
            self.require(self.timestamp(approval['issued_at']) <= self.timestamp(record['recorded_at']), 'Approval after recording')
        elif kind == 'event':
            self.require(body['revision'] == body['expected_revision'] + 1, 'Event revision must advance by one')
            self.require(self.timestamp(body['effective_at']) <= self.timestamp(record['recorded_at']), 'Event effective time after recording')
        elif kind == 'observation':
            self.require(self.timestamp(body['observed_at']) <= self.timestamp(body['acceptance']['evaluated_at']) <= self.timestamp(record['recorded_at']), 'Observation time order')

    def acceptance_statement(self, record: dict) -> dict:
        target = deepcopy(record)
        acceptance = target['body'].pop('acceptance')
        return {'environment': 'synthetic', 'observation_digest': canonical_digest(target), 'assessment': {k: v for k, v in acceptance.items() if k != 'proof_ref'}}

    def fixture_resource(self, reference: dict, resources: dict[str, bytes]) -> bytes:
        uri = reference['uri']
        self.require(uri.startswith('fixture://'), 'Only fixture resources are supported; live verification is unavailable')
        self.require(uri in resources, 'Missing fixture resource')
        content = resources[uri]
        self.require(hashlib.sha256(content).hexdigest() == reference['digest'], 'Fixture digest mismatch')
        return content

    def validate_test_profile(self, profile: dict) -> None:
        self.schema_validator('profile').validate(profile)

    def validate_test_record(self, record: dict, profile: dict, resources: dict[str, bytes]) -> None:
        self.validate_test_profile(profile)
        self.validate_record(record)
        self.require(record['environment'] == 'synthetic', 'Live records cannot use the test verifier')
        self.require(record['profile_ref'] == self.versioned_ref(profile, 'profile_id'), 'Test profile binding mismatch')
        self.require(record['finding']['key']['repository_id'] == profile['repository_id'], 'Test repository mismatch')
        if record['record_type'] in ('decision', 'closure'):
            approval = record['approval']
            binding = profile['role_binding']
            self.require(approval['role_binding_ref'] == self.versioned_ref(binding), 'Role binding mismatch')
            self.require(approval['subject_id'] == binding['assignments'][approval['role']], 'Subject not assigned to role')
            self.require(approval['channel'] == profile['approval_channel'], 'Approval channel mismatch')
            proof = json.loads(self.fixture_resource(approval['proof_ref'], resources))
            expected = {k: v for k, v in approval.items() if k != 'proof_ref'}
            self.require(proof == {'environment': 'synthetic', 'approval': expected}, 'Synthetic approval proof mismatch')
        elif record['record_type'] == 'remediation':
            self.fixture_resource(record['body']['work_ref'], resources)
        elif record['record_type'] == 'observation':
            body = record['body']
            context = body['source_context']
            self.require(context['kind'] in profile['allowed_contexts'], 'Context not accepted by test profile')
            self.require(context['producer_id'] in profile['allowed_producers'], 'Producer not accepted by test profile')
            self.require(context['repository_id'] == profile['repository_id'], 'Source repository mismatch')
            self.require(body['acceptance']['profile_ref'] == record['profile_ref'], 'Acceptance profile mismatch')
            proof = json.loads(self.fixture_resource(body['acceptance']['proof_ref'], resources))
            self.require(proof == self.acceptance_statement(record), 'Synthetic acceptance proof mismatch')
            snapshot_bytes = self.fixture_resource(body['snapshot_ref'], resources)
            snapshot = json.loads(snapshot_bytes)
            report_schema = json.loads((self.root / 'schemas/governance-repository-security-report.schema.json').read_text())
            self.validator_class(report_schema, format_checker=FORMAT_CHECKER).validate(snapshot)
            self.require(snapshot['repository_id'] == context['repository_id'], 'Snapshot repository mismatch')
            self.require(snapshot['observed_at'] == body['observed_at'], 'Snapshot observation time mismatch')
            self.require(snapshot['profile_version'] == body['profile_version'], 'Snapshot profile mismatch')
            criteria = [c for c in snapshot['criteria'] if c['id'] == record['finding']['key']['rule_id']]
            self.require(len(criteria) == 1, 'Snapshot must contain exactly one matching criterion')
            self.require(criteria[0]['key'] == body['rule_key'] and criteria[0]['status'] == body['result'], 'Snapshot criterion mismatch')
            trust = body['trust']
            source = trust['capture']['source']
            for key in ('repository_id', 'commit_id', 'run_id', 'run_attempt'):
                self.require(source[key] == context[key], 'Trust source context mismatch')
            subjects = trust['capture']['subjects']
            self.require(any((s['digest'] == body['snapshot_ref']['digest'] and s['size_bytes'] == len(snapshot_bytes) and (s['evidence_ref'] == body['snapshot_ref']['uri']) for s in subjects)), 'Trust subject does not bind snapshot')
            if body['acceptance']['outcome'] == 'accepted':
                self.check_test_trust(record, profile)

    def check_test_trust(self, observation: dict, profile: dict) -> None:
        """Check asserted synthetic acceptance, without authenticating a producer."""
        body = observation['body']
        trust = body['trust']
        self.require(trust['assessment_status'] == 'evaluated' and trust['effective_level'] in ('provenance_verified', 'attested'), 'Insufficient observation trust')
        checks = trust['checks']
        self.require(len({c['id'] for c in checks}) == len(checks), 'Duplicate trust check IDs')
        by_id = {c['id']: c for c in checks}
        self.require(all((name in by_id and by_id[name]['result'] == 'pass' and by_id[name]['evidence_refs'] for name in profile['required_checks'])), 'Required trust check missing or not passed')
        observed, accepted, verified = (self.timestamp(value) for value in (body['observed_at'], body['acceptance']['evaluated_at'], trust['verified_at']))
        self.require(observed <= verified <= accepted, 'Trust verification outside acceptance window')
        self.require(0 <= (accepted - observed).total_seconds() <= profile['maximum_age_seconds'], 'Observation stale at acceptance')

    def resolve_record(self, reference: dict, records: dict[str, dict], kind: str) -> dict:
        self.require(reference['id'] in records, 'Missing referenced record')
        value = records[reference['id']]
        self.require(value['record_type'] == kind and self.record_ref(value) == reference, 'Record reference binding mismatch')
        return value

    def check_closure_prerequisites(self, closure: dict, records: dict[str, dict], profile: dict, resources: dict[str, bytes], *, as_of: str) -> None:
        """Check a synthetic closure packet, not ledger state, revocation history or authority."""
        self.validate_test_record(closure, profile, resources)
        self.require(closure['record_type'] == 'closure', 'Expected a closure')
        body = closure['body']
        self.require(body['as_of'] == as_of, 'Explicit as_of must match the closure content')
        now = self.timestamp(as_of)
        self.require(self.timestamp(closure['recorded_at']) <= now, 'Closure recorded after as_of')
        self.require(closure['approval']['disposition'] == 'approve', 'Closure not approved')
        remediation = self.resolve_record(body['remediation_ref'], records, 'remediation')
        decision = self.resolve_record(remediation['body']['decision_ref'], records, 'decision')
        failing = self.resolve_record(body['failing_observation_ref'], records, 'observation')
        passing = self.resolve_record(body['passing_observation_ref'], records, 'observation')
        for record in (remediation, decision, failing, passing):
            self.validate_test_record(record, profile, resources)
            self.require(record['finding'] == closure['finding'], 'Closure finding/scope mismatch')
            self.require(self.timestamp(record['recorded_at']) <= now, 'Referenced record after as_of')
        self.require(decision['approval']['disposition'] == 'approve', 'Remediation decision not approved')
        self.require(decision['body']['observation_ref'] == self.record_ref(failing), 'Decision concerns a different failure')
        self.require(remediation['body']['action'] == decision['body']['action'], 'Remediation differs from authorized action')
        self.require(remediation['body']['progress'] == 'completed', 'Remediation is not completed')
        self.require(failing['body']['result'] == 'fail' and passing['body']['result'] == 'pass', 'Closure requires criterion FAIL and PASS')
        fail_time, pass_time = (self.timestamp(r['body']['observed_at']) for r in (failing, passing))
        self.require(fail_time < pass_time, 'PASS must be newer than the failure')
        self.require(self.timestamp(remediation['recorded_at']) <= pass_time <= self.timestamp(closure['approval']['issued_at']), 'Closure evidence must follow remediation and precede approval')
        self.require(self.timestamp(decision['recorded_at']) <= self.timestamp(remediation['recorded_at']), 'Remediation predates decision')
        self.require(decision['body']['expected_revision'] < remediation['body']['expected_revision'] < body['expected_revision'], 'Closure packet revisions out of order')
        for key in ('profile_version', 'policy_version', 'source_schema'):
            self.require(failing['body'][key] == passing['body'][key], 'Incompatible evidence versions')
        for observation in (failing, passing):
            self.require(observation['body']['acceptance']['outcome'] == 'accepted', 'Observation not accepted')
        trust = passing['body']['trust']
        self.require(pass_time <= self.timestamp(trust['verified_at']) <= self.timestamp(closure['approval']['issued_at']), 'Trust verification time outside closure window')
        self.require(0 <= (now - pass_time).total_seconds() <= profile['maximum_age_seconds'], 'Closure evidence is stale or from the future')

    def check_event_references(self, event: dict, records: dict[str, dict]) -> None:
        """Check one event's references; no append, concurrency control or projection."""
        self.validate_record(event)
        self.require(event['record_type'] == 'event', 'Expected an event')
        body = event['body']
        if body['previous_event_ref'] is not None:
            previous = self.resolve_record(body['previous_event_ref'], records, 'event')
            self.validate_record(previous)
            self.require(previous['finding'] == event['finding'] and previous['environment'] == event['environment'] and (previous['profile_ref'] == event['profile_ref']), 'Event predecessor scope mismatch')
            self.require(previous['body']['revision'] == body['expected_revision'], 'Event predecessor revision mismatch')
            self.require(self.timestamp(previous['recorded_at']) <= self.timestamp(event['recorded_at']), 'Event predecessor recorded later')
        kinds = {'finding_opened': 'observation', 'observation_added': 'observation', 'decision_recorded': 'decision', 'remediation_recorded': 'remediation', 'finding_closed': 'closure', 'finding_reopened': 'observation', 'exception_recorded': 'exception'}
        for reference in body['source_refs']:
            if body['event_type'] == 'clarification_required':
                self.require(reference['id'] in records, 'Missing clarification source')
                kind = records[reference['id']]['record_type']
            else:
                kind = kinds[body['event_type']]
            source = self.resolve_record(reference, records, kind)
            self.validate_record(source)
            self.require(source['finding'] == event['finding'] and source['environment'] == event['environment'] and (source['profile_ref'] == event['profile_ref']), 'Event source scope mismatch')
            self.require(self.timestamp(source['recorded_at']) <= self.timestamp(event['recorded_at']), 'Event source recorded later')
            if body['event_type'] in ('finding_opened', 'finding_reopened'):
                self.require(source['body']['result'] == 'fail' and source['body']['acceptance']['outcome'] == 'accepted', 'Opening requires accepted criterion FAIL')
