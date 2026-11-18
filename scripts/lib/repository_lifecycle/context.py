"""Read-only lifecycle validation context, independent of an operating node."""
import json
from pathlib import Path

from lib.repository_lifecycle.contracts import LifecycleContracts
from lib.repository_lifecycle.kernel import LifecycleKernel
from lib.repository_lifecycle.adapter import LifecycleAdapter
from lib.repository_lifecycle.store import LifecycleStore
from lib.repository_lifecycle.decisions import LifecycleDecisions
from lib.repository_lifecycle.closure import LifecycleClosure
from lib.repository_lifecycle.exceptions import LifecycleExceptions

from lib.repository_lifecycle.preparation import LifecyclePreparation
from lib.repository_lifecycle.admission import LifecycleAdmission
from lib.repository_lifecycle.personal import LifecyclePersonalStatements
from lib.repository_lifecycle.actions import LifecyclePilotActions
from lib.repository_lifecycle.operating import LifecycleOperatingAcceptance
from lib.repository_lifecycle.lifecycle_pilot_validation import LifecyclePilotValidationReport
from lib.repository_lifecycle.personal_channel_probe import LifecycleStatementReport
from lib.repository_lifecycle.personal_channel_evidence import LifecycleStatementEvidenceReport
from lib.repository_lifecycle.lifecycle_pilot_actions import LifecycleActionReport
from lib.repository_lifecycle.governance_lifecycle_overview import LifecycleOverview
from lib.repository_lifecycle.governance_lifecycle_viewer import LifecycleViewer
from lib.repository_lifecycle.governance_lifecycle_pilot import LifecyclePilotReport
from lib.repository_lifecycle.governance_lifecycle_exceptions import LifecycleExceptionReport
from lib.repository_lifecycle.ledger import LifecycleLedger

class RepositoryLifecycle:
    def __init__(self, root, *, validator_class, path_factory=Path, provider_factory=None):
        self.root = root
        self.path_factory = path_factory
        options = {'validator_class': validator_class, 'path_factory': path_factory}
        self.contracts = LifecycleContracts(root, self, **options)
        self.adapter = LifecycleAdapter(root, self, **options)
        self.kernel = LifecycleKernel(root, self, **options)
        self.store = LifecycleStore(root, self, **options)
        self.decisions = LifecycleDecisions(root, self, **options)
        self.closure = LifecycleClosure(root, self, **options)
        self.exceptions = LifecycleExceptions(root, self, **options)
        self.preparation = LifecyclePreparation(root, self, path_factory=path_factory)
        self.admission = LifecycleAdmission(root, self, path_factory=path_factory)
        self.personal = LifecyclePersonalStatements(root, self, path_factory=path_factory)
        self.actions = LifecyclePilotActions(root, self, path_factory=path_factory)
        self.operating = LifecycleOperatingAcceptance(root, self, path_factory=path_factory)
        self.lifecycle_pilot_validation = LifecyclePilotValidationReport(root, self, path_factory=path_factory)
        self.personal_channel_probe = LifecycleStatementReport(root, self, path_factory=path_factory)
        self.personal_channel_evidence = LifecycleStatementEvidenceReport(root, self, path_factory=path_factory)
        self.lifecycle_pilot_actions = LifecycleActionReport(root, self, path_factory=path_factory)
        self.governance_lifecycle_overview = LifecycleOverview(root, self, path_factory=path_factory)
        self.governance_lifecycle_viewer = LifecycleViewer(root, self, path_factory=path_factory)
        self.governance_lifecycle_pilot = LifecyclePilotReport(root, self, path_factory=path_factory)
        self.governance_lifecycle_exceptions = LifecycleExceptionReport(root, self, path_factory=path_factory)
        self.ledger = LifecycleLedger(root, self, path_factory=path_factory)
        self.provider = provider_factory(self) if provider_factory is not None else None

    def load_examples(self):
        profile = json.loads((self.root / 'model/governance/lifecycle/synthetic-grs002-profile.json').read_text())
        records = {}
        for path in sorted((self.root / 'docs/examples/governance-lifecycle').glob('*.json')):
            record = json.loads(path.read_text())
            self.contracts.require(record['record_id'] not in records, 'Duplicate example record ID')
            records[record['record_id']] = record
        self.contracts.require({r['record_type'] for r in records.values()} == set(self.contracts.kinds), 'Missing example record kind')
        fixtures = self.root / 'tests/fixtures/governance-lifecycle/resources'
        resources = {'fixture://' + p.name: p.read_bytes() for p in fixtures.glob('*.json')}
        return profile, records, resources

    def validate_examples(self):
        profile, records, resources = self.load_examples()
        self.contracts.validate_test_profile(profile)
        for record in records.values():
            self.contracts.validate_test_record(record, profile, resources)
            if record['record_type'] == 'event':
                self.contracts.check_event_references(record, records)
        closure = records['closure:synthetic-001']
        self.contracts.check_closure_prerequisites(closure, records, profile, resources, as_of=closure['body']['as_of'])
        return {'returncode': 0, 'stdout': f"CLG-01: {len(records)} synthetic records and closure prerequisites valid; no live acceptance or state transition.\n", 'stderr': ''}

    def validate_current(self, ledger, index_path, profile_path):
        profile = self.adapter.strict_json(profile_path.read_bytes())
        transactions = self.store.load_transactions(ledger)
        self.kernel.replay(transactions, profile)
        index = self.adapter.strict_json(index_path.read_bytes())
        self.contracts.require(not transactions or self.contracts.timestamp(index['as_of']) >= self.contracts.timestamp(transactions[-1]['recorded_at']),
                               'Current index cannot hide a later accepted ledger transaction')
        expected = self.kernel.project(transactions, profile, as_of=index['as_of'])
        self.contracts.require(index == expected, 'Lifecycle index differs from the immutable ledger projection')
        return expected

    def validate_default_ledger(self, *, print_line):
        """The V1 subprocess's zero-argument validation, without native flag flows.

        Retained output may describe its source's accepted pilot. This method
        reads and compares that history only; it does not publish it as this
        V2 node's operating state. Native prefix and new-provider checks remain
        separately scoped operations and are never reported as executed here.
        """
        if self.provider is None:
            raise ValueError('explicit_lifecycle_capture_profile_required')
        default_ledger = self.root / 'governance/lifecycle/synthetic'
        self.contracts.require(all(tx['schema_version'] != '0.4.0' for tx in self.store.load_transactions(default_ledger)),
                               'Exceptions require their separate scenario')
        self.preparation.validate_preparation()
        self.lifecycle_pilot_validation.validate()
        self.personal_channel_probe.validate()
        self.personal_channel_evidence.validate()
        self.lifecycle_pilot_actions.validate()
        self.operating.validate()
        index = self.ledger.validate_current()
        pilot = self.ledger.validate_pilot()
        exceptions = self.ledger.validate_exceptions()
        overview = self.governance_lifecycle_overview.validate_overview()
        self.governance_lifecycle_viewer.validate_viewer(overview=overview)
        print_line(f"Lifecycle: exceptions {exceptions['counts']}; original scenario {index['counts']}; synthetic closure pilot {pilot['counts']}; no live activation.")
