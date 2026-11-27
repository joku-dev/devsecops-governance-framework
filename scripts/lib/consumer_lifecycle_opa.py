"""Closed independent policy evaluation, materialization and no-process replay."""
from pathlib import PurePosixPath as P
import hashlib
from lib.personal_channel_process import process_value
from lib.synthetic_lifecycle_io import path_spec
from lib.requirement_validation_replay import IntegrityError

STREAM_LIMITS = (16 * 1024**2, 256 * 1024)


def digest(raw):
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def frame_value(frame, arguments):
    if (type(frame) is not dict or set(frame) != {'path', 'identity', 'mode', 'files'}
            or type(frame['path']) is not str or not P(frame['path']).is_absolute()
            or P(frame['path']).parent != P(arguments['workarea'])
            or not P(frame['path']).name.startswith('tmpconsumer-opa-')
            or not 16 <= len(P(frame['path']).name) <= 80
            or type(frame['identity']) is not list or len(frame['identity']) != 2
            or any(type(n) is not int or n < 0 for n in frame['identity'])
            or type(frame['mode']) is not int or frame['mode'] != 0o700
            or frame['files'] != arguments['files']):
        raise IntegrityError('consumer_opa_materialization_changed')
    path_spec(frame['path'], frame['path'], arguments['workarea'])
    return frame


def cleanup_value(wire, frame):
    if (type(wire) is not dict or set(wire) != {'frame', 'owned_before', 'absent_after'}
            or wire['frame'] != frame or wire['owned_before'] is not True or wire['absent_after'] is not True):
        raise IntegrityError('consumer_opa_materialization_cleanup_unproven')


def result_value(wire, spec, profile, blob, tool, approved_hashes):
    if (type(wire) is not dict or type(wire.get('program')) is not dict
            or wire['program'].get('label') != tool or wire['program'].get('sha256') not in approved_hashes):
        raise IntegrityError('consumer_opa_pinned_tool_changed')
    return process_value(wire, spec, profile, blob, emit_stderr=lambda _: (_ for _ in ()).throw(
        IntegrityError('consumer_opa_captured_stderr_was_inherited')), stream_limits=STREAM_LIMITS)


class ReplayConsumerOPA:
    def __init__(self, owner, source, *, profile, tool, approved_hashes, workarea):
        self.owner, self.source, self.profile = owner, str(source), profile
        self.tool, self.approved_hashes, self.workarea = tool, approved_hashes, str(workarea)

    def run(self, command, *, capture_output, check, timeout):
        spec = self.profile.request(command, capture_output=capture_output, check=check, timeout=timeout,
                                    source=self.source, cwd=self.owner.cwd, owner=self.owner)
        files = {name: self.owner.read(path, path) for name, path in self.profile.files(spec).items()}
        self.profile.admit_files(files)
        frame = None
        if self.owner.mode == 'private-candidate':
            args = {'workarea': self.workarea, 'files': {name: digest(raw) for name, raw in files.items()}}
            ok, frame = self.owner.outcome('consumer-opa-materialization-create', args, 'json')
            if not ok:
                raise IntegrityError('consumer_opa_materialization_incomplete')
            frame_value(frame, args)
        spec = self.profile.bind(spec, frame)
        try:
            ok, wire = self.owner.outcome('consumer-independent-opa-process', spec, 'json')
            if not ok:
                raise IntegrityError('consumer_opa_process_capture_incomplete')
            return result_value(wire, spec, self.profile, self.owner.blob, self.tool, self.approved_hashes)
        finally:
            # Original temporary inputs remain part of the same ordered stream.
            for name, path in self.profile.files(spec).items():
                if self.owner.read(path, path) != files[name]:
                    raise IntegrityError('consumer_opa_original_input_changed')
            if frame is not None:
                ok, wire = self.owner.outcome('consumer-opa-materialization-cleanup', {'frame': frame}, 'json')
                if not ok:
                    raise IntegrityError('consumer_opa_materialization_cleanup_incomplete')
                cleanup_value(wire, frame)
