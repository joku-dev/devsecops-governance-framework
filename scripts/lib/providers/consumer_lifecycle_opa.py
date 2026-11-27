"""Pinned original independent OPA query over captured, owned temporary bytes."""
from pathlib import Path, PurePosixPath as P
from copy import deepcopy
import hashlib
import os
import stat
import subprocess
import sys
import platform
import tempfile
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.providers.personal_channel_process import NativeReadProcess
from lib.providers.consumer_lifecycle_tools import approved_external_program
from lib.providers.workbook_import_io import ordinary_ancestors, original_error, failure_value
from lib.providers.synthetic_lifecycle_io import capture_port
from lib.consumer_lifecycle_opa import digest, frame_value, cleanup_value, result_value, STREAM_LIMITS
from lib.synthetic_lifecycle_io import path_spec
from lib.requirement_validation_budget import InputAdmissionError

QUERY = 'data.architecture.operation_readiness.deny'
POLICY_SHA256 = '7fd4dbfeb08aea67600b7e083363cfdff1dc93d2e0d457c90d6ca2b0b1a44fda'


class LegacyConsumerOPAProfile:
    def request(self, command, *, capture_output, check, timeout, source, cwd, owner):
        if (type(command) is not list or len(command) != 8
                or command[:4] != ['opa', 'eval', '--format=json', '--data']
                or command[5] != '--input' or command[7] != QUERY
                or capture_output is not True or check is not True or type(timeout) is not int or timeout != 30):
            raise InputAdmissionError('consumer_original_independent_opa_call_required')
        policy, data = command[4], command[6]
        for path in (policy, data):
            path_spec(path, path, cwd)
        if (P(policy).name != 'policy.rego' or P(data).name != 'input.json' or P(policy).parent != P(data).parent
                or not any(str(P(policy).parent) == session.path and not session.done
                           for session in getattr(owner, 'pilot_temporary_sessions', []))):
            raise InputAdmissionError('consumer_owned_active_opa_temporary_required')
        return {'kind': 'opa-checked-run', 'original_arguments': command, 'source_root': source,
                'cwd': cwd, 'timeout': 30, 'text': False, 'materialization': None}

    def files(self, spec):
        return {'policy.rego': spec['original_arguments'][4], 'input.json': spec['original_arguments'][6]}

    def admit_files(self, files):
        if (set(files) != {'policy.rego', 'input.json'} or any(type(raw) is not bytes or len(raw) > 10 * 1024**2 for raw in files.values())
                or hashlib.sha256(files['policy.rego']).hexdigest() != POLICY_SHA256):
            raise InputAdmissionError('consumer_pinned_policy_and_bounded_input_required')

    def bind(self, spec, frame):
        return {**spec, 'materialization': frame}

    def actual_arguments(self, spec, selected):
        original = spec['original_arguments']; result = [original[0] if selected is None else selected, *original[1:]]
        if spec['materialization'] is not None:
            parent = P(spec['materialization']['path']); result[4] = str(parent / 'policy.rego'); result[6] = str(parent / 'input.json')
        return result


class NativeConsumerOPA(NativePersonalTransport):
    def __init__(self, owner, source, *, tool, approved_hashes, workarea):
        super().__init__(owner, source, LegacyConsumerOPAProfile(), emit_stderr=lambda _: None, stream_limits=STREAM_LIMITS)
        if type(approved_hashes) is not frozenset or not approved_hashes:
            raise InputAdmissionError('consumer_opa_explicit_approved_checksums_required')
        self.tool, self.approved_hashes, self.workarea = str(tool), approved_hashes, str(workarea)
        self.admit_tool()
        self.resources = {}

    def admit_tool(self):
        return approved_external_program(self.tool, self.owner.cwd, self.root,
                                         self.owner.private_state, self.approved_hashes)

    def create(self, files):
        parent = Path(self.workarea); ordinary_ancestors(parent)
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise InputAdmissionError('consumer_opa_private_workarea_required')
        resource = tempfile.TemporaryDirectory(prefix='tmpconsumer-opa-', dir=parent)
        # Guard cleanup explicitly; a lost observation never deletes a later
        # replacement through the resource's implicit finalizer.
        resource._finalizer.detach()
        path = Path(resource.name)
        self.resources[str(path)] = resource
        for name, raw in files.items():
            with (path / name).open('xb') as stream:
                stream.write(raw)
            (path / name).chmod(0o600)
        info = path.lstat()
        return {'path': str(path), 'identity': [info.st_dev, info.st_ino], 'mode': stat.S_IMODE(info.st_mode),
                'files': {name: digest(raw) for name, raw in files.items()}}

    def check_frame(self, frame):
        path = Path(frame['path']); ordinary_ancestors(path)
        info = path.lstat()
        if ([info.st_dev, info.st_ino] != frame['identity'] or stat.S_IMODE(info.st_mode) != 0o700
                or info.st_uid != os.geteuid() or {p.name for p in path.iterdir()} != set(frame['files'])):
            raise InputAdmissionError('consumer_opa_materialized_directory_changed')
        for name, expected in frame['files'].items():
            target = path / name; info = target.lstat()
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) != 0o600 or digest(target.read_bytes()) != expected):
                raise InputAdmissionError('consumer_opa_materialized_bytes_changed')

    def cleanup(self, frame):
        self.check_frame(frame)
        resource = self.resources.pop(frame['path']); resource.cleanup()
        if Path(frame['path']).exists():
            raise InputAdmissionError('consumer_opa_materialized_cleanup_incomplete')
        return {'frame': frame, 'owned_before': True, 'absent_after': True}

    @capture_port
    def run(self, command, *, capture_output, check, timeout):
        spec = self.profile.request(command, capture_output=capture_output, check=check, timeout=timeout,
                                    source=self.root, cwd=self.owner.cwd, owner=self.owner)
        files = {name: self.owner.read(path, path) for name, path in self.profile.files(spec).items()}
        self.profile.admit_files(files)
        frame = None
        if self.owner.mode == 'private-candidate':
            args = {'workarea': self.workarea, 'files': {name: digest(raw) for name, raw in files.items()}}
            try:
                frame = self.owner.perform('consumer-opa-materialization-create', args, lambda: self.create(files))
                frame_value(frame, args)
            except Exception as caught:
                self.owner.record.capture_incomplete = True
                raise InputAdmissionError('consumer_opa_materialization_capture_incomplete') from caught
        spec = self.profile.bind(spec, frame)
        cache = {}
        def store(raw):
            ref = self.owner.blob(raw); cache[ref['sha256']] = raw; return ref
        def effect():
            before = self.context(); identity = self.admit_tool()
            if frame is not None:
                self.check_frame(frame)
            actual = self.profile.actual_arguments(spec, self.tool)
            process = NativeReadProcess(stream_limits=STREAM_LIMITS); code = None; out = err = b''; start = None
            try:
                code, out, err = process.run(actual, spec['cwd'], {'LANG': 'C.UTF-8', 'PATH': ''}, 30)
            except OSError as caught:
                start = failure_value(original_error(caught, 'opa'))
            after = self.context()
            if before != after or self.admit_tool() != identity:
                raise InputAdmissionError('consumer_opa_source_or_tool_changed')
            if frame is not None:
                self.check_frame(frame)
            observe = process.observation
            if observe['stream_budget_exceeded']:
                raise InputAdmissionError('consumer_opa_stream_capture_incomplete')
            error = signal = None
            if observe['timed_out']:
                error = {'type': 'TimeoutExpired', 'message': str(subprocess.TimeoutExpired(command, 30, output=out))}
            elif code:
                error = {'type': 'CalledProcessError', 'message': str(subprocess.CalledProcessError(code, command, output=out))}
                if code < 0:
                    signal = {'implementation': sys.implementation.name, 'version': list(sys.version_info[:3]), 'system': platform.system()}
            return {'schema_version': 1, 'specification': spec, 'actual_arguments': actual, 'program': identity,
                    'source_before': before, 'source_after': after, 'returncode': code, 'stdout': store(out), 'stderr': store(err),
                    'start_error': start, 'original_error': error, 'signal_context': signal, 'effective_encoding': None,
                    'observation': observe}
        try:
            wire = self.owner.perform('consumer-independent-opa-process', spec, effect)
            return result_value(wire, spec, self.profile, lambda ref: cache[ref['sha256']], self.tool, self.approved_hashes)
        finally:
            for name, path in self.profile.files(spec).items():
                if self.owner.read(path, path) != files[name]:
                    raise InputAdmissionError('consumer_opa_original_input_changed')
            if frame is not None:
                try:
                    wire = self.owner.perform('consumer-opa-materialization-cleanup', {'frame': frame}, lambda: self.cleanup(frame))
                    cleanup_value(wire, frame)
                except Exception as caught:
                    self.owner.record.capture_incomplete = True
                    raise InputAdmissionError('consumer_opa_materialization_cleanup_incomplete') from caught
