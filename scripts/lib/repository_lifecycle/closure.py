"""Original lifecycle consistency over an explicit retained data context.

Technical reference: V1 6b557f. Original records remain declared historical
facts; these checks never grant this node live approval, identity or consent.
"""
import base64
from copy import deepcopy

class LifecycleClosure:

    def __init__(self, root, context, *, validator_class, path_factory):
        self.root = root
        self.context = context
        self.validator_class = validator_class
        self.path_factory = path_factory

    def accepted_resources(self, state):
        resources = {}
        for transaction in state['transactions']:
            if transaction['outcome'] == 'accepted':
                for uri, content in transaction['resources'].items():
                    data = base64.b64decode(content, validate=True)
                    self.context.contracts.require(uri not in resources or resources[uri] == data, 'Accepted resource URI changed content')
                    resources[uri] = data
        return resources

    def prepare_closure_transaction(self, record, resources, profile, state, *, expected_revision):
        self.context.contracts.require(record.get('record_type') == 'closure' and record.get('schema_version') == '0.2.0', 'Closure intake requires the synthetic 0.2.0 closure contract')
        self.context.contracts.validate_test_record(record, profile, resources)
        self.context.contracts.require(set(resources) == {record['approval']['proof_ref']['uri']}, 'Only the bound closure consent resource is accepted')
        self.context.adapter.strict_json(self.context.contracts.fixture_resource(record['approval']['proof_ref'], resources))
        previous = state['closures'].get(record['record_id'])
        if previous is not None:
            self.context.contracts.require(previous == record, 'Closure ID already binds different immutable content')
            return None
        fid = record['finding']['finding_id']
        body = record['body']
        revision = self.context.kernel.current_revision(state, fid)
        self.context.contracts.require(type(expected_revision) is int and expected_revision == body['expected_revision'] == revision and (revision > 0), 'Stale expected finding revision')
        self.context.contracts.require(fid not in state['active_closures'], 'Finding already closed')
        self.context.contracts.require(not any((t['observation']['finding']['finding_id'] == fid for t in state['conflicts'])), 'Unresolved evidence conflict prevents closure')
        self.context.contracts.require(body['as_of'] == record['recorded_at'], 'Closure as_of must equal acceptance recording time')
        self.context.contracts.require(self.context.contracts.timestamp(record['recorded_at']) >= self.context.contracts.timestamp(state['transactions'][-1]['recorded_at']), 'Closure predates accepted ledger head')
        self.context.contracts.require(self.context.contracts.timestamp(record['approval']['issued_at']) >= self.context.contracts.timestamp(state['events'][fid][-1]['recorded_at']), 'Closure consent predates accepted finding revision')
        records = {**state['observations'], **state['actions']}
        remediation = self.context.contracts.resolve_record(body['remediation_ref'], records, 'remediation')
        self.context.contracts.require(state['remediation_heads'].get(remediation['body']['remediation_id']) == remediation, 'Closure must reference latest remediation revision')
        decision = self.context.contracts.resolve_record(remediation['body']['decision_ref'], records, 'decision')
        self.context.contracts.require(state['decision_status'].get(decision['record_id']) == 'approved', 'Closure remediation approval is not active')
        passing = self.context.contracts.resolve_record(body['passing_observation_ref'], records, 'observation')
        observations = [r for r in state['observations'].values() if r['finding']['finding_id'] == fid]
        latest = max(observations, key=lambda r: (r['body']['observed_at'], r['record_id']))
        self.context.contracts.require(latest == passing, 'Closure must use the latest accepted observation')
        failures = [r for r in observations if r['body']['result'] == 'fail']
        self.context.contracts.require(all((self.context.contracts.timestamp(r['body']['observed_at']) < self.context.contracts.timestamp(passing['body']['observed_at']) for r in failures)), 'PASS must follow every accepted failure')
        self.context.contracts.require(all((self.context.contracts.timestamp(r['body']['observed_at']) <= self.context.contracts.timestamp(remediation['recorded_at']) for r in failures)), 'Remediation must follow every accepted failure')
        prior_closures = [c for c in state['closures'].values() if c['finding']['finding_id'] == fid]
        if prior_closures:
            last = prior_closures[-1]
            self.context.contracts.require(self.context.contracts.timestamp(decision['recorded_at']) > self.context.contracts.timestamp(last['recorded_at']), 'Reopened finding requires a new decision')
        evidence = self.accepted_resources(state)
        for uri, data in resources.items():
            self.context.contracts.require(uri not in evidence or evidence[uri] == data, 'Closure resource shadows accepted evidence')
            evidence[uri] = data
        self.context.contracts.check_closure_prerequisites(record, records, profile, evidence, as_of=body['as_of'])
        previous_event = state['events'][fid][-1]
        event = {'schema_version': '0.1.0', 'record_type': 'event', 'environment': 'synthetic', 'profile_ref': deepcopy(record['profile_ref']), 'finding': deepcopy(record['finding']), 'recorded_at': record['recorded_at'], 'body': {'event_type': 'finding_closed', 'revision': revision + 1, 'expected_revision': revision, 'previous_event_ref': self.context.contracts.record_ref(previous_event), 'effective_at': record['approval']['issued_at'], 'policy_version': passing['body']['policy_version'], 'source_refs': [self.context.contracts.record_ref(record)]}}
        event['record_id'] = 'event:' + self.context.contracts.canonical_digest(event)
        self.context.contracts.check_event_references(event, {**records, record['record_id']: record, previous_event['record_id']: previous_event})
        transaction = {'schema_version': '0.3.0', 'environment': 'synthetic', 'sequence': len(state['transactions']) + 1, 'previous_ref': self.context.kernel.transaction_ref(state['transactions'][-1]), 'profile_ref': self.context.contracts.versioned_ref(profile, 'profile_id'), 'recorded_at': record['recorded_at'], 'expected_revision': revision, 'outcome': 'accepted', 'reason': 'finding_closed', 'record': deepcopy(record), 'event': event, 'resources': {uri: base64.b64encode(data).decode('ascii') for uri, data in sorted(resources.items())}}
        transaction['transaction_id'] = 'transaction:' + self.context.contracts.canonical_digest(transaction)
        self.context.contracts.schema_validator('closure-transaction').validate(transaction)
        return transaction

    def reopens(self, observation, state):
        closed = state['active_closures'].get(observation['finding']['finding_id'])
        if closed is None or observation['body']['result'] != 'fail':
            return False
        passing = state['observations'][closed['body']['passing_observation_ref']['id']]
        return self.context.contracts.timestamp(observation['body']['observed_at']) > self.context.contracts.timestamp(passing['body']['observed_at'])

    def add_closure_projection(self, index, state):
        index['schema_version'] = '0.3.0'
        index['counts']['closures'] = len(state['closures'])
        for finding in index['findings']:
            fid = finding['finding_id']
            closed = state['active_closures'].get(fid)
            finding['closure_supported'] = True
            finding['closure_refs'] = [self.context.contracts.record_ref(c) for c in state['closures'].values() if c['finding']['finding_id'] == fid]
            finding['active_closure_ref'] = self.context.contracts.record_ref(closed) if closed and (not finding['conflict_refs']) else None
            finding['reopen_count'] = sum((e['body']['event_type'] == 'finding_reopened' for e in state['events'][fid]))
            if finding['active_closure_ref'] is not None:
                finding['state'] = 'closed'
