"""Complete V1 diagnostic candidate functions over explicit context dependencies."""

from copy import deepcopy

import argparse,hashlib

_DEFAULT_DEVSECOPS_ADAPTER=object()

GATE_IDS = ('architecture_readiness', 'integration_readiness', 'operation_readiness', 'release_readiness')

class CandidateNormalization:

    def __init__(self, context):
        self.contracts = context.contracts

    def check_context(self, report_bytes, context, *, evaluated_at):
        self.contracts.schema_validator('candidate-context').validate(context)
        self.contracts.require(hashlib.sha256(report_bytes).hexdigest() == context['report_sha256'], 'Report digest differs from declared context')
        self.contracts.require(self.contracts.timestamp(context['observed_at']) <= self.contracts.timestamp(evaluated_at), 'Observation time is after candidate evaluation')
        if context['synthetic']:
            return 'test'
        if context['event'] == 'pull_request':
            return 'pull_request'
        if context['event'] == 'workflow_dispatch':
            return 'manual'
        if context['event'] == 'release':
            return 'release'
        return 'mainline' if context['branch'] == 'main' else 'branch'

    def make_candidates(self, report_bytes, context, outcomes, *, evaluated_at, adapter_id, source_contract, domain, granularity):
        kind = self.check_context(report_bytes, context, evaluated_at=evaluated_at)
        results = []
        for outcome in outcomes:
            record = {'subject': {'repository_id': context['repository_id'], 'domain': domain, 'rule_id': outcome['rule_id'], 'resource': 'repository'}, 'granularity': granularity, 'result': outcome['result'], 'source_pointer': outcome['source_pointer'], 'source_messages': deepcopy(outcome.get('source_messages', []))}
            record['candidate_id'] = 'candidate:' + self.contracts.canonical_digest({'adapter_id': adapter_id, 'source_contract': source_contract, 'context': context, 'outcome': record})
            results.append(record)
        report = {'schema_version': '0.1.0', 'record_type': 'lifecycle-input-candidates', 'environment': 'diagnostic', 'official_state': False, 'enforcement': 'report_only', 'acceptance_status': 'not_evaluated', 'trust_status': 'unverified', 'evaluated_at': evaluated_at, 'adapter': {'id': adapter_id, 'version': '0.1.0', 'source_contract': source_contract}, 'source': {'context': deepcopy(context), 'declared_context_kind': kind, 'size_bytes': len(report_bytes), 'age_seconds': int((self.contracts.timestamp(evaluated_at) - self.contracts.timestamp(context['observed_at'])).total_seconds())}, 'counts': {status: sum((r['result'] == status for r in results)) for status in ('pass', 'fail', 'not_tested', 'not_applicable', 'findings')}, 'candidates': results, 'acceptance_gaps': ['producer_authentication', 'baseline_and_policy_resolution', 'approved_scope_and_trust_profile', 'approved_freshness_and_replay_policy', 'accountable_live_acceptance']}
        self.contracts.schema_validator('candidates').validate(report)
        return report

class DevsecopsCandidateAdapter:

    def __init__(self, context, normalization):
        self.contracts = context.contracts
        self.normalization = normalization
        self.strict_json = context.adapter.strict_json

    def adapt_devsecops(self, report_bytes, context, *, evaluated_at):
        self.normalization.check_context(report_bytes, context, evaluated_at=evaluated_at)
        report = self.strict_json(report_bytes)
        self.contracts.schema_validator('devsecops-source').validate(report)
        for field in ('event', 'purpose', 'release_context'):
            self.contracts.require(report['run_context'][field] == context[field], 'Producer/context mismatch: ' + field)
        self.contracts.require(report['run_context'].get('source') != 'demo' or context['synthetic'] is True, 'Demo report requires declared synthetic context')
        controls = report['controls']
        ids = [c['control_id'] for c in controls]
        self.contracts.require(len(ids) == len(set(ids)), 'Duplicate control IDs are ambiguous')
        for control in controls:
            self.contracts.require(control['control_id'].startswith('DSCB-' + control['level'] + '-REQ-'), 'Control ID/level mismatch')
        expected = {status: sum((c['status'] == status for c in controls)) for status in ('pass', 'fail', 'not_tested', 'not_applicable')}
        expected.update(total_controls=len(controls), applicable_controls=len(controls) - expected['not_applicable'], tested_controls=expected['pass'] + expected['fail'])
        self.contracts.require(report['summary'] == expected, 'Summary differs from declared control rows')
        outcomes = [{'rule_id': c['control_id'], 'result': c['status'], 'source_pointer': f'/controls/{i}', 'source_messages': [c['message']] if c.get('message') else []} for i, c in enumerate(controls)]
        return self.normalization.make_candidates(report_bytes, context, outcomes, evaluated_at=evaluated_at, adapter_id='devsecops-control-candidates', source_contract='control-evaluation-report@1.0.0', domain='devsecops', granularity='control')

class ArchitectureCandidateAdapter:

    def __init__(self, context, normalization):
        self.contracts = context.contracts
        self.normalization = normalization
        self.strict_json = context.adapter.strict_json

    def adapt_architecture(self, report_bytes, context, *, evaluated_at):
        self.normalization.check_context(report_bytes, context, evaluated_at=evaluated_at)
        report = self.strict_json(report_bytes)
        self.contracts.require('schema_version' not in report, 'Versioned architecture producer requires an explicit adapter revision')
        self.contracts.schema_validator('architecture-source').validate(report)
        gates = report['gates']
        ids = [gate['id'] for gate in gates]
        self.contracts.require(len(ids) == len(set(ids)) and set(ids) == set(GATE_IDS), 'Expected exactly the four supported architecture gates')
        self.contracts.require(context['commit_id'].startswith(report['target']['commit']), 'Declared full commit conflicts with report target commit')
        for gate in gates:
            self.contracts.require(gate['status'] == ('findings' if gate['findings'] else 'pass'), 'Gate status contradicts finding messages')
            self.contracts.require(all((message.strip() for message in gate['findings'])), 'Blank finding message is ambiguous')
        expected = {'gate_count': len(gates), 'passed': sum((not gate['findings'] for gate in gates)), 'with_findings': sum((bool(gate['findings']) for gate in gates)), 'finding_count': sum((len(gate['findings']) for gate in gates))}
        self.contracts.require(report['summary'] == expected, 'Architecture summary differs from explicit gate outcomes')
        outcomes = [{'rule_id': gate['id'], 'result': gate['status'], 'source_pointer': f'/gates/{i}', 'source_messages': gate['findings']} for i, gate in enumerate(gates)]
        return self.normalization.make_candidates(report_bytes, context, outcomes, evaluated_at=evaluated_at, adapter_id='architecture-gate-candidates', source_contract='architecture-gate-report@legacy-shape-v1', domain='architecture', granularity='gate')

class CandidateWriter:

    def __init__(self, root, context, *, path_factory, adapter):
        self.ROOT = root
        self.Path = path_factory
        self.require = context.contracts.require
        self.strict_json = context.adapter.strict_json
        self.json_bytes = context.adapter.json_bytes
        self.adapter = adapter

    def write_candidates(self, report, context, output, *, evaluated_at, adapter=_DEFAULT_DEVSECOPS_ADAPTER):
        if adapter is _DEFAULT_DEVSECOPS_ADAPTER:
            adapter = self.adapter
        report, context, output = (self.Path(report), self.Path(context), self.Path(output))
        self.require(output.resolve() not in (report.resolve(), context.resolve()), 'Output cannot overwrite adapter inputs')
        if output.resolve().is_relative_to(self.ROOT):
            self.require(any((output.resolve().is_relative_to((self.ROOT / path).resolve()) for path in ('generated/reports/lifecycle-candidates', 'docs/examples/lifecycle-candidates'))), 'Candidate outputs require a dedicated diagnostic path')
        result = adapter(report.read_bytes(), self.strict_json(context.read_bytes()), evaluated_at=evaluated_at)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(self.json_bytes(result))
        return result

class DevsecopsCandidateProgram:

    def __init__(self, writer, adapter, *, path_factory, argument_parser, argv):
        self.writer = writer
        self.adapter = adapter
        self.Path = path_factory
        self.argument_parser = argument_parser
        self.argv = argv
        self.description = 'Prepare diagnostic control candidates, never accepted lifecycle observations.'

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--report', type=self.Path, required=True)
        parser.add_argument('--context', type=self.Path, required=True)
        parser.add_argument('--output', type=self.Path, required=True)
        parser.add_argument('--evaluated-at', required=True)
        args = parser.parse_args(self.argv)
        result = self.writer.write_candidates(args.report, args.context, args.output, evaluated_at=args.evaluated_at)
        print(f"Prepared {len(result['candidates'])} unverified control candidates; no lifecycle intake or state change.")

class ArchitectureCandidateProgram:

    def __init__(self, writer, adapter, *, path_factory, argument_parser, argv):
        self.writer = writer
        self.adapter = adapter
        self.Path = path_factory
        self.argument_parser = argument_parser
        self.argv = argv
        self.description = 'Prepare diagnostic architecture gate candidates without inferring marker findings.'

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--report', type=self.Path, required=True)
        parser.add_argument('--context', type=self.Path, required=True)
        parser.add_argument('--output', type=self.Path, required=True)
        parser.add_argument('--evaluated-at', required=True)
        args = parser.parse_args(self.argv)
        result = self.writer.write_candidates(args.report, args.context, args.output, evaluated_at=args.evaluated_at, adapter=self.adapter)
        print(f"Prepared {len(result['candidates'])} unverified gate candidates; no marker inference or lifecycle intake.")
