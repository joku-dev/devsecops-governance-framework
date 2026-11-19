"""Concrete whole-compliance environment on one complete owned product source.

Only admitted current own programs execute. The inspected consumer is data.
The parent application must supervise this environment in its fixed own worker;
it is not a server-side generic command dispatcher or an execution attestation.
"""
from copy import deepcopy
import hashlib
import importlib.util
import importlib.metadata
import io
import json
import os
import platform
from pathlib import Path
import re
import shutil
import sys
from types import SimpleNamespace

import control_evaluation as controls
from lib.ci_bundle_storage import reserve
from lib.compliance_operation import legacy_timestamp
from lib.functional_parity import git_read
from lib.local_source_application import LocalSourceInspectionContext
from lib.portable.contracts import ROOT
from lib.provider_ports import local_source_profile
from lib.repository_application import RepositoryContext
from lib.result_bytes import safe_bytes
from lib.result_snapshot_store import explicit_time
from lib.source_inspection_application import INTEGRATION
from lib.runtime_package import admit
from lib.providers.attestation_verification import executable
from lib.providers.compliance_opa import ComplianceOPA, MAX_INPUT
from lib.providers.product_test_worker import retain_package

OWN_MODULE = 'scripts/lib/providers/compliance_native.py'
CONTROLLER = 'tests/integration/run_product_unit_tests.py'


class NativeComplianceEnvironment:
    def __init__(self, *, instance_root, package, package_pin, workarea,
                 at, output_file, cwd, target_repo=None, input_file=None, on_event):
        from lib.v2_application import instance
        self.revision = git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()
        if git_read(ROOT, 'show', self.revision + ':' + OWN_MODULE) != Path(__file__).read_bytes():
            raise ValueError('committed_complete_compliance_environment_required')
        self.instance, self.settings = instance(instance_root)
        if self.settings['development']:
            raise ValueError('installed_committed_compliance_runtime_required')
        explicit_time(at); self.at = at
        if not callable(on_event):
            raise ValueError('complete_compliance_native_journal_required')
        self.on_event = on_event
        self.area = Path(workarea)
        if (not self.area.is_absolute() or self.area.exists() or self.area.is_symlink()
                or any(p.is_symlink() for p in self.area.parents)):
            raise ValueError('fresh_owned_compliance_workarea_required')
        self.area.mkdir(mode=0o700)
        reserve(self.area, 8 * 1024**3)
        self.package = retain_package(package, package_pin, self.area / 'input.zip')
        self.manifest = admit(self.area / 'input.zip', package_pin, self.area / 'admitted')
        self.root = self.area / 'admitted/source'
        if (self.manifest['source_commit'] != self.revision
                or self.manifest['source_tree'] != git_read(ROOT, 'rev-parse', 'HEAD^{tree}').decode().strip()
                or not self.manifest['prepared_dependencies'] or self.manifest['opa'] is None
                or self.manifest['target'] != {'system': platform.system(), 'machine': platform.machine()}):
            raise ValueError('exact_current_prepared_compliance_package_required')
        self.root.chmod(0o700)
        for name, version in re.findall(r'^([A-Za-z0-9_.-]+)==([^\s;]+)',
                (self.root / 'requirements-source-document-intake.lock').read_text(), re.M):
            if importlib.metadata.version(name) != version:
                raise ValueError('pinned_complete_compliance_dependency_required')
        # Loading this fixed current own engineering helper is distinct from
        # loading caller/consumer code. Its complete archive was just admitted.
        helper = self.root / CONTROLLER
        if helper.read_bytes() != git_read(ROOT, 'show', self.revision + ':' + CONTROLLER):
            raise ValueError('complete_compliance_controller_binding_changed')
        spec = importlib.util.spec_from_file_location('axiom_complete_compliance_own_controller', helper)
        self.controller = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.controller)
        self.effects = sys.modules[self.controller.retain_effects.__module__]
        self.before = self.controller.source_files(self.root, self.manifest)
        self.expected = deepcopy(self.before)
        self.generated_baseline = {name: (self.root / name).read_bytes()
            for name in self.before if name.startswith('generated/')}
        self.generated_before = {name: (self.root / name).read_bytes()
            for name in self.effects.GENERATED if name in self.before}
        self.example_sha = self.before['docs/examples/evidence-attestation.example.json']['sha256']
        self.tools = {}; tools = self.area / 'tools'; tools.mkdir(mode=0o700)
        for name in ('git', 'node', 'openssl'):
            found = shutil.which(name)
            if found is None:
                raise ValueError('complete_compliance_tool_missing')
            path, sha = executable(found); self.tools[name] = {'path': path, 'sha256': sha}
            (tools / name).symlink_to(path)
        opa = self.area / 'admitted/opa'
        path, sha = executable(opa)
        if sha != self.manifest['opa']['sha256']:
            raise ValueError('complete_compliance_prepared_opa_changed')
        self.tools['opa'] = {'path': path, 'sha256': sha}; (tools / 'opa').symlink_to(path)
        path, sha = executable(Path(sys.prefix) / 'bin/opa')
        if sha != self.manifest['opa']['sha256']:
            raise ValueError('complete_compliance_environment_opa_required')
        self.tools['environment-opa'] = {'path': path, 'sha256': sha}
        path, sha = executable(sys.executable)
        self.tools['python'] = {'path': path, 'sha256': sha}
        temporary = self.area / 'tmp'; temporary.mkdir(mode=0o700)
        self.environment = {'PATH': os.pathsep.join([str(tools), str(Path(sys.executable).parent), '/usr/bin', '/bin']),
            'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
            'PIP_NO_INDEX': '1', 'PIP_FIND_LINKS': str(self.area / 'admitted/wheels'),
            'VALIDATION_VENV': sys.prefix, 'TMPDIR': str(temporary),
            'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_COUNT': '0',
            'GIT_TERMINAL_PROMPT': '0', 'GIT_ASKPASS': '/bin/false'}
        self.native = self.area / 'native'; self.native.mkdir(mode=0o700)
        # Reference preparation requires a clean clone; do it before the
        # original validator's generated effects, never by discarding them.
        self.references = self.controller.prepare(self.root, self.revision,
            self.root / 'tests/fixtures/product-test-reference-inputs', self.area / 'reference-inputs')
        self.on_event({'kind': 'compliance-preflight', 'phase': 'intent'})
        self.preflight = self.controller.run_command('preflight', self.root, self.environment, self.native, timeout=120)
        self.on_event({'kind': 'compliance-preflight', 'phase': 'finished', 'outcome': deepcopy(self.preflight)})
        if self.preflight['returncode']:
            raise ValueError('complete_compliance_toolchain_preflight_failed')
        self.cwd = Path(cwd)
        if not self.cwd.is_absolute():
            raise ValueError('absolute_compliance_cwd_required')
        target = Path(self.root if target_repo is None else target_repo)
        self.target = self.resolve(target)
        if self.instance.is_relative_to(self.target):
            raise ValueError('compliance_instance_must_be_outside_inspected_source')
        self.input_label = self.resolve(Path(self.root / 'policies/example-input.release-candidate.json'
                                if input_file is None else input_file))
        self.input_bytes = None
        self.input_error = None
        self.input_observed = False
        self.input_snapshot = self.area / 'control-input.json'
        self.output = Path(output_file)
        if not self.output.is_absolute():
            self.output = self.cwd / self.output
        self.exports = {self.output, self.output.with_name('control-evaluation-report.json'),
                        self.output.with_name('control-evaluation-report.md')}
        self.opa = None
        self.stdout = io.StringIO()
        self.suboperations = []
        self.unit_outcome = None
        self.unit_statistics = None
        self.projection = None
        self.projection_bytes = None
        self.write_effects = []

    def assert_current(self):
        from lib.v2_application import instance
        path, value = instance(self.instance)
        if path != self.instance or value != self.settings:
            raise ValueError('complete_compliance_instance_changed')

    def checkpoint(self, *, allow_generated_metadata=False):
        self.assert_current()
        if (git_read(self.root, 'rev-parse', 'HEAD').decode().strip() != self.revision
                or git_read(self.root, 'rev-parse', 'HEAD^{tree}').decode().strip() != self.manifest['source_tree']):
            raise ValueError('complete_compliance_own_source_revision_changed')
        members = [p for p in self.root.rglob('*') if p.relative_to(self.root).parts[0] != '.git']
        if any(p.is_symlink() for p in members):
            raise ValueError('complete_compliance_own_source_symlink')
        physical = {p.relative_to(self.root).as_posix() for p in members if p.is_file()}
        additions = physical - set(self.expected)
        if additions - self.effects.GENERATED_ADDITIONS:
            raise ValueError('unknown_complete_compliance_source_addition')
        if additions:
            if self.projection_bytes is None:
                raise ValueError('complete_compliance_viewer_output_not_verified')
            for name in additions:
                if safe_bytes(self.root / name, limit=8*1024**2) != self.projection_bytes:
                    raise ValueError('complete_compliance_viewer_output_changed')
        if physical != set(self.expected) | additions:
            raise ValueError('complete_compliance_source_membership_changed')
        after = {}
        for name, row in self.expected.items():
            path = self.root / name
            if not path.is_file() or ('100755' if path.stat().st_mode & 0o111 else '100644') != row['mode']:
                raise ValueError('complete_compliance_source_file_or_mode_changed')
            raw = safe_bytes(path, limit=16*1024**2)
            sha = hashlib.sha256(raw).hexdigest()
            if sha != row['sha256'] or len(raw) != row['bytes']:
                if name == 'generated/viewer/app/data.json' and self.projection_bytes is not None:
                    if raw != self.projection_bytes:
                        raise ValueError('complete_compliance_viewer_output_changed')
                else:
                    if not allow_generated_metadata:
                        raise ValueError('complete_compliance_source_changed_outside_own_phase')
                    self.effects.checked_change(name, self.generated_baseline.get(name), raw, self.root, self.example_sha)
            after[name] = {'sha256': sha, 'bytes': len(raw), 'mode': row['mode']}
        for row in self.tools.values():
            if executable(row['path']) != (row['path'], row['sha256']):
                raise ValueError('complete_compliance_tool_changed')
        return after

    def resolve(self, path):
        return (path if path.is_absolute() else self.cwd / path).resolve()

    def run(self, command):
        self.checkpoint()
        if command == ['python3', str(self.root / 'scripts/check_repo_governance_integration.py'),
                       '--target-repo', str(self.target)]:
            return self.integration()
        if command == ['python3', str(self.root / 'scripts/validate_governance_repo.py')]:
            return self.repository()
        if command == ['python3', '-m', 'unittest', 'discover', '-s', 'tests']:
            return self.unit_tests()
        if self.opa is None:
            self.observe_input()
            self.opa = ComplianceOPA(tool=self.tools['opa']['path'], source_revision=self.revision,
                display_root=self.root, input_label=self.input_label, input_bytes=self.input_bytes,
                workarea=self.area / 'opa', on_event=self.on_event)
        return self.opa.run(command)

    def observe_input(self):
        if self.input_observed:
            return
        self.input_observed = True
        try:
            self.input_bytes = safe_bytes(self.input_label, limit=MAX_INPUT)
        except (FileNotFoundError, PermissionError, IsADirectoryError) as error:
            self.input_error = error
        if self.input_error is None:
            self.input_snapshot.write_bytes(self.input_bytes); self.input_snapshot.chmod(0o600)
        self.on_event({'kind': 'compliance-frozen-control-input', 'input_label': str(self.input_label),
            'bytes': None if self.input_bytes is None else len(self.input_bytes),
            'sha256': None if self.input_bytes is None else hashlib.sha256(self.input_bytes).hexdigest(),
            'error_type': None if self.input_error is None else type(self.input_error).__name__})

    def integration(self):
        context = LocalSourceInspectionContext(self.instance, self.settings)
        identifier, value = context.create('integration', self.target, None,
            local_source_profile('legacy-worktree-signatures-v1'), self.at)
        context.inspect(identifier)
        row = {'kind': 'integration', 'assessment_id': identifier, 'execution': 'complete',
               'original_finding_exit': context.legacy_exit(identifier)}
        self.suboperations.append(row); self.on_event({'kind': 'compliance-suboperation', 'observation': row})
        raw = safe_bytes(context.artifacts / identifier / Path(INTEGRATION).name, limit=8*1024**2)
        return SimpleNamespace(returncode=row['original_finding_exit'], stdout=raw.decode(), stderr='')

    def repository(self):
        context = RepositoryContext(self.instance, self.settings)
        identifier, value = context.create(self.at, engine_profile='legacy-repository-validator-v1', source_worktree=self.root)
        loaded = context.load(identifier)
        self.checkpoint()
        before, after = loaded['inputs'], loaded['outputs']
        if (set(before) != set(self.expected) or not set(before) <= set(after)
                or any(not name.startswith('generated/') for name in set(after)-set(before))):
            raise ValueError('complete_compliance_repository_source_set_changed')
        for name, old in before.items():
            if safe_bytes(self.root / name, limit=16*1024**2) != old:
                raise ValueError('complete_compliance_repository_capture_differs')
            if old != after[name] and not name.startswith('generated/'):
                raise ValueError('complete_compliance_repository_program_or_input_changed')
        inspected = context.inspect(identifier, bounded_worker=True)
        if (value['outcome']['execution'] == 'complete'
                and inspected['state'] != 'retained_declared_replay_consistent'):
            raise ValueError('complete_compliance_repository_replay_differs')
        # This is an exact recorded own-engine overlay, including actual failed
        # generator outcomes. It is not a general generated-file exemption.
        # Subsequent unit changes are checked against this precise new baseline.
        for name, raw in after.items():
            old = before.get(name)
            if old != raw:
                self.on_event({'kind': 'compliance-own-source-write', 'path': name,
                    'repository_assessment': identifier, 'repository_replay_state': inspected['state'],
                    'before_sha256': None if old is None else hashlib.sha256(old).hexdigest(),
                    'after_sha256': hashlib.sha256(raw).hexdigest()})
                path = self.root / name
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                path.write_bytes(raw)
                if old is None:
                    path.chmod(0o600)
            mode = self.expected[name]['mode'] if name in self.expected else '100644'
            self.expected[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'mode': mode}
            if name.startswith('generated/'):
                self.generated_baseline[name] = raw
        self.checkpoint()
        row = {'kind': 'repository', 'assessment_id': identifier, 'execution': value['outcome']['execution'],
               'original_finding_exit': value['outcome']['exit_code'],
               'replay_state': inspected['state']}
        self.suboperations.append(row); self.on_event({'kind': 'compliance-suboperation', 'observation': row})
        return SimpleNamespace(returncode=value['outcome']['exit_code'],
            stdout=value['outcome']['stdout'], stderr=value['outcome']['stderr'])

    def unit_tests(self):
        if self.unit_outcome is not None:
            raise ValueError('complete_compliance_unit_phase_reused')
        self.on_event({'kind': 'compliance-own-unit-tests', 'phase': 'intent',
            'source_revision': self.revision, 'full_fixed_discovery': True})
        unit_before = {name: (self.root / name).read_bytes()
            for name in self.effects.GENERATED if name in self.expected}
        self.unit_outcome = self.controller.run_command('unit-tests', self.root, self.environment, self.native)
        raw = safe_bytes(self.native / 'unit-tests-stderr.bin', limit=8*1024**2)
        matches = list(re.finditer(rb'^Ran ([0-9]+) tests? in ([0-9.]+)s\s*$', raw, re.M))
        if not matches or self.unit_outcome['returncode'] not in (0, 1):
            raise ValueError('complete_compliance_whole_unit_outcome_required')
        summary = re.search(rb'^(OK(?: \(skipped=([0-9]+)\))?|FAILED \([^\n]+\))$', raw[matches[-1].end():], re.M)
        if not summary or (self.unit_outcome['returncode'] == 0) != summary[1].startswith(b'OK'):
            raise ValueError('complete_compliance_whole_unit_summary_differs')
        skipped = re.search(rb'skipped=([0-9]+)', summary[1])
        self.unit_statistics = {'tests_run': int(matches[-1][1]), 'seconds': float(matches[-1][2]),
            'skipped': int(skipped[1]) if skipped else 0}
        if self.unit_statistics['tests_run'] <= 0:
            raise ValueError('complete_compliance_whole_unit_outcome_required')
        if (self.root / 'generated/viewer/app/data.json').exists():
            self.projection = self.controller.run_command('viewer-projection', self.root, self.environment, self.native, timeout=120)
            if self.projection['returncode']:
                raise ValueError('complete_compliance_viewer_projection_incomplete')
            self.projection_bytes = safe_bytes(self.native / 'viewer-projection-stdout.bin', limit=8*1024**2)
        after = self.checkpoint(allow_generated_metadata=True)
        metadata = self.effects.retain_effects(self.root, unit_before,
            self.area / 'unit-generated-effects', self.example_sha)
        additions = {'generated/viewer/app/data.json'} if self.projection_bytes is not None else set()
        artifacts = self.effects.retain_additions(self.root, additions, self.projection_bytes,
            self.area / 'unit-generated-artifacts')
        for name, row in after.items():
            self.expected[name] = row
            if name.startswith('generated/'):
                self.generated_baseline[name] = (self.root / name).read_bytes()
        for row in artifacts:
            path = self.root / row['path']
            if path.stat().st_mode & 0o111:
                raise ValueError('ordinary_complete_compliance_viewer_data_required')
            self.expected[row['path']] = {'sha256': row['sha256'], 'bytes': row['bytes'], 'mode': '100644'}
            self.generated_baseline[row['path']] = path.read_bytes()
        self.checkpoint()
        self.on_event({'kind': 'compliance-own-unit-tests', 'phase': 'finished',
            'native_outcome': deepcopy(self.unit_outcome), 'statistics': deepcopy(self.unit_statistics),
            'metadata_effects': metadata, 'generated_artifacts': artifacts,
            'final_source_files': deepcopy(self.expected)})
        return SimpleNamespace(returncode=self.unit_outcome['returncode'],
            stdout=safe_bytes(self.native / 'unit-tests-stdout.bin', limit=8*1024**2).decode(), stderr=raw.decode())

    def control_report(self, path):
        if path != self.input_label or self.opa is None:
            raise ValueError('complete_compliance_control_input_or_phase_changed')
        self.checkpoint()
        if self.input_error is not None:
            raise self.input_error
        def native(command):
            expected = ['opa', 'eval', '-f', 'json', '-d', str(controls.ROOT / 'policies/opa'), '-i', str(self.input_snapshot)]
            if command[:-1] != expected:
                raise ValueError('complete_compliance_control_native_mapping_changed')
            logical = ['opa', 'eval', '-f', 'json', '-d', str(self.root / 'policies/opa'), '-i', str(self.input_label), command[-1]]
            self.on_event({'kind': 'compliance-control-native-path-binding',
                'calculation_command': command, 'logical_command': logical})
            return self.opa.run(logical)
        report = controls.generate_control_evaluation_report(self.input_snapshot, native_run=native)
        report['input_file'] = str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path)
        return report

    def control_markdown(self, report):
        return controls.render_control_evaluation_markdown(report)

    def write(self, path, text):
        resolved = path.resolve()
        if (path not in self.exports or resolved.is_relative_to(ROOT.resolve()) or resolved.is_relative_to(self.instance)
                or any(p.is_symlink() for p in (path, *path.parents))
                or path.is_file() and path.stat().st_nlink != 1
                or path.exists() and not (path.is_file() or path.is_dir())):
            raise ValueError('complete_compliance_explicit_export_scope_required')
        # Retain both sides even when the original write raises after truncation
        # or partial output. Do not roll back an original observable effect.
        index = len(self.write_effects)+1
        def capture(phase):
            if path.is_symlink():
                raise ValueError('complete_compliance_export_changed_to_symlink')
            if not path.exists():
                return {'kind': 'missing'}
            if path.is_dir():
                return {'kind': 'directory'}
            raw = safe_bytes(path, limit=16*1024**2)
            retained = self.area / ('export-effect-'+str(index)+'-'+phase+'.bin')
            retained.write_bytes(raw); retained.chmod(0o600)
            return {'kind': 'file', 'retained': retained.name, 'bytes': len(raw),
                    'sha256': hashlib.sha256(raw).hexdigest()}
        row = {'path': str(path), 'before': capture('before')}
        try:
            path.write_text(text, encoding='utf-8')
        except Exception as error:
            row.update(outcome='raised', error_type=type(error).__name__, after=capture('after'))
            self.write_effects.append(row)
            raise
        row.update(outcome='returned', error_type=None, after=capture('after'))
        self.write_effects.append(row)
        raw = safe_bytes(self.area / row['after']['retained'], limit=16*1024**2)
        if raw != text.encode():
            raise ValueError('complete_compliance_export_bytes_changed')

    def exists(self, path):
        if path not in self.exports and not path.is_relative_to(self.root):
            raise ValueError('complete_compliance_artifact_scope_changed')
        return path.exists()

    def timestamp(self):
        return legacy_timestamp(self.at)

    def print(self, text):
        print(text, file=self.stdout)
