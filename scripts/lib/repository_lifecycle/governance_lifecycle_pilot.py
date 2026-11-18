"""Retained V1 historical consistency over explicit data and capture adapters.

Historical outputs describe their original scope; they confer no operating
acceptance, personal consent or authority on the executing V2 node.
"""
_OMITTED = object()

class LifecyclePilotReport:

    def __init__(self, root, context, *, path_factory):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.input_pilot_ledger = self.root / 'governance/lifecycle/synthetic-closure'
        self.input_pilot_index = self.root / 'status/governance-lifecycle-closure-index.json'
        self.input_pilot_report = self.root / 'generated/reports/governance-lifecycle-pilot.md'

    def render_report(self, index):
        counts = index['counts']
        lines = ['# CLG-04 Synthetic Lifecycle Pilot', '', f"As of: `{index['as_of']}`", '', 'Environment: **synthetic**. Enforcement: **report-only**. Official state: **false**.', 'Live pilot acceptance: **pending LD-01–05 and LD-07**. Fixture consent does not authenticate a human.', '', f"Transactions: {counts['transactions']}; observations: {counts['observations']}; events: {counts['events']}; closures: {counts.get('closures', 0)}; conflicts: {counts['conflicts']}.", '', '| Finding | State | Evidence | Revision | Occurrences | Closures | Reopenings |', '|---|---|---|---|---|---|---|']
        for finding in index['findings']:
            lines.append(f"| `{finding['finding_id']}` | {finding['state']} | {finding['evidence_status']} | {finding['revision']} | {finding['occurrences']} | {len(finding.get('closure_refs', []))} | {finding.get('reopen_count', 0)} |")
        lines += ['', '## Immutable event history', '', 'The index references the accepted ledger head and each closure. Replay retains completed closure history after reopening; a late older failure does not undo closure.', '', 'This separate pilot does not resolve the original CLG-02/03 conflict, change consumer results or activate live intake.', '']
        return '\n'.join(lines)
