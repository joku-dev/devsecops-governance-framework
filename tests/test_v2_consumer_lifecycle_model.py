"""Whole V1 consumer evidence/action/acceptance projections on isolated history.

The immutable bytes are engineering test data, never this node's authority.
Original source programs run only in a separate test-oracle interpreter.
"""
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import argparse
import base64
import copy
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts')]
from jsonschema import Draft202012Validator
from lib.consumer_lifecycle_context import compose
from lib.providers.consumer_lifecycle_profile import LegacyConsumerProfile
from lib.providers.consumer_lifecycle_evidence import LegacyConsumerEvidence
from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture

FIXTURE = ROOT / 'tests/fixtures/v2-consumer-lifecycle-original'
AT = '2026-11-15T12:00:00Z'


def materialize(root):
    contract = json.loads((FIXTURE / 'contract.json').read_bytes())
    original = json.loads((ROOT / 'tests/fixtures/v2-personal-channel-original/contract.json').read_bytes())
    rows = {name: {**row, 'fixture': 'tests/fixtures/v2-personal-channel-original/' + row['fixture']}
            for name, row in original['oracle_files'].items()}
    rows.update(contract['oracle_data']['files'])
    for name, row in rows.items():
        raw = (ROOT / row['fixture']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
        assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['git_blob']
        path = root / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(0o700 if row.get('git_mode') == '100755' else 0o600)
    # The runner is also one of the original executable-function fixtures.
    for name, row in contract['files'].items():
        if name in rows:
            continue
        raw = (FIXTURE / row['fixture']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
        path = root / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(raw)


def composed(root, *, process=subprocess, fetch=None, argv=(), clock=lambda: AT,
             store_factory=None, argument_parser=argparse.ArgumentParser, description=None):
    return compose(
        root, path_factory=Path, validator_class=Draft202012Validator,
        profile_factory=lambda c: LegacyConsumerProfile(c, default_fetch=fetch),
        provider_factory=lambda c: LegacyPersonalChannelCapture(c, fetch=fetch, clock=clock),
        evidence_factory=lambda c, profile, architecture: LegacyConsumerEvidence(
            root, c, path_factory=Path, profile=profile, process=process,
            temporary=tempfile, clock=clock, validator_class=Draft202012Validator,
            default_fetch=fetch, architecture=architecture),
        process=process, temporary=tempfile, clock=clock,
        argument_parser=argument_parser, argv=argv, store_factory=store_factory, description=description)


def canonical(value):
    return json.loads(json.dumps(value, sort_keys=True, default=lambda x: sorted(x) if isinstance(x, set) else str(x)))


def outcome(call):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            result = {'value': canonical(call()), 'error': None}
        except Exception as caught:
            result = {'value': None, 'error': {'type': type(caught).__name__, 'message': str(caught)}}
    return result | {'stdout': out.getvalue(), 'stderr': err.getvalue()}


ORACLE = r'''
import sys,json,io
from pathlib import Path
from contextlib import redirect_stdout,redirect_stderr
from lib.governance_lifecycle import consumer_contracts as contracts,consumer_admission as admission,consumer_actions as actions,consumer_acceptance as acceptance,consumer_evidence as evidence,store
root=Path(sys.argv[1]);kind=sys.argv[2]
def call():
 if kind=='model':return contracts.validate_preparation(root)
 if kind=='receipts':return admission.project_receipts(store.load_transactions(root/admission.VALIDATION_LEDGER),contracts.load_operating(root))
 if kind=='actions':return actions.project_actions(root)
 if kind=='acceptance':return acceptance.projection(root)
 if kind=='validate':return acceptance.validate(root)
 if kind=='capture':return evidence.replay_capture(root/'generated/reports/consumer-lifecycle-preflight/main-run-34778861076')
 raise AssertionError('Unknown explicit oracle operation')
out,err=io.StringIO(),io.StringIO()
with redirect_stdout(out),redirect_stderr(err):
 try:result={'value':call(),'error':None}
 except Exception as caught:result={'value':None,'error':{'type':type(caught).__name__,'message':str(caught)}}
print(json.dumps(result|{'stdout':out.getvalue(),'stderr':err.getvalue()},sort_keys=True,default=lambda x:sorted(x) if isinstance(x,set) else str(x)))
'''


class WholeConsumerModel(unittest.TestCase):
    def setUp(self):
        previous = os.umask(0o077)
        self.addCleanup(os.umask, previous)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / 'data'
        self.root.mkdir(mode=0o700)
        materialize(self.root)
        self.context, self.program = composed(self.root)

    def compare(self, kind):
        old = subprocess.run([sys.executable, '-B', '-c', ORACLE, str(self.root), kind],
                             cwd=self.root, capture_output=True, timeout=180,
                             env={**os.environ, 'PYTHONPATH': str(self.root / 'scripts'), 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(old.returncode, 0, old.stderr[-4000:])
        c = self.context
        calls = {
            'model': lambda: c.consumer_contracts.validate_preparation(),
            'receipts': lambda: c.consumer_admission.project_receipts(c.store.load_transactions(self.root / c.consumer_admission.VALIDATION_LEDGER), c.consumer_contracts.load_operating()),
            'actions': lambda: c.consumer_actions.project_actions(),
            'acceptance': lambda: c.consumer_acceptance.projection(),
            'validate': lambda: c.consumer_acceptance.validate(),
            'capture': lambda: c.consumer_evidence.replay_capture(self.root / 'generated/reports/consumer-lifecycle-preflight/main-run-34778861076'),
        }
        actual = outcome(calls[kind])
        self.assertEqual(actual, json.loads(old.stdout))
        return actual

    def test_original_consumer_profile_and_roles_validate_unchanged(self):
        result = self.compare('model')
        self.assertIsNone(result['error'])
        self.assertEqual(result['value']['profile']['scope']['repository_id'], 'joku-dev/governance-framework-demo-consumer')

    def test_complete_retained_evidence_receipts_actions_and_acceptance_match_original(self):
        for kind in ('capture', 'receipts', 'actions', 'acceptance', 'validate'):
            with self.subTest(kind=kind):
                self.assertIsNone(self.compare(kind)['error'])

    def test_role_scope_and_revision_mutations_keep_original_errors(self):
        path = self.root / 'model/governance/lifecycle/consumer-operation/roles.json'
        raw = path.read_bytes()
        for mutate in (lambda v: v.update(status='withdrawn'),
                       lambda v: v['scope'].update(repository_id='fixture/foreign'),
                       lambda v: v['assignments'].update(closure_approver='github-user:42')):
            value = json.loads(raw)
            mutate(value)
            path.write_text(json.dumps(value))
            with self.subTest(mutate=mutate):
                self.assertIsNotNone(self.compare('model')['error'])
        path.write_bytes(raw)

    def test_complete_action_chain_and_receipt_tampering_is_rejected_by_both(self):
        for ledger, kind in (('actions', 'actions'), ('observations', 'receipts')):
            path = next((self.root / 'governance/consumer-lifecycle' / ledger / 'transactions').glob('*.json'))
            raw = path.read_bytes()
            value = json.loads(raw)
            value['transaction_id'] = 'transaction:' + '0' * 64
            path.write_text(json.dumps(value))
            with self.subTest(ledger=ledger):
                self.assertIsNotNone(self.compare(kind)['error'])
            path.write_bytes(raw)

    def test_acceptance_manifest_change_is_visible_without_rewriting_history(self):
        before = {p.relative_to(self.root).as_posix(): p.read_bytes()
                  for p in (self.root / 'governance/consumer-lifecycle').rglob('*.json')}
        path = self.root / 'scripts/run_consumer_lifecycle.py'
        path.write_bytes(path.read_bytes() + b'\n# explicit isolated manifest drift\n')
        result = self.compare('acceptance')
        self.assertIsNone(result['error'])
        self.assertFalse(result['value']['operating_acceptance']['implementation_matches'])
        self.assertFalse(result['value']['live_activation_approved'])
        self.assertEqual(result['value']['finding_state'], 'inactive')
        self.assertEqual(before, {p.relative_to(self.root).as_posix(): p.read_bytes()
                                 for p in (self.root / 'governance/consumer-lifecycle').rglob('*.json')})
