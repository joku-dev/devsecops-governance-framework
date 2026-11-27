"""Complete original consumer lifecycle functions over explicit data/effect ports.

Retained source history is not this node's operating authority.
"""
from __future__ import annotations
from copy import deepcopy
from referencing import Registry, Resource
import base64, hashlib
_OMITTED = object()
_DEFAULT_FETCH = object()
ACTION_LEDGER = 'governance/consumer-lifecycle/actions'

class ConsumerActions:

    def __init__(self, root, context, *, path_factory, profile, process=None, temporary=None, clock=None, validator_class=None, default_fetch=None, architecture=None, argument_parser=None, argv=(), description=None):
        self.root, self.context, self.Path, self.profile = (root, context, path_factory, profile)
        self.process, self.temporary, self.clock = (process, temporary, clock)
        self.validator_class, self.default_fetch, self.architecture = (validator_class, default_fetch, architecture)
        self.argument_parser, self.argv, self.description = (argument_parser, list(argv), description)
        self.positive_id = profile.positive_id
        self.ACTION_LEDGER = ACTION_LEDGER

    def assess_action_comments(self, request, comments, *, captured_at, previous_comments=()):
        self.context.consumer_contracts.schema_validator('pilot-action-request').validate(request)
        result = self.context.provider.assess_bound_comments(request, comments, captured_at=captured_at, previous_comments=previous_comments)
        result['record_type'] = 'lifecycle-pilot-action-consent-result'
        return result

    def prior_statements(self, actions, request):
        records = {}
        for action in actions:
            if action['request'] == request:
                for comment in action['snapshot']['result']['relevant_comments']:
                    records.setdefault(comment['id'], comment)
        return list(records.values())

    def proof_projection(self, snapshot):
        result = snapshot['result']
        return {k: result[k] for k in ('request_digest', 'status', 'last_statement_id', 'issues')} | {'comments': [self.context.provider.comment_identity(c) for c in result['relevant_comments']]}

    def resolve(self, ref, records):
        result = next((r for r in records if self.context.kernel.transaction_ref(r) == ref), None)
        self.context.contracts.require(result is not None, 'Referenced immutable record is missing or differs')
        return result

    def fresh(self, receipt, at, profile):
        self.context.contracts.require(receipt['outcome'] == 'eligible_for_pilot', 'Quarantined evidence cannot authorize an action')
        age = (self.context.contracts.timestamp(at) - self.context.contracts.timestamp(receipt['source']['observed_at'])).total_seconds()
        self.context.contracts.require(0 <= age <= profile['operating_policy']['maximum_age_seconds'], 'Action evidence is stale or future-dated')

    def state_at(self, receipts, actions):
        """Project only already validated actions and receipts, retaining closed/revoked history."""
        state = {'decision': None, 'progress': None, 'closure': None, 'roles_active': True, 'withdrawn': set(), 'reopened': False}
        for action in actions:
            request = action['request']
            body = request['body']
            kind = body['kind']
            if action['outcome'] in ('withdrawn', 'needs_clarification'):
                for old in actions:
                    if old['request'] == request and old['outcome'] == 'eligible_for_pilot':
                        state['withdrawn'].add(old['transaction_id'])
            elif action['outcome'] == 'eligible_for_pilot':
                if kind == 'decision':
                    if state['decision']:
                        state['withdrawn'].add(state['decision']['transaction_id'])
                    state.update(decision=action, progress=None, closure=None)
                elif kind == 'progress':
                    state['progress'] = action
                elif kind == 'closure':
                    state['closure'] = action
                elif kind == 'withdrawal':
                    state['withdrawn'].add(body['target_ref']['id'])
                elif kind == 'role_withdrawal':
                    state['roles_active'] = False
        if state['decision'] and state['decision']['transaction_id'] in state['withdrawn']:
            state.update(decision=None, progress=None, closure=None)
        if state['progress'] and state['progress']['transaction_id'] in state['withdrawn']:
            state.update(progress=None, closure=None)
        if state['closure'] and state['closure']['transaction_id'] in state['withdrawn']:
            state['closure'] = None
        if not state['roles_active']:
            state.update(decision=None, progress=None, closure=None)
        if state['closure']:
            passed = self.resolve(state['closure']['request']['body']['passing_ref'], receipts)
            if any((r['outcome'] == 'eligible_for_pilot' and r['criterion']['status'] == 'fail' and (self.context.contracts.timestamp(r['source']['observed_at']) > self.context.contracts.timestamp(passed['source']['observed_at'])) for r in receipts)):
                state.update(decision=None, progress=None, closure=None, reopened=True)
        return state

    def required_role(self, request, actions):
        kind = request['body']['kind']
        if kind == 'closure':
            return 'closure_approver'
        if kind == 'role_withdrawal':
            return 'role_registry_owner'
        if kind == 'withdrawal':
            target = self.resolve(request['body']['target_ref'], actions)
            self.context.contracts.require(target['request']['body']['kind'] in ('decision', 'closure'), 'Only a decision or closure can be withdrawn')
            return target['request']['required_role']
        return 'remediation_decider'

    def validate_context(self, request, profile, binding, receipts, actions, *, at, allow_historical=False):
        self.context.consumer_contracts.schema_validator('pilot-action-request').validate(request)
        self.context.contracts.require(request['operating_profile_ref'] == self.context.preparation.revision_ref(profile), 'Action operating profile differs')
        self.context.contracts.require(request['role_binding_ref'] == self.context.preparation.revision_ref(binding), 'Action role binding differs')
        role = self.required_role(request, actions)
        self.context.contracts.require(request['required_role'] == role and binding['status'] == 'confirmed' and (binding['assignments'][role] == request['required_subject_id']), 'Action role or appointed subject differs')
        self.context.contracts.require(self.context.contracts.timestamp(binding['recorded_at']) <= self.context.contracts.timestamp(request['created_at']) <= self.context.contracts.timestamp(at), 'Request is outside confirmed role/capture time')
        if allow_historical:
            return
        state = self.state_at(receipts, actions)
        self.context.contracts.require(state['roles_active'], 'Pilot roles have been withdrawn')
        self.context.contracts.require(bool(receipts) and request['expected_receipt_head'] == self.context.kernel.transaction_ref(receipts[-1]), 'Stale evidence head')
        self.context.contracts.require(request['expected_action_head'] == (self.context.kernel.transaction_ref(actions[-1]) if actions else None), 'Stale action head')
        self.context.contracts.require(request['expected_revision'] == len(receipts) + len(actions), 'Stale finding revision')
        head_time = max([r['recorded_at'] for r in receipts] + [a['recorded_at'] for a in actions])
        self.context.contracts.require(self.context.contracts.timestamp(request['created_at']) >= self.context.contracts.timestamp(head_time), 'Request predates bound state revision')
        body = request['body']
        kind = body['kind']
        if kind in ('withdrawal', 'role_withdrawal'):
            return
        self.context.contracts.require(not any((r['outcome'] == 'quarantined' for r in receipts)), 'Unresolved evidence conflict prevents actions')
        failures = [r for r in receipts if r['criterion']['status'] == 'fail']
        self.context.contracts.require(bool(failures), 'A real eligible failure is required; PASS cannot create a finding')
        latest = max(receipts, key=lambda r: (r['source']['observed_at'], r['transaction_id']))
        if kind == 'decision':
            self.context.contracts.require(state['closure'] is None, 'Finding is closed')
            failed = self.resolve(body['failure_ref'], receipts)
            self.context.contracts.require(failed == max(failures, key=lambda r: r['source']['observed_at']), 'Decision must bind latest failure')
            self.fresh(failed, at, profile)
            self.context.contracts.require(body['supersedes_ref'] == (self.context.kernel.transaction_ref(state['decision']) if state['decision'] else None), 'Decision predecessor differs')
            self.context.contracts.require(self.context.contracts.timestamp(body['plan']['target_at']) >= self.context.contracts.timestamp(at), 'Decision deadline predates consent capture')
            self.context.contracts.require(body['plan']['owner_id'] in {s['subject_id'] for s in binding['subjects']}, 'Remediation owner is not appointed in this pilot')
        elif kind in ('progress', 'closure'):
            self.context.contracts.require(state['closure'] is None and state['decision'] is not None, 'No active decision for an open finding')
            self.context.contracts.require(body['decision_ref'] == self.context.kernel.transaction_ref(state['decision']), 'Action references an inactive decision')
            if kind == 'progress':
                expected = 'in_progress' if state['progress'] is None else 'completed' if state['progress']['request']['body']['progress'] == 'in_progress' else None
                self.context.contracts.require(body['progress'] == expected, 'Invalid remediation progress transition')
            else:
                self.context.contracts.require(state['progress'] is not None and state['progress']['request']['body']['progress'] == 'completed', 'Remediation is not completed')
                self.context.contracts.require(body['progress_ref'] == self.context.kernel.transaction_ref(state['progress']), 'Closure progress revision differs')
                passed = self.resolve(body['passing_ref'], receipts)
                self.context.contracts.require(passed == latest and passed['criterion']['status'] == 'pass', 'Closure requires the latest eligible PASS')
                self.fresh(passed, at, profile)
                self.context.contracts.require(all((self.context.contracts.timestamp(r['source']['observed_at']) < self.context.contracts.timestamp(passed['source']['observed_at']) for r in failures)), 'PASS must follow every failure')
                self.context.contracts.require(self.context.contracts.timestamp(passed['source']['observed_at']) >= self.context.contracts.timestamp(state['progress']['recorded_at']), 'PASS predates completed remediation')
                self.context.contracts.require(all((self.context.contracts.timestamp(r['source']['observed_at']) <= self.context.contracts.timestamp(state['progress']['recorded_at']) for r in failures)), 'Failure postdates remediation')

    def prepare_action(self, snapshot, profile, binding, receipts, actions, *, recorded_at, expected_sequence):
        request = snapshot['request']
        self.context.contracts.require(snapshot['capture_method'] in (self.profile.capture_method, 'injected_test_transport'), 'Unknown capture transport')
        result = self.context.provider.replay_bound_snapshot(snapshot, assessor=self.assess_action_comments)
        same = [a for a in actions if a['request'] == request]
        if same and self.proof_projection(snapshot) == self.proof_projection(same[-1]['snapshot']):
            return None
        self.context.contracts.require(type(expected_sequence) is int and expected_sequence == len(actions), 'Stale action sequence')
        self.context.contracts.require(snapshot['previous_comments'] == self.prior_statements(actions, request), 'Prior personal statements omitted or changed')
        status = result['status']
        self.context.contracts.require(status in ('confirmed', 'rejected', 'revoked', 'needs_clarification'), 'Personal action statement is missing')
        historical = bool(same) and status in ('rejected', 'revoked', 'needs_clarification')
        self.context.contracts.require(status != 'needs_clarification' or historical, 'Malformed initial consent cannot create an action')
        self.context.contracts.require(status != 'revoked' or historical, 'Revocation must reference a retained consent')
        self.validate_context(request, profile, binding, receipts, actions, at=recorded_at, allow_historical=historical)
        if not historical:
            self.context.contracts.require(self.context.contracts.timestamp(result['relevant_comments'][-1]['created_at']) >= self.context.contracts.timestamp(request['created_at']), 'Consent predates request')
        self.context.contracts.require(self.context.contracts.timestamp(result['captured_at']) <= self.context.contracts.timestamp(recorded_at), 'Action predates provider capture')
        self.context.contracts.require(all((self.context.contracts.timestamp(recorded_at) >= self.context.contracts.timestamp(a['recorded_at']) for a in actions)), 'Action clock regressed')
        self.context.contracts.require(all((self.context.contracts.timestamp(recorded_at) >= self.context.contracts.timestamp(r['recorded_at']) for r in receipts)), 'Action predates receipt head')
        outcome = {'confirmed': 'eligible_for_pilot', 'rejected': 'withdrawn' if same else 'rejected', 'revoked': 'withdrawn', 'needs_clarification': 'needs_clarification'}[status]
        transaction = {'schema_version': '0.1.0', 'record_type': 'lifecycle-pilot-action-receipt', 'environment': 'live_pilot_validation', 'official_state': False, 'live_activation_approved': False, 'sequence': len(actions) + 1, 'previous_ref': self.context.kernel.transaction_ref(actions[-1]) if actions else None, 'recorded_at': recorded_at, 'request': deepcopy(request), 'snapshot': deepcopy(snapshot), 'outcome': outcome, 'receipt_head_at_recording': self.context.kernel.transaction_ref(receipts[-1])}
        transaction['transaction_id'] = 'transaction:' + self.context.contracts.canonical_digest(transaction)
        self.context.consumer_contracts.schema_validator('pilot-action-receipt').validate(transaction)
        return transaction

    def replay_actions(self, receipts, actions, profile, binding):
        receipts = self.context.consumer_admission.replay_receipts(receipts, profile)
        history = []
        last_receipt_count = 0
        for action in actions:
            self.context.consumer_contracts.schema_validator('pilot-action-receipt').validate(action)
            receipt = self.resolve(action['receipt_head_at_recording'], receipts)
            count = receipt['sequence']
            self.context.contracts.require(count >= last_receipt_count, 'Action receipt history regressed')
            self.context.contracts.require(all((self.context.contracts.timestamp(r['recorded_at']) >= self.context.contracts.timestamp(action['recorded_at']) for r in receipts[count:])), 'Later receipt predates action history')
            expected = self.prepare_action(action['snapshot'], profile, binding, receipts[:count], history, recorded_at=action['recorded_at'], expected_sequence=len(history))
            self.context.contracts.require(expected is not None and expected == action, 'Action receipt chain or projection differs')
            history.append(action)
            last_receipt_count = count
        return history

    def load_context(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.Path(repo)
        profile = self.context.consumer_contracts.load_operating(root)
        binding = self.context.consumer_contracts.validate_preparation(root)['binding']
        receipts = self.context.store.load_transactions(root / self.context.consumer_admission.VALIDATION_LEDGER)
        actions = self.replay_actions(receipts, self.context.store.load_transactions(root / self.ACTION_LEDGER), profile, binding)
        return (profile, binding, receipts, actions)

    def collect_action(self, request, repo=_OMITTED, *, fetch=None, captured_at=None):
        if repo is _OMITTED:
            repo = self.root
        profile, binding, receipts, actions = self.load_context(repo)
        self.context.consumer_contracts.schema_validator('pilot-action-request').validate(request)
        options = {'fetch': fetch} if fetch is not None else {}
        snapshot = self.context.provider.collect_bound(request, assessor=self.assess_action_comments, previous_comments=self.prior_statements(actions, request), captured_at=captured_at, **options)
        self.prepare_action(snapshot, profile, binding, receipts, actions, recorded_at=snapshot['result']['captured_at'], expected_sequence=len(actions))
        return snapshot

    def append_action_snapshot(self, repo, snapshot, *, recorded_at, expected_sequence):
        root = self.Path(repo)
        with self.context.store.writer_lock(root / self.context.consumer_admission.VALIDATION_LEDGER), self.context.store.writer_lock(root / self.ACTION_LEDGER):
            profile, binding, receipts, actions = self.load_context(root)
            action = self.prepare_action(snapshot, profile, binding, receipts, actions, recorded_at=recorded_at, expected_sequence=expected_sequence)
            if action is None:
                return {'outcome': 'duplicate', 'transaction_ref': None}
            self.context.store.publish_transaction(root / self.ACTION_LEDGER / 'transactions', action)
            return {'outcome': action['outcome'], 'transaction_ref': self.context.kernel.transaction_ref(action)}

    def verify_new_actions(self, repo, base_ref, *, fetch=None, checked_at=None):
        root = self.Path(repo)
        profile, binding, receipts, actions = self.load_context(root)
        old = set(self.process.check_output(['git', 'ls-tree', '-r', '--name-only', base_ref, '--', self.ACTION_LEDGER], cwd=root, text=True).splitlines())
        options = {'fetch': fetch} if fetch is not None else {}
        checked = 0
        for action in actions:
            name = f"{self.ACTION_LEDGER}/transactions/{action['sequence']:08d}-{action['transaction_id'].split(':')[1]}.json"
            if name in old:
                continue
            request = action['request']
            self.context.contracts.require(action['snapshot']['capture_method'] == self.profile.capture_method, self.profile.literal('legacy_23e9b3bf4fa896bc'))
            fresh_snapshot = self.context.provider.collect_bound(request, assessor=self.assess_action_comments, previous_comments=action['snapshot']['previous_comments'], captured_at=checked_at, **options)
            self.context.contracts.require(self.proof_projection(fresh_snapshot) == self.proof_projection(action['snapshot']), 'New action differs from independently retrieved personal statement')
            now = fresh_snapshot['result']['captured_at']
            self.context.contracts.require(self.context.contracts.timestamp(action['recorded_at']) <= self.context.contracts.timestamp(now), 'Action claims future recording time')
            if action['outcome'] == 'eligible_for_pilot' and request['body']['kind'] not in ('withdrawal', 'role_withdrawal'):
                self.context.contracts.require(action['receipt_head_at_recording'] == self.context.kernel.transaction_ref(receipts[-1]), 'New action is stale against merged evidence')
                prior = actions[:action['sequence'] - 1]
                self.validate_context(request, profile, binding, receipts, prior, at=now)
                state = self.state_at(receipts, prior)
                for dependency in (state['decision'], state['progress']):
                    if dependency is None:
                        continue
                    live = self.context.provider.collect_bound(dependency['request'], assessor=self.assess_action_comments, previous_comments=self.prior_statements(prior, dependency['request']), captured_at=checked_at, **options)
                    self.context.contracts.require(self.proof_projection(live) == self.proof_projection(dependency['snapshot']), 'Action prerequisite was changed or withdrawn at the provider')
            checked += 1
        return checked

    def project_actions(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        profile, binding, receipts, actions = self.load_context(repo)
        state = self.state_at(receipts, actions)
        failures = [r for r in receipts if r['outcome'] == 'eligible_for_pilot' and r['criterion']['status'] == 'fail']
        conflicted = any((r['outcome'] == 'quarantined' for r in receipts))
        status = 'not_observed' if not receipts else 'needs_clarification' if conflicted else 'no_finding' if not failures else 'closed' if state['closure'] else 'open'
        return {'schema_version': '0.1.0', 'index_type': 'consumer-lifecycle-action-validation', 'official_state': False, 'live_activation_approved': False, 'enforcement': 'report_only', 'profile_ref': self.context.preparation.revision_ref(profile), 'role_binding_ref': self.context.preparation.revision_ref(binding), 'as_of': max([r['recorded_at'] for r in receipts] + [a['recorded_at'] for a in actions], default=None), 'revision': len(receipts) + len(actions), 'receipt_head_ref': self.context.kernel.transaction_ref(receipts[-1]) if receipts else None, 'action_head_ref': self.context.kernel.transaction_ref(actions[-1]) if actions else None, 'finding_state': status, 'roles_active': state['roles_active'], 'active_decision_ref': self.context.kernel.transaction_ref(state['decision']) if state['decision'] else None, 'active_closure_ref': self.context.kernel.transaction_ref(state['closure']) if state['closure'] and (not conflicted) else None, 'counts': {'receipts': len(receipts), 'actions': len(actions), 'failures': len(failures), 'quarantined': sum((r['outcome'] == 'quarantined' for r in receipts))}, 'action_refs': [self.context.kernel.transaction_ref(a) for a in actions], 'limitation': 'Action eligibility validation only. Consumer operating acceptance and the dedicated operational publisher remain required.'}
