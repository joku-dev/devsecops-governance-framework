"""Entire original five synthetic lifecycle generators over explicit ports.

No selected source program is imported; source history remains declared data.
"""

from __future__ import annotations

from collections import Counter

import base64,hashlib,json,re

_OMITTED=object()

class SyntheticIndex:

    def __init__(self, root, context, *, path_factory, argument_parser, argv, overview=None):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.argument_parser = argument_parser
        self.argv = argv
        self.overview = overview
        self.description = 'Generate a synthetic-only index from the complete immutable lifecycle ledger.'
        self.DEFAULT_LEDGER = self.root / 'governance/lifecycle/synthetic'
        self.DEFAULT_INDEX = self.root / 'status/governance-lifecycle-synthetic-index.json'
        self.DEFAULT_PROFILE = self.root / 'model/governance/lifecycle/synthetic-grs002-profile.json'

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--ledger', type=self.path_factory, default=self.DEFAULT_LEDGER)
        parser.add_argument('--output', type=self.path_factory, default=self.DEFAULT_INDEX)
        parser.add_argument('--as-of', required=True)
        args = parser.parse_args(self.argv)
        self.context.contracts.require(not args.output.resolve().is_relative_to(args.ledger.resolve()), 'Projection must be outside the immutable ledger')
        index = self.context.kernel.project(self.context.store.load_transactions(args.ledger), self.context.adapter.strict_json(self.DEFAULT_PROFILE.read_bytes()), as_of=args.as_of)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(self.context.adapter.json_bytes(index))
        print(f"Wrote {args.output}; synthetic only, {index['counts']['findings']} findings")

class SyntheticPilot:

    def __init__(self, root, context, *, path_factory, argument_parser, argv, overview=None):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.argument_parser = argument_parser
        self.argv = argv
        self.overview = overview
        self.description = 'Generate explicit-time synthetic CLG-04 projection and pilot report.'
        self.PILOT_LEDGER = self.root / 'governance/lifecycle/synthetic-closure'
        self.PILOT_INDEX = self.root / 'status/governance-lifecycle-closure-index.json'
        self.PILOT_REPORT = self.root / 'generated/reports/governance-lifecycle-pilot.md'
        self.DEFAULT_PROFILE = root / 'model/governance/lifecycle/synthetic-grs002-profile.json'

    def render_report(self, index):
        counts = index['counts']
        lines = ['# CLG-04 Synthetic Lifecycle Pilot', '', f"As of: `{index['as_of']}`", '', 'Environment: **synthetic**. Enforcement: **report-only**. Official state: **false**.', 'Live pilot acceptance: **pending LD-01–05 and LD-07**. Fixture consent does not authenticate a human.', '', f"Transactions: {counts['transactions']}; observations: {counts['observations']}; events: {counts['events']}; closures: {counts.get('closures', 0)}; conflicts: {counts['conflicts']}.", '', '| Finding | State | Evidence | Revision | Occurrences | Closures | Reopenings |', '|---|---|---|---|---|---|---|']
        for finding in index['findings']:
            lines.append(f"| `{finding['finding_id']}` | {finding['state']} | {finding['evidence_status']} | {finding['revision']} | {finding['occurrences']} | {len(finding.get('closure_refs', []))} | {finding.get('reopen_count', 0)} |")
        lines += ['', '## Immutable event history', '', 'The index references the accepted ledger head and each closure. Replay retains completed closure history after reopening; a late older failure does not undo closure.', '', 'This separate pilot does not resolve the original CLG-02/03 conflict, change consumer results or activate live intake.', '']
        return '\n'.join(lines)

    def generate(self, ledger, index_path, report_path, *, as_of):
        for path in (index_path, report_path):
            self.context.contracts.require(not path.resolve().is_relative_to(ledger.resolve()), 'Generated output must be outside immutable history')
        self.context.contracts.require(index_path.resolve() != report_path.resolve(), 'Index and report paths must differ')
        index = self.context.kernel.project(self.context.store.load_transactions(ledger), self.context.adapter.strict_json(self.DEFAULT_PROFILE.read_bytes()), as_of=as_of)
        for path, data in ((index_path, self.context.adapter.json_bytes(index)), (report_path, self.render_report(index).encode())):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return index

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--ledger', type=self.path_factory, default=self.PILOT_LEDGER)
        parser.add_argument('--output', type=self.path_factory, default=self.PILOT_INDEX)
        parser.add_argument('--report', type=self.path_factory, default=self.PILOT_REPORT)
        parser.add_argument('--as-of', required=True)
        args = parser.parse_args(self.argv)
        index = self.generate(args.ledger, args.output, args.report, as_of=args.as_of)
        print(f"Generated synthetic pilot: {index['counts']}; live acceptance pending.")

class SyntheticExceptions:

    def __init__(self, root, context, *, path_factory, argument_parser, argv, overview=None):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.argument_parser = argument_parser
        self.argv = argv
        self.overview = overview
        self.description = 'Generate a synthetic exception projection/report at an explicit evaluation instant.'
        self.EXCEPTION_LEDGER = self.root / 'governance/lifecycle/synthetic-exceptions'
        self.EXCEPTION_INDEX = self.root / 'status/governance-lifecycle-exception-index.json'
        self.EXCEPTION_REPORT = self.root / 'generated/reports/governance-lifecycle-exceptions.md'
        self.DEFAULT_PROFILE = root / 'model/governance/lifecycle/synthetic-grs002-profile.json'

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

    def generate(self, ledger, output, report, *, as_of):
        for path in (output, report):
            self.context.contracts.require(not path.resolve().is_relative_to(ledger.resolve()), 'Output must be outside immutable history')
        self.context.contracts.require(output.resolve() != report.resolve(), 'Index and report paths must differ')
        index = self.context.kernel.project(self.context.store.load_transactions(ledger), self.context.adapter.strict_json(self.DEFAULT_PROFILE.read_bytes()), as_of=as_of)
        for path, data in ((output, self.context.adapter.json_bytes(index)), (report, self.render_report(index).encode())):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return index

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--ledger', type=self.path_factory, default=self.EXCEPTION_LEDGER)
        parser.add_argument('--output', type=self.path_factory, default=self.EXCEPTION_INDEX)
        parser.add_argument('--report', type=self.path_factory, default=self.EXCEPTION_REPORT)
        parser.add_argument('--as-of', required=True)
        args = parser.parse_args(self.argv)
        result = self.generate(args.ledger, args.output, args.report, as_of=args.as_of)
        print(f"Synthetic exception projection: {result['counts']}; no waiver-based closure.")

class SyntheticOverview:

    def __init__(self, root, context, *, path_factory, argument_parser, argv, overview=None):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.argument_parser = argument_parser
        self.argv = argv
        self.overview = overview
        self.description = 'Replay three separate synthetic histories into an explicit-time overview.'
        self.SCENARIOS = ('synthetic', 'synthetic-closure', 'synthetic-exceptions')
        self.PROFILE = 'model/governance/lifecycle/synthetic-grs002-profile.json'
        self.OUTPUT = 'status/governance-lifecycle-overview.json'
        self.REPORT = 'generated/reports/governance-lifecycle-overview.md'
        self.EVENT_TYPES = ('finding_opened', 'observation_added', 'clarification_required', 'decision_recorded', 'remediation_recorded', 'finding_closed', 'finding_reopened', 'exception_recorded')

    def tally(self, values, keys):
        counts = Counter(values)
        self.context.contracts.require(set(counts) <= set(keys), 'Unsupported metric category; reporting contract needs review')
        return {key: counts[key] for key in keys}

    def summarize(self, transactions, profile, *, as_of):
        index = self.context.kernel.project(transactions, profile, as_of=as_of)
        visible = [tx for tx in transactions if self.context.contracts.timestamp(tx['recorded_at']) <= self.context.contracts.timestamp(as_of)]
        events = [{'transaction_ref': self.context.kernel.transaction_ref(tx), 'event_ref': self.context.contracts.record_ref(tx['event']), 'finding_id': tx['event']['finding']['finding_id'], 'revision': tx['event']['body']['revision'], 'event_type': tx['event']['body']['event_type'], 'recorded_at': tx['event']['recorded_at'], 'effective_at': tx['event']['body']['effective_at']} for tx in visible if tx['event']]
        observations = [tx['observation'] for tx in visible if 'observation' in tx and tx['outcome'] == 'accepted']
        cases = [case for f in index['findings'] for case in f.get('remediation_cases', [])]
        exceptions = [record for f in index['findings'] for record in f.get('exception_treatment', {}).get('exception_records', [])]
        metrics = {'records': {name: index['counts'].get(name, 0) for name in ('transactions', 'observations', 'events', 'conflicts', 'decisions', 'remediations', 'closures', 'exceptions')}, 'event_types': self.tally((event['event_type'] for event in events), self.EVENT_TYPES), 'accepted_observation_results': self.tally((r['body']['result'] for r in observations), ('pass', 'fail')), 'current_finding_states': self.tally((f['state'] for f in index['findings']), ('open', 'closed', 'needs_clarification')), 'current_remediation_progress': self.tally((case['progress'] for case in cases), ('planned', 'in_progress', 'completed')), 'current_overdue_cases': sum((case['overdue'] for case in cases)), 'current_exception_statuses': self.tally((record['status'] for record in exceptions), ('scheduled', 'active', 'expired', 'revoked', 'rejected', 'withdrawal_recorded')), 'current_coverage_by_finding': self.tally((f.get('exception_treatment', {}).get('coverage', 'not_evaluated') for f in index['findings']), ('not_evaluated', 'not_applicable', 'none', 'partial', 'full')), 'current_findings_needing_renewed_decision': sum((f.get('exception_treatment', {}).get('renewed_decision_required', False) for f in index['findings']))}
        return {'projection': index, 'metrics': metrics, 'events': events}

    def build_overview(self, repo=_OMITTED, *, as_of):
        if repo is _OMITTED:
            repo = self.root
        root = self.path_factory(repo)
        profile = self.context.adapter.strict_json((root / self.PROFILE).read_bytes())
        scenarios = []
        for name in self.SCENARIOS:
            ledger_path = f'governance/lifecycle/{name}'
            ledger = root / ledger_path
            self.context.contracts.require(ledger.is_dir() and (ledger / 'transactions').is_dir(), 'Required scenario ledger is missing')
            result = self.summarize(self.context.store.load_transactions(ledger), profile, as_of=as_of)
            scenarios.append({'scenario_id': name, 'ledger_path': ledger_path, **result})
        overview = {'schema_version': '0.1.0', 'report_type': 'governance-lifecycle-synthetic-overview', 'environment': 'synthetic', 'official_state': False, 'enforcement': 'report_only', 'as_of': as_of, 'aggregation': 'separate_scenarios', 'scenarios': scenarios}
        self.context.contracts.schema_validator('overview').validate(overview)
        return overview

    def render_report(self, overview):
        lines = ['# CLG-06.1 Synthetic Lifecycle Overview', '', f"As of: `{overview['as_of']}`", '', 'Environment: **synthetic**; **report-only**; official state: **false**.', 'These are separate test histories sharing a finding identity, not three portfolio repositories.', 'No cross-scenario totals or production performance claims are calculated.', 'Live acceptance remains pending LD-01–05 and LD-07; fixture consent is not authenticated human approval.', '', '| Scenario | Open | Closed | Clarification | Accepted FAIL / PASS | Quarantines | Closure events | Reopen events |', '|---|---:|---:|---:|---:|---:|---:|---:|']
        for scenario in overview['scenarios']:
            m = scenario['metrics']
            states, results, events = (m['current_finding_states'], m['accepted_observation_results'], m['event_types'])
            lines.append(f"| {scenario['scenario_id']} | {states['open']} | {states['closed']} | {states['needs_clarification']} | {results['fail']} / {results['pass']} | {m['records']['conflicts']} | {events['finding_closed']} | {events['finding_reopened']} |")
        lines += ['', 'Historical closure events remain counted after reopening. PASS, completed work and waiver coverage do not themselves close findings.', '', '| Scenario | Work cases: planned / in progress / completed | Overdue cases | Coverage by finding | Renewed decision needed |', '|---|---|---:|---|---:|']
        for scenario in overview['scenarios']:
            m = scenario['metrics']
            work = m['current_remediation_progress']
            coverage = ', '.join((f'{key}: {count}' for key, count in m['current_coverage_by_finding'].items() if count)) or 'no findings'
            lines.append(f"| {scenario['scenario_id']} | {work['planned']} / {work['in_progress']} / {work['completed']} | {m['current_overdue_cases']} | {coverage} | {m['current_findings_needing_renewed_decision']} |")
        lines += ['', "Work counts include retained cases with withdrawn authorization; each case's authorization is visible in the JSON projection.", 'Coverage concerns explicit accepted failing observations. `not_evaluated` means this projection has no exception treatment dimension.', 'Expiry and overdue status are evaluated at `as_of`; they do not invent ledger events.', '']
        for scenario in overview['scenarios']:
            head = scenario['projection']['ledger_head_ref']
            lines += [f"## {scenario['scenario_id']}", '', f"Ledger: `{scenario['ledger_path']}`", f"Evaluated head: `{(head['id'] if head else 'none')}`", '', '| Revision | Event | Recorded at | Effective at |', '|---:|---|---|---|']
            for event in scenario['events']:
                lines.append(f"| {event['revision']} | {event['event_type']} | {event['recorded_at']} | {event['effective_at']} |")
            lines += ['', 'The JSON overview binds each event to its immutable event and transaction digests and embeds the verified finding projection.', '']
        return '\n'.join(lines)

    def generate(self, repo=_OMITTED, *, as_of, output=None, report=None):
        if repo is _OMITTED:
            repo = self.root
        root = self.path_factory(repo)
        output, report = (self.path_factory(output) if output else root / self.OUTPUT, self.path_factory(report) if report else root / self.REPORT)
        self.context.contracts.require(output.resolve() != report.resolve(), 'JSON and report paths must differ')
        for path in (output, report):
            self.context.contracts.require(not path.resolve().is_relative_to((root / 'governance/lifecycle').resolve()), 'Output must be outside immutable history')
            self.context.contracts.require(not path.resolve().is_relative_to((root / 'model').resolve()), 'Output must be outside source models')
        overview = self.build_overview(root, as_of=as_of)
        for path, data in ((output, self.context.adapter.json_bytes(overview)), (report, self.render_report(overview).encode())):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return overview

    def validate_overview(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.path_factory(repo)
        actual = self.context.adapter.strict_json((root / self.OUTPUT).read_bytes())
        expected = self.build_overview(root, as_of=actual['as_of'])
        self.context.contracts.require(actual == expected, 'Lifecycle overview differs from immutable history')
        for scenario in self.SCENARIOS:
            transactions = self.context.store.load_transactions(root / 'governance/lifecycle' / scenario)
            self.context.contracts.require(not transactions or self.context.contracts.timestamp(actual['as_of']) >= self.context.contracts.timestamp(transactions[-1]['recorded_at']), 'Current overview cannot hide later accepted history')
        self.context.contracts.require((root / self.REPORT).read_text() == self.render_report(expected), 'Lifecycle overview report differs from projection')
        return expected

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--as-of', required=True)
        parser.add_argument('--output', type=self.path_factory)
        parser.add_argument('--report', type=self.path_factory)
        args = parser.parse_args(self.argv)
        self.generate(as_of=args.as_of, output=args.output, report=args.report)
        print('Generated three separate synthetic scenario summaries; no official portfolio state.')

class SyntheticViewer:

    def __init__(self, root, context, *, path_factory, argument_parser, argv, overview=None):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.argument_parser = argument_parser
        self.argv = argv
        self.overview = overview
        self.description = 'Generate a standalone read-only viewer from the verified synthetic overview.'
        self.TEMPLATE = self.root / 'scripts/templates/governance-lifecycle-viewer.html'
        self.OUTPUT = 'generated/viewer/governance-lifecycle-viewer.html'

    def safe_json(self, value):
        """Preserve exact JSON values while preventing HTML script-element termination."""
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        for char, escaped in (('&', '\\u0026'), ('<', '\\u003c'), ('>', '\\u003e'), ('\u2028', '\\u2028'), ('\u2029', '\\u2029')):
            payload = payload.replace(char, escaped)
        return payload

    def render_viewer(self, overview):
        self.context.contracts.schema_validator('overview').validate(overview)
        template = self.TEMPLATE.read_text(encoding='utf-8')
        self.context.contracts.require(template.count('@@DATA@@') == template.count('@@SCRIPT_HASH@@') == 1, 'Invalid viewer template placeholders')
        scripts = re.findall('<script id="app">(.*?)</script>', template, re.S)
        self.context.contracts.require(len(scripts) == 1, 'Viewer must contain one fixed executable script')
        digest = base64.b64encode(hashlib.sha256(scripts[0].encode('utf-8')).digest()).decode('ascii')
        return template.replace('@@SCRIPT_HASH@@', digest).replace('@@DATA@@', self.safe_json(overview))

    def generate(self, repo=_OMITTED, *, output=None):
        if repo is _OMITTED:
            repo = self.root
        root = self.path_factory(repo)
        path = self.path_factory(output) if output else root / self.OUTPUT
        for protected in ('governance/lifecycle', 'model', 'status', 'scripts', 'schemas'):
            self.context.contracts.require(not path.resolve().is_relative_to((root / protected).resolve()), 'Viewer output cannot overwrite its inputs')
        self.context.contracts.require(path.resolve() != (root / 'generated/viewer/status-viewer.html').resolve(), 'Official status viewer is separate')
        html = self.render_viewer(self.overview.validate_overview(root))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding='utf-8')
        return html

    def validate_viewer(self, repo=_OMITTED, *, overview=None):
        if repo is _OMITTED:
            repo = self.root
        root = self.path_factory(repo)
        if overview is None:
            overview = self.overview.validate_overview(root)
        expected = self.render_viewer(overview)
        self.context.contracts.require((root / self.OUTPUT).read_text(encoding='utf-8') == expected, 'Lifecycle viewer differs from verified overview')
        return expected

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--output', type=self.path_factory)
        args = parser.parse_args(self.argv)
        self.generate(output=args.output)
        print('Generated read-only synthetic lifecycle viewer; official consumer status is separate.')
