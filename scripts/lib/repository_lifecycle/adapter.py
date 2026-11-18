"""Original lifecycle consistency over an explicit retained data context.

Technical reference: V1 6b557f. Original records remain declared historical
facts; these checks never grant this node live approval, identity or consent.
"""
from copy import deepcopy
import hashlib
import json

class LifecycleAdapter:

    def __init__(self, root, context, *, validator_class, path_factory):
        self.root = root
        self.context = context
        self.validator_class = validator_class
        self.path_factory = path_factory

    def json_bytes(self, value):
        return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')

    def strict_json(self, data):

        def pairs(items):
            result = {}
            for key, value in items:
                self.context.contracts.require(key not in result, 'Duplicate JSON member: ' + key)
                result[key] = value
            return result

        def invalid_constant(value):
            raise ValueError('Non-JSON numeric constant: ' + value)
        return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid_constant)

    def adapt_grs002(self, report_bytes, context, trust, *, recorded_at, profile, policy_version):
        """Preserve supplied synthetic trust assertions; never infer real provenance."""
        self.context.contracts.validate_test_profile(profile)
        self.context.contracts.require(context.get('kind') == 'test', 'Adapter supports synthetic test context only')
        self.context.contracts.require(context.get('repository_id') == profile['repository_id'], 'Adapter repository mismatch')
        report = self.strict_json(report_bytes)
        schema = json.loads((self.root / 'schemas/governance-repository-security-report.schema.json').read_text())
        self.validator_class(schema, format_checker=self.context.contracts.format_checker).validate(report)
        self.context.contracts.require(report['observation'].get('synthetic') is True, 'Report must be explicitly synthetic')
        self.context.contracts.require(report['repository_id'] == profile['repository_id'], 'Report repository mismatch')
        criteria = [c for c in report['criteria'] if c['id'] == 'GRS-002']
        self.context.contracts.require(len(criteria) == 1 and criteria[0]['key'] == 'pull_request_review_required', 'Exactly one GRS-002 criterion is required')
        digest = hashlib.sha256(report_bytes).hexdigest()
        trust = deepcopy(trust)
        subjects = [s for s in trust['capture']['subjects'] if s['id'] == 'governance_repository_security_report']
        self.context.contracts.require(len(subjects) == 1 and subjects[0]['digest'] == digest and (subjects[0]['size_bytes'] == len(report_bytes)), 'Trust subject does not match raw report')
        uri = subjects[0]['evidence_ref']
        self.context.contracts.require(uri.startswith('fixture://'), 'Adapter cannot accept live evidence resources')
        self.context.contracts.require(trust['capture']['source']['workflow_name'] == context['producer_id'], 'Trust producer mismatch')
        key = {'repository_id': report['repository_id'], 'domain': 'governance_repository_security', 'rule_id': 'GRS-002', 'finding_type': 'criterion_failure', 'resource': 'refs/heads/main'}
        finding = {'fingerprint_version': '1', 'key': key, 'finding_id': self.context.contracts.finding_id(key)}
        identity = {'finding': finding, 'source_context': context, 'snapshot_digest': digest, 'profile_version': report['profile_version'], 'policy_version': policy_version}
        record = {'schema_version': '0.1.0', 'record_type': 'observation', 'record_id': 'observation:' + self.context.contracts.canonical_digest(identity), 'environment': 'synthetic', 'profile_ref': self.context.contracts.versioned_ref(profile, 'profile_id'), 'finding': finding, 'recorded_at': recorded_at, 'body': {'observed_at': report['observed_at'], 'result': criteria[0]['status'], 'rule_key': 'pull_request_review_required', 'granularity': 'criterion', 'profile_version': report['profile_version'], 'policy_version': policy_version, 'source_schema': 'governance-repository-security-report.schema.json@0.2.0', 'source_context': deepcopy(context), 'snapshot_ref': {'uri': uri, 'digest': digest}, 'trust': trust, 'acceptance': {'evaluated_at': recorded_at, 'profile_ref': self.context.contracts.versioned_ref(profile, 'profile_id'), 'outcome': 'accepted', 'verifier_id': 'synthetic-contract-verifier'}}}
        proof = self.json_bytes(self.context.contracts.acceptance_statement(record))
        proof_uri = 'fixture://acceptance-' + hashlib.sha256(proof).hexdigest() + '.json'
        self.context.contracts.require(proof_uri != uri, 'Report and proof resource URI collision')
        record['body']['acceptance']['proof_ref'] = {'uri': proof_uri, 'digest': hashlib.sha256(proof).hexdigest()}
        resources = {uri: report_bytes, proof_uri: proof}
        self.context.contracts.validate_test_record(record, profile, resources)
        return (record, resources)
