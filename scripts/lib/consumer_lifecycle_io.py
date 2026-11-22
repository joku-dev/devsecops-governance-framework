"""Two consumer ledgers and closed original ancestor-link observations."""
from pathlib import PurePosixPath as P
from lib.synthetic_ledger_io import ReplayIO as LedgerReplay, observation
from lib.lifecycle_preflight_io import ReplayPreflightIO
from lib.pilot_action_ledgers import DualReplayProjection, select, NativeEffectRouter
from lib.synthetic_ledger_private import PrivateLedgerPort
from lib.synthetic_ledger_projection import LedgerProjection
from lib.synthetic_ledger_replay_effects import ReplayLedgerEffects
from lib.synthetic_ledger_budget import PILOT_RUN
from lib.synthetic_lifecycle_io import path_spec
from lib.workbook_import_io import error_wire
from lib.consumer_lifecycle_output import ConsumerReplayOutput
from lib.requirement_validation_replay import IntegrityError

LEDGERS = ('governance/consumer-lifecycle/observations', 'governance/consumer-lifecycle/actions')


def roots(source):
    return tuple(str(P(source) / name) for name in LEDGERS)


class ConsumerLedgerProjection(LedgerProjection):
    def __init__(self, blob, ledgers):
        self.ledgers = tuple(ledgers)
        super().__init__(blob, budget=PILOT_RUN, ledger=self.ledgers[0])
    def bounded_scope(self, path, value):
        prior = self.ledger
        try:
            if any(P(path).parent == P(name) / 'transactions' for name in self.ledgers):
                self.ledger = select(path, self.ledgers)
            return super().bounded_scope(path, value)
        finally:
            self.ledger = prior


class ConsumerReplayProjection(DualReplayProjection):
    def __init__(self, owner):
        super().__init__(owner)
        self.tree = ConsumerLedgerProjection(owner.blob, owner.ledgers)


class PrivateConsumerEffects(PrivateLedgerPort):
    def path(self, path):
        name, label = super().path(path)
        select(name, self.io.ledgers)
        return name, label
    def link(self, source, target):
        source_name, _ = self.path(source)
        target_name, _ = self.path(target)
        if select(source_name, self.io.ledgers) != select(target_name, self.io.ledgers):
            raise IntegrityError('consumer_cross_ledger_publication_forbidden')
        return super().link(source, target)


def link_snapshot(value):
    if value == {'kind': 'missing'}:
        return value
    if (type(value) is not dict or set(value) != {'kind', 'mode', 'identity', 'uid'}
            or value['kind'] not in ('file', 'directory', 'link', 'other')
            or type(value['mode']) is not int or not 0 <= value['mode'] <= 0o7777
            or type(value['uid']) is not int or value['uid'] < 0
            or type(value['identity']) is not list or len(value['identity']) != 2
            or any(type(n) is not int or n < 0 for n in value['identity'])):
        raise IntegrityError('consumer_original_link_snapshot_changed')
    return value


def link_value(owner, path, label, wire):
    if type(wire) is not dict or set(wire) != {'snapshot', 'after', 'failure'}:
        raise IntegrityError('consumer_original_link_observation_changed')
    if wire['failure'] is not None:
        if wire['snapshot'] is not None or wire['after'] is not None:
            raise IntegrityError('consumer_failed_link_observation_changed')
        raise error_wire(wire['failure'], label)
    value = link_snapshot(wire['snapshot'])
    if value != link_snapshot(wire['after']):
        raise IntegrityError('consumer_link_replaced_during_observation')
    prior = owner.consumer_links.get(path)
    if prior is not None and prior != value and path not in owner.touched:
        raise IntegrityError('consumer_original_link_binding_changed')
    owner.consumer_links[path] = value
    return value['kind'] == 'link'


class ReplayConsumerIO(LedgerReplay, ReplayPreflightIO):
    def __init__(self, *args, source, transaction_name, **kwargs):
        self.ledgers = roots(source)
        super().__init__(*args, ledger=self.ledgers[0], transaction_name=transaction_name, ledger_budget=PILOT_RUN, **kwargs)
        self.consumer_links = {}
        if self.mode == 'private-candidate':
            self.projection = self.output = ConsumerReplayProjection(self)
        else:
            self.output = ConsumerReplayOutput(self)

    def ledger_path(self, path):
        return any(P(path).parent == P(name) / 'transactions' for name in self.ledgers)

    def remember_ledger(self, path, value):
        info = observation(value, self.blob, path=path, ledger=select(path, self.ledgers),
                           transaction_name=self.transaction_name, max_file=self.ledger_budget.file) or {'kind': 'missing'}
        if path in self.metadata and self.metadata[path] != info:
            raise IntegrityError('consumer_repeated_ledger_metadata_changed')
        self.metadata[path] = info

    def probe(self, path, kind, label):
        if kind != 'is_symlink' or self.projection is not None and self.projection.tree.affected(path):
            return super().probe(path, kind, label)
        selection = path_spec(path, label, self.cwd)
        ok, wire = self.outcome('consumer-original-link-probe', {'selection': selection}, 'json')
        if not ok:
            raise IntegrityError('consumer_link_capture_incomplete')
        return link_value(self, path, label, wire)


def replay_effects(owner, *, source, transaction_name):
    if owner.mode == 'private-candidate':
        return PrivateConsumerEffects(owner, str(P(source) / 'governance/consumer-lifecycle'))
    return NativeEffectRouter(owner, roots(source), factory=ReplayLedgerEffects, transaction_name=transaction_name)
