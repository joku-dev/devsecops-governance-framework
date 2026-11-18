"""Retained V1 historical consistency over explicit data and capture adapters.

Historical outputs describe their original scope; they confer no operating
acceptance, personal consent or authority on the executing V2 node.
"""
_OMITTED = object()
INDEX = 'status/governance-lifecycle-live-validation.json'
REPORT = 'generated/reports/governance-lifecycle-live-validation.md'

class LifecyclePilotValidationReport:

    def __init__(self, root, context, *, path_factory):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.INDEX = INDEX
        self.REPORT = REPORT

    def render(self, index):
        return f"# Durable CLG Pilot Validation\n\nDiagnostic pilot eligibility only; live activation and personal decisions remain separate.\n\nRecorded through: `{index['as_of']}`. Official state: `false`.\n\nReceipts: {index['counts']['receipts']}; eligible: {index['counts']['eligible']}; quarantined: {index['counts']['quarantined']}.\n\nLatest captured GRS-002: `{index['latest_criterion_result']}`. Pilot finding: `{index['pilot_finding']}`. PASS never creates or closes a Finding.\n"

    def validate(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        index = self.context.admission.project_receipts(self.context.store.load_transactions(repo / self.context.admission.VALIDATION_LEDGER), self.context.admission.load_operating(repo))
        self.context.contracts.require(self.context.adapter.strict_json((repo / INDEX).read_bytes()) == index, 'Pilot validation index differs')
        self.context.contracts.require((repo / REPORT).read_text() == self.render(index), 'Pilot validation report differs')
        return index
