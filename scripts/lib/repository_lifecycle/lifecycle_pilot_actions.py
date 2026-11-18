"""Retained V1 historical consistency over explicit data and capture adapters.

Historical outputs describe their original scope; they confer no operating
acceptance, personal consent or authority on the executing V2 node.
"""
_OMITTED = object()
INDEX = 'status/governance-lifecycle-pilot-actions.json'
REPORT = 'generated/reports/governance-lifecycle-pilot-actions.md'

class LifecycleActionReport:

    def __init__(self, root, context, *, path_factory):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.INDEX = INDEX
        self.REPORT = REPORT

    def render(self, index):
        return '\n'.join(['# GitHub Pilot Action Validation', '', f"As of: `{index['as_of']}`. Revision: `{index['revision']}`.", f"Finding state: **{index['finding_state']}**. Actions: **{index['counts']['actions']}**.", f"Pilot roles active: `{str(index['roles_active']).lower()}`.", f"Active decision: `{index['active_decision_ref']}`.", f"Active closure: `{index['active_closure_ref']}`.", '', 'The personal channel probe is not action consent. A PASS without a prior failure creates no finding.', 'Decision, progress and closure statements require their own exact request digest and current state revision.', 'Retained consent can be withdrawn; no automated remediation is performed.', 'This is a diagnostic eligibility projection, not operational activation or official consumer status.', index['limitation'], ''])

    def validate(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        index = self.context.actions.project_actions(repo)
        self.context.contracts.require(self.context.adapter.strict_json((repo / INDEX).read_bytes()) == index, 'Pilot action index differs')
        self.context.contracts.require((repo / REPORT).read_text() == self.render(index), 'Pilot action report differs')
        return index
