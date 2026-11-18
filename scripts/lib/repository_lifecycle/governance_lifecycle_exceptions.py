"""Retained V1 historical consistency over explicit data and capture adapters.

Historical outputs describe their original scope; they confer no operating
acceptance, personal consent or authority on the executing V2 node.
"""
_OMITTED = object()

class LifecycleExceptionReport:

    def __init__(self, root, context, *, path_factory):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.input_exception_ledger = self.root / 'governance/lifecycle/synthetic-exceptions'
        self.input_exception_index = self.root / 'status/governance-lifecycle-exception-index.json'
        self.input_exception_report = self.root / 'generated/reports/governance-lifecycle-exceptions.md'

    def render_report(self, index):
        lines = ['# CLG-05 Synthetic Exceptions', '', f"As of: `{index['as_of']}`", '', 'Environment: **synthetic**; **report-only**; official state: **false**.', 'Coverage refers to explicitly accepted failing observations, not unobserved resources or future failures.', 'Fixture consent does not authenticate real authority. Live acceptance remains pending.', '', '| Finding state | Evidence | Coverage | Covered observations | Uncovered observations | Renewed decision required |', '|---|---|---|---|---|---|']
        for finding in index['findings']:
            t = finding.get('exception_treatment', {})
            lines.append(f"| {finding['state']} | {finding['evidence_status']} | {t.get('coverage', 'none')} | {len(t.get('covered_observation_refs', []))} | {len(t.get('uncovered_observation_refs', []))} | {str(t.get('renewed_decision_required', False)).lower()} |")
        lines += ['', '| Exception record | Disposition | Effective status | Valid from | Expires at (exclusive) |', '|---|---|---|---|---|']
        for finding in index['findings']:
            for record in finding.get('exception_treatment', {}).get('exception_records', []):
                lines.append(f"| `{record['record_ref']['id']}` | {record['disposition']} | {record['status']} | {record['valid_from']} | {record['expires_at']} |")
        lines += ['', 'Risk acceptance does not count as remediation or closure. Finding state, conflicts and work progress remain independently visible in the JSON index.', '']
        return '\n'.join(lines)
