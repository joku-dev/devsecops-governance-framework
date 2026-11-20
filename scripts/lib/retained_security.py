"""Whole retained security/release reconstruction without native effects or IO.

Bindings are caller-checked declarations, never authenticated producer identity.
The same reconstruction is used by local operation inspection and composition.
"""
from copy import deepcopy
import errno
import hashlib
from pathlib import PurePosixPath

from lib.portable.contracts import canonical_digest
from lib.provider_ports import SecurityCollector, ReplaySecurityAPI, SELF_SECURITY_PROFILE, security_request_paths
from lib.release_replay import ReplayReleaseEnvironment
from lib.release_verification import ReleaseVerification
from lib.repository_paths import RepositoryPaths
from lib.result_snapshot_store import explicit_time
from lib.validation_application import AUTHORITY


class InertReleaseInputs:
    """Only the path operations used by the unchanged release decisions."""
    def __init__(self, files):
        self.files = files
        self.directories = {''} | {str(p) for name in files for p in PurePosixPath(name).parents if str(p) != '.'}

    def stat(self, name):
        if name in self.files:
            return {'kind': 'file', 'bytes': len(self.files[name]), 'mode': 0o100600}
        if name in self.directories:
            return {'kind': 'directory', 'bytes': 0, 'mode': 0o40700}
        return None

    def read(self, name):
        if name not in self.files:
            raise FileNotFoundError(errno.ENOENT, 'No such file or directory', name)
        return self.files[name]


class InertReleaseEnvironment:
    def __init__(self, label, files, replay):
        self.root = RepositoryPaths(label, InertReleaseInputs(files)).root
        self.replay = replay

    def temporary_file(self, *args, **options):
        return self.replay.temporary_file(*args, **options)

    def run(self, command, **options):
        if options.get('cwd') is not None:
            if str(options['cwd']) != str(self.root):
                raise ValueError('retained_release_cwd_changed')
            options['cwd'] = self.replay.root
        return self.replay.run(command, **options)


def equivalent(actual, expected, message):
    if canonical_digest(actual) != canonical_digest(expected):
        raise ValueError(message)


def release(tree, binding, operation):
    from lib.release_validation_application import PENDING_FIELDS, START_FIELDS, KIND, MAX_MANIFEST, MAX_REFERENCES, MAX_RECORD, MAX_START, check_manifest
    from lib.result_assessments import identity
    identity(operation)
    pending = tree.json('pending.json', MAX_MANIFEST)
    value = tree.json('assessment.json', MAX_RECORD)
    if (set(pending) != PENDING_FIELDS
            or set(value) != PENDING_FIELDS | {'execution', 'exception_type', 'exit_code', 'report', 'native_context', 'native_observations'}
            or value.get('operation_id') != operation or type(value.get('schema_version')) is not int
            or value['schema_version'] != 1 or value['kind'] != KIND
            or value['source_tree'] != binding['source_tree']):
        raise ValueError('release_record_binding_or_authority_changed')
    equivalent({k: value[k] for k in PENDING_FIELDS}, pending, 'release_record_binding_or_authority_changed')
    equivalent({k: value.get(k) for k in {*binding, *AUTHORITY}}, {**binding, **AUTHORITY}, 'release_record_binding_or_authority_changed')
    equivalent(tree.json('native-results.json', MAX_RECORD), value, 'release_native_result_journal_changed')
    if tree.children() != {'inputs', 'input-manifest.json', 'references.json', 'pending.json', 'starts', 'native-work', 'native-results.json', 'assessment.json'}:
        raise ValueError('release_operation_members_changed')
    if 'native-work' not in tree.directories or tree.children('native-work'):
        raise ValueError('release_native_workarea_not_clean')
    explicit_time(value['assessed_at'])
    manifest = tree.json('input-manifest.json', MAX_MANIFEST)
    references = tree.json('references.json', MAX_REFERENCES)
    if not isinstance(manifest.get('files'), dict):
        raise ValueError('invalid_release_input_manifest')
    data = tree.inputs('inputs', manifest['files'])
    check_manifest(manifest, data, references, revision=binding['source_revision'], tree=binding['source_tree'])
    if value['input_id'] != canonical_digest(manifest) or value['source_root'] != manifest['source_root']:
        raise ValueError('release_input_binding_changed')
    if (value['execution'] != 'complete' or value['exception_type'] is not None
            or type(value['exit_code']) is not int or value['exit_code'] != 0):
        raise ValueError('release_incomplete_execution_cannot_replay')
    rows = value['native_observations']
    if not isinstance(rows, list) or len(rows) > 16384:
        raise ValueError('release_native_observation_budget')
    if 'starts' not in tree.directories or tree.children('starts') != {f'{i:05}.json' for i in range(1, len(rows) + 1)}:
        raise ValueError('release_start_journal_members_changed')
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or not START_FIELDS <= set(row):
            raise ValueError('release_start_observation_missing')
        start = {key: deepcopy(row[key]) for key in START_FIELDS}
        start.update(returncode=None, timed_out=False, output_truncated=False, error_type=None)
        expected = {'operation_id': operation, 'input_id': value['input_id'], 'sequence': index, 'observation': start}
        equivalent(tree.json(f'starts/{index:05}.json', MAX_START), expected, 'release_start_journal_changed')
    replay = ReplayReleaseEnvironment(tree.path('inputs'), data, references, value['native_context'], rows, label_only=True)
    report = ReleaseVerification(InertReleaseEnvironment(tree.path('inputs'), data, replay)).verify_release_integrity()
    replay.finish()
    equivalent(report, value['report'], 'release_report_replay_changed')
    return deepcopy(value), report


def security(tree, binding, operation, release_inspector):
    from lib.self_security_application import PENDING, OUTCOME, KIND, MAX_RECORD, FILES, render
    from lib.result_assessments import identity
    identity(operation)
    value = tree.json('assessment.json', MAX_RECORD)
    pending = tree.json('pending.json', 4 * 1024**2)
    if (set(pending) != PENDING or set(value) != PENDING | OUTCOME
            or value['operation_id'] != operation or value['kind'] != KIND
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['profile'] != SELF_SECURITY_PROFILE or type(value['provided_observation']) is not bool
            or type(value['fail_on_findings']) is not bool or type(value['exit_code']) is not int
            or value['execution'] != 'complete' or value['exception_type'] is not None):
        raise ValueError('security_binding_or_execution_changed')
    equivalent({k: value[k] for k in PENDING}, pending, 'security_binding_or_execution_changed')
    equivalent({k: value.get(k) for k in {*binding, *AUTHORITY}}, {**binding, **AUTHORITY}, 'security_binding_or_execution_changed')
    equivalent(tree.json('native-results.json', MAX_RECORD), value, 'security_result_journal_changed')
    if tree.children() != {'inputs', 'requests', 'responses', 'pending.json', 'outputs', 'native-results.json', 'assessment.json'}:
        raise ValueError('security_operation_members_changed')
    inputs = tree.inputs('inputs', value['input_files'])
    expected_directories = {str(parent) for name in inputs for parent in PurePosixPath(name).parents if str(parent) != '.'}
    if not value['provided_observation']:
        expected_directories.add('source')
    if tree.child_directories('inputs') != expected_directories:
        raise ValueError('security_input_directory_members_changed')
    if hashlib.sha256(inputs['model.yaml']).hexdigest() != value['model_sha256']:
        raise ValueError('security_model_changed')
    provided = value['provided_observation']
    request_paths = [] if provided else security_request_paths(value['repository'])
    for name in ('requests', 'responses'):
        if name not in tree.directories or tree.children(name) != {f'{i:02}.json' for i in range(1, len(request_paths) + 1)}:
            raise ValueError('security_request_journal_members_changed')
    if provided:
        if (set(inputs) != {'model.yaml', 'observation.json'} or value['native_responses'] != []
                or value['release_assessment'] is not None or value['source_root'] is not None
                or value['resolved_observed_at'] is not None):
            raise ValueError('provided_security_observation_scope_changed')
        import json
        observation = json.loads(inputs['observation.json'].decode('utf-8'))
    else:
        if (not isinstance(value['source_root'], str) or not PurePosixPath(value['source_root']).is_absolute()
                or not isinstance(value['resolved_observed_at'], str)
                or set(inputs) - {'model.yaml'} != {n for n in inputs if n.startswith('source/.github/')}):
            raise ValueError('security_native_scope_changed')
        if not isinstance(value['native_responses'], list) or len(value['native_responses']) != 7:
            raise ValueError('security_native_response_count')
        for index, path in enumerate(request_paths, 1):
            equivalent(tree.json(f'requests/{index:02}.json'), {'sequence': index, 'method': 'GET', 'path': path}, 'security_request_journal_changed')
            equivalent(tree.json(f'responses/{index:02}.json', 5 * 1024**2), value['native_responses'][index - 1], 'security_request_journal_changed')
        release_value, release_report = release_inspector(value['release_assessment'])
        if release_value['source_root'] != value['source_root']:
            raise ValueError('security_release_scope_changed')
        api = ReplaySecurityAPI(value['repository'], value['native_responses'])
        source = {name.removeprefix('source/'): raw for name, raw in inputs.items() if name.startswith('source/')}
        observation = SecurityCollector(tree.path('inputs/source'), api, release_report, inert_files=source).collect_live(value['repository'], value['resolved_observed_at'])
        api.finish()
    files, code = render(inputs['model.yaml'], observation, value['fail_on_findings'])
    if set(files) != set(FILES) or code != value['exit_code'] or tree.inputs('outputs', value['output_files']) != files:
        raise ValueError('security_complete_report_replay_changed')
    return deepcopy(value), files
