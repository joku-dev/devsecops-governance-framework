"""Complete original consumer lifecycle functions over explicit data/effect ports.

Retained source history is not this node's operating authority.
"""
from __future__ import annotations
from copy import deepcopy
from referencing import Registry, Resource
import base64, hashlib
_OMITTED = object()
_DEFAULT_FETCH = object()
REQUEST_PATH = 'model/governance/lifecycle/consumer-operation' + '/acceptance.json'
CAPTURES = 'governance/consumer-lifecycle/acceptance'
INDEX = 'status/governance-consumer-lifecycle.json'
REPORT = 'generated/reports/governance-consumer-lifecycle.md'
STATEMENT_PATH = 'generated/reports/consumer-lifecycle-acceptance-statement.md'

class ConsumerAcceptance:

    def __init__(self, root, context, *, path_factory, profile, process=None, temporary=None, clock=None, validator_class=None, default_fetch=None, architecture=None, argument_parser=None, argv=(), description=None):
        self.root, self.context, self.Path, self.profile = (root, context, path_factory, profile)
        self.process, self.temporary, self.clock = (process, temporary, clock)
        self.validator_class, self.default_fetch, self.architecture = (validator_class, default_fetch, architecture)
        self.argument_parser, self.argv, self.description = (argument_parser, list(argv), description)
        self.positive_id = profile.positive_id
        self.REQUEST_PATH = REQUEST_PATH
        self.CAPTURES = CAPTURES
        self.INDEX = INDEX
        self.REPORT = REPORT
        self.STATEMENT_PATH = STATEMENT_PATH
        self.MANIFEST_PATHS = profile.manifest_paths

    def manifest(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        return {name: hashlib.sha256((self.Path(repo) / name).read_bytes()).hexdigest() for name in self.MANIFEST_PATHS}

    def request(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        value = self.context.adapter.strict_json((self.Path(repo) / self.REQUEST_PATH).read_bytes())
        self.context.consumer_contracts.schema_validator('operating-acceptance').validate(value)
        self.context.contracts.require(set(value['implementation_manifest']) == set(self.MANIFEST_PATHS), 'Acceptance implementation scope differs')
        profile = self.context.consumer_contracts.load_operating(repo)
        binding = self.context.consumer_contracts.validate_preparation(repo)['binding']
        self.context.contracts.require(value['operating_profile_ref'] == self.context.preparation.revision_ref(profile) and value['role_binding_ref'] == self.context.preparation.revision_ref(binding), 'Acceptance profile or role revision differs')
        self.context.contracts.require(value['required_subject_id'] == binding['assignments']['role_registry_owner'], 'Named acceptance subject differs')
        return value

    def assess(self, request, comments, *, captured_at, previous_comments=()):
        self.context.consumer_contracts.schema_validator('operating-acceptance').validate(request)
        result = self.context.provider.assess_bound_comments(request, comments, captured_at=captured_at, previous_comments=previous_comments)
        result['record_type'] = 'lifecycle-operating-acceptance-result'
        result['operating_acceptance_granted'] = result['status'] == 'confirmed'
        return result

    def prior_comments(self, captures):
        records = {}
        for capture in captures:
            for comment in capture['result']['relevant_comments']:
                records.setdefault(comment['id'], comment)
        return list(records.values())

    def captures(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.Path(repo)
        expected = self.request(root)
        directory = root / self.CAPTURES
        self.context.contracts.require(not directory.is_symlink(), 'Acceptance capture directory cannot be a symlink')
        result = []
        for n, path in enumerate(sorted(directory.iterdir()) if directory.exists() else [], 1):
            self.context.contracts.require(path.is_file() and (not path.is_symlink()) and (path.name == f'{n:08d}.json'), 'Acceptance capture sequence or type differs')
            snapshot = self.context.adapter.strict_json(path.read_bytes())
            self.context.contracts.require(set(snapshot) == {'request', 'result', 'issue_response', 'comment_pages_before', 'comment_pages_after', 'previous_comments', 'capture_method'}, 'Consumer acceptance snapshot fields differ')
            self.context.contracts.require(snapshot['request'] == expected and snapshot['capture_method'] == self.profile.capture_method, 'Acceptance capture source or request differs')
            self.context.contracts.require(snapshot['previous_comments'] == self.prior_comments(result), 'Acceptance capture loses prior statement history')
            self.context.provider.replay_bound_snapshot(snapshot, assessor=self.assess)
            self.context.contracts.require(not result or self.context.contracts.timestamp(snapshot['result']['captured_at']) >= self.context.contracts.timestamp(result[-1]['result']['captured_at']), 'Acceptance capture time regressed')
            result.append(snapshot)
        return result

    def collect(self, repo=_OMITTED, *, fetch=None, captured_at=None):
        if repo is _OMITTED:
            repo = self.root
        root = self.Path(repo)
        value = self.request(root)
        history = self.captures(root)
        options = {'fetch': fetch} if fetch is not None else {}
        return self.context.provider.collect_bound(value, assessor=self.assess, previous_comments=self.prior_comments(history), captured_at=captured_at, **options)

    def capture(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.Path(repo)
        history = self.captures(root)
        snapshot = self.collect(root)
        self.context.contracts.require(snapshot['result']['status'] != 'waiting_for_personal_statement', 'Personal consumer operating statement is still missing')
        destination = root / self.CAPTURES / f'{len(history) + 1:08d}.json'
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(self.context.adapter.json_bytes(snapshot))
        return snapshot

    def proof(self, snapshot):
        result = snapshot['result']
        return {key: result[key] for key in ('request_digest', 'status', 'last_statement_id', 'issues')} | {'comments': [self.context.provider.comment_identity(c) for c in result['relevant_comments']]}

    def effective(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        value = self.request(repo)
        history = self.captures(repo)
        status = history[-1]['result']['status'] if history else 'waiting_for_personal_acceptance'
        unchanged = value['implementation_manifest'] == self.manifest(repo)
        roles = self.context.consumer_actions.project_actions(repo)['roles_active']
        return {'status': status, 'implementation_matches': unchanged, 'roles_active': roles, 'effective': status == 'confirmed' and unchanged and roles, 'request_digest': self.context.contracts.canonical_digest(value), 'capture_digest': self.context.contracts.canonical_digest(history[-1]) if history else None, 'captured_at': history[-1]['result']['captured_at'] if history else None}

    def verify_provider(self, repo=_OMITTED, *, fetch=None):
        if repo is _OMITTED:
            repo = self.root
        history = self.captures(repo)
        self.context.contracts.require(bool(history), 'No retained operating acceptance exists')
        latest = self.collect(repo, fetch=fetch)
        self.context.contracts.require(self.proof(latest) == self.proof(history[-1]), self.profile.literal('legacy_88eda6a67b47f06e'))
        self.context.contracts.require(self.effective(repo)['effective'], 'Personal operating acceptance is not effective')
        self.verify_required_guard(fetch=fetch)
        return latest

    def verify_new_captures(self, repo, base_ref, *, fetch=None, checked_at=None):
        root = self.Path(repo)
        history = self.captures(root)
        old = set(self.process.check_output(['git', 'ls-tree', '-r', '--name-only', base_ref, '--', self.CAPTURES], cwd=root, text=True).splitlines())
        count = 0
        for n, snapshot in enumerate(history, 1):
            if f'{self.CAPTURES}/{n:08d}.json' in old:
                continue
            latest = self.collect(root, fetch=fetch, captured_at=checked_at)
            self.context.contracts.require(self.proof(latest) == self.proof(snapshot), self.profile.literal('legacy_d9e4219f7cabd9ef'))
            self.context.contracts.require(self.context.contracts.timestamp(snapshot['result']['captured_at']) <= self.context.contracts.timestamp(latest['result']['captured_at']), 'Operating acceptance capture is future-dated')
            if snapshot['result']['status'] == 'confirmed':
                self.context.contracts.require(self.request(root)['implementation_manifest'] == self.manifest(root), 'Implementation changed after acceptance request')
            count += 1
        index = self.projection(root)
        if index['live_activation_approved']:
            previous = self.process.run(['git', 'show', f'{base_ref}:{self.INDEX}'], cwd=root, capture_output=True)
            if previous.returncode or previous.stdout != (root / self.INDEX).read_bytes():
                self.verify_provider(root, fetch=fetch)
        return count

    def projection(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        candidate = self.context.consumer_actions.project_actions(repo)
        acceptance = self.effective(repo)
        return {'schema_version': '0.1.0', 'index_type': 'governance-consumer-lifecycle-pilot', 'official_state': acceptance['effective'], 'live_activation_approved': acceptance['effective'], 'enforcement': 'report_only', 'scope': self.context.consumer_contracts.load_operating(repo)['scope'], 'operating_acceptance': acceptance, 'candidate_projection_digest': self.context.contracts.canonical_digest(candidate), 'evidence_as_of': candidate['as_of'], 'as_of': max(filter(None, (candidate['as_of'], acceptance['captured_at'])), default=None), 'finding_state': candidate['finding_state'] if acceptance['effective'] else 'inactive', 'counts': candidate['counts'], 'active_decision_ref': candidate['active_decision_ref'] if acceptance['effective'] else None, 'active_closure_ref': candidate['active_closure_ref'] if acceptance['effective'] else None, 'promotion_basis': 'Explicit consumer operating acceptance of the separate pilot validation projection; source receipts remain unchanged', 'limitation': 'Manual report-only operation_readiness pilot for the neutral demo only; no automatic remediation, waivers or baseline changes.'}

    def validate(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.Path(repo)
        index = self.projection(root)
        self.context.contracts.require(self.context.adapter.strict_json((root / self.INDEX).read_bytes()) == index, 'Live pilot index differs')
        self.context.contracts.require((root / self.REPORT).read_text() == self.render(index), 'Live pilot report differs')
        expected = self.statement_template(self.request(root), self.context.personal.statement_body)
        self.context.contracts.require((root / self.STATEMENT_PATH).read_text() == expected, 'Operating acceptance statement template differs')
        return index

    def generate(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.Path(repo)
        index = self.projection(root)
        (root / self.INDEX).write_bytes(self.context.adapter.json_bytes(index))
        (root / self.REPORT).write_text(self.render(index))
        (root / self.STATEMENT_PATH).write_text(self.statement_template(self.request(root), self.context.personal.statement_body))

    def validate_publication(self, repo, base_ref):
        root = self.Path(repo)
        self.check_prefix(root, base_ref)
        index = self.validate(root)
        self.context.consumer_admission.verify_new_receipts(root, base_ref)
        self.context.consumer_actions.verify_new_actions(root, base_ref)
        self.verify_new_captures(root, base_ref)
        if index['live_activation_approved']:
            self.verify_provider(root)
        else:
            old = set(self.process.check_output(['git', 'ls-tree', '-r', '--name-only', base_ref, '--', self.context.consumer_admission.VALIDATION_LEDGER, self.context.consumer_actions.ACTION_LEDGER], cwd=root, text=True).splitlines())
            for path in (root / self.context.consumer_admission.VALIDATION_LEDGER / 'transactions').glob('*.json'):
                self.context.contracts.require(str(path.relative_to(root)) in old, 'Inactive consumer cannot publish a new observation')
            for action in self.context.store.load_transactions(root / self.context.consumer_actions.ACTION_LEDGER):
                name = f"{self.context.consumer_actions.ACTION_LEDGER}/transactions/{action['sequence']:08d}-{action['transaction_id'].split(':')[1]}.json"
                if name not in old:
                    self.context.contracts.require(action['outcome'] != 'eligible_for_pilot' or action['request']['body']['kind'] in ('withdrawal', 'role_withdrawal'), 'Inactive consumer cannot publish an action grant')
        return index

    def check_prefix(self, repo, base_ref):
        root = self.Path(repo).resolve()
        paths = self.process.check_output(['git', 'ls-tree', '-r', '--name-only', base_ref, '--', 'governance/consumer-lifecycle', self.context.consumer_contracts.MODEL], cwd=root, text=True).splitlines()
        for name in paths:
            path = root / name
            self.context.contracts.require(path.is_file() and (not any((p.is_symlink() for p in (path, *path.parents)))), 'Missing or symlinked accepted consumer history')
            before = self.process.check_output(['git', 'show', base_ref + ':' + name], cwd=root)
            self.context.contracts.require(path.read_bytes() == before, 'Accepted consumer history or model was rewritten: ' + name)
        return len(paths)

    def verify_required_guard(self, *, fetch=None):
        return self.profile.verify_required_guard(fetch=fetch)

    def render(self, index):
        return self.profile.render(index)

    def statement_template(self, value, body):
        return self.profile.statement_template(value, body)
