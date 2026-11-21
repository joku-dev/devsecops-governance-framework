"""Lazy ledger-aware input capture; all other source IO retains its contract."""
from lib.synthetic_ledger_budget import DEFAULT, admitted
import os
from pathlib import Path
import stat
from lib.providers.synthetic_lifecycle_io import NativeIO as LifecycleIO, capture_port
from lib.providers.synthetic_ledger_files import LedgerFiles
from lib.providers.synthetic_ledger_effects import error_value
from lib.providers.workbook_import_io import original_error


class NativeIO(LifecycleIO):
    def __init__(self, *args, ledger, transaction_name, ledger_budget=DEFAULT, **kwargs):
        self.ledger_budget = admitted(ledger_budget)
        super().__init__(*args, **kwargs)
        self.ledger = Path(ledger)
        self.ledger_files = LedgerFiles(self, ledger, transaction_name=transaction_name, budget=self.ledger_budget)
        self.transaction_name = transaction_name
        self.ledger_reads = {}
        if self.mode == 'private-candidate':
            from lib.providers.synthetic_ledger_private import CaptureProjection
            self.projection = self.output = CaptureProjection(self)

    def ledger_path(self, path): return Path(path).parent == self.ledger / 'transactions'

    def mkdir(self, *args):
        prior = set(self.touched)
        try: return super().mkdir(*args)
        finally:
            created = {name: value for name, value in self.touched.items()
                       if name not in prior and value['kind'] == 'directory'}
            if created and hasattr(self, 'effect_state'): self.effect_state.mkdir(created)

    def ledger_observe(self, path):
        try: value = Path(path).lstat()
        except (FileNotFoundError, NotADirectoryError): value = None
        if value is not None and stat.S_ISREG(value.st_mode):
            return self.ledger_files.read(path, path)[1]
        info = self.entry(path)
        state = {'kind': info['kind']}
        if info['kind'] != 'missing': state.update(mode=info['mode'], identity=info['identity'])
        return {'snapshot': state, 'metadata': None if info['kind'] == 'missing' else info, 'aliases': []}

    @capture_port
    def read(self, path, label):
        if self.projection is not None and self.projection.tree.affected(path):
            self.check(path, label)
            return self.projection.read(path, label)
        if not self.ledger_path(path): return super().read(path, label)
        spec = self.check(path, label)
        observed = failure = None
        def effect():
            nonlocal observed
            try: raw, observed = self.ledger_files.read(path, label)
            except OSError as error: raise original_error(error, label) from None
            self.remember(path, observed['metadata'])
            self.ledger_reads[path] = raw
            return raw
        try: return self.perform('synthetic-ledger-read', {'selection': spec}, effect, encoding='bytes')
        except OSError as error:
            failure = error_value(error)
            raise
        finally: self.append({'kind': 'synthetic-ledger-read-after', 'selection': spec,
                              'observation': observed, 'failure': failure})

    @capture_port
    def probe(self, path, kind, label):
        if self.projection is not None and self.projection.tree.affected(path):
            self.check(path, label)
            return self.projection.probe(path, kind, label)
        if not self.ledger_path(path): return super().probe(path, kind, label)
        from lib.synthetic_lifecycle_io import PROBES
        from lib.requirement_validation_budget import InputAdmissionError
        if kind not in PROBES: raise InputAdmissionError('synthetic_ledger_original_probe_required')
        spec = self.check(path, label)
        observed = failure = None
        def effect():
            nonlocal observed
            observed = self.ledger_observe(path)
            self.remember(path, observed['metadata'] or {'kind': 'missing'})
            state = observed['snapshot']['kind']
            return state != 'missing' if kind == 'exists' else state == 'file' if kind == 'is_file' else state == 'directory' if kind == 'is_dir' else False
        try: return self.perform('synthetic-ledger-probe', {'selection': spec, 'probe': kind}, effect)
        except OSError as error:
            failure = error_value(error)
            raise
        finally: self.append({'kind': 'synthetic-ledger-probe-after', 'selection': spec, 'probe': kind,
                              'observation': observed, 'failure': failure})
