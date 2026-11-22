"""Actual two-ledger IO and read-only lstat of original system ancestors.

Root-owned ancestors are not writable product inputs. Their identity, type,
owner and mode are observed without binding unrelated directory timestamps.
Ordinary source reads/writes retain the existing ownership and alias guards.
"""
from pathlib import Path
import os
import stat
from lib.providers.synthetic_ledger_io import NativeIO as LedgerIO
from lib.providers.lifecycle_preflight_io import NativePreflightIO
from lib.providers.synthetic_ledger_files import LedgerFiles
from lib.providers.synthetic_lifecycle_io import capture_port, Inputs
from lib.providers.workbook_import_io import ordinary_ancestors, original_error, failure_value
from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
from lib.pilot_action_ledgers import select, NativeEffectRouter
from lib.consumer_lifecycle_io import roots, link_value, ConsumerLedgerProjection, PrivateConsumerEffects
from lib.synthetic_ledger_budget import PILOT_RUN
from lib.synthetic_ledger_private import PrivateLedgerPort
from lib.providers.synthetic_ledger_private import CaptureProjection
from lib.providers.consumer_lifecycle_output import ConsumerNativeOutput
from lib.providers.consumer_lifecycle_storage import MAX_EVENTS
from lib.requirement_validation_budget import InputAdmissionError


def reserve_consumer(owner):
    if owner.record.sequence >= MAX_EVENTS - 32:
        owner.record.capture_incomplete = True
        raise InputAdmissionError('consumer_event_budget')


class ConsumerInputs(Inputs):
    def reserve(self):
        reserve_consumer(self)


class ConsumerCaptureProjection(CaptureProjection):
    def __init__(self, owner):
        super().__init__(owner)
        self.tree = ConsumerLedgerProjection(self.resolve, owner.ledgers)


class ConsumerFileRouter:
    def __init__(self, owner, transaction_name):
        self.parts = {name: LedgerFiles(owner, name, transaction_name=transaction_name, budget=PILOT_RUN)
                      for name in owner.ledgers}
    def read(self, path, label):
        return self.parts[select(path, self.parts)].read(path, label)
    def directory(self, path):
        return self.parts[select(str(path), self.parts)].directory(path)


class NativeConsumerIO(LedgerIO, NativePreflightIO):
    def __init__(self, *args, source, transaction_name, **kwargs):
        self.ledgers = roots(source)
        super().__init__(*args, ledger=self.ledgers[0], transaction_name=transaction_name, ledger_budget=PILOT_RUN, **kwargs)
        self.ledger_files = ConsumerFileRouter(self, transaction_name)
        self.consumer_links = {}
        self.data = ConsumerInputs(self.record)
        if self.mode == 'private-candidate':
            self.projection = self.output = ConsumerCaptureProjection(self)
        else:
            self.output = ConsumerNativeOutput(self)

    def reserve(self):
        reserve_consumer(self)

    def ledger_path(self, path):
        return any(Path(path).parent == Path(name) / 'transactions' for name in self.ledgers)

    @capture_port
    def probe(self, path, kind, label):
        if kind != 'is_symlink' or self.projection is not None and self.projection.tree.affected(path):
            return super().probe(path, kind, label)
        selection = self.check(path, label)
        def inspect():
            selected = Path(path)
            try:
                ordinary_ancestors(selected.parent)
                value = selected.lstat()
            except (FileNotFoundError, NotADirectoryError):
                return {'kind': 'missing'}
            kind = ('link' if stat.S_ISLNK(value.st_mode) else 'directory' if stat.S_ISDIR(value.st_mode)
                    else 'file' if stat.S_ISREG(value.st_mode) else 'other')
            return {'kind': kind, 'mode': stat.S_IMODE(value.st_mode), 'identity': [value.st_dev, value.st_ino], 'uid': value.st_uid}
        def effect():
            try:
                before = inspect()
                return {'snapshot': before, 'after': inspect(), 'failure': None}
            except OSError as caught:
                return {'snapshot': None, 'after': None, 'failure': failure_value(original_error(caught, label))}
        wire = self.perform('consumer-original-link-probe', {'selection': selection}, effect)
        return link_value(self, path, label, wire)


def native_effects(owner, *, source, transaction_name):
    if owner.mode == 'private-candidate':
        return PrivateConsumerEffects(owner, str(Path(source) / 'governance/consumer-lifecycle'))
    return NativeEffectRouter(owner, roots(source), factory=NativeLedgerEffects, transaction_name=transaction_name)
