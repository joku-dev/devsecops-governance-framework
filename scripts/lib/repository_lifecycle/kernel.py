"""Original lifecycle consistency over an explicit retained data context.

Technical reference: V1 6b557f. Original records remain declared historical
facts; these checks never grant this node live approval, identity or consent.
"""
from copy import deepcopy
import base64

class LifecycleKernel:

    def __init__(self, root, context, *, validator_class, path_factory):
        self.root = root
        self.context = context
        self.validator_class = validator_class
        self.path_factory = path_factory

    def producer_digest(self, observation):
        body = observation['body']
        payload = {key: body[key] for key in ('observed_at', 'result', 'rule_key', 'granularity', 'profile_version', 'policy_version', 'source_schema', 'source_context')}
        payload['snapshot_digest'] = body['snapshot_ref']['digest']
        return self.context.contracts.canonical_digest(payload)

    def transaction_ref(self, transaction):
        return {'id': transaction['transaction_id'], 'digest': self.context.contracts.canonical_digest(transaction)}

    def transaction_name(self, transaction):
        return f"{transaction['sequence']:08d}-{transaction['transaction_id'].split(':')[1]}.json"

    def empty_state(self):
        return {'transactions': [], 'observations': {}, 'deliveries': {}, 'events': {}, 'conflicts': [], 'actions': {}, 'decision_status': {}, 'remediation_heads': {}, 'closures': {}, 'active_closures': {}, 'exceptions': {}, 'exception_waivers': {}, 'revoked_exceptions': set()}

    def current_revision(self, state, finding):
        events = state['events'].get(finding, [])
        return events[-1]['body']['revision'] if events else 0

    def classify(self, observation, state):
        identity = self.context.contracts.observation_identity(observation)
        prior = state['deliveries'].get(identity)
        if prior:
            if self.producer_digest(prior) != self.producer_digest(observation):
                return 'producer_conflict'
            if self.context.contracts.canonical_digest(prior['body']['trust']) != self.context.contracts.canonical_digest(observation['body']['trust']):
                return 'reassessment_required'
            return 'duplicate'
        candidates = [r for r in state['observations'].values() if r['finding'] == observation['finding']]
        body = observation['body']
        for previous in candidates:
            other = previous['body']
            if any((body[k] != other[k] for k in ('profile_version', 'policy_version', 'source_schema'))):
                return 'incompatible_version'
            if body['observed_at'] == other['observed_at'] and body['result'] != other['result']:
                return 'ambiguous_time'
        return 'new_observation'

    def make_event(self, observation, state, reason):
        fid = observation['finding']['finding_id']
        events = state['events'].get(fid, [])
        conflict = reason != 'new_observation'
        if not events and (conflict or observation['body']['result'] != 'fail'):
            return None
        event_type = 'clarification_required' if conflict else 'observation_added' if events else 'finding_opened'
        if not conflict and state['active_closures']:
            reopens = self.context.closure.reopens
            if reopens(observation, state):
                event_type = 'finding_reopened'
        source = observation
        if conflict:
            source = next((r for r in state['observations'].values() if r['finding'] == observation['finding']))
        body = {'event_type': event_type, 'revision': len(events) + 1, 'expected_revision': len(events), 'previous_event_ref': self.context.contracts.record_ref(events[-1]) if events else None, 'effective_at': observation['body']['observed_at'], 'policy_version': source['body']['policy_version'], 'source_refs': [self.context.contracts.record_ref(source)]}
        event = {'schema_version': '0.1.0', 'record_type': 'event', 'environment': 'synthetic', 'profile_ref': observation['profile_ref'], 'finding': observation['finding'], 'recorded_at': observation['recorded_at'], 'body': body}
        event['record_id'] = 'event:' + self.context.contracts.canonical_digest(event)
        records = {**state['observations'], **{e['record_id']: e for es in state['events'].values() for e in es}}
        if not conflict:
            records[observation['record_id']] = observation
        self.context.contracts.check_event_references(event, records)
        return event

    def prepare_transaction(self, observation, resources, profile, state, *, expected_revision):
        self.context.contracts.require(observation.get('record_type') == 'observation', 'CLG-02 accepts observations only')
        self.context.contracts.validate_test_record(observation, profile, resources)
        self.context.contracts.require(observation['body']['acceptance']['outcome'] == 'accepted', 'Observation is not accepted by the synthetic profile')
        required_uris = {observation['body']['snapshot_ref']['uri'], observation['body']['acceptance']['proof_ref']['uri']}
        self.context.contracts.require(set(resources) == required_uris and len(resources) == 2, 'Exactly snapshot and acceptance resources are required')
        reason = self.classify(observation, state)
        if reason == 'duplicate':
            return None
        for transaction in state['conflicts']:
            other = transaction['observation']
            if self.context.contracts.observation_identity(other) == self.context.contracts.observation_identity(observation) and self.producer_digest(other) == self.producer_digest(observation) and (self.context.contracts.canonical_digest(other['body']['trust']) == self.context.contracts.canonical_digest(observation['body']['trust'])):
                return None
        fid = observation['finding']['finding_id']
        self.context.contracts.require(type(expected_revision) is int and expected_revision == self.current_revision(state, fid), 'Stale expected finding revision')
        if state['transactions']:
            self.context.contracts.require(self.context.contracts.timestamp(observation['recorded_at']) >= self.context.contracts.timestamp(state['transactions'][-1]['recorded_at']), 'Recording time predates the accepted ledger head')
        if reason == 'new_observation':
            self.context.contracts.require(observation['record_id'] not in state['observations'], 'Observation ID reused for different producer context')
        event = self.make_event(observation, state, reason)
        transaction = {'schema_version': '0.1.0', 'environment': 'synthetic', 'sequence': len(state['transactions']) + 1, 'previous_ref': self.transaction_ref(state['transactions'][-1]) if state['transactions'] else None, 'profile_ref': self.context.contracts.versioned_ref(profile, 'profile_id'), 'recorded_at': observation['recorded_at'], 'expected_revision': expected_revision, 'outcome': 'accepted' if reason == 'new_observation' else 'quarantined', 'reason': reason, 'observation': deepcopy(observation), 'resources': {uri: base64.b64encode(data).decode('ascii') for uri, data in sorted(resources.items())}, 'event': event}
        transaction['transaction_id'] = 'transaction:' + self.context.contracts.canonical_digest(transaction)
        self.context.contracts.schema_validator('transaction').validate(transaction)
        return transaction

    def apply_transaction(self, transaction, state):
        if transaction['schema_version'] == '0.4.0':
            apply_exception = self.context.exceptions.apply_exception
            state['transactions'].append(transaction)
            apply_exception(transaction, state)
            state['events'][transaction['record']['finding']['finding_id']].append(transaction['event'])
            return
        if transaction['schema_version'] == '0.3.0':
            record = transaction['record']
            state['transactions'].append(transaction)
            state['closures'][record['record_id']] = record
            fid = record['finding']['finding_id']
            state['active_closures'][fid] = record
            state['events'][fid].append(transaction['event'])
            return
        if transaction['schema_version'] == '0.2.0':
            apply_action = self.context.decisions.apply_action
            state['transactions'].append(transaction)
            apply_action(transaction, state)
            fid = transaction['record']['finding']['finding_id']
            state['events'].setdefault(fid, []).append(transaction['event'])
            return
        observation = transaction['observation']
        state['transactions'].append(transaction)
        if transaction['outcome'] == 'accepted':
            state['observations'][observation['record_id']] = observation
            state['deliveries'][self.context.contracts.observation_identity(observation)] = observation
        else:
            state['conflicts'].append(transaction)
        if transaction['event']:
            fid = observation['finding']['finding_id']
            state['events'].setdefault(fid, []).append(transaction['event'])
            if transaction['event']['body']['event_type'] == 'finding_reopened':
                state['active_closures'].pop(fid)

    def replay(self, transactions, profile):
        """Verify the complete ordered chain by regenerating each transaction, then reduce."""
        self.context.contracts.validate_test_profile(profile)
        state = self.empty_state()
        for transaction in transactions:
            action = transaction.get('schema_version') == '0.2.0'
            closure = transaction.get('schema_version') == '0.3.0'
            exception = transaction.get('schema_version') == '0.4.0'
            self.context.contracts.schema_validator('exception-transaction' if exception else 'closure-transaction' if closure else 'action-transaction' if action else 'transaction').validate(transaction)
            resources = {uri: base64.b64decode(data, validate=True) for uri, data in transaction['resources'].items()}
            if exception:
                prepare_exception_transaction = self.context.exceptions.prepare_exception_transaction
                expected = prepare_exception_transaction(transaction['record'], resources, profile, state, expected_revision=transaction['expected_revision'])
            elif closure:
                prepare_closure_transaction = self.context.closure.prepare_closure_transaction
                expected = prepare_closure_transaction(transaction['record'], resources, profile, state, expected_revision=transaction['expected_revision'])
            elif action:
                prepare_action_transaction = self.context.decisions.prepare_action_transaction
                expected = prepare_action_transaction(transaction['record'], resources, profile, state, expected_revision=transaction['expected_revision'])
            else:
                expected = self.prepare_transaction(transaction['observation'], resources, profile, state, expected_revision=transaction['expected_revision'])
            self.context.contracts.require(expected is not None, 'Duplicate lifecycle packet was persisted')
            self.context.contracts.require(transaction == expected, 'Transaction chain, content, sequence or event mismatch')
            self.apply_transaction(transaction, state)
        return state

    def project(self, transactions, profile, *, as_of):
        self.context.contracts.timestamp(as_of)
        self.replay(transactions, profile)
        visible = [tx for tx in transactions if self.context.contracts.timestamp(tx['recorded_at']) <= self.context.contracts.timestamp(as_of)]
        state = self.replay(visible, profile)
        findings = []
        for fid, events in sorted(state['events'].items()):
            observations = [r for r in state['observations'].values() if r['finding']['finding_id'] == fid]
            failures = [r for r in observations if r['body']['result'] == 'fail']
            latest = max(observations, key=lambda r: (r['body']['observed_at'], r['record_id']))
            conflicts = [tx for tx in state['conflicts'] if tx['observation']['finding']['finding_id'] == fid]
            first_fail = min(failures, key=lambda r: (r['body']['observed_at'], r['record_id']))
            findings.append({'finding_id': fid, 'identity': latest['finding'], 'state': 'needs_clarification' if conflicts else 'open', 'revision': self.current_revision(state, fid), 'occurrences': len(failures), 'first_failure_ref': self.context.contracts.record_ref(first_fail), 'latest_observation_ref': self.context.contracts.record_ref(latest), 'last_event_ref': self.context.contracts.record_ref(events[-1]), 'evidence_status': latest['body']['result'], 'observation_refs': sorted((self.context.contracts.record_ref(r) for r in observations), key=lambda r: r['id']), 'conflict_refs': [self.transaction_ref(t) for t in conflicts], 'closure_supported': False})
        index = {'schema_version': '0.1.0', 'index_type': 'governance-lifecycle-synthetic', 'environment': 'synthetic', 'official_state': False, 'enforcement': 'report_only', 'as_of': as_of, 'profile_ref': self.context.contracts.versioned_ref(profile, 'profile_id'), 'ledger_head_ref': self.transaction_ref(visible[-1]) if visible else None, 'counts': {'transactions': len(visible), 'observations': len(state['observations']), 'events': sum((len(es) for es in state['events'].values())), 'conflicts': len(state['conflicts']), 'findings': len(findings)}, 'findings': findings, 'conflict_refs': [self.transaction_ref(tx) for tx in state['conflicts']]}
        if state['actions']:
            add_action_projection = self.context.decisions.add_action_projection
            add_action_projection(index, state, as_of)
        if state['closures']:
            add_closure_projection = self.context.closure.add_closure_projection
            add_closure_projection(index, state)
        if state['exceptions']:
            add_exception_projection = self.context.exceptions.add_exception_projection
            add_exception_projection(index, state, as_of)
        self.context.contracts.schema_validator('exception-index' if state['exceptions'] else 'closure-index' if state['closures'] else 'action-index' if state['actions'] else 'index').validate(index)
        return index
