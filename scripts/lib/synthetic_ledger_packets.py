"""Whole original synthetic packets over explicit data and lifecycle contexts.

Fabrication remains labelled synthetic, with no real approval or trust authority.
"""
from copy import deepcopy
from datetime import date,timedelta
import hashlib,json

class SyntheticObservations:

    def __init__(self, root, context):
        self.root = root
        self.context = context

    def synthetic_packet(self, profile, *, result, observed_at, recorded_at, run_id, policy_version='0.1.0'):
        example = json.loads((self.root / 'docs/examples/governance-lifecycle/observation-fail.json').read_text())
        report = json.loads((self.root / 'tests/fixtures/governance-lifecycle/resources/synthetic-fail-report.json').read_text())
        report['observed_at'] = observed_at
        criterion = next((c for c in report['criteria'] if c['id'] == 'GRS-002'))
        criterion.update(status=result, observed=result == 'pass')
        report['overall_status'] = 'pass' if result == 'pass' else 'findings'
        count = len(report['criteria'])
        report['summary'].update({'pass': count - int(result == 'fail'), 'fail': int(result == 'fail'), 'critical_failures': int(result == 'fail')})
        report_bytes = self.context.adapter.json_bytes(report)
        digest = hashlib.sha256(report_bytes).hexdigest()
        uri = 'fixture://report-' + digest + '.json'
        context = deepcopy(example['body']['source_context'])
        context['run_id'] = run_id
        trust = deepcopy(example['body']['trust'])
        trust['verified_at'] = observed_at
        for check in trust['checks']:
            check['evidence_refs'] = [uri]
        capture = trust['capture']
        capture['captured_at'] = observed_at
        capture['source'].update(run_id=run_id, source_uri=uri)
        capture['subjects'][0].update(evidence_ref=uri, digest=digest, size_bytes=len(report_bytes))
        for step in capture['custody']:
            step.update(at=observed_at, source_uri=uri, output_refs=[uri])
        return self.context.adapter.adapt_grs002(report_bytes, context, trust, recorded_at=recorded_at, profile=profile, policy_version=policy_version)

class SyntheticActions:

    def __init__(self, root, context):
        self.root = root
        self.context = context

    def resource(self, value):
        data = self.context.adapter.json_bytes(value)
        digest = hashlib.sha256(data).hexdigest()
        uri = 'fixture://action-' + digest + '.json'
        return ({'uri': uri, 'digest': digest}, {uri: data})

    def decision_packet(self, profile, observation, *, record_id, revision, at, case_id, disposition='approve', previous=None):
        work, resources = self.resource({'environment': 'synthetic', 'case_id': case_id, 'work_item': 'Synthetic remediation work'})
        plan = {'remediation_id': case_id, 'owner_id': 'test-human:remediation-owner', 'target_at': '2026-09-14T12:00:00Z', 'action': 'Investigate and restore the synthetic GRS-002 review requirement.', 'work_ref': work}
        body = {'expected_revision': revision, 'purpose': 'remediate', 'observation_ref': self.context.contracts.record_ref(observation), 'action': plan['action'], 'rationale': 'Synthetic consent only.', 'remediation_plan': plan}
        if previous:
            body['supersedes_ref'] = self.context.contracts.record_ref(previous)
            if disposition == 'revoke':
                body.update({k: deepcopy(previous['body'][k]) for k in ('observation_ref', 'action', 'remediation_plan')})
                work = previous['body']['remediation_plan']['work_ref']
                _, resources = self.resource({'environment': 'synthetic', 'case_id': body['remediation_plan']['remediation_id'], 'work_item': 'Synthetic remediation work'})
        record = {'schema_version': '0.2.0', 'record_type': 'decision', 'record_id': record_id, 'environment': 'synthetic', 'profile_ref': self.context.contracts.versioned_ref(profile, 'profile_id'), 'finding': deepcopy(observation['finding']), 'recorded_at': at, 'body': body}
        binding = profile['role_binding']
        approval = {'target_digest': self.context.contracts.approval_target(record), 'finding_id': record['finding']['finding_id'], 'expected_revision': revision, 'subject_id': binding['assignments']['remediation_decider'], 'subject_type': 'human', 'role': 'remediation_decider', 'role_binding_ref': self.context.contracts.versioned_ref(binding), 'channel': 'synthetic_fixture', 'issued_at': at, 'disposition': disposition}
        proof, proof_resources = self.resource({'environment': 'synthetic', 'approval': deepcopy(approval)})
        approval['proof_ref'] = proof
        record['approval'] = approval
        resources.update(proof_resources)
        return (record, resources)

    def remediation_packet(self, decision, decision_resources, *, record_id, revision, at, progress='planned', previous=None):
        body = {**deepcopy(decision['body']['remediation_plan']), 'expected_revision': revision, 'decision_ref': self.context.contracts.record_ref(decision), 'progress': progress}
        if previous:
            body['supersedes_ref'] = self.context.contracts.record_ref(previous)
        record = {'schema_version': '0.2.0', 'record_type': 'remediation', 'record_id': record_id, 'environment': 'synthetic', 'profile_ref': deepcopy(decision['profile_ref']), 'finding': deepcopy(decision['finding']), 'recorded_at': at, 'body': body}
        proof, resources = self.resource(self.context.decisions.progress_statement(record))
        body['progress_evidence_ref'] = proof
        uri = body['work_ref']['uri']
        resources[uri] = decision_resources[uri]
        return (record, resources)

    def closure_packet(self, profile, failing, passing, remediation, *, record_id, revision, at):
        body = {'expected_revision': revision, 'reason': 'remediated', 'remediation_ref': self.context.contracts.record_ref(remediation), 'failing_observation_ref': self.context.contracts.record_ref(failing), 'passing_observation_ref': self.context.contracts.record_ref(passing), 'as_of': at, 'rationale': 'Synthetic closure consent only; not operational approval.'}
        record = {'schema_version': '0.2.0', 'record_type': 'closure', 'record_id': record_id, 'environment': 'synthetic', 'profile_ref': self.context.contracts.versioned_ref(profile, 'profile_id'), 'finding': deepcopy(failing['finding']), 'recorded_at': at, 'body': body}
        binding = profile['role_binding']
        approval = {'target_digest': self.context.contracts.approval_target(record), 'finding_id': record['finding']['finding_id'], 'expected_revision': revision, 'subject_id': binding['assignments']['closure_approver'], 'subject_type': 'human', 'role': 'closure_approver', 'role_binding_ref': self.context.contracts.versioned_ref(binding), 'channel': 'synthetic_fixture', 'issued_at': at, 'disposition': 'approve'}
        proof, resources = self.resource({'environment': 'synthetic', 'approval': deepcopy(approval)})
        approval['proof_ref'] = proof
        record['approval'] = approval
        return (record, resources)

class SyntheticExceptions:

    def __init__(self, root, context):
        self.root = root
        self.context = context

    def exception_packet(self, profile, observations, *, record_id, revision, at, waiver_id='synthetic-waiver:demo', risk='medium', expiry='2026-09-13', valid_from=None, disposition='approve', previous=None, previous_resources=None):
        binding_profile = self.context.exceptions.exception_profile()
        binding = binding_profile['bindings'][risk]
        subjects = sorted(binding['subjects'])
        finding = observations[0]['finding']
        waiver = {'id': waiver_id, 'environment': 'synthetic', 'scope': finding['key']['resource'], 'object_id': finding['finding_id'], 'affected_requirements': ['GRS-002'], 'risk_classification': risk, 'justification': 'Synthetic temporary risk acceptance for named observations only.', 'compensating_controls': ['Synthetic manual review evidence retained.'], 'approval_authority': binding['authority'], 'approved_by': ','.join(subjects), 'approved_on': at[:10], 'expiry': expiry, 'expired': False, 'status': 'rejected' if disposition == 'reject' else 'approved'}
        waiver_ref, resources = self.context.synthetic_actions.resource(waiver)
        body = {'expected_revision': revision, 'waiver_ref': waiver_ref, 'covered_observation_refs': sorted((self.context.contracts.record_ref(r) for r in observations), key=lambda r: r['id']), 'valid_from': valid_from or at, 'expires_at': (date.fromisoformat(expiry) + timedelta(days=1)).isoformat() + 'T00:00:00Z'}
        if previous is not None:
            body = {**deepcopy(previous['body']), 'expected_revision': revision, 'supersedes_ref': self.context.contracts.record_ref(previous)}
            uri = body['waiver_ref']['uri']
            resources = {uri: previous_resources[uri]}
        record = {'schema_version': '0.1.0', 'record_type': 'exception', 'record_id': record_id, 'environment': 'synthetic', 'profile_ref': self.context.contracts.versioned_ref(profile, 'profile_id'), 'finding': deepcopy(finding), 'recorded_at': at, 'body': body}
        approval = {'target_digest': self.context.contracts.approval_target(record), 'finding_id': finding['finding_id'], 'expected_revision': revision, 'authority': binding['authority'], 'subjects': subjects, 'subject_type': 'human', 'exception_profile_ref': self.context.contracts.versioned_ref(binding_profile, 'profile_id'), 'channel': 'synthetic_fixture', 'issued_at': at, 'disposition': disposition}
        proof, proof_resources = self.context.synthetic_actions.resource({'environment': 'synthetic', 'approval': deepcopy(approval)})
        approval['proof_ref'] = proof
        record['approval'] = approval
        resources.update(proof_resources)
        return (record, resources)
