"""Actual consumer GH/Git pipes and replay after removing all selected inputs."""
from pathlib import Path
import base64
import hashlib
import os
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from lib.providers.consumer_lifecycle_transport import NativeConsumerTransport, ReplayConsumerTransport, NativeConsumerCentralTransport, ReplayConsumerCentralTransport
from lib.providers.consumer_lifecycle_protocol import MODEL, HISTORY, OBSERVATIONS, ACTIONS, INDEX, CENTRAL
from lib.providers.synthetic_lifecycle_storage import Record, read_record
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO
import test_v2_consumer_lifecycle_program as reference


class ActualConsumerReadTransport(unittest.TestCase):
    def setUp(self):
        self.fixture = reference.WholeConsumerProgram()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        import json
        self.profile = json.loads((self.root / MODEL / 'profile.json').read_bytes())
        private = self.root.parent / 'read-record'
        private.mkdir(mode=0o700)
        self.record = Record(private / 'records', {'prototype': 'actual consumer readonly transport'}, {'prototype': True})
        self.record.append({'kind': 'execution-intent'})
        self.owner = NativeIO(self.record, mode='private-candidate', cwd=str(self.root), private_state=private, product_root=ROOT)
        self.stderr = []
        self.native = NativeConsumerTransport(self.owner, self.root, self.profile, emit_stderr=self.stderr.append,
            environment={**os.environ, 'PATH': str(self.fixture.tools) + os.pathsep + os.environ['PATH']})

    def replay(self, calls, expected):
        self.assertFalse(self.record.capture_incomplete)
        self.record.finish('complete', {'exit_code': 0, 'transport_calls': len(calls)}, self.owner.touched)
        _, _, _, events, blob, closed = read_record(self.record.root)
        cache = {p.name: p.read_bytes() for p in self.record.blobs.iterdir()}
        def inert(ref):
            raw = cache[ref['sha256']]
            self.assertEqual(hashlib.sha256(raw).hexdigest(), ref['sha256'])
            self.assertEqual(len(raw), ref['bytes'])
            return raw
        shutil.rmtree(self.root)
        shutil.rmtree(self.fixture.tools)
        replay = ReplayIO(events, inert, 'private-candidate', str(self.root))
        emitted = []
        port = ReplayConsumerTransport(replay, self.root, self.profile, emit_stderr=emitted.append)
        central = ReplayConsumerCentralTransport(replay, self.root, emit_stderr=emitted.append)
        actual = []
        with (patch('subprocess.Popen', side_effect=AssertionError('No native program')),
              patch('os.open', side_effect=AssertionError('No selected input or native output'))):
            for method, args, kwargs in calls:
                selected = central if (method != 'fetch' or args[0].startswith('repos/' + CENTRAL + '/issues/')
                    or args[0] == 'repos/' + CENTRAL + '/rules/branches/main') else port
                value = getattr(selected, method)(*args, **kwargs)
                actual.append((value.returncode, value.stdout, value.stderr) if method == 'run' else value)
            replay.finish()
        self.assertEqual(actual, expected)
        self.assertEqual(emitted, self.stderr)
        for name, raw in cache.items():
            self.assertEqual(blob({'sha256': name, 'bytes': len(raw)}), raw)
        self.assertTrue(closed())

    def test_actual_provider_raw_zip_personal_and_guard_bytes_replay_without_source_or_tool(self):
        keys = list(self.fixture.responses)
        chosen = [next(k for k in keys if k.startswith('raw:') and 'architecture_operation_readiness.rego' in k),
                  next(k for k in keys if k.endswith('/zip')),
                  next(k for k in keys if '/issues/101/comments?' in k),
                  'json:repos/' + CENTRAL + '/rules/branches/main']
        calls, expected = [], []
        central = NativeConsumerCentralTransport(self.owner, self.root, emit_stderr=self.stderr.append,
            environment={**os.environ, 'PATH': str(self.fixture.tools) + os.pathsep + os.environ['PATH']})
        for key in chosen:
            media, endpoint = key.split(':', 1)
            raw = media == 'raw'
            if endpoint.startswith('repos/' + CENTRAL + '/') and '/contents/' not in endpoint and '/git/' not in endpoint:
                value = central.fetch(endpoint)
                options = {}
            else:
                value = self.native.fetch(endpoint, raw=raw)
                options = {'raw': raw}
            self.assertEqual(value, base64.b64decode(self.fixture.responses[key], validate=True))
            calls.append(('fetch', [endpoint], options))
            expected.append(value)
        self.replay(calls, expected)

    def test_actual_git_tree_blob_index_and_tracked_request_checks_replay_with_original_types(self):
        def git(*args):
            return subprocess.run(['git', *args], cwd=self.root, capture_output=True, check=True)
        git('init', '--initial-branch=fixture', '-q')
        git('add', '--all')
        git('-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', '-c', 'user.name=AXIOM isolated fixture',
            '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'Controlled readonly consumer data')
        calls = [
            ('check_output', [['git', 'ls-tree', '-r', '--name-only', 'HEAD', '--', HISTORY, MODEL]], {'cwd': self.root, 'text': True}),
            ('check_output', [['git', 'show', 'HEAD:' + MODEL + '/profile.json']], {'cwd': self.root}),
            ('run', [['git', 'show', 'HEAD:' + INDEX]], {'cwd': self.root, 'capture_output': True}),
            ('run', [['git', 'ls-files', '--error-unmatch', '--', MODEL + '/action-requests/00000004.json']],
             {'cwd': self.root, 'capture_output': True, 'check': True}),
        ]
        expected = []
        for method, args, kwargs in calls:
            original_kwargs = {**kwargs}
            command = args[0]
            if method == 'check_output':
                value = subprocess.check_output(command, **original_kwargs)
            else:
                value = subprocess.run(command, **original_kwargs)
            actual = getattr(self.native, method)(*args, **kwargs)
            wanted = (value.returncode, value.stdout, value.stderr) if method == 'run' else value
            self.assertEqual((actual.returncode, actual.stdout, actual.stderr) if method == 'run' else actual, wanted)
            expected.append(wanted)
        self.replay(calls, expected)
