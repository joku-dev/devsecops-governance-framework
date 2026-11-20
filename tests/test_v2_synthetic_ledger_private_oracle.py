"""Complete unchanged V1 mains versus an isolated private inode projection.

Only the reference subprocess writes its disposable data tree. Candidate source
reads, locks, temporaries, links and reports run through the in-memory ports.
Both sides explicitly use creation mask 077; this is no future native claim.
"""
from pathlib import Path, PurePosixPath
from contextlib import redirect_stdout, redirect_stderr
import argparse, hashlib, io, json, os, subprocess, sys, traceback, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from lib.synthetic_ledger_projection import LedgerProjection, PrivateLedgerEffects
from lib.synthetic_ledger_context import compose, PROGRAMS
from lib.synthetic_lifecycle_context import LifecyclePaths
from lib.repository_schemas import RepositorySchemas
import test_v2_synthetic_ledger_core as original_core


class PrivateInputs:
    def __init__(self, source):
        self.blobs = {}
        self.tree = LedgerProjection(lambda ref: self.blobs[ref['sha256']])
        self.store(b'')
        # Test-only complete, explicit, stable source preimage. Product admission
        # will obtain retained bounded snapshots through a separate adapter.
        # The preimage anchor is the selected data root. Shared host ancestors
        # such as /tmp are outside this private candidate, not source metadata.
        directories = [source]
        paths = directories + sorted(source.rglob('*'))
        for serial, path in enumerate(paths, 1):
            value = {'kind': 'directory' if path.is_dir() else 'file',
                     'mode': path.stat().st_mode & 0o777, 'identity': [99, serial]}
            if value['kind'] == 'file': value['content'] = self.store(path.read_bytes())
            self.tree.load_one(str(path), value)
        for name, value in self.tree.base.items():
            if value['kind'] == 'directory':
                names = sorted(PurePosixPath(child).name for child in self.tree.base
                               if child != name and str(PurePosixPath(child).parent) == name)
                self.tree.load_membership(name, names)

    def store(self, raw):
        ref = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        self.blobs[ref['sha256']] = raw
        return ref

    def read(self, path, label): return self.tree.read(path, label)
    def probe(self, path, kind, label): return self.tree.probe(path, kind)
    def iterdir(self, path, label): return self.tree.entries(path, label)
    def text_encoding(self, encoding, errors): return encoding or 'utf-8'
    def mkdir(self, path, mode, parents, exist_ok, label):
        return self.tree.mkdir(path, mode, parents, exist_ok, label)
    def write_bytes(self, path, raw, label):
        self.tree.write(path, raw, self.store(raw), label)
        return len(raw)
    def write_text(self, path, text, encoding, errors, label):
        raw = text.encode(encoding or 'utf-8', errors or 'strict')
        self.write_bytes(path, raw, label)
        return len(text)

    def snapshot(self, root):
        files, directories = {}, {}
        for name in self.tree.base.keys() | self.tree.nodes.keys():
            if name == str(root) or not PurePosixPath(name).is_relative_to(root): continue
            relative = str(PurePosixPath(name).relative_to(root))
            value = self.tree.state(name)
            if value['kind'] == 'file': files[relative] = (self.tree.blob(value['content']), value['mode'])
            elif value['kind'] == 'directory': directories[relative] = value['mode']
        return files, directories


class WholePrivateLedgerOracle(unittest.TestCase):
    setUp = original_core.WholeSyntheticLedgerCore.setUp
    selected_transaction = original_core.WholeSyntheticLedgerCore.selected_transaction
    record_arguments = original_core.WholeSyntheticLedgerCore.record_arguments

    def compare(self, name, args, *, expected_code=0):
        before = original_core.snapshot(self.root)
        driver = ('import os,runpy,sys;os.umask(0o077);'
                  'sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name="__main__")')
        reference = subprocess.run([sys.executable, '-B', '-c', driver,
            str(self.root / 'scripts' / PROGRAMS[name][0]), *args], cwd=self.root,
            capture_output=True, timeout=90,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(self.root / 'scripts')})
        self.assertEqual(reference.returncode, expected_code, reference.stderr[-2500:])
        after = original_core.snapshot(self.root)
        original_core.restore(self.root, before)
        selected = PrivateInputs(self.root)
        paths = LifecyclePaths(str(self.root), str(self.root), selected)
        events = []
        effects = PrivateLedgerEffects(selected.tree, selected.store,
            absolute=paths.absolute, emit=events.append)
        schemas = RepositorySchemas(paths.path(str(self.root)), identifier_bases=(
            'https://joku-dev.github.io/devsecops-governance-framework/schemas/',))
        context, programs = compose(paths.path(str(self.root)), validator_class=schemas,
            path_factory=paths.path, argument_parser=argparse.ArgumentParser,
            argv=list(args), native=effects, locking=effects, temporary=effects)
        out, err = io.StringIO(), io.StringIO()
        code, error, trace = 0, None, None
        with redirect_stdout(out), redirect_stderr(err):
            try: programs[name].main()
            except SystemExit as failure: code = failure.code or 0
            except Exception as failure: code, error, trace = 1, failure, traceback.format_exc()
        self.assertEqual(code, reference.returncode, (name, error, trace))
        self.assertEqual(out.getvalue().encode(), reference.stdout)
        if error is None: self.assertEqual(err.getvalue().encode(), reference.stderr)
        else: self.assertTrue(reference.stderr.decode().endswith(type(error).__name__ + ': ' + str(error) + '\n'))
        self.assertEqual(selected.snapshot(str(self.root)), after)
        self.assertEqual(original_core.snapshot(self.root), before, 'Candidate must never write selected source files')
        self.assertEqual(effects.descriptors, {})
        self.assertEqual(effects.locks, {})
        self.assertTrue(all(event['native_effect'] is False for event in events))
        return context, selected, events

    def demo(self, name):
        args = ['--ledger', str(self.root / 'private-ledger'), '--output', str(self.root / 'exports/index.json')]
        if name in ('closure', 'exception'): args += ['--report', str(self.root / 'exports/report.md')]
        self.compare(name, args)

    def test_whole_synthetic_demo_private_outputs_equal_unchanged_original(self): self.demo('synthetic')
    def test_whole_action_demo_private_outputs_equal_unchanged_original(self): self.demo('action')
    def test_whole_closure_demo_private_outputs_equal_unchanged_original(self): self.demo('closure')
    def test_whole_exception_demo_private_outputs_equal_unchanged_original(self): self.demo('exception')

    def test_whole_four_record_intakes_preserve_existing_history_and_complete_new_bytes(self):
        for kind, scenario in (('decision', 'synthetic-closure'), ('remediation', 'synthetic-closure'),
                               ('closure', 'synthetic-closure'), ('exception', 'synthetic-exceptions')):
            with self.subTest(kind=kind):
                args, *_ = self.record_arguments(scenario, kind, 'private-' + kind)
                self.compare('record', args)

    def test_whole_observation_intake_private_outputs_equal_original(self):
        import base64
        _, _, row, record = self.selected_transaction('synthetic-closure', 'observation')
        inputs = self.root / 'observation-inputs'
        inputs.mkdir()
        (inputs / 'report.json').write_bytes(base64.b64decode(row['resources'][record['body']['snapshot_ref']['uri']], validate=True))
        (inputs / 'context.json').write_bytes(json.dumps(record['body']['source_context']).encode())
        (inputs / 'trust.json').write_bytes(json.dumps(record['body']['trust']).encode())
        args = ['--synthetic', '--ledger', str(self.root / 'observation-ledger'),
                '--report', str(inputs / 'report.json'), '--context', str(inputs / 'context.json'),
                '--trust', str(inputs / 'trust.json'), '--recorded-at', record['recorded_at'],
                '--policy-version', record['body']['policy_version'], '--expected-revision', '0']
        self.compare('observation', args)


if __name__ == '__main__': unittest.main()
