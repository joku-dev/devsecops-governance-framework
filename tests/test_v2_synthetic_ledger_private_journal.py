"""Whole six original mains versus lazy private capture and no-native replay."""
from pathlib import Path, PurePosixPath
import hashlib, json, os, subprocess, sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
import test_v2_synthetic_ledger_private_oracle as reference
import test_v2_synthetic_ledger_core as core_reference
from lib.synthetic_ledger_execution import execute
from lib.synthetic_ledger_context import PROGRAMS
from lib.synthetic_lifecycle_application import closed_validator
from lib.providers.synthetic_ledger_io import NativeIO
from lib.synthetic_ledger_io import ReplayIO
from lib.synthetic_ledger_private import PrivateLedgerPort
from lib.providers.synthetic_lifecycle_storage import Record, read_record
from lib.repository_lifecycle.context import RepositoryLifecycle


class WholePrivateLedgerJournal(reference.WholePrivateLedgerOracle):
    def compare(self, name, args, *, expected_code=0):
        before = core_reference.snapshot(self.root)
        driver = ('import os,runpy,sys;os.umask(0o077);sys.argv=sys.argv[1:];'
                  'runpy.run_path(sys.argv[0],run_name="__main__")')
        original = subprocess.run([sys.executable, '-B', '-c', driver,
            str(self.root / 'scripts' / PROGRAMS[name][0]), *args], cwd=self.root,
            capture_output=True, timeout=90,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(self.root / 'scripts')})
        self.assertEqual(original.returncode, expected_code, original.stderr[-2500:])
        after = core_reference.snapshot(self.root)
        core_reference.restore(self.root, before)
        private = Path(self.temp.name).resolve() / 'private'
        private.mkdir(mode=0o700, exist_ok=True)
        record = Record(private / 'records', {'program': name, 'argv': args}, {'prototype': True})
        record.append({'kind': 'execution-intent'})
        parser = RepositoryLifecycle(ROOT, validator_class=None)
        name_of = lambda raw: parser.kernel.transaction_name(parser.adapter.strict_json(raw))
        selected = []
        def factory(binding):
            inputs = NativeIO(record, mode='private-candidate', cwd=str(self.root), private_state=private,
                product_root=ROOT, ledger=binding['path'], transaction_name=name_of)
            effects = PrivateLedgerPort(inputs, binding['path'])
            selected.append((inputs, effects))
            return inputs, effects
        result = execute(str(self.root), str(self.root), name, args, port_factory=factory,
            validator_factory=lambda io: closed_validator(io, {'resources': []}))
        kernel = result['kernel_result']; inputs, effects = selected[0]
        self.assertEqual(kernel['exit_code'], original.returncode, kernel)
        self.assertEqual(kernel['stdout'].encode(), original.stdout)
        if kernel['kernel_exception'] is None: self.assertEqual(kernel['stderr'].encode(), original.stderr)
        else:
            error = kernel['kernel_exception']
            self.assertTrue(original.stderr.decode().endswith(error['type'] + ': ' + error['message'] + '\n'))
        self.assertEqual(core_reference.snapshot(self.root), before, 'Private model must not change selected source')
        files, directories = dict(before[0]), dict(before[1])
        for path, value in inputs.projected_changes.items():
            relative = str(PurePosixPath(path).relative_to(str(self.root)))
            if value['kind'] == 'file': files[relative] = (inputs.projection.resolve(value['content']), value['mode'])
            elif value['kind'] == 'directory': directories[relative] = value['mode']
            elif value['kind'] == 'missing': files.pop(relative, None); directories.pop(relative, None)
            else: self.fail('Unexpected private changed node')
        self.assertEqual((files, directories), after)
        self.assertEqual(inputs.touched, {})
        self.assertEqual(effects.descriptors, {})
        self.assertFalse(record.capture_incomplete)
        record.finish('complete', {'exit_code': kernel['exit_code']}, {})
        _, _, _, events, _, _ = read_record(record.root)
        blobs = {p.name: p.read_bytes() for p in record.blobs.iterdir()}; seen = set()
        def blob(ref):
            raw = blobs[ref['sha256']]
            self.assertEqual(hashlib.sha256(raw).hexdigest(), ref['sha256']); self.assertEqual(len(raw), ref['bytes'])
            seen.add(ref['sha256'])
            return raw
        replay_inputs = ReplayIO(events, blob, 'private-candidate', str(self.root),
            ledger=result['binding']['path'], transaction_name=name_of)
        replay_effects = PrivateLedgerPort(replay_inputs, result['binding']['path'])
        hidden = self.root.parent / 'hidden-private-source'
        self.root.rename(hidden)
        try:
            with (patch('os.open', side_effect=AssertionError('No native filesystem')),
                  patch('pathlib.Path.read_bytes', side_effect=AssertionError('No selected data')),
                  patch('subprocess.Popen', side_effect=AssertionError('No programs')),
                  patch('socket.create_connection', side_effect=AssertionError('No network'))):
                replayed = execute(str(self.root), str(self.root), name, args,
                    port_factory=lambda binding: (replay_inputs, replay_effects),
                    validator_factory=lambda io: closed_validator(io, {'resources': []}))
            self.assertEqual(replayed['kernel_result'], kernel)
            self.assertEqual(replayed['binding'], result['binding'])
            self.assertEqual(replay_inputs.projected_changes, inputs.projected_changes)
            self.assertEqual(replay_inputs.files, inputs.files)
            self.assertEqual(replay_effects.descriptors, {})
            replay_inputs.finish()
            self.assertEqual(seen, set(blobs))
        finally: hidden.rename(self.root)
        return None, inputs, events

    def test_original_read_only_lock_error_changes_neither_source_nor_candidate_history(self):
        ledger = self.root / 'read-only-ledger'
        ledger.mkdir()
        (ledger / '.append.lock').write_bytes(b'')
        (ledger / '.append.lock').chmod(0o400)
        args = ['--ledger', str(ledger), '--output', str(self.root / 'index.json')]
        self.compare('synthetic', args, expected_code=1)

    def test_original_output_inside_history_guard_precedes_all_candidate_effects(self):
        ledger = self.root / 'guard-ledger'
        args = ['--ledger', str(ledger), '--output', str(ledger / 'forbidden-index.json')]
        self.compare('synthetic', args, expected_code=1)

    def test_original_directory_output_error_preserves_complete_candidate_history(self):
        directory = self.root / 'output-directory'
        directory.mkdir()
        args = ['--ledger', str(self.root / 'partial-ledger'), '--output', str(directory)]
        self.compare('synthetic', args, expected_code=1)

    def test_original_equals_relative_unicode_paths_use_the_declared_cwd(self):
        self.compare('synthetic', ['--ledger=state/Ü ledger', '--output=exports/日本語.json'])

    def test_existing_pending_canonical_source_pair_remains_readable_without_export(self):
        args, ledger, *_ = self.record_arguments('synthetic-closure', 'decision', 'source-pair')
        canonical = next((ledger / 'transactions').glob('*.json'))
        pending = ledger / 'transactions/.pending-retained-source'
        os.link(canonical, pending)
        before = core_reference.pending_snapshot(ledger)
        self.compare('record', args)
        self.assertEqual(core_reference.pending_snapshot(ledger), before)

    def test_direct_private_alias_preimage_is_bound_and_replayed_without_source(self):
        args, ledger, *_ = self.record_arguments('synthetic-closure', 'decision', 'direct-pair')
        canonical = next((ledger / 'transactions').glob('*.json'))
        os.link(canonical, ledger / 'transactions/.pending-direct-preimage')
        before = core_reference.pending_snapshot(ledger)
        private = Path(self.temp.name).resolve() / 'direct-private'
        private.mkdir(mode=0o700)
        record = Record(private / 'records', {'prototype': 'alias-preimage'}, {'prototype': True})
        record.append({'kind': 'execution-intent'})
        parser = RepositoryLifecycle(ROOT, validator_class=None)
        name_of = lambda raw: parser.kernel.transaction_name(parser.adapter.strict_json(raw))
        inputs = NativeIO(record, mode='private-candidate', cwd=str(self.root),
            private_state=private, product_root=ROOT, ledger=str(ledger), transaction_name=name_of)
        inputs.projection.prepare(str(canonical), str(canonical))
        record.finish('complete', {'exit_code': 0, 'prototype': 'alias-preimage'}, {})
        _, _, _, events, _, _ = read_record(record.root)
        blobs = {p.name: p.read_bytes() for p in record.blobs.iterdir()}
        seen = set()
        def blob(ref):
            raw = blobs[ref['sha256']]
            self.assertEqual(hashlib.sha256(raw).hexdigest(), ref['sha256'])
            self.assertEqual(len(raw), ref['bytes'])
            seen.add(ref['sha256'])
            return raw
        self.assertTrue(any(row['kind'] == 'synthetic-ledger-private-alias-preimage' for row in events))
        self.assertEqual(core_reference.pending_snapshot(ledger), before)
        replay = ReplayIO(events, blob, 'private-candidate', str(self.root),
                          ledger=str(ledger), transaction_name=name_of)
        hidden = self.root.parent / 'hidden-direct-pair'
        self.root.rename(hidden)
        try:
            with patch('os.open', side_effect=AssertionError('No native replay')):
                replay.projection.prepare(str(canonical), str(canonical))
            replay.finish()
            self.assertEqual(seen, set(blobs))
        finally:
            hidden.rename(self.root)
