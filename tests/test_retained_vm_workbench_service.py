"""Explicit V1 VM compatibility cannot replace admitted V2 instances."""
import contextlib
import io
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import serve_governance_workbench as workbench


class RetainedVMServiceContract(unittest.TestCase):
    def test_explicit_service_preserves_key_projection_port_and_shutdown(self):
        server = Mock()
        server.server_address = ('127.0.0.1', 8766)
        server.serve_forever.side_effect = KeyboardInterrupt
        application = Mock()
        key = 'synthetic-retained-service-key-001'
        output = io.StringIO()
        with patch.dict(os.environ, {'AXIOM_WORKBENCH_KEY': key}), \
                patch.object(workbench, 'Workbench', return_value=application) as constructor, \
                patch.object(workbench, 'make_server', return_value=server) as make, \
                patch('lib.v2_application.run') as admitted, contextlib.redirect_stdout(output):
            result = workbench.main(['--legacy-service-profile', 'vm-v1', '--port', '8766',
                '--consumer-projection', '/private/synthetic/projection'])
        self.assertEqual(result, 0)
        constructor.assert_called_once_with(enable_pr=False,
            consumer_projection=Path('/private/synthetic/projection'), publisher=None, state_dir=None)
        make.assert_called_once_with(application, key, 8766)
        server.serve_forever.assert_called_once_with()
        server.server_close.assert_called_once_with()
        admitted.assert_not_called()
        self.assertNotIn(key, output.getvalue())

    def test_profile_cannot_override_v2_instance_or_admitted_application(self):
        for args, kwargs in [
            (['--legacy-service-profile', 'vm-v1', '--instance', '/private/synthetic/instance'], {}),
            (['--legacy-service-profile', 'vm-v1'], {'application': Mock(), 'access_key': 'x' * 32}),
        ]:
            with self.subTest(args=args), patch.object(workbench, 'Workbench') as constructor, \
                    patch.object(workbench, 'make_server') as server, \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as outcome:
                    workbench.main(args, **kwargs)
                self.assertEqual(outcome.exception.code, 2)
                constructor.assert_not_called()
                server.assert_not_called()

    def test_invalid_environment_key_creates_no_legacy_state(self):
        with patch.dict(os.environ, {'AXIOM_WORKBENCH_KEY': 'short'}), \
                patch.object(workbench, 'Workbench') as constructor, \
                patch.object(workbench, 'make_server') as server, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as outcome:
                workbench.main(['--legacy-service-profile', 'vm-v1'])
        self.assertEqual(outcome.exception.code, 2)
        constructor.assert_not_called()
        server.assert_not_called()

    def test_legacy_service_does_not_enable_unconfigured_publication(self):
        with patch.dict(os.environ, {'AXIOM_WORKBENCH_KEY': 'x' * 32}), \
                patch.object(workbench, 'Workbench') as constructor, \
                patch.object(workbench, 'make_server') as server, \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as outcome:
                workbench.main(['--legacy-service-profile', 'vm-v1', '--enable-pr'])
        self.assertEqual(outcome.exception.code, 2)
        constructor.assert_not_called()
        server.assert_not_called()
