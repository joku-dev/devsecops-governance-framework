"""Original lifecycle consistency over an explicit retained data context.

Technical reference: V1 6b557f. Original records remain declared historical
facts; these checks never grant this node live approval, identity or consent.
"""
from copy import deepcopy
import base64

class LifecycleDecisions:

    def __init__(self, root, context, *, validator_class, path_factory):
        self.root = root
        self.context = context
        self.validator_class = validator_class
        self.path_factory = path_factory

    def progress_statement(self, record):
        target = deepcopy(record)
        target['body'].pop('progress_evidence_ref', None)
        return {'environment': 'synthetic', 'remediation_record_digest': self.context.contracts.canonical_digest(target)}

    def latest_approval(self, state, finding_id):
        approvals = [r for r in state['actions'].values() if r['record_type'] == 'decision' and r['finding']['finding_id'] == finding_id and (r['approval']['disposition'] == 'approve')]
        return approvals[-1] if approvals else None

    def validate_decision(self, record, resources, state):
        body = record['body']
        plan = body['remediation_plan']
        observation = self.context.contracts.resolve_record(body['observation_ref'], state['observations'], 'observation')
        self.context.contracts.require(observation['finding'] == record['finding'] and observation['profile_ref'] == record['profile_ref'], 'Decision observation scope/profile mismatch')
        self.context.contracts.require(observation['body']['result'] == 'fail', 'Decision must reference an accepted failure')
        self.context.contracts.require(body['action'] == plan['action'], 'Decision action differs from the bound plan')
        if record['approval']['disposition'] == 'approve':
            self.context.contracts.require(self.context.contracts.timestamp(plan['target_at']) >= self.context.contracts.timestamp(record['approval']['issued_at']), 'Plan deadline predates consent')
        self.context.contracts.fixture_resource(plan['work_ref'], resources)
        fid = record['finding']['finding_id']
        latest = self.latest_approval(state, fid)
        predecessor = body.get('supersedes_ref')
        disposition = record['approval']['disposition']
        if disposition == 'reject':
            self.context.contracts.require(predecessor is None, 'A rejected proposal cannot supersede an approval')
            return
        if predecessor is not None:
            previous = self.context.contracts.resolve_record(predecessor, state['actions'], 'decision')
            self.context.contracts.require(latest is not None and predecessor == self.context.contracts.record_ref(latest), 'Supersession must name the latest approved decision')
            self.context.contracts.require(previous['finding'] == record['finding'] and previous['profile_ref'] == record['profile_ref'], 'Supersession scope/profile mismatch')
        else:
            self.context.contracts.require(latest is None, 'Replacement approval must reference its predecessor')
        if disposition == 'revoke':
            self.context.contracts.require(latest is not None and state['decision_status'][latest['record_id']] == 'approved', 'Only the currently active approval can be withdrawn')
            self.context.contracts.require(all((body[k] == latest['body'][k] for k in ('observation_ref', 'action', 'remediation_plan'))), 'Withdrawal must identify the unchanged approved plan')
        else:
            used = {r['body']['remediation_plan']['remediation_id'] for r in state['actions'].values() if r['record_type'] == 'decision' and r['approval']['disposition'] == 'approve'}
            self.context.contracts.require(plan['remediation_id'] not in used, 'Replacement approval requires a new remediation case')

    def validate_remediation(self, record, resources, state):
        body = record['body']
        decision = self.context.contracts.resolve_record(body['decision_ref'], state['actions'], 'decision')
        self.context.contracts.require(state['decision_status'].get(decision['record_id']) == 'approved', 'Remediation approval is not active')
        self.context.contracts.require(decision['finding'] == record['finding'] and decision['profile_ref'] == record['profile_ref'], 'Remediation decision scope/profile mismatch')
        plan = decision['body']['remediation_plan']
        self.context.contracts.require(all((body[k] == value for k, value in plan.items())), 'Remediation differs from the approved plan')
        self.context.contracts.require(self.context.contracts.timestamp(decision['recorded_at']) <= self.context.contracts.timestamp(record['recorded_at']), 'Remediation predates decision')
        previous = state['remediation_heads'].get(body['remediation_id'])
        if previous is None:
            self.context.contracts.require('supersedes_ref' not in body and body['progress'] == 'planned', 'Initial remediation must be planned without a predecessor')
        else:
            self.context.contracts.require(body.get('supersedes_ref') == self.context.contracts.record_ref(previous), 'Remediation predecessor is not the accepted latest revision')
            self.context.contracts.require(body['decision_ref'] == previous['body']['decision_ref'], 'Remediation updates cannot switch their authorization')
            next_progress = {'planned': 'in_progress', 'in_progress': 'completed'}.get(previous['body']['progress'])
            self.context.contracts.require(body['progress'] == next_progress, 'Invalid remediation progress transition')
        proof = self.context.adapter.strict_json(self.context.contracts.fixture_resource(body['progress_evidence_ref'], resources))
        self.context.contracts.require(proof == self.progress_statement(record), 'Synthetic progress proof mismatch')

    def action_event(self, record, state):
        fid = record['finding']['finding_id']
        previous = state['events'][fid][-1]
        event_type = 'decision_recorded' if record['record_type'] == 'decision' else 'remediation_recorded'
        effective_at = record['approval']['issued_at'] if record['record_type'] == 'decision' else record['recorded_at']
        body = {'event_type': event_type, 'revision': previous['body']['revision'] + 1, 'expected_revision': previous['body']['revision'], 'previous_event_ref': self.context.contracts.record_ref(previous), 'effective_at': effective_at, 'policy_version': previous['body']['policy_version'], 'source_refs': [self.context.contracts.record_ref(record)]}
        event = {'schema_version': '0.1.0', 'record_type': 'event', 'environment': 'synthetic', 'profile_ref': record['profile_ref'], 'finding': record['finding'], 'recorded_at': record['recorded_at'], 'body': body}
        event['record_id'] = 'event:' + self.context.contracts.canonical_digest(event)
        records = {**state['observations'], **state['actions'], record['record_id']: record, **{e['record_id']: e for es in state['events'].values() for e in es}}
        self.context.contracts.check_event_references(event, records)
        return event

    def prepare_action_transaction(self, record, resources, profile, state, *, expected_revision):
        self.context.contracts.require(record.get('record_type') in ('decision', 'remediation') and record.get('schema_version') == '0.2.0', 'CLG-03 accepts version 0.2.0 decisions/remediations only')
        self.context.contracts.validate_test_record(record, profile, resources)
        body = record['body']
        if record['record_type'] == 'decision':
            required_uris = {record['approval']['proof_ref']['uri'], body['remediation_plan']['work_ref']['uri']}
        else:
            required_uris = {body['work_ref']['uri'], body['progress_evidence_ref']['uri']}
        self.context.contracts.require(set(resources) == required_uris and len(resources) == 2, 'Exactly the two bound action resources are required')
        if record['record_type'] == 'decision':
            self.context.contracts.fixture_resource(body['remediation_plan']['work_ref'], resources)
        else:
            self.context.contracts.fixture_resource(body['progress_evidence_ref'], resources)
        previous = state['actions'].get(record['record_id'])
        if previous:
            self.context.contracts.require(previous == record, 'Action ID already binds different immutable content')
            return None
        fid = record['finding']['finding_id']
        self.context.contracts.require(fid not in state['active_closures'], 'Finding is closed; a new failure is required before further actions')
        revision = self.context.kernel.current_revision(state, fid)
        self.context.contracts.require(revision > 0, 'An accepted open finding is required')
        self.context.contracts.require(type(expected_revision) is int and expected_revision == body['expected_revision'] == revision, 'Stale expected finding revision')
        self.context.contracts.require(self.context.contracts.timestamp(record['recorded_at']) >= self.context.contracts.timestamp(state['transactions'][-1]['recorded_at']), 'Action recording time predates accepted ledger head')
        if record['record_type'] == 'decision':
            self.context.contracts.require(self.context.contracts.timestamp(record['approval']['issued_at']) >= self.context.contracts.timestamp(state['events'][fid][-1]['recorded_at']), 'Consent predates the accepted finding revision')
            self.validate_decision(record, resources, state)
        else:
            self.validate_remediation(record, resources, state)
        transaction = {'schema_version': '0.2.0', 'environment': 'synthetic', 'sequence': len(state['transactions']) + 1, 'previous_ref': self.context.kernel.transaction_ref(state['transactions'][-1]), 'profile_ref': self.context.contracts.versioned_ref(profile, 'profile_id'), 'recorded_at': record['recorded_at'], 'expected_revision': expected_revision, 'outcome': 'accepted', 'reason': 'decision_recorded' if record['record_type'] == 'decision' else 'remediation_recorded', 'record': deepcopy(record), 'resources': {uri: base64.b64encode(data).decode('ascii') for uri, data in sorted(resources.items())}, 'event': self.action_event(record, state)}
        transaction['transaction_id'] = 'transaction:' + self.context.contracts.canonical_digest(transaction)
        self.context.contracts.schema_validator('action-transaction').validate(transaction)
        return transaction

    def apply_action(self, transaction, state):
        record = transaction['record']
        state['actions'][record['record_id']] = record
        if record['record_type'] == 'decision':
            disposition = record['approval']['disposition']
            predecessor = record['body'].get('supersedes_ref')
            if disposition == 'revoke':
                state['decision_status'][predecessor['id']] = 'revoked'
            elif disposition == 'approve' and predecessor and (state['decision_status'][predecessor['id']] == 'approved'):
                state['decision_status'][predecessor['id']] = 'superseded'
            state['decision_status'][record['record_id']] = {'approve': 'approved', 'reject': 'rejected', 'revoke': 'withdrawal_recorded'}[disposition]
        else:
            state['remediation_heads'][record['body']['remediation_id']] = record

    def add_action_projection(self, index, state, as_of):
        index['schema_version'] = '0.2.0'
        index['counts']['decisions'] = sum((r['record_type'] == 'decision' for r in state['actions'].values()))
        index['counts']['remediations'] = sum((r['record_type'] == 'remediation' for r in state['actions'].values()))
        for finding in index['findings']:
            fid = finding['finding_id']
            decisions = [r for r in state['actions'].values() if r['record_type'] == 'decision' and r['finding']['finding_id'] == fid]
            active = [r for r in decisions if state['decision_status'][r['record_id']] == 'approved']
            finding['active_decision_ref'] = self.context.contracts.record_ref(active[0]) if active else None
            finding['decision_records'] = [{'record_ref': self.context.contracts.record_ref(r), 'disposition': r['approval']['disposition'], 'effective_status': state['decision_status'][r['record_id']]} for r in decisions]
            cases = []
            for case_id, record in sorted(state['remediation_heads'].items()):
                if record['finding']['finding_id'] != fid:
                    continue
                body = record['body']
                cases.append({'remediation_id': case_id, 'latest_record_ref': self.context.contracts.record_ref(record), 'decision_ref': body['decision_ref'], 'owner_id': body['owner_id'], 'target_at': body['target_at'], 'progress': body['progress'], 'authorization_status': state['decision_status'][body['decision_ref']['id']], 'overdue': body['progress'] != 'completed' and self.context.contracts.timestamp(as_of) > self.context.contracts.timestamp(body['target_at'])})
            finding['remediation_cases'] = cases
