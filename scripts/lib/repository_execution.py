"""Finite orchestration ports for the complete original repository validator.

Program names identify registered in-process product functions, never caller
programs. Journal callbacks must persist each intent before its operation. An
uncaught callback failure remains an incomplete execution, not a passing check.
"""
import io
from pathlib import PurePosixPath
from types import SimpleNamespace

from lib.validation_files import relative

PROGRAMS = frozenset('scripts/' + name + '.py' for name in (
    'generate_governance_graph', 'generate_multi_consumer_readiness', 'verify_evidence_attestation',
    'generate_blocking_readiness', 'generate_blocking_mode_alignment', 'generate_replay_triage_report',
    'generate_source_lineage_report', 'generate_governance_change_impact_report',
    'generate_architecture_source_replacement_assessment', 'generate_source_document_intake_status',
    'generate_source_document_intake_review_briefs', 'generate_source_document_requirement_delta',
    'generate_source_document_process_status', 'validate_governance_lifecycle_contracts',
    'validate_governance_lifecycle_ledger', 'validate_evidence_agent_provenance',
    'validate_document_consistency_review_operations'))
SNAPSHOT_CALLBACKS = (
    'load_measured_security_snapshots', 'load_measured_l1_snapshots', 'load_assurance_profile',
    'load_assurance_snapshots', 'validate_assurance_source', 'load_staging_deployment_snapshots',
    'load_consolidated_l1_snapshots', 'validate_consolidated_l1_sources')
MAX_OUTPUT = 1024 * 1024


class RepositoryOutput(io.StringIO):
    def write(self, text):
        if len((self.getvalue() + text).encode('utf-8')) > MAX_OUTPUT:
            raise ValueError('repository_validation_output_budget')
        return super().write(text)


class RepositoryExecution:
    def __init__(self, root, *, validator_class, programs, snapshots, verify_release_integrity,
                 opa_check, append_event, python='python'):
        label = str(root)
        if (not PurePosixPath(label).is_absolute() or str(PurePosixPath(label)) != label
                or '..' in PurePosixPath(label).parts or any(ord(c) < 32 for c in label)):
            raise ValueError('absolute_repository_execution_root_required')
        if type(programs) is not dict or set(programs) != PROGRAMS or not all(callable(fn) for fn in programs.values()):
            raise ValueError('complete_repository_program_ports_required')
        if (not callable(validator_class) or not callable(verify_release_integrity) or not callable(append_event)
                or opa_check is not None and not callable(opa_check)):
            raise ValueError('explicit_repository_execution_ports_required')
        if type(python) is not str or not python or len(python) > 8192 or '\0' in python or python == 'opa':
            raise ValueError('repository_in_process_program_label_required')
        self.root, self.label, self.validator_class = root, label, validator_class
        self.programs = dict(programs)
        self.release = verify_release_integrity
        self.opa_check, self.append_event, self.python = opa_check, append_event, python
        self.stdout, self.stderr = RepositoryOutput(), RepositoryOutput()
        self.sequence = 0
        for name in SNAPSHOT_CALLBACKS:
            function = getattr(snapshots, name, None)
            if not callable(function):
                raise ValueError('complete_repository_snapshot_ports_required')
            setattr(self, name, function)

    def which(self, name):
        if name != 'opa':
            raise ValueError('unsupported_repository_validation_tool')
        return 'opa' if self.opa_check is not None else None

    def print(self, *values, **options):
        if options.get('file') is not None and options['file'] not in (self.stdout, self.stderr):
            raise ValueError('repository_validation_output_stream_required')
        if options.get('file') is None:
            options['file'] = self.stdout
        print(*values, **options)

    def operation(self, request, callback):
        self.sequence += 1
        if self.sequence > 4096:
            raise ValueError('repository_validation_operation_budget')
        identity = {'sequence': self.sequence, 'request': request}
        self.append_event({**identity, 'phase': 'intent'})
        try:
            outcome = callback()
        except BaseException as error:
            self.append_event({**identity, 'phase': 'incomplete', 'error_type': type(error).__name__})
            raise
        self.append_event({**identity, 'phase': 'completed', 'outcome': outcome})
        return outcome

    @staticmethod
    def outcome(value):
        if (type(value) is not dict or set(value) != {'returncode', 'stdout', 'stderr'}
                or type(value['returncode']) is not int
                or any(type(value[key]) is not str or len(value[key].encode('utf-8')) > MAX_OUTPUT
                       for key in ('stdout', 'stderr'))):
            raise ValueError('complete_repository_program_outcome_required')
        return dict(value)

    def run(self, command, *, cwd=None, capture_output=True, text=True, check=False):
        if (capture_output is not True or text is not True or check is not False
                or cwd is not None and str(cwd) != self.label
                or type(command) is not list or not 2 <= len(command) <= 16
                or any(type(value) is not str or '\0' in value or len(value) > 8192 for value in command)):
            raise ValueError('unsupported_repository_validation_command')
        if command[0] == 'opa':
            if command != ['opa', 'check', self.label + '/policies/opa'] or self.opa_check is None:
                raise ValueError('unsupported_repository_opa_command')
            request = {'kind': 'native-port', 'operation': 'opa-check'}
            value = self.operation(request, lambda: self.outcome(self.opa_check()))
        else:
            if command[0] != self.python:
                raise ValueError('unsupported_repository_validation_program')
            path = PurePosixPath(command[1])
            if not path.is_absolute() or str(path) != command[1]:
                raise ValueError('repository_program_path_required')
            try:
                program = relative(path.relative_to(self.label).as_posix())
            except ValueError:
                raise ValueError('repository_program_outside_input') from None
            if program not in self.programs:
                raise ValueError('unregistered_repository_product_program')
            arguments = tuple(command[2:])
            if program != 'scripts/verify_evidence_attestation.py' and arguments:
                raise ValueError('unsupported_repository_program_arguments')
            if program == 'scripts/verify_evidence_attestation.py' and arguments != (
                    self.label + '/docs/examples/evidence-attestation.example.json', '--output',
                    self.label + '/generated/reports/evidence-attestation-pilot.json', '--evaluated-at',
                    '2026-07-17T10:01:00Z'):
                raise ValueError('unsupported_repository_attestation_arguments')
            request = {'kind': 'product-function', 'program': program, 'arguments': list(arguments)}
            value = self.operation(request, lambda: self.outcome(self.programs[program](arguments)))
        return SimpleNamespace(**value)

    def verify_release_integrity(self, root, policy):
        if str(root) != self.label or str(policy) != self.label + '/model/governance/release-signing-policy.yaml':
            raise ValueError('repository_release_scope_differs')
        return self.operation({'kind': 'native-port', 'operation': 'release-integrity'}, lambda: self.release(root, policy))
