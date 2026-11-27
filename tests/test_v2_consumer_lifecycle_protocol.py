"""Consumer transport admission against whole historical GETs and write attacks."""
from pathlib import Path
import copy
import json
import os
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from lib.providers.consumer_lifecycle_protocol import LegacyConsumerProtocol, LegacyConsumerCentralProtocol, MODEL, HISTORY, OBSERVATIONS, ACTIONS, ACCEPTANCE, INDEX, CENTRAL
from lib.providers.consumer_lifecycle_transport import NativeConsumerTransport, ReplayConsumerTransport
from lib.requirement_validation_budget import InputAdmissionError
from test_v2_consumer_lifecycle_program import provider_responses
from test_v2_consumer_lifecycle_model import materialize
import tempfile


class ConsumerReadProtocol(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        materialize(self.root)
        self.profile = json.loads((self.root / MODEL / 'profile.json').read_bytes())
        self.protocol = LegacyConsumerProtocol(self.profile)

    def test_every_whole_original_evidence_and_personal_get_is_admitted_with_exact_raw_options(self):
        for run in ('34778861076', '37113784702'):
            for key in provider_responses(self.root, run):
                media, endpoint = key.split(':', 1)
                with self.subTest(endpoint=endpoint):
                    protocol = LegacyConsumerCentralProtocol() if endpoint.startswith('repos/' + CENTRAL + '/issues/') or endpoint.endswith('/rules/branches/main') else self.protocol
                    spec = protocol.request('get', {'endpoint': endpoint, 'raw': media == 'raw'}, str(self.root), '/caller')
                    self.assertEqual(spec['original_arguments'], ['gh', 'api', '--hostname', 'github.com', '--method', 'GET', endpoint]
                                     + (['-H', 'Accept: application/vnd.github.raw+json'] if media == 'raw' else []))
                    self.assertEqual(spec['cwd'], '/caller')
                    self.assertEqual(spec['timeout'], 90)

    def test_cross_scope_mutation_pagination_media_and_shell_paths_are_rejected(self):
        consumer = 'repos/' + self.profile['scope']['repository_id']
        for endpoint, raw in ((consumer + '/actions/runs/0', False),
                              (consumer + '/actions/runs/1/artifacts?per_page=100&page=11', False),
                              ('repos/other/consumer/actions/runs/1', False),
                              ('repos/' + CENTRAL + '/issues/1/comments', False),
                              (consumer + '/contents/../../private?ref=' + 'a' * 40, True),
                              (consumer + '/actions/runs/1', True),
                              ('https://api.github.com/' + consumer, False),
                              (consumer + '\nPOST', False)):
            with self.subTest(endpoint=endpoint), self.assertRaises(InputAdmissionError):
                self.protocol.request('get', {'endpoint': endpoint, 'raw': raw}, str(self.root), '/caller')
        for kind in ('post', 'put', 'delete', 'graphql', 'shell'):
            with self.assertRaises(InputAdmissionError):
                self.protocol.request(kind, {}, str(self.root), '/caller')

    def test_all_original_git_scopes_are_readonly_and_preserve_binary_vs_text(self):
        root = str(self.root)
        for paths in ([OBSERVATIONS], [ACTIONS], [ACCEPTANCE], [OBSERVATIONS, ACTIONS], [HISTORY, MODEL]):
            self.protocol.request('git-tree', {'command': ['git', 'ls-tree', '-r', '--name-only', 'HEAD', '--', *paths], 'cwd': root, 'text': True}, root, '/caller')
        for path in (HISTORY + '/acceptance/00000001.json', MODEL + '/profile.json'):
            self.protocol.request('git-tree', {'command': ['git', 'show', 'HEAD:' + path], 'cwd': root, 'text': False}, root, '/caller')
        self.protocol.request('git-run', {'command': ['git', 'show', 'HEAD:' + INDEX], 'cwd': root, 'capture_output': True}, root, '/caller')
        self.protocol.request('git-checked-run', {'command': ['git', 'ls-files', '--error-unmatch', '--', MODEL + '/action-requests/00000004.json'], 'cwd': root, 'capture_output': True, 'check': True}, root, '/caller')
        for command in (['git', 'push'], ['git', 'reset', '--hard'], ['git', 'show', 'HEAD:private.txt'],
                        ['git', 'show', 'HEAD:' + MODEL + '/../private.txt'],
                        ['git', 'ls-tree', '-r', '--name-only', '--help', '--', HISTORY]):
            with self.subTest(command=command), self.assertRaises(InputAdmissionError):
                self.protocol.request('git-tree', {'command': command, 'cwd': root, 'text': False}, root, '/caller')

    def test_complete_original_read_token_helper_uses_private_environment_copy(self):
        environment = {'GH_TOKEN': 'publisher-fixture', 'CONSUMER_EVIDENCE_TOKEN': 'reader-fixture'}
        node = NativeConsumerTransport(object(), self.root, self.profile, emit_stderr=lambda _: None, environment=environment)
        endpoint = 'repos/' + self.profile['scope']['repository_id']
        with patch.object(node, 'request', return_value=b'{}') as request:
            self.assertEqual(node.fetch(endpoint), b'{}')
            request.assert_called_once_with('get', {'endpoint': endpoint, 'raw': False})
        self.assertEqual(environment['GH_TOKEN'], 'publisher-fixture')
        self.assertEqual(node.environment['GH_TOKEN'], 'reader-fixture')
        environment['CONSUMER_EVIDENCE_TOKEN'] = 'later-external-change'
        self.assertEqual(node.reader_environment['CONSUMER_EVIDENCE_TOKEN'], 'reader-fixture')

    def test_replay_does_not_lookup_credentials_environment_source_or_native_process(self):
        with patch('os.environ', {}), patch('subprocess.Popen', side_effect=AssertionError('No process')):
            node = ReplayConsumerTransport(object(), self.root, self.profile, emit_stderr=lambda _: None)
            with patch.object(node, 'request', return_value=b'raw') as request:
                self.assertEqual(node.fetch('explicit-endpoint', raw=True), b'raw')
                request.assert_called_once_with('get', {'endpoint': 'explicit-endpoint', 'raw': True})
