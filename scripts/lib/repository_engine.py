"""Complete original repository decisions over a closed inert captured view.

Native and legacy-capture ports must be chosen by the product composition.
Missing ports never become successful placeholder checks. This engine grants
no operating authority and does not write back to the inspected repository.
"""
import io
import json

from lib import dcr_operations
from lib.repository_dataset import RepositoryDataset
from lib.repository_execution import PROGRAMS, RepositoryExecution
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.repository_provenance_validation import RepositoryProvenanceValidation
from lib.repository_report_data import RepositoryReportData
from lib.repository_report_operations import RepositoryReportOperations
from lib.repository_schemas import RepositorySchemas
from lib.repository_snapshot_validation import RepositorySnapshotValidation
from lib.repository_validation import RepositoryValidation
from lib.release_verification import ReleaseVerification


class RepositoryReleaseBridge:
    def __init__(self, dataset, port):
        if (str(port.root) != str(dataset.root) or not callable(getattr(port, 'run', None))
                or not callable(getattr(port, 'temporary_file', None))):
            raise ValueError('repository_release_native_scope_required')
        self.root, self.port = dataset.root, port

    def temporary_file(self, *args, **options):
        return self.port.temporary_file(*args, **options)

    def run(self, command, **options):
        if options.get('cwd') is not None:
            if str(options['cwd']) != str(self.root):
                raise ValueError('repository_release_native_cwd_differs')
            options['cwd'] = self.port.root
        return self.port.run(command, **options)


class RepositoryEngine:
    def __init__(self, manifest, files, commit, *, capture_adapter_factory, schema_identifier_bases,
                 source_configuration_profile, clock, verify_attestation, release_port, opa_port, append_event):
        if not all(callable(value) for value in (capture_adapter_factory, clock, verify_attestation, append_event)):
            raise ValueError('explicit_repository_engine_ports_required')
        if opa_port is not None and not callable(getattr(opa_port, 'check', None)):
            raise ValueError('repository_opa_check_port_required')
        self.append_event, self.opa_port = append_event, opa_port
        self.executed = False
        self.dataset = RepositoryDataset(manifest, files, commit,
            append_effect=lambda row: append_event({'kind': 'dataset-effect', **row}))
        root = self.dataset.root
        self.schemas = RepositorySchemas(root, identifier_bases=schema_identifier_bases)
        self.lifecycle = RepositoryLifecycle(root, validator_class=self.schemas,
            path_factory=self.dataset.namespace.path, provider_factory=capture_adapter_factory)
        self.provenance = RepositoryProvenanceValidation(root, validator_class=self.schemas)
        snapshots = RepositorySnapshotValidation(root, validator_class=self.schemas)
        release = ReleaseVerification(RepositoryReleaseBridge(self.dataset, release_port))
        self.reports = RepositoryReportOperations(root, self.dataset.membership(),
            mkdir=self.dataset.mkdir, write=self.dataset.write, clock=clock,
            source_configuration_profile=source_configuration_profile, verify_attestation=verify_attestation,
            invoke=self.invoke, data_factory=lambda raw_yaml: RepositoryReportData(self.dataset, raw_yaml=raw_yaml))
        programs = {name: (lambda args, selected=name: self.reports.run(selected, args)) for name in PROGRAMS}
        programs.update({
            'scripts/validate_governance_lifecycle_contracts.py': lambda _: self.lifecycle.validate_examples(),
            'scripts/validate_governance_lifecycle_ledger.py': self.default_ledger,
            'scripts/validate_evidence_agent_provenance.py': lambda _: self.provenance.run(),
            'scripts/validate_document_consistency_review_operations.py': self.dcr})
        self.environment = RepositoryExecution(root, validator_class=self.schemas, programs=programs,
            snapshots=snapshots, verify_release_integrity=release.verify_release_integrity,
            opa_check=None if opa_port is None else self.opa_check, append_event=append_event)

    def invoke(self, program, arguments):
        result = self.environment.run(['python', str(self.dataset.root / program), *arguments], cwd=self.dataset.root)
        return {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}

    def default_ledger(self, arguments):
        output = io.StringIO()
        self.lifecycle.validate_default_ledger(print_line=lambda line: print(line, file=output))
        return {'returncode': 0, 'stdout': output.getvalue(), 'stderr': ''}

    def dcr(self, arguments):
        value = dcr_operations.validate(self.dataset.root, validator_class=self.schemas)
        return {'returncode': 0, 'stdout': json.dumps(value, sort_keys=True) + '\n', 'stderr': ''}

    def opa_check(self):
        selected = {name: raw for name, raw in self.dataset.files.items() if name.startswith('policies/opa/')}
        result = self.opa_port.check(selected, directory_present='policies/opa' in self.dataset.directories)
        return {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}

    def execute(self):
        if self.executed:
            raise ValueError('repository_engine_already_executed')
        self.executed = True
        error_type = None
        try:
            code = RepositoryValidation(self.environment).main()
        except Exception as error:
            # The original child traceback cannot be manufactured from a new
            # in-process stack. Preserve this as incomplete until that original
            # exception/child-process behavior has a complete explicit profile.
            error_type, code = type(error).__name__, 2
        return {'execution': 'complete' if error_type is None else 'incomplete',
                'exception_type': error_type, 'exit_code': code,
                'stdout': self.environment.stdout.getvalue(), 'stderr': self.environment.stderr.getvalue()}
