"""Ordered original generator effects over explicit retained data and ports.

These are trusted in-process product functions. No inspected Python or shell
program is executed, and an unimplemented native port never supplies success.
"""
import errno
import json
from pathlib import Path

import yaml

from lib import report_graph, report_multi_consumer, report_blocking_readiness
from lib import report_blocking_alignment, report_replay_triage
from lib import report_lineage, report_impact, report_source_replacement
from lib import report_source_intake, report_source_briefs, report_requirement_delta, report_source_process
from lib import attestation_assessment
from lib.report_data import ReportData
from lib.provider_ports import committed_intake_signatures, configuration_source_profile

SOURCE_GENERATORS = {
    'scripts/generate_source_lineage_report.py': (report_lineage, 'source-lineage-report', False),
    'scripts/generate_governance_change_impact_report.py': (report_impact, 'governance-change-impact', True),
    'scripts/generate_architecture_source_replacement_assessment.py': (report_source_replacement, 'architecture-source-replacement-assessment', False),
    'scripts/generate_source_document_intake_status.py': (report_source_intake, 'source-document-intake-status', True),
    'scripts/generate_source_document_intake_review_briefs.py': (report_source_briefs, 'source-document-intake-review-briefs', True),
    'scripts/generate_source_document_requirement_delta.py': (report_requirement_delta, 'source-document-requirement-delta', True),
    'scripts/generate_source_document_process_status.py': (report_source_process, 'source-document-process-status', False),
}


class OriginalReportData(ReportData):
    """Bounded file access, retaining original json.loads grammar and errors."""
    def __init__(self, root, membership, *, raw_yaml=False):
        super().__init__(root, membership)
        self.raw_yaml = raw_yaml

    def raw(self, path):
        name = self.relative(path)
        if name in self.directories:
            raise IsADirectoryError(errno.EISDIR, 'Is a directory', str(path))
        if name not in self.files:
            raise FileNotFoundError(errno.ENOENT, 'No such file or directory', str(path))
        return super().raw(path)

    def json(self, path):
        return json.loads(self.raw(path).decode('utf-8'))

    def yaml(self, path):
        value = yaml.safe_load(self.raw(path))
        return value if self.raw_yaml else value or {}


class RepositoryReportOperations:
    def __init__(self, root, membership, *, mkdir, write, clock,
                 source_configuration_profile, verify_attestation, invoke, data_factory=None):
        if data_factory is not None and not callable(data_factory):
            raise ValueError('repository_report_data_factory_required')
        self.root = Path(root).resolve() if data_factory is None else root.resolve()
        self.data_factory = data_factory
        self.membership = membership
        self.mkdir = mkdir
        self.write = write
        self.clock = clock
        self.profile = source_configuration_profile
        self.verify_attestation = verify_attestation
        self.invoke = invoke

    def data(self, *, raw_yaml=False):
        if self.data_factory is not None:
            return self.data_factory(raw_yaml=raw_yaml)
        return OriginalReportData(self.root, self.membership, raw_yaml=raw_yaml)

    @staticmethod
    def outcome(stdout, *, code=0, stderr=''):
        return {'returncode': code, 'stdout': stdout, 'stderr': stderr}

    def json(self, name, value, *, ensure_ascii=True):
        self.write(name, (json.dumps(value, indent=2, ensure_ascii=ensure_ascii) + '\n').encode('utf-8'))

    def source(self, program):
        module, stem, caught = SOURCE_GENERATORS[program]
        try:
            self.prepare(program)
            report = module.build_report(self.data(), self.clock())
        except RuntimeError as issue:
            if not caught:
                raise
            return self.outcome('', code=1, stderr=f'Error: {issue}\n')
        json_path = 'generated/reports/' + stem + '.json'
        md_path = 'generated/reports/' + stem + '.md'
        self.mkdir('generated/reports')
        # Preserve original partial effects if encoding/rendering/writing fails.
        self.json(json_path, report, ensure_ascii=module is not report_source_process)
        self.write(md_path, module.render_markdown(report).encode('utf-8'))
        if module is report_source_process:
            return self.outcome(f'Wrote {json_path} and {md_path}\n'
                f"Authorized-source baseline readiness: {report['authorized_source_baseline']['status']}\n")
        lines = [f'Wrote {json_path}', f'Wrote {md_path}']
        summary = report['summary']
        code = 0
        if module is report_lineage:
            lines.extend([f"- source documents: {summary['source_document_count']}",
                f"- direct derived artifact links: {summary['derived_artifact_count']}",
                f"- missing derived artifacts: {summary['missing_derived_artifacts']}",
                f"- unresolved source references: {summary['unresolved_source_reference_count']}"])
            code = 1 if report['missing_derived_artifacts'] else 0
        elif module is report_source_replacement:
            lines.append(f"- likely replacements: {summary['likely_replacements']}")
        elif module is report_source_intake:
            lines.extend([f"- registered source documents: {summary['registered_source_documents']}",
                f"- open review items: {summary['open_review_items']}",
                f"- replacement review items: {summary['replacement_review_items']}"])
        elif module is report_source_briefs:
            lines.extend([f"- review briefs: {summary['review_briefs']}",
                f"- human decisions required: {summary['human_decision_required']}"])
        elif module is report_requirement_delta:
            lines.extend([f"- replacement pairs: {summary['replacement_pairs']}",
                f"- status counts: {summary['status_counts']}"])
        return self.outcome('\n'.join(lines) + '\n', code=code)

    def child(self, script, *, lineage_message=False):
        result = self.invoke('scripts/' + script, ())
        if result['returncode'] != 0:
            details = result['stderr'].strip() or result['stdout'].strip() or 'unknown error'
            if lineage_message:
                raise RuntimeError(f'source lineage generation failed: {details}')
            raise RuntimeError(f'{script} failed: {details}')

    def placeholders(self, stems):
        self.mkdir('generated/reports')
        for stem, title in stems:
            for suffix, raw in (('.json', b'{}\n'), ('.md', ('# ' + title + '\n').encode())):
                name = 'generated/reports/' + stem + suffix
                if not self.data().exists(self.root / name):
                    self.write(name, raw)

    def prepare(self, program):
        if program == 'scripts/generate_governance_change_impact_report.py':
            self.child('generate_source_lineage_report.py', lineage_message=True)
        elif program == 'scripts/generate_source_document_intake_status.py':
            self.placeholders([('source-document-intake-status', 'Source Document Intake Status'),
                ('source-document-intake-review-briefs', 'Source Document Intake Review Briefs'),
                ('source-document-requirement-delta', 'Source Document Requirement Delta')])
            self.child('generate_source_lineage_report.py')
            self.child('generate_architecture_source_replacement_assessment.py')
        elif program == 'scripts/generate_source_document_intake_review_briefs.py':
            self.placeholders([('source-document-intake-review-briefs', 'Source Document Intake Review Briefs')])
            self.child('generate_source_document_intake_status.py')
            self.child('generate_governance_change_impact_report.py')
        elif program == 'scripts/generate_source_document_requirement_delta.py':
            self.child('generate_architecture_source_replacement_assessment.py')

    def graph(self):
        data = self.data()
        def json_loader(root, name):
            path = root / name
            return data.json(path) if data.exists(path) else {}
        def yaml_loader(root, name):
            path = root / name
            return data.yaml(path) if data.exists(path) else {}
        value = report_graph.build_graph(self.root, json_loader=json_loader, yaml_loader=yaml_loader)
        name = 'generated/graph/governance-graph.json'
        self.mkdir('generated/graph')
        self.json(name, value)
        return self.outcome(f"Wrote {name} ({len(value['nodes'])} nodes, {len(value['edges'])} edges)\n")

    def multi_consumer(self):
        profile = self.profile
        if (not isinstance(profile, dict) or profile != configuration_source_profile(profile.get('provider'))
                or profile.get('source_signature_only') is not True):
            raise ValueError('explicit_repository_source_configuration_profile_required')
        data = self.data(raw_yaml=True)
        observations = committed_intake_signatures(profile['provider'], lambda name: data.raw(data.root / name))
        value = report_multi_consumer.generate(data, None, observations)
        json_path = 'generated/reports/multi-consumer-readiness.json'
        md_path = 'generated/reports/multi-consumer-readiness.md'
        self.json(json_path, value)
        self.write(md_path, report_multi_consumer.render_markdown(value).encode('utf-8'))
        return self.outcome(f'Wrote {json_path}\nWrote {md_path}\n', code=0 if value['ready'] else 1)

    def readiness(self):
        data = self.data(raw_yaml=True)
        conflicts = sorted(name for name in data.files | data.directories
                           if name.startswith('status/intake-conflicts/') and name.endswith('.json'))
        # The original command does not observe a clock. Reuse its pure
        # assessment directly rather than invent time for a report wrapper.
        value = report_blocking_readiness.assess(
            integrations=data.yaml(self.root / 'status/application-repository-integrations.yaml'),
            devsecops=data.json(self.root / 'status/repository-results-index.json'),
            architecture=data.json(self.root / 'status/architecture-results-index.json'),
            typed=data.json(self.root / 'status/typed-evidence-results-index.json'),
            health=data.json(self.root / 'status/intake-health.json'),
            model=data.yaml(self.root / 'model/enforcement/blocking-readiness.yaml'), conflict_files=conflicts)
        name = 'generated/reports/blocking-readiness.json'
        self.json(name, value)
        return self.outcome(f"Wrote {name}: {value['summary']['ready']} ready, {value['summary']['not_ready']} not ready\n")

    def alignment(self):
        value = report_blocking_alignment.generate(self.data(raw_yaml=True), self.clock())
        name = 'generated/reports/blocking-mode-alignment.json'
        self.json(name, value)
        return self.outcome(f"Wrote {name}: {value['alignment_status']}, {value['summary']['legacy_risk_active']} legacy risk, {value['summary']['unsafe_blocking']} unsafe\n")

    def triage(self):
        value = report_replay_triage.generate(self.data(), None)
        self.json('generated/reports/replay-triage.json', value)
        self.write('generated/reports/replay-triage.md', report_replay_triage.render_markdown(value).encode('utf-8'))
        return self.outcome(f"Wrote Replay Triage: {value['summary']['assessments']} assessments, {value['summary']['official_latest_findings']} official latest findings\n")

    def attestation(self, arguments):
        expected = (str(self.root / 'docs/examples/evidence-attestation.example.json'), '--output',
                    str(self.root / 'generated/reports/evidence-attestation-pilot.json'), '--evaluated-at',
                    '2026-07-17T10:01:00Z')
        if tuple(arguments) != expected:
            raise ValueError('unsupported_repository_attestation_arguments')
        data = self.data()
        value = attestation_assessment.input_object(data.raw(data.root / 'docs/examples/evidence-attestation.example.json'))
        roots = attestation_assessment.registry(data.raw(data.root / 'model/evidence/evidence-trust-roots.yaml'))
        statement = value['statement']
        result = attestation_assessment.assess(attestation=value, registry=roots,
            expected_context={key: statement[key] for key in attestation_assessment.CONTEXT_FIELDS},
            expected_subject=statement['subject'], evaluated_at=expected[-1], attestation_ref=expected[0],
            verify=self.verify_attestation)
        self.mkdir('generated/reports')
        self.json('generated/reports/evidence-attestation-pilot.json', result)
        return self.outcome(attestation_assessment.summary(result))

    def run(self, program, arguments=()):
        if program == 'scripts/verify_evidence_attestation.py':
            return self.attestation(arguments)
        if arguments:
            raise ValueError('unsupported_repository_generator_arguments')
        if program in SOURCE_GENERATORS:
            return self.source(program)
        callbacks = {'scripts/generate_governance_graph.py': self.graph,
                     'scripts/generate_multi_consumer_readiness.py': self.multi_consumer,
                     'scripts/generate_blocking_readiness.py': self.readiness,
                     'scripts/generate_blocking_mode_alignment.py': self.alignment,
                     'scripts/generate_replay_triage_report.py': self.triage}
        if program not in callbacks:
            raise ValueError('unsupported_repository_generator')
        return callbacks[program]()
