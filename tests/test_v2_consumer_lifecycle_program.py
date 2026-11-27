"""All seven original consumer runner operations, controlled GETs, actual Git/OPA.

Fake provider bytes are isolated test data, not authenticated live completion.
No fixture consent is posted or transferred to the product's operating state.
"""
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import argparse
import ast
import base64
import fcntl
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from lib.synthetic_ledger_store import SyntheticLedgerStore
from lib.retained_argparse import parser_base, formatter_factory
from lib.providers.retained_argparse import capture_context
from test_v2_consumer_lifecycle_model import materialize, composed, FIXTURE, AT
from test_v2_synthetic_ledger_core import snapshot, restore


def provider_responses(root, run_id='37113784702'):
    """Exact saved provider bytes mapped to their original finite GET endpoints."""
    responses = {}
    def put(endpoint, raw, *, media=False):
        key = ('raw:' if media else 'json:') + endpoint
        if key in responses:
            assert responses[key] == base64.b64encode(raw).decode()
        responses[key] = base64.b64encode(raw).decode()
    def json_put(endpoint, value):
        put(endpoint, json.dumps(value).encode())
    captures = [root / 'generated/reports/consumer-lifecycle-preflight/main-run-34778861076']
    saved = []
    for path in sorted((root / 'governance/consumer-lifecycle/observations/transactions').glob('*.json')):
        receipt = json.loads(path.read_bytes())
        saved.append({name: base64.b64decode(raw, validate=True) for name, raw in receipt['capture'].items()})
    saved.extend({p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()} for folder in captures)
    for files in saved:
        profile = json.loads(files['profile.json'])
        source = profile['source']
        repository = 'repos/' + profile['scope']['repository_id']
        baseline = 'repos/' + source['baseline_repository']
        run = json.loads(files['run-before.json'])
        # Repository and workflow bytes legitimately differ between captures.
        # Select one whole historical snapshot for this controlled exchange;
        # never merge or normalize competing provider responses.
        if str(run['id']) != run_id:
            continue
        artifact = json.loads(files['artifact-before.json'])
        put(repository, files['repository.json'])
        put(repository + '/actions/runs/' + str(run['id']), files['run-before.json'])
        put(repository + '/actions/workflows/' + str(run['workflow_id']), files['workflow.json'])
        json_put(repository + '/actions/runs/' + str(run['id']) + '/artifacts?per_page=100&page=1', {'total_count': 1, 'artifacts': [artifact]})
        artifact_endpoint = repository + '/actions/artifacts/' + str(artifact['id'])
        put(artifact_endpoint, files['artifact-before.json'])
        put(artifact_endpoint + '/zip', files['artifact.zip'])
        put(repository + '/contents/' + source['workflow_path'] + '?ref=' + run['head_sha'], files['consumer-workflow.yml'], media=True)
        put(baseline + '/git/ref/tags/' + source['baseline_ref'], files['baseline-ref.json'])
        put(baseline + '/git/tags/' + source['baseline_tag_object'], files['baseline-tag.json'])
        for name in source['reference_files']:
            put(baseline + '/contents/' + name + '?ref=' + source['reference_commit'], files['producer/' + name], media=True)
    snapshots = [json.loads(p.read_bytes()) for p in (root / 'governance/consumer-lifecycle/acceptance').glob('*.json')]
    snapshots.extend(json.loads(p.read_bytes())['snapshot'] for p in (root / 'governance/consumer-lifecycle/actions/transactions').glob('*.json'))
    for value in snapshots:
        request = value['request']
        endpoint = f"repos/{request['repository_id']}/issues/{request['discussion_number']}"
        put(endpoint, value['issue_response'].encode())
        for i, page in enumerate(value['comment_pages_after'], 1):
            put(endpoint + f'/comments?per_page=100&page={i}', page.encode())
    json_put('repos/joku-dev/devsecops-governance-framework/rules/branches/main', [
        {'type': 'required_status_checks', 'parameters': {'strict_required_status_checks_policy': True,
         'required_status_checks': [{'context': 'Consumer Lifecycle Guard', 'integration_id': 15368}]}}])
    return responses


class FakeRead:
    def __init__(self, responses):
        self.responses, self.calls = responses, []
    def __call__(self, endpoint, *, raw=False):
        key = ('raw:' if raw else 'json:') + endpoint
        self.calls.append(key)
        return base64.b64decode(self.responses[key], validate=True)


WRAPPER = r'''
import runpy,sys
from unittest.mock import patch
from datetime import datetime as NativeDatetime
from lib.governance_lifecycle import consumer_evidence,consumer_acceptance,consumer_admission,consumer_actions,personal_probe
class FixedClock:
 @staticmethod
 def now(zone):return NativeDatetime.fromisoformat('2026-11-15T12:00:00+00:00').astimezone(zone)
for module in (consumer_evidence,consumer_acceptance,consumer_admission,consumer_actions,personal_probe):
 if hasattr(module,'datetime'):module.datetime=FixedClock
path=sys.argv[1];sys.argv=sys.argv[1:]
with patch('datetime.datetime',FixedClock):runpy.run_path(path,run_name='__main__')
'''


class WholeConsumerProgram(unittest.TestCase):
    def setUp(self):
        old = os.umask(0o077)
        self.addCleanup(os.umask, old)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.parent = Path(temp.name).resolve()
        self.root = self.parent / 'data'
        self.root.mkdir(mode=0o700)
        materialize(self.root)
        self.responses = provider_responses(self.root)
        self.tools = self.parent / 'fake-provider'
        self.tools.mkdir(mode=0o700)
        (self.tools / 'responses.json').write_text(json.dumps(self.responses))
        fake = '''import base64,json,sys
from pathlib import Path
b=Path(__file__).resolve().parent;args=sys.argv[1:]
assert args[:5]==['api','--hostname','github.com','--method','GET']
assert len(args) in (6,8)
assert len(args)==6 or args[6:]==['-H','Accept: application/vnd.github.raw+json']
key=('raw:' if len(args)==8 else 'json:')+args[5]
with (b/'calls.jsonl').open('a') as h:h.write(json.dumps(key)+'\\n')
sys.stdout.buffer.write(base64.b64decode(json.loads((b/'responses.json').read_bytes())[key],validate=True))
'''
        gh = self.tools / 'gh'
        gh.write_text('#!' + sys.executable + '\n' + fake)
        gh.chmod(0o700)
        contract = json.loads((FIXTURE / 'contract.json').read_bytes())
        raw = (FIXTURE / contract['files']['scripts/run_consumer_lifecycle.py']['fixture']).read_bytes()
        self.description = ast.get_docstring(ast.parse(raw))

    def compare(self, args, *, expected=0):
        (self.tools / 'responses.json').write_text(json.dumps(self.responses))
        before = snapshot(self.root)
        calls = self.tools / 'calls.jsonl'
        calls.unlink(missing_ok=True)
        old = subprocess.run([sys.executable, '-B', '-c', WRAPPER, str(self.root / 'scripts/run_consumer_lifecycle.py'), *args],
                             cwd=self.root, capture_output=True, timeout=240,
                             env={**os.environ, 'PYTHONPATH': str(self.root / 'scripts'),
                                  'PATH': str(self.tools) + os.pathsep + os.environ['PATH'],
                                  'PYTHONDONTWRITEBYTECODE': '1', 'COLUMNS': '60', 'LINES': '24'})
        self.assertEqual(old.returncode, expected, old.stderr[-4000:])
        after = snapshot(self.root)
        restore(self.root, before)
        fake = FakeRead(self.responses)
        with patch.dict(os.environ, {'COLUMNS': '60', 'LINES': '24'}):
            parser_context = capture_context()
        context, program = composed(
            self.root, fetch=fake, argv=args, description=self.description,
            store_factory=lambda c: SyntheticLedgerStore(c, path_factory=Path, native=os, locking=fcntl, temporary=tempfile),
            argument_parser=lambda **kw: parser_base(parser_context)(prog='run_consumer_lifecycle.py', formatter_class=formatter_factory(parser_context), **kw))
        out, err = io.StringIO(), io.StringIO()
        code, error = 0, None
        with redirect_stdout(out), redirect_stderr(err):
            try:
                program.main()
            except SystemExit as caught:
                code = caught.code
            except Exception as caught:
                code, error = 1, {'type': type(caught).__name__, 'message': str(caught)}
        self.assertEqual(code, old.returncode, (error, old.stderr[-4000:]))
        self.assertEqual(out.getvalue().encode(), old.stdout)
        if error is None:
            self.assertEqual(err.getvalue().encode(), old.stderr)
        else:
            self.assertTrue(old.stderr.decode().endswith(error['type'] + ': ' + error['message'] + '\n'), (error, old.stderr[-4000:]))
        actual_files, actual_dirs = snapshot(self.root)
        expected_files, expected_dirs = after
        changed = [name for name in sorted(set(actual_files) | set(expected_files))
                   if actual_files.get(name) != expected_files.get(name)]
        self.assertEqual(changed, [], 'Whole original output bytes/modes differ: ' + repr(changed))
        self.assertEqual(actual_dirs, expected_dirs)
        self.assertEqual(fake.calls, [json.loads(x) for x in calls.read_text().splitlines()] if calls.exists() else [])
        return context, error

    def test_complete_validate_refresh_and_acceptance_paths(self):
        for operation in ('validate', 'refresh', 'acceptance'):
            with self.subTest(operation=operation):
                self.compare(['--operation', operation])

    def test_prepare_acceptance_binds_the_complete_original_manifest_and_excludes_new_authority(self):
        (self.root / 'model/governance/lifecycle/consumer-operation/acceptance.json').unlink()
        shutil.rmtree(self.root / 'governance/consumer-lifecycle/acceptance')
        context, error = self.compare(['--operation', 'prepare-acceptance', '--discussion-number', '900001'])
        self.assertIsNone(error)
        value = context.consumer_acceptance.projection()
        self.assertFalse(value['live_activation_approved'])
        self.assertFalse(value['official_state'])

    def test_complete_preflight_fetches_and_independently_checks_archived_opa_evidence(self):
        self.responses = provider_responses(self.root, '34778861076')
        self.compare(['--operation', 'preflight', '--source-run-id', '34778861076', '--output', str(self.root / 'generated/reports/consumer-lifecycle-preflight/new-controlled-capture')])

    def test_observe_existing_receipt_is_idempotent_and_keeps_original_lock_effects(self):
        context, error = self.compare(['--operation', 'observe', '--source-run-id', '37113784702'])
        self.assertIsNone(error)
        self.assertEqual(len(context.store.load_transactions(self.root / context.consumer_admission.VALIDATION_LEDGER)), 3)

    def test_action_existing_request_is_idempotent_after_actual_tracked_git_check(self):
        def git(*args):
            return subprocess.run(['git', *args], cwd=self.root, capture_output=True, check=True)
        git('init', '-q')
        git('add', '--', 'model/governance/lifecycle/consumer-operation/action-requests/00000004.json')
        context, error = self.compare(['--operation', 'action', '--request-path', 'model/governance/lifecycle/consumer-operation/action-requests/00000004.json'])
        self.assertIsNone(error)
        self.assertEqual(len(context.store.load_transactions(self.root / context.consumer_actions.ACTION_LEDGER)), 4)

    def test_original_parser_and_missing_positive_arguments(self):
        for args, expected in ((['--help'], 0), ([], 2), (['--operation', 'unknown'], 2),
                               (['--operation', 'prepare-acceptance', '--discussion-number', '0'], 1),
                               (['--operation', 'preflight'], 1),
                               (['--operation', 'observe', '--source-run-id', '-1'], 1),
                               (['--operation', 'action'], 1)):
            with self.subTest(args=args):
                self.compare(args, expected=expected)
