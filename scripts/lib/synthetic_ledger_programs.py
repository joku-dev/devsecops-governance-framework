"""All six original synthetic ledger entrypoints over explicit context/IO ports."""
import json

class SyntheticHistoryDemo:

    def __init__(self, root, context, *, path_factory, argument_parser, argv):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.argument_parser = argument_parser
        self.argv = argv
        self.default_profile = root / 'model/governance/lifecycle/synthetic-grs002-profile.json'
        self.description = 'Reproduce a bounded synthetic CLG-02 history; no live repository settings change.'
        self.as_of = '2026-09-13T11:30:00Z'

    def run_demo(self, ledger, output):
        self.context.contracts.require(not output.resolve().is_relative_to(ledger.resolve()), 'Projection must be outside immutable history')
        self.context.contracts.require(not self.context.store.load_transactions(ledger), 'Demo requires an empty ledger; existing history is never reset')
        profile = self.context.adapter.strict_json(self.default_profile.read_bytes())
        cases = [('fail', '10:00', '10:00', 'demo-1', 0, 'accepted'), ('fail', '10:00', '10:01', 'demo-1', 0, 'duplicate'), ('fail', '10:10', '10:10', 'demo-2', 1, 'accepted'), ('pass', '11:00', '11:00', 'demo-3', 2, 'accepted'), ('fail', '10:05', '11:10', 'demo-4', 3, 'accepted'), ('fail', '11:00', '11:20', 'demo-3', 4, 'quarantined'), ('fail', '11:00', '11:21', 'demo-3', 4, 'duplicate')]
        for result, observed, recorded, run_id, revision, expected in cases:
            observation, resources = self.context.synthetic.synthetic_packet(profile, result=result, observed_at=f'2026-09-13T{observed}:00Z', recorded_at=f'2026-09-13T{recorded}:00Z', run_id=run_id)
            outcome = self.context.store.append_observation(ledger, observation, resources, profile, expected_revision=revision)
            self.context.contracts.require(outcome['outcome'] == expected, 'Unexpected synthetic demo outcome')
        index = self.context.kernel.project(self.context.store.load_transactions(ledger), profile, as_of=self.as_of)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(self.context.adapter.json_bytes(index))
        return index

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--ledger', type=self.path_factory, required=True)
        parser.add_argument('--output', type=self.path_factory, required=True)
        args = parser.parse_args(self.argv)
        index = self.context.demo_synthetic.run_demo(args.ledger, args.output)
        print(f"Synthetic demo complete: {index['counts']}; no operational closure.")

class SyntheticActionDemo:

    def __init__(self, root, context, *, path_factory, argument_parser, argv):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.argument_parser = argument_parser
        self.argv = argv
        self.default_profile = root / 'model/governance/lifecycle/synthetic-grs002-profile.json'
        self.description = 'Reproduce CLG-02 then append synthetic CLG-03 consent, progress and withdrawal.'
        self.as_of = '2026-09-13T12:10:00Z'

    def append_demo_actions(self, ledger, output):
        self.context.contracts.require(not output.resolve().is_relative_to(ledger.resolve()), 'Projection must be outside immutable history')
        profile = self.context.adapter.strict_json(self.default_profile.read_bytes())
        history = self.context.store.load_transactions(ledger)
        golden = self.context.adapter.strict_json((self.root / 'tests/fixtures/governance-lifecycle/clg02-index.json').read_bytes())
        self.context.contracts.require(self.context.kernel.project(history, profile, as_of=golden['as_of']) == golden and len(history) == 5, 'Action demo requires the exact CLG-02 history')
        observation = history[0]['observation']
        decision, resources = self.context.synthetic_actions.decision_packet(profile, observation, record_id='decision:demo-approve', revision=5, at='2026-09-13T11:40:00Z', case_id='remediation-case:demo-1')
        self.context.store.append_action(ledger, decision, resources, profile, expected_revision=5)
        planned, planned_resources = self.context.synthetic_actions.remediation_packet(decision, resources, record_id='remediation:demo-planned', revision=6, at='2026-09-13T11:50:00Z')
        self.context.store.append_action(ledger, planned, planned_resources, profile, expected_revision=6)
        progress, progress_resources = self.context.synthetic_actions.remediation_packet(decision, resources, record_id='remediation:demo-progress', revision=7, at='2026-09-13T12:00:00Z', progress='in_progress', previous=planned)
        self.context.store.append_action(ledger, progress, progress_resources, profile, expected_revision=7)
        withdrawal, withdrawal_resources = self.context.synthetic_actions.decision_packet(profile, observation, record_id='decision:demo-revoke', revision=8, at='2026-09-13T12:10:00Z', case_id='remediation-case:demo-1', disposition='revoke', previous=decision)
        self.context.store.append_action(ledger, withdrawal, withdrawal_resources, profile, expected_revision=8)
        self.context.contracts.require(self.context.store.append_action(ledger, decision, resources, profile, expected_revision=5)['outcome'] == 'duplicate', 'Retry must not reactivate revoked consent')
        index = self.context.kernel.project(self.context.store.load_transactions(ledger), profile, as_of=self.as_of)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(self.context.adapter.json_bytes(index))
        return index

    def run_action_demo(self, ledger, output):
        self.context.demo_synthetic.run_demo(ledger, output)
        return self.append_demo_actions(ledger, output)

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--ledger', type=self.path_factory, required=True)
        parser.add_argument('--output', type=self.path_factory, required=True)
        args = parser.parse_args(self.argv)
        index = self.run_action_demo(args.ledger, args.output)
        print(f"Synthetic action demo complete: {index['counts']}; approval withdrawn, finding remains open for clarification.")

class SyntheticClosureDemo:

    def __init__(self, root, context, *, path_factory, argument_parser, argv):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.argument_parser = argument_parser
        self.argv = argv
        self.default_profile = root / 'model/governance/lifecycle/synthetic-grs002-profile.json'
        self.description = 'Run an isolated synthetic FAIL/consent/remediation/PASS/closure/reopening pilot.'
        self.as_of = '2026-09-13T14:20:00Z'

    def run_closure_demo(self, ledger, output, report):
        self.context.contracts.require(not self.context.store.load_transactions(ledger), 'Closure demo requires an empty ledger; no accepted history is reset')
        for path in (output, report):
            self.context.contracts.require(not path.resolve().is_relative_to(ledger.resolve()), 'Output must be outside immutable history')
        profile = self.context.adapter.strict_json(self.default_profile.read_bytes())

        def observation(result, observed, recorded, run, revision):
            packet = self.context.synthetic.synthetic_packet(profile, result=result, observed_at=f'2026-09-13T{observed}:00Z', recorded_at=f'2026-09-13T{recorded}:00Z', run_id=run)
            self.context.store.append_observation(ledger, *packet, profile, expected_revision=revision)
            return packet[0]
        failing = observation('fail', '13:00', '13:00', 'closure-demo-fail', 0)
        decision = self.context.synthetic_actions.decision_packet(profile, failing, record_id='decision:closure-demo', revision=1, at='2026-09-13T13:10:00Z', case_id='remediation-case:closure-demo')
        self.context.store.append_action(ledger, *decision, profile, expected_revision=1)
        previous = None
        for revision, progress, at in ((2, 'planned', '13:20'), (3, 'in_progress', '13:30'), (4, 'completed', '13:40')):
            packet = self.context.synthetic_actions.remediation_packet(*decision, record_id='remediation:closure-demo-' + progress, revision=revision, at=f'2026-09-13T{at}:00Z', progress=progress, previous=previous)
            self.context.store.append_action(ledger, *packet, profile, expected_revision=revision)
            previous = packet[0]
        passing = observation('pass', '13:50', '13:50', 'closure-demo-pass', 5)
        closure = self.context.synthetic_actions.closure_packet(profile, failing, passing, previous, record_id='closure:demo', revision=6, at='2026-09-13T14:00:00Z')
        self.context.store.append_closure(ledger, *closure, profile, expected_revision=6)
        self.context.contracts.require(self.context.kernel.project(self.context.store.load_transactions(ledger), profile, as_of='2026-09-13T14:00:00Z')['findings'][0]['state'] == 'closed', 'Synthetic closure checkpoint failed')
        observation('fail', '13:05', '14:10', 'closure-demo-late', 7)
        self.context.contracts.require(self.context.kernel.project(self.context.store.load_transactions(ledger), profile, as_of='2026-09-13T14:10:00Z')['findings'][0]['state'] == 'closed', 'Historical failure incorrectly reopened finding')
        observation('fail', '14:20', '14:20', 'closure-demo-recurrence', 8)
        self.context.contracts.require(self.context.store.append_closure(ledger, *closure, profile, expected_revision=6)['outcome'] == 'duplicate', 'Closure retry must not close a reopened finding')
        return self.context.report_pilot.generate(ledger, output, report, as_of=self.as_of)

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--ledger', type=self.path_factory, required=True)
        parser.add_argument('--output', type=self.path_factory, required=True)
        parser.add_argument('--report', type=self.path_factory, required=True)
        args = parser.parse_args(self.argv)
        index = self.run_closure_demo(args.ledger, args.output, args.report)
        print(f"Synthetic pilot completed: {index['counts']}; finding reopened, closure history retained.")

class SyntheticExceptionDemo:

    def __init__(self, root, context, *, path_factory, argument_parser, argv):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.argument_parser = argument_parser
        self.argv = argv
        self.default_profile = root / 'model/governance/lifecycle/synthetic-grs002-profile.json'
        self.description = 'Exercise partial/overlapping coverage, recurrence, withdrawal, expiry and fresh consent.'
        self.as_of = '2026-09-14T00:10:00Z'

    def run_exception_demo(self, ledger, output, report):
        self.context.contracts.require(not self.context.store.load_transactions(ledger), 'Exception demo requires an empty ledger')
        for path in (output, report):
            self.context.contracts.require(not path.resolve().is_relative_to(ledger.resolve()), 'Output must be outside immutable history')
        profile = self.context.adapter.strict_json(self.default_profile.read_bytes())
        observations = []

        def observe(at, run, revision):
            packet = self.context.synthetic.synthetic_packet(profile, result='fail', observed_at=at, recorded_at=at, run_id=run)
            self.context.store.append_observation(ledger, *packet, profile, expected_revision=revision)
            observations.append(packet[0])
        observe('2026-09-13T15:00:00Z', 'exception-demo-1', 0)
        observe('2026-09-13T15:10:00Z', 'exception-demo-2', 1)
        decision = self.context.synthetic_actions.decision_packet(profile, observations[0], record_id='decision:exception-demo', revision=2, at='2026-09-13T15:20:00Z', case_id='remediation-case:exception-demo')
        self.context.store.append_action(ledger, *decision, profile, expected_revision=2)
        planned = self.context.synthetic_actions.remediation_packet(*decision, record_id='remediation:exception-demo-planned', revision=3, at='2026-09-13T15:30:00Z')
        self.context.store.append_action(ledger, *planned, profile, expected_revision=3)
        first = self.context.synthetic_exceptions.exception_packet(profile, observations[:1], record_id='exception:partial', revision=4, at='2026-09-13T16:00:00Z', waiver_id='synthetic-waiver:partial')
        self.context.store.append_exception(ledger, *first, profile, expected_revision=4)
        second = self.context.synthetic_exceptions.exception_packet(profile, observations[1:], record_id='exception:remaining', revision=5, at='2026-09-13T16:10:00Z', waiver_id='synthetic-waiver:remaining')
        self.context.store.append_exception(ledger, *second, profile, expected_revision=5)
        observe('2026-09-13T16:20:00Z', 'exception-demo-new-failure', 6)
        revoke = self.context.synthetic_exceptions.exception_packet(profile, observations[:1], record_id='exception:withdraw', revision=7, at='2026-09-13T16:30:00Z', disposition='revoke', previous=first[0], previous_resources=first[1])
        self.context.store.append_exception(ledger, *revoke, profile, expected_revision=7)
        at_expiry = self.context.kernel.project(self.context.store.load_transactions(ledger), profile, as_of='2026-09-14T00:00:00Z')['findings'][0]
        self.context.contracts.require(at_expiry['exception_treatment']['coverage'] == 'none' and at_expiry['exception_treatment']['renewed_decision_required'], 'Expiry must expose all uncovered observations and renewed decision need')
        renewal = self.context.synthetic_exceptions.exception_packet(profile, observations, record_id='exception:renewal', revision=8, at=self.as_of, waiver_id='synthetic-waiver:renewal', expiry='2026-09-14')
        self.context.store.append_exception(ledger, *renewal, profile, expected_revision=8)
        self.context.contracts.require(self.context.store.append_exception(ledger, *first, profile, expected_revision=4)['outcome'] == 'duplicate', 'Old approval retry must never reactivate withdrawn coverage')
        return self.context.report_exceptions.generate(ledger, output, report, as_of=self.as_of)

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--ledger', type=self.path_factory, required=True)
        parser.add_argument('--output', type=self.path_factory, required=True)
        parser.add_argument('--report', type=self.path_factory, required=True)
        args = parser.parse_args(self.argv)
        index = self.run_exception_demo(args.ledger, args.output, args.report)
        print(f"Synthetic exception demo completed: {index['counts']}; finding remains open.")

class SyntheticObservationIntake:

    def __init__(self, root, context, *, path_factory, argument_parser, argv):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.argument_parser = argument_parser
        self.argv = argv
        self.default_profile = root / 'model/governance/lifecycle/synthetic-grs002-profile.json'
        self.description = 'Append one explicitly synthetic GRS-002 packet to a local lifecycle ledger.'

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--synthetic', action='store_true', required=True)
        parser.add_argument('--ledger', type=self.path_factory, required=True)
        parser.add_argument('--report', type=self.path_factory, required=True)
        parser.add_argument('--context', type=self.path_factory, required=True)
        parser.add_argument('--trust', type=self.path_factory, required=True)
        parser.add_argument('--recorded-at', required=True)
        parser.add_argument('--policy-version', required=True)
        parser.add_argument('--expected-revision', type=int, required=True)
        args = parser.parse_args(self.argv)
        profile = self.context.adapter.strict_json((self.root / 'model/governance/lifecycle/synthetic-grs002-profile.json').read_bytes())
        record, resources = self.context.adapter.adapt_grs002(args.report.read_bytes(), self.context.adapter.strict_json(args.context.read_bytes()), self.context.adapter.strict_json(args.trust.read_bytes()), recorded_at=args.recorded_at, profile=profile, policy_version=args.policy_version)
        result = self.context.store.append_observation(args.ledger, record, resources, profile, expected_revision=args.expected_revision)
        print(json.dumps(result, indent=2))

class SyntheticActionIntake:

    def __init__(self, root, context, *, path_factory, argument_parser, argv):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.argument_parser = argument_parser
        self.argv = argv
        self.default_profile = root / 'model/governance/lifecycle/synthetic-grs002-profile.json'
        self.description = 'Intake an explicit synthetic decision/remediation/closure/exception packet; never approve a real decision.'

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--synthetic', action='store_true', required=True)
        parser.add_argument('--ledger', type=self.path_factory, required=True)
        parser.add_argument('--record', type=self.path_factory, required=True)
        parser.add_argument('--resources', type=self.path_factory, required=True, help='Directory containing the referenced flat fixture resources')
        parser.add_argument('--expected-revision', type=int, required=True)
        args = parser.parse_args(self.argv)
        record = self.context.adapter.strict_json(args.record.read_bytes())
        body = record['body']
        if record['record_type'] == 'exception':
            refs = [record['approval']['proof_ref'], body['waiver_ref']]
        elif record['record_type'] == 'closure':
            refs = [record['approval']['proof_ref']]
        elif record['record_type'] == 'decision':
            refs = [record['approval']['proof_ref'], body['remediation_plan']['work_ref']]
        else:
            self.context.contracts.require(record['record_type'] == 'remediation', 'Only decisions and remediations are supported')
            refs = [body['work_ref'], body['progress_evidence_ref']]
        resources = {}
        for ref in refs:
            uri = ref['uri']
            self.context.contracts.require(uri.startswith('fixture://'), 'Live resources are not supported')
            name = uri[len('fixture://'):]
            self.context.contracts.require(name not in ('', '.', '..') and self.path_factory(name).name == name and ('\\' not in name), 'Fixture resources must have flat filenames')
            path = args.resources / name
            self.context.contracts.require(not path.is_symlink(), 'Fixture resource cannot be a symlink')
            resources[uri] = path.read_bytes()
        append = self.context.store.append_exception if record['record_type'] == 'exception' else self.context.store.append_closure if record['record_type'] == 'closure' else self.context.store.append_action
        result = append(args.ledger, record, resources, self.context.adapter.strict_json(self.default_profile.read_bytes()), expected_revision=args.expected_revision)
        print(self.context.adapter.json_bytes(result).decode(), end='')
