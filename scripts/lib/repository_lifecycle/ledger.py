"""Retained V1 historical consistency over explicit data and capture adapters.

Historical outputs describe their original scope; they confer no operating
acceptance, personal consent or authority on the executing V2 node.
"""
_OMITTED = object()
LEDGER_PATH = 'governance/lifecycle/synthetic'
PILOT_LEDGER_PATH = 'governance/lifecycle/synthetic-closure'
EXCEPTION_LEDGER_PATH = 'governance/lifecycle/synthetic-exceptions'
EXCEPTION_PROFILE_PATH = 'model/governance/lifecycle/synthetic-exception-profile.json'
PROFILE_PATH = 'model/governance/lifecycle/synthetic-grs002-profile.json'

class LifecycleLedger:

    def __init__(self, root, context, *, path_factory):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.LEDGER_PATH = LEDGER_PATH
        self.PILOT_LEDGER_PATH = PILOT_LEDGER_PATH
        self.EXCEPTION_LEDGER_PATH = EXCEPTION_LEDGER_PATH
        self.EXCEPTION_PROFILE_PATH = EXCEPTION_PROFILE_PATH
        self.PROFILE_PATH = PROFILE_PATH
        self.input_ledger_paths = (LEDGER_PATH, PILOT_LEDGER_PATH, EXCEPTION_LEDGER_PATH, self.context.admission.VALIDATION_LEDGER, self.context.actions.ACTION_LEDGER)

    def validate_current(self, ledger=_OMITTED, index_path=_OMITTED, profile_path=_OMITTED):
        if ledger is _OMITTED:
            ledger = self.root / 'governance/lifecycle/synthetic'
        if index_path is _OMITTED:
            index_path = self.root / 'status/governance-lifecycle-synthetic-index.json'
        if profile_path is _OMITTED:
            profile_path = self.root / 'model/governance/lifecycle/synthetic-grs002-profile.json'
        profile = self.context.adapter.strict_json(self.path_factory(profile_path).read_bytes())
        transactions = self.context.store.load_transactions(ledger)
        self.context.kernel.replay(transactions, profile)
        index = self.context.adapter.strict_json(self.path_factory(index_path).read_bytes())
        self.context.contracts.require(not transactions or self.context.contracts.timestamp(index['as_of']) >= self.context.contracts.timestamp(transactions[-1]['recorded_at']), 'Current index cannot hide a later accepted ledger transaction')
        expected = self.context.kernel.project(transactions, profile, as_of=index['as_of'])
        self.context.contracts.require(index == expected, 'Lifecycle index differs from the immutable ledger projection')
        return expected

    def validate_pilot(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        render_report = self.context.governance_lifecycle_pilot.render_report
        root = self.path_factory(repo)
        self.context.contracts.require(all((tx['schema_version'] != '0.4.0' for tx in self.context.store.load_transactions(root / PILOT_LEDGER_PATH))), 'Exceptions require their separate scenario; closure publisher scope is unchanged')
        index = self.validate_current(root / PILOT_LEDGER_PATH, root / 'status/governance-lifecycle-closure-index.json', root / PROFILE_PATH)
        report = root / 'generated/reports/governance-lifecycle-pilot.md'
        self.context.contracts.require(report.read_text() == render_report(index), 'Lifecycle pilot report differs from projection')
        return index

    def validate_exceptions(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        render_report = self.context.governance_lifecycle_exceptions.render_report
        root = self.path_factory(repo)
        index = self.validate_current(root / EXCEPTION_LEDGER_PATH, root / 'status/governance-lifecycle-exception-index.json', root / PROFILE_PATH)
        self.context.contracts.require((root / 'generated/reports/governance-lifecycle-exceptions.md').read_text() == render_report(index), 'Exception report differs from projection')
        return index
