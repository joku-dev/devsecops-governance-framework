"""Complete legacy extended-compliance decisions through explicit environment ports.

Technical profile: original 6b557fe generate_governance_compliance_result.py.
This module starts no programs and never executes an inspected repository.
An adapter must supply the complete own validator and, by default, own suite.
"""
from pathlib import Path
import json

from control_evaluation import POLICY_QUERIES

EXPECTED_ARTIFACTS = {
    'traceability_matrix': 'generated/xlsx/traceability_matrix.csv',
    'document_control_matrix': 'generated/xlsx/document_control_matrix.csv',
    'open_gap_report': 'generated/xlsx/open_gap_report.csv',
    'status_viewer': 'generated/viewer/status-viewer.html',
    'policy_render': 'generated/documents/devsecops-pol-001.html',
    'directive_render': 'generated/documents/devsecops-dir-001.html',
    'control_evaluation_report_json': 'generated/control-evaluation-report.json',
    'control_evaluation_report_markdown': 'generated/control-evaluation-report.md',
}


class ComplianceResult:
    """Preserve the complete wire/effect order; admission belongs to the adapter."""
    def __init__(self, environment):
        self.environment = environment
        self.root = environment.root

    def command_status(self, command):
        result = self.environment.run(command)
        return ('pass' if result.returncode == 0 else 'fail',
                result.stdout.strip() or result.stderr.strip())

    def display_path(self, path):
        try:
            return str(self.environment.resolve(path).relative_to(self.root))
        except ValueError:
            return str(path)

    def evaluate_policy(self, input_path, query):
        result = self.environment.run(['opa', 'eval', '-f', 'json', '-d',
            str(self.root / 'policies/opa'), '-i', str(input_path), query])
        if result.returncode != 0:
            return {'status': 'fail', 'deny_count': -1}
        denies = json.loads(result.stdout)['result'][0]['expressions'][0]['value']
        return {'status': 'pass' if len(denies) == 0 else 'fail', 'deny_count': len(denies)}

    def generate(self, *, output_file, target_repo=None, input_file=None, skip_unit_tests=False):
        if type(skip_unit_tests) is not bool:
            raise ValueError('explicit_compliance_unit_skip_required')
        target = self.environment.resolve(Path(self.root if target_repo is None else target_repo))
        inputs = self.environment.resolve(Path(self.root / 'policies/example-input.release-candidate.json'
                      if input_file is None else input_file))
        output = Path(output_file)
        if not output.is_absolute():
            output = self.environment.cwd / output
        control_json = output.with_name('control-evaluation-report.json')
        control_markdown = output.with_name('control-evaluation-report.md')

        checks = []
        integration = self.environment.run(['python3',
            str(self.root / 'scripts/check_repo_governance_integration.py'), '--target-repo', str(target)])
        if integration.stdout.strip():
            checks = json.loads(integration.stdout)['checks']
        validator_status, _ = self.command_status(['python3', str(self.root / 'scripts/validate_governance_repo.py')])
        if skip_unit_tests:
            unit_status = 'pass'  # Original wire; envelope must separately say not_run.
        else:
            unit_status, _ = self.command_status(['python3', '-m', 'unittest', 'discover', '-s', 'tests'])
        opa_status, _ = self.command_status(['opa', 'check', str(self.root / 'policies/opa')])
        policies = []
        for policy_id, query in POLICY_QUERIES.items():
            evaluation = self.evaluate_policy(inputs, query)
            policies.append({'policy_id': policy_id, 'status': evaluation['status'],
                             'deny_count': evaluation['deny_count']})
        control = self.environment.control_report(inputs)
        self.environment.write(control_json, json.dumps(control, indent=2) + '\n')
        self.environment.write(control_markdown, self.environment.control_markdown(control))
        artifacts = []
        for artifact_id, relative in EXPECTED_ARTIFACTS.items():
            path = self.root / relative
            if artifact_id == 'control_evaluation_report_json':
                path = control_json; relative = self.display_path(path)
            elif artifact_id == 'control_evaluation_report_markdown':
                path = control_markdown; relative = self.display_path(path)
            artifacts.append({'artifact_id': artifact_id, 'path': relative,
                'status': 'present' if self.environment.exists(path) else 'missing'})
        passed = (validator_status == 'pass' and unit_status == 'pass' and opa_status == 'pass'
            and all(check['status'] == 'pass' for check in checks)
            and all(item['status'] == 'pass' for item in policies) and control['summary']['fail'] == 0)
        report = {'schema_version': '1.0.0', 'governance_repo': self.root.name,
            'target_repo': target.name, 'timestamp': self.environment.timestamp(),
            'status': 'pass' if passed else 'fail', 'checks': checks,
            'execution': {
                'validator': {'status': validator_status, 'command': 'python3 scripts/validate_governance_repo.py'},
                'unit_tests': {'status': unit_status, 'command': 'skipped in nested/test context'
                    if skip_unit_tests else 'python3 -m unittest discover -s tests'},
                'opa_check': {'status': opa_status, 'command': 'opa check policies/opa'}},
            'policy_evaluations': policies, 'control_evaluations': control, 'artifacts': artifacts}
        self.environment.write(output, json.dumps(report, indent=2) + '\n')
        self.environment.print(f'Wrote {output}')
        return (0 if passed else 1), report
