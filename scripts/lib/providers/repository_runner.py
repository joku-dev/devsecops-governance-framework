"""Trusted finite native composition for a private whole repository operation.

The caller must admit its node/runtime and supply exact source bindings before
calling this function. This module never loads programs from the source it
inspects and never activates operating, release, consent or publisher state.
"""
import base64
from copy import deepcopy
from pathlib import Path
import tempfile

from lib import repository_operation as contract
from lib.providers.repository_operations import RepositoryOperation, load_operation
from lib.providers.repository_git import RepositoryGit
from lib.providers.repository_source import RepositorySource
from lib.providers.repository_opa import RepositoryOPA
from lib.providers.release_references import ReleaseReferences
from lib.providers.release_verification import ReleaseVerificationEnvironment
from lib.providers.attestation_verification import verify, outcome, executable
from lib.repository_replay import crypto_input


def execute_repository_operation(root, header, *, source, git_tool, opa_tool, approved_opa_hashes,
                                 clock, engine_options, assert_current):
    from lib.repository_engine import RepositoryEngine
    contract.binding(header)
    if Path(source).is_symlink() or Path(root).is_symlink():
        raise ValueError('ordinary_repository_operation_paths_required')
    source, root = Path(source).resolve(strict=True), Path(root).resolve(strict=True)
    if (str(source) != header['source_root'] or root.is_relative_to(source)
            or not callable(clock) or not callable(assert_current)
            or type(engine_options) is not dict or set(engine_options) != {
                'capture_adapter_factory', 'schema_identifier_bases', 'source_configuration_profile'}):
        raise ValueError('explicit_repository_operation_composition_required')
    with RepositoryOperation(root, header) as operation:
        assert_current()
        def source_phase(phase):
            return lambda row: operation.append({'kind': 'source-git', 'phase': phase, 'observation': row})
        git = RepositoryGit(source, git_tool, on_intent=source_phase('intent'),
            on_start=source_phase('started'), on_finish=source_phase('finished'))
        manifest, files, commit = RepositorySource(git, header['source_revision'], profile=header['profile']).capture()
        references = ReleaseReferences(source, read=git.read).capture()
        operation.retain_inputs(manifest, files, commit)
        with tempfile.TemporaryDirectory(prefix='.repository-native-', dir=root.parent) as temporary:
            area = Path(temporary)
            def native_phase(port, phase):
                return lambda row: operation.append({'kind': 'native', 'port': port, 'phase': phase, 'observation': row})
            opa = None
            if opa_tool is not None:
                if Path(executable(opa_tool)[0]).is_relative_to(source):
                    raise ValueError('repository_opa_tool_inside_inspected_source')
                opa = RepositoryOPA(opa_tool, approved_hashes=approved_opa_hashes, workarea=area,
                    on_intent=native_phase('opa', 'intent'), on_start=native_phase('opa', 'started'),
                    on_finish=native_phase('opa', 'finished'))
            def crypto(key, statement, signature):
                profile = 'legacy-attestation-pilot-v1'
                operation.append({'kind': 'crypto', 'phase': 'intent', 'profile': profile,
                                  'input': crypto_input(key, statement, signature)})
                row, stdout, stderr = verify(key, statement, signature, area, profile,
                    lambda value: operation.append({'kind': 'crypto', 'phase': 'started', 'observation': value}),
                    forbidden_root=source)
                packet = {'profile': profile, 'input': crypto_input(key, statement, signature), 'observation': row,
                    'stdout_base64': base64.b64encode(stdout).decode('ascii'),
                    'stderr_base64': base64.b64encode(stderr).decode('ascii')}
                operation.append({'kind': 'crypto', 'phase': 'finished', 'packet': packet})
                return outcome(row)
            def observed_clock():
                value = clock()
                operation.append({'kind': 'clock', 'value': value})
                return value
            with ReleaseVerificationEnvironment(source, files, references, area,
                    on_intent=native_phase('release', 'intent'), on_start=native_phase('release', 'started'),
                    on_finish=native_phase('release', 'finished')) as release:
                engine = RepositoryEngine(manifest, files, commit, **engine_options,
                    clock=observed_clock, verify_attestation=crypto, release_port=release, opa_port=opa,
                    append_event=lambda row: operation.append({'kind': 'engine-event', 'event': row}))
                result = engine.execute()
                metadata = deepcopy(release.metadata)
            opa_context = None if opa is None else {'tool_path': opa.tool[0], 'tool_sha256': opa.tool[1], 'workarea': str(area)}
        assert_current()
        operation.finish(result, engine.dataset.files, {'schema_version': 1, 'opa_context': opa_context,
            'release_context': metadata, 'references': references})
    return load_operation(root, header)
