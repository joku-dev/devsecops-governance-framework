"""Offline audit of every finite source Git call and the closed input graph.

No checkout, Path.resolve, native process or provider call is needed. Working
file bytes remain declared captures; this checks their closure and the actual
retained Git acquisition transcript, never independently attesting execution.
"""
from copy import deepcopy
from pathlib import PurePosixPath

from lib import repository_capture as contract
from lib.providers.repository_git import RepositoryGit
from lib.providers.release_references import ReleaseReferences
from lib.providers.repository_journal import encoded

INITIAL = {'arguments', 'argv', 'source_root', 'tool_path', 'tool_sha256', 'process_started',
    'returncode', 'error_type', 'timed_out', 'output_truncated', 'stdout_limit'}
FINAL = INITIAL | {'cleanup_signal_permission_denied', 'cleanup_absence_check', 'stdout_base64', 'stderr_base64'}


class ReplayRepositoryGit:
    def __init__(self, source_root, phases):
        # Resolve the shared neutral checks after provider composition has
        # finished importing; repository_replay itself uses provider ports.
        from lib.repository_replay import native_complete, raw_stream, tool_identity
        path = PurePosixPath(source_root)
        if (type(source_root) is not str or not path.is_absolute() or str(path) != source_root
                or '..' in path.parts or len(source_root) > 8192 or any(ord(c) < 32 for c in source_root)
                or type(phases) is not list or not phases or len(phases) > 3 * 20064 or len(phases) % 3):
            raise ValueError('invalid_repository_acquisition_replay_context')
        self.root, self.rows, self.position, total = source_root, [], 0, 0
        self.tool = None
        for index in range(0, len(phases), 3):
            group = phases[index:index + 3]
            if any(type(row) is not dict or set(row) != {'phase', 'observation'} for row in group):
                raise ValueError('repository_acquisition_phase_contract_changed')
            if [row['phase'] for row in group] != ['intent', 'started', 'finished']:
                raise ValueError('repository_acquisition_phase_order_changed')
            intent, started, finished = [row['observation'] for row in group]
            if (any(type(row) is not dict for row in (intent, started, finished))
                    or set(intent) != INITIAL or set(started) != INITIAL or set(finished) != FINAL):
                raise ValueError('repository_acquisition_observation_contract_changed')
            native_complete(finished)
            if finished['returncode'] != 0 or finished['source_root'] != source_root:
                raise ValueError('repository_acquisition_native_read_incomplete')
            before = {key: finished[key] for key in INITIAL}
            before.update(process_started=False, returncode=None)
            after_start = {**before, 'process_started': True}
            if encoded(intent) != encoded(before) or encoded(started) != encoded(after_start):
                raise ValueError('repository_acquisition_native_phase_binding_changed')
            tool = finished['tool_path'], finished['tool_sha256']
            tool_identity(*tool)
            if PurePosixPath(tool[0]).is_relative_to(path) or self.tool is not None and self.tool != tool:
                raise ValueError('repository_acquisition_tool_binding_changed')
            self.tool = tool
            prefix = [tool[0], '--no-optional-locks', '--literal-pathspecs',
                '-c', 'safe.directory=' + source_root, '-c', 'core.hooksPath=/dev/null',
                '-c', 'core.fsmonitor=false', '-c', 'core.attributesFile=/dev/null', '-c', 'protocol.allow=never']
            arguments = finished['arguments']
            if (type(arguments) is not list or not arguments
                    or any(type(value) is not str or '\0' in value or len(value) > 8192 for value in arguments)
                    or finished['argv'] != prefix + arguments):
                raise ValueError('repository_acquisition_argv_changed')
            maximum = RepositoryGit.limit(tuple(arguments))
            if type(finished['stdout_limit']) is not int or not 0 < finished['stdout_limit'] <= maximum:
                raise ValueError('repository_acquisition_stream_limit_changed')
            total += len(raw_stream(finished, 'stdout', maximum=finished['stdout_limit']))
            total += len(raw_stream(finished, 'stderr'))
            if total > 2 * contract.MAX_TOTAL:
                raise ValueError('repository_acquisition_transcript_byte_budget')
            self.rows.append(deepcopy(finished))

    def read(self, *arguments, limit=None):
        from lib.repository_replay import raw_stream
        if self.position >= len(self.rows):raise ValueError('repository_acquisition_read_missing')
        row = self.rows[self.position]
        maximum = RepositoryGit.limit(arguments)
        if limit is not None and (type(limit) is not int or not 0 < limit <= maximum):
            raise ValueError('repository_acquisition_requested_limit_changed')
        if row['arguments'] != list(arguments) or row['stdout_limit'] != (maximum if limit is None else limit):
            raise ValueError('repository_acquisition_request_changed')
        self.position += 1
        return raw_stream(row, 'stdout', maximum=row['stdout_limit'])

    def finish(self):
        if self.position != len(self.rows):raise ValueError('repository_acquisition_reads_unused')


class ReplayReferences(ReleaseReferences):
    def __init__(self, source_root, read):
        # The ordinary live adapter resolves and verifies an actual checkout.
        # This adapter only compares the already retained original label.
        self.root, self.reader = PurePosixPath(source_root), read
        if self.git('rev-parse', '--show-toplevel').decode('utf-8').strip() != source_root:
            raise ValueError('repository_acquisition_release_root_changed')


def audit_acquisition(manifest, files, commit, references, phases):
    contract.check_capture(manifest, files, commit, revision=manifest['revision'])
    port = ReplayRepositoryGit(manifest['source_root'], phases)
    if not port.read('--version').decode('utf-8').strip().startswith('git version '):
        raise ValueError('repository_acquisition_git_version_changed')
    def binding():
        actual = [port.read(*args).decode('utf-8').rstrip('\n') for args in (
            ('rev-parse', '--show-toplevel'), ('rev-parse', '--show-object-format'),
            ('rev-parse', '--verify', 'HEAD^{commit}'), ('rev-parse', '--verify', 'HEAD^{tree}'))]
        if actual != [manifest['source_root'], manifest['object_format'], manifest['revision'], manifest['tree']]:
            raise ValueError('repository_acquisition_source_binding_changed')
    binding()
    if port.read('cat-file', 'commit', manifest['revision']) != commit:
        raise ValueError('repository_acquisition_commit_bytes_changed')
    inventory = contract.parse_tree(port.read('ls-tree', '-r', '-t', '-l', '-z', '--full-tree', manifest['revision']),
        tree=manifest['tree'], algorithm=manifest['object_format'])
    if encoded(inventory) != encoded(manifest['inventory']):
        raise ValueError('repository_acquisition_inventory_changed')
    if manifest['profile'] == contract.COMMITTED:
        seen = {}
        for name, row in inventory.items():
            if row['kind'] != 'blob':continue
            oid = row['git_object']
            if oid not in seen:seen[oid] = port.read('cat-file', 'blob', oid)
            if seen[oid] != files[name]:raise ValueError('repository_acquisition_blob_bytes_changed')
        binding()
    else:
        # The live held working capture checks the binding after each complete
        # file walk. Working bytes cannot be authenticated by a Git blob read.
        binding(); binding()
    captured = ReplayReferences(manifest['source_root'], port.read).capture()
    if (encoded(captured) != encoded(references) or captured['source_head'] != manifest['revision']
            or captured['source_tree'] != manifest['tree'] or captured['object_format'] != manifest['object_format']):
        raise ValueError('repository_acquisition_release_references_changed')
    port.finish()
    return {'native_reads': len(port.rows), 'closed_input_graph_consistent': True,
            'independent_execution_attested': False}
