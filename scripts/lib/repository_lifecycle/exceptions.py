"""Original lifecycle consistency over an explicit retained data context.

Technical reference: V1 6b557f. Original records remain declared historical
facts; these checks never grant this node live approval, identity or consent.
"""
import base64
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import re
import yaml

class LifecycleExceptions:

    def __init__(self, root, context, *, validator_class, path_factory):
        self.root = root
        self.context = context
        self.validator_class = validator_class
        self.path_factory = path_factory
        self.input_exception_profile = self.root / 'model/governance/lifecycle/synthetic-exception-profile.json'

    def exception_profile(self):
        profile = self.context.adapter.strict_json(self.input_exception_profile.read_bytes())
        self.context.contracts.schema_validator('exception-profile').validate(profile)
        self.context.contracts.require(hashlib.sha256(profile['authority_model'].encode()).hexdigest() == profile['source_digest'], 'Exception authority snapshot digest mismatch')
        authorities = yaml.safe_load(profile['authority_model'])['authorities']
        self.context.contracts.require(set(authorities) == set(profile['bindings']), 'Exception authority snapshot risk classes differ')
        for risk, binding in profile['bindings'].items():
            self.context.contracts.require(binding['authority'] == authorities[risk]['approval_authority'], 'Exception authority snapshot binding mismatch')
            self.context.contracts.require(len(binding['subjects']) == (2 if risk == 'critical' else 1), 'Joint critical authority requires two distinct test subjects')
        return profile

    def read_waiver(self, record, resources):
        waiver = self.context.adapter.strict_json(self.context.contracts.fixture_resource(record['body']['waiver_ref'], resources))
        schema = self.context.adapter.strict_json((self.root / 'schemas/waiver.schema.json').read_bytes())
        self.validator_class(schema, format_checker=self.context.contracts.format_checker).validate(waiver)
        self.context.contracts.require(waiver.get('environment') == 'synthetic', 'Waiver must be explicitly synthetic')
        self.context.contracts.require(waiver['scope'] == record['finding']['key']['resource'] and waiver['object_id'] == record['finding']['finding_id'], 'Waiver scope/object mismatch')
        self.context.contracts.require(waiver['affected_requirements'] == ['GRS-002'], 'Unsupported waiver requirement mapping')
        self.context.contracts.require(re.fullmatch('synthetic-waiver:[a-zA-Z0-9._-]+', waiver['id']) is not None and bool(waiver['compensating_controls']) and all((str(c).strip() for c in waiver['compensating_controls'])), 'Synthetic waiver identity and compensating controls required')
        return waiver

    def transaction_resources(self, transaction):
        return {uri: base64.b64decode(data, validate=True) for uri, data in transaction['resources'].items()}

    def prepare_exception_transaction(self, record, resources, profile, state, *, expected_revision):
        self.context.contracts.require(record.get('record_type') == 'exception' and record.get('schema_version') == '0.1.0', 'Unsupported exception record')
        self.context.contracts.validate_test_record(record, profile, resources)
        approval, body = (record['approval'], record['body'])
        self.context.contracts.require(set(resources) == {approval['proof_ref']['uri'], body['waiver_ref']['uri']} and len(resources) == 2, 'Exactly waiver and consent fixture resources are required')
        bound_profile = self.exception_profile()
        waiver = self.read_waiver(record, resources)
        binding = bound_profile['bindings'][waiver['risk_classification']]
        self.context.contracts.require(approval['exception_profile_ref'] == self.context.contracts.versioned_ref(bound_profile, 'profile_id'), 'Exception profile binding mismatch')
        self.context.contracts.require(approval['authority'] == waiver['approval_authority'] == binding['authority'], 'Wrong waiver approval authority')
        self.context.contracts.require(approval['subjects'] == sorted(binding['subjects']), 'Waiver consent does not include exactly the assigned subjects')
        self.context.contracts.require(waiver['approved_by'] == ','.join(approval['subjects']), 'Waiver approved_by does not bind subjects')
        self.context.contracts.require(approval['target_digest'] == self.context.contracts.approval_target(record), 'Exception content binding mismatch')
        self.context.contracts.require(approval['finding_id'] == record['finding']['finding_id'] and approval['expected_revision'] == body['expected_revision'], 'Exception approval scope/revision mismatch')
        self.context.contracts.require(self.context.contracts.timestamp(approval['issued_at']) <= self.context.contracts.timestamp(record['recorded_at']), 'Exception consent after recording')
        proof = self.context.adapter.strict_json(self.context.contracts.fixture_resource(approval['proof_ref'], resources))
        self.context.contracts.require(proof == {'environment': 'synthetic', 'approval': {k: v for k, v in approval.items() if k != 'proof_ref'}}, 'Synthetic exception consent proof mismatch')
        previous = state['exceptions'].get(record['record_id'])
        if previous is not None:
            self.context.contracts.require(previous == record, 'Exception ID already binds different immutable content')
            return None
        fid = record['finding']['finding_id']
        revision = self.context.kernel.current_revision(state, fid)
        self.context.contracts.require(type(expected_revision) is int and expected_revision == body['expected_revision'] == revision and (revision > 0), 'Stale expected finding revision')
        self.context.contracts.require(self.context.contracts.timestamp(record['recorded_at']) >= self.context.contracts.timestamp(state['transactions'][-1]['recorded_at']), 'Exception predates ledger head')
        self.context.contracts.require(self.context.contracts.timestamp(approval['issued_at']) >= self.context.contracts.timestamp(state['events'][fid][-1]['recorded_at']), 'Exception consent predates finding head')
        covered = [self.context.contracts.resolve_record(ref, state['observations'], 'observation') for ref in body['covered_observation_refs']]
        self.context.contracts.require(all((r['finding'] == record['finding'] and r['profile_ref'] == record['profile_ref'] and (r['body']['result'] == 'fail') for r in covered)), 'Coverage must bind accepted failures of this finding/profile')
        self.context.contracts.require(body['covered_observation_refs'] == sorted(body['covered_observation_refs'], key=lambda ref: ref['id']), 'Coverage references must be sorted')
        expires = (date.fromisoformat(waiver['expiry']) + timedelta(days=1)).isoformat() + 'T00:00:00Z'
        self.context.contracts.require(body['expires_at'] == expires and self.context.contracts.timestamp(body['valid_from']) < self.context.contracts.timestamp(expires), 'Waiver expiry mapping/window mismatch')
        disposition = approval['disposition']
        predecessor = body.get('supersedes_ref')
        if disposition == 'revoke':
            self.context.contracts.require(predecessor is not None, 'Withdrawal requires original grant reference')
            grant = self.context.contracts.resolve_record(predecessor, state['exceptions'], 'exception')
            self.context.contracts.require(grant['approval']['disposition'] == 'approve' and grant['record_id'] not in state['revoked_exceptions'], 'Only a previously approved, not yet withdrawn grant can be revoked')
            self.context.contracts.require(grant['finding'] == record['finding'] and grant['profile_ref'] == record['profile_ref'] and all((body[k] == grant['body'][k] for k in ('waiver_ref', 'covered_observation_refs', 'valid_from', 'expires_at'))), 'Withdrawal must bind unchanged grant scope/content')
        else:
            self.context.contracts.require(predecessor is None, 'New approvals/rejections cannot rewrite a grant; renewal requires a new waiver')
            self.context.contracts.require(fid not in state['active_closures'], 'Finding is closed; no new exception treatment')
            self.context.contracts.require(waiver['approved_on'] == approval['issued_at'][:10], 'Waiver approval date differs from consent')
            self.context.contracts.require(waiver['status'] == ('approved' if disposition == 'approve' else 'rejected') and waiver['expired'] is False, 'Waiver status differs from consent disposition')
            self.context.contracts.require(self.context.contracts.timestamp(body['valid_from']) >= self.context.contracts.timestamp(record['recorded_at']), 'Exception cannot grant retroactive coverage')
            if disposition == 'approve':
                self.context.contracts.require(self.context.contracts.timestamp(expires) > self.context.contracts.timestamp(record['recorded_at']), 'Exception already expired at acceptance')
                for existing in state['exceptions'].values():
                    if existing['approval']['disposition'] == 'approve':
                        self.context.contracts.require(state['exception_waivers'][existing['record_id']]['id'] != waiver['id'], 'Renewal requires a fresh waiver ID')
                outstanding = self.outstanding_failures(state, fid)
                self.context.contracts.require(all((r['record_id'] in outstanding for r in covered)), 'Cannot grant coverage for a previous closed episode')
        previous_event = state['events'][fid][-1]
        event = {'schema_version': '0.2.0', 'record_type': 'event', 'environment': 'synthetic', 'profile_ref': deepcopy(record['profile_ref']), 'finding': deepcopy(record['finding']), 'recorded_at': record['recorded_at'], 'body': {'event_type': 'exception_recorded', 'revision': revision + 1, 'expected_revision': revision, 'previous_event_ref': self.context.contracts.record_ref(previous_event), 'effective_at': approval['issued_at'], 'policy_version': previous_event['body']['policy_version'], 'source_refs': [self.context.contracts.record_ref(record)]}}
        event['record_id'] = 'event:' + self.context.contracts.canonical_digest(event)
        self.context.contracts.check_event_references(event, {record['record_id']: record, previous_event['record_id']: previous_event})
        tx = {'schema_version': '0.4.0', 'environment': 'synthetic', 'sequence': len(state['transactions']) + 1, 'previous_ref': self.context.kernel.transaction_ref(state['transactions'][-1]), 'profile_ref': self.context.contracts.versioned_ref(profile, 'profile_id'), 'recorded_at': record['recorded_at'], 'expected_revision': revision, 'outcome': 'accepted', 'reason': 'exception_recorded', 'record': deepcopy(record), 'event': event, 'resources': {uri: base64.b64encode(data).decode('ascii') for uri, data in sorted(resources.items())}}
        tx['transaction_id'] = 'transaction:' + self.context.contracts.canonical_digest(tx)
        self.context.contracts.schema_validator('exception-transaction').validate(tx)
        return tx

    def apply_exception(self, transaction, state):
        record = transaction['record']
        state['exceptions'][record['record_id']] = record
        state['exception_waivers'][record['record_id']] = self.read_waiver(record, self.transaction_resources(transaction))
        if record['approval']['disposition'] == 'revoke':
            state['revoked_exceptions'].add(record['body']['supersedes_ref']['id'])

    def outstanding_failures(self, state, fid):
        closures = [c for c in state['closures'].values() if c['finding']['finding_id'] == fid]
        cutoff = state['observations'][closures[-1]['body']['passing_observation_ref']['id']]['body']['observed_at'] if closures else None
        return {r['record_id']: r for r in state['observations'].values() if r['finding']['finding_id'] == fid and r['body']['result'] == 'fail' and (cutoff is None or self.context.contracts.timestamp(r['body']['observed_at']) > self.context.contracts.timestamp(cutoff))}

    def effective_exception_status(self, record, state, as_of):
        disposition = record['approval']['disposition']
        if disposition != 'approve':
            return 'rejected' if disposition == 'reject' else 'withdrawal_recorded'
        if record['record_id'] in state['revoked_exceptions']:
            return 'revoked'
        if self.context.contracts.timestamp(as_of) >= self.context.contracts.timestamp(record['body']['expires_at']):
            return 'expired'
        return 'scheduled' if self.context.contracts.timestamp(as_of) < self.context.contracts.timestamp(record['body']['valid_from']) else 'active'

    def add_exception_projection(self, index, state, as_of):
        add_action_projection = self.context.decisions.add_action_projection
        add_closure_projection = self.context.closure.add_closure_projection
        add_action_projection(index, state, as_of)
        add_closure_projection(index, state)
        index['schema_version'] = '0.4.0'
        index['counts']['exceptions'] = len(state['exceptions'])
        for finding in index['findings']:
            fid = finding['finding_id']
            outstanding = self.outstanding_failures(state, fid)
            records, covered, ended = ([], set(), set())
            for record in state['exceptions'].values():
                if record['finding']['finding_id'] != fid:
                    continue
                body = record['body']
                status = self.effective_exception_status(record, state, as_of)
                ids = {ref['id'] for ref in body['covered_observation_refs']}
                if status == 'active':
                    covered.update(ids & outstanding.keys())
                if status in ('expired', 'revoked'):
                    ended.update(ids & outstanding.keys())
                waiver = state['exception_waivers'][record['record_id']]
                records.append({'record_ref': self.context.contracts.record_ref(record), 'disposition': record['approval']['disposition'], 'status': status, 'valid_from': body['valid_from'], 'expires_at': body['expires_at'], 'risk_classification': waiver['risk_classification'], 'waiver_id': waiver['id'], 'covered_observation_refs': deepcopy(body['covered_observation_refs'])})
            uncovered = outstanding.keys() - covered
            finding['exception_treatment'] = {'coverage': 'not_applicable' if not outstanding else 'full' if not uncovered else 'partial' if covered else 'none', 'covered_observation_refs': [self.context.contracts.record_ref(outstanding[i]) for i in sorted(covered)], 'uncovered_observation_refs': [self.context.contracts.record_ref(outstanding[i]) for i in sorted(uncovered)], 'renewed_decision_required': bool(ended - covered), 'exception_records': records}
