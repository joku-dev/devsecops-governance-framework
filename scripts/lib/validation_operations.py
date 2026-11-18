"""Original runtime-validation command semantics over inert inputs and explicit OPA.

Report functions execute in process. An OPA port supplies actual bounded native
observations or retained observations during replay; caller source never executes.
"""
import io
import json
from types import SimpleNamespace

import yaml

from lib import architecture_assessment as architecture
from lib import combined_reporting, control_reporting
from lib.validation_files import relative


class RuntimeValidationEnvironment:
    def __init__(self, files, opa, *, python='python', fault=None):
        self.files = files
        self.root = files.root
        self.opa = opa
        self.python = python
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.commands = []
        self.fault = fault

    def print(self, *values, **options):
        options.setdefault('file', self.stdout)
        print(*values, **options)

    def which(self, name):
        if name != 'opa':
            raise ValueError('unsupported_validation_tool')
        return 'opa' if self.opa.available else None

    def path(self, value):
        if not isinstance(value, str) or not value.startswith(self.files.label + '/'):
            raise ValueError('validation_command_path_outside_input')
        name = relative(value[len(self.files.label) + 1:])
        return self.root / name

    def read_json(self, value):
        return json.loads(self.path(value).read_text(encoding='utf-8'))

    def write(self, value, raw):
        path = self.path(value)
        self.files.write(path.relative, raw)

    def run(self, command, *, cwd=None, capture_output=True, text=True, check=False):
        if not capture_output or not text or check or cwd is not None:
            raise ValueError('unsupported_runtime_validation_command_options')
        command = list(command)
        if not command or any(not isinstance(x, str) for x in command):
            raise ValueError('invalid_runtime_validation_command')
        if command[0] == 'opa':
            return self.opa.run(command, self.files)
        if command[0] != self.python or len(command) < 2:
            raise ValueError('unsupported_runtime_validation_program')
        program = self.path(command[1]).relative
        callbacks = {
            'scripts/generate_architecture_traceability_csv.py': self.traceability,
            'scripts/generate_architecture_governance_report.py': self.architecture_report,
            'scripts/generate_end_to_end_governance_report.py': self.combined_report,
        }
        if program not in callbacks:
            raise ValueError('unsupported_runtime_validation_generator')
        entry = {'program': program, 'arguments': command[2:],
                 'execution_kind': 'trusted_in_process_generator', 'process_started': False}
        self.commands.append(entry)
        output = io.StringIO()
        try:
            if self.fault is not None:
                self.fault(program)
            callbacks[program](command[2:], output)
            result = SimpleNamespace(returncode=0, stdout=output.getvalue(), stderr='')
        except SystemExit as error:
            result = SimpleNamespace(returncode=error.code if type(error.code) is int else 1,
                stdout=output.getvalue(), stderr='' if type(error.code) is int else str(error.code) + '\n')
        except Exception as error:
            # Original uncaught generator errors become sanitized diagnostic
            # text rather than pretending an external Python process ran.
            result = SimpleNamespace(returncode=1, stdout=output.getvalue(),
                                     stderr=type(error).__name__ + ': ' + str(error) + '\n')
        entry.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        return result

    @staticmethod
    def options(arguments, expected):
        if len(arguments) != len(expected) * 2 or arguments[::2] != list(expected):
            raise ValueError('unsupported_runtime_validation_generator_arguments')
        return dict(zip(expected, arguments[1::2]))

    def traceability(self, arguments, output):
        if arguments:
            raise ValueError('unsupported_traceability_arguments')
        raw = control_reporting.architecture_traceability(self.root,
            loader=lambda path: yaml.safe_load(path.read_text(encoding='utf-8')))
        self.files.write('generated/csv/architecture_runtime_traceability.csv', raw.encode())
        count = sum(len(yaml.safe_load(p.read_text(encoding='utf-8')).get('requirements', []))
                    for p in (self.root / 'architecture').glob('arch-*.yaml'))
        print('Generated generated/csv/architecture_runtime_traceability.csv', file=output)
        print(f'- architecture requirements: {count}', file=output)

    def architecture_report(self, arguments, output):
        options = self.options(arguments, ('--input', '--output-json', '--output-md'))
        input_path = self.path(options['--input'])
        remediation_path = self.root / 'architecture/remediation-actions.yaml'
        remediations = yaml.safe_load(remediation_path.read_text(encoding='utf-8')).get('remediations', []) if remediation_path.exists() else []
        gates = []
        for gate in architecture.GATES:
            if not self.which('opa'):
                raise SystemExit('OPA executable not found')
            result = self.run(['opa', 'eval', '--format=json', '--data', str(self.root / gate['policy']),
                               '--input', str(input_path), gate['query']])
            if result.returncode:
                raise SystemExit(result.stderr.strip() or result.stdout.strip())
            findings = json.loads(result.stdout)['result'][0]['expressions'][0]['value']
            gates.append({'id': gate['id'], 'title': gate['title'],
                'status': 'pass' if not findings else 'findings', 'findings': findings,
                'remediations': architecture.match_remediations(findings, remediations)})
        target = architecture.load_target_summary(input_path)
        value = architecture.load_architecture(input_path)
        detailed = value.get('detailed_evidence', {'report_only': True, 'declared_types': [],
                                                'by_type': {}, 'by_coarse_type': {}})
        advisories = architecture.detailed_evidence_advisories(value, detailed)
        report = {'target': target, 'gates': gates, 'detailed_evidence': detailed,
            'advisories': advisories, 'summary': {'gate_count': len(gates),
                'passed': sum(not gate['findings'] for gate in gates),
                'with_findings': sum(bool(gate['findings']) for gate in gates),
                'finding_count': sum(len(gate['findings']) for gate in gates)}}
        self.write(options['--output-json'], (json.dumps(report, indent=2) + '\n').encode())
        self.write(options['--output-md'], architecture.render_markdown(target, gates, detailed, advisories).encode())
        print(f"Generated {options['--output-json']}", file=output)
        print(f"Generated {options['--output-md']}", file=output)
        print(f"- gates: {report['summary']['gate_count']}", file=output)
        print(f"- findings: {report['summary']['finding_count']}", file=output)

    def combined_report(self, arguments, output):
        options = self.options(arguments, ('--architecture-json', '--devsecops-json', '--output-json', '--output-md'))
        left = self.read_json(options['--architecture-json'])
        right = self.read_json(options['--devsecops-json'])
        a_status, a_count, a_findings = combined_reporting.architecture_summary(left)
        d_status, d_count, d_findings = combined_reporting.devsecops_summary(right)
        report = {'target': left.get('target') or right.get('target') or {},
            'overall_status': 'pass' if a_status == 'PASS' and d_status == 'PASS' else 'findings',
            'domains': {'architecture': {'status': a_status.lower(), 'finding_count': a_count, 'findings': a_findings},
                        'devsecops': {'status': d_status.lower(), 'finding_count': d_count, 'findings': d_findings}},
            'summary': {'finding_count': a_count + d_count}}
        self.write(options['--output-json'], (json.dumps(report, indent=2) + '\n').encode())
        self.write(options['--output-md'], combined_reporting.render_markdown(left, right,
            'ha-cpswms-architecture-governance-report.md', 'ha-cpswms-devsecops-governance-report.md').encode())
        print(f"Generated {options['--output-json']}", file=output)
        print(f"Generated {options['--output-md']}", file=output)
        print(f"- overall_status: {report['overall_status']}", file=output)
        print(f"- findings: {report['summary']['finding_count']}", file=output)
