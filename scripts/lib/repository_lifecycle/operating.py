"""Retained V1 historical consistency over explicit data and capture adapters.

Historical outputs describe their original scope; they confer no operating
acceptance, personal consent or authority on the executing V2 node.
"""
import hashlib
_OMITTED = object()
REQUEST_PATH = 'model/governance/lifecycle/operating-acceptance/00000001.json'
CAPTURES = 'generated/reports/lifecycle-operating-acceptance'
INDEX = 'status/governance-lifecycle-live.json'
REPORT = 'generated/reports/governance-lifecycle-live.md'
STATEMENT_PATH = 'generated/reports/lifecycle-operating-acceptance-statement.md'
MANIFEST_PATHS = ('requirements-validation.txt', 'scripts/validation-toolchain.env', 'scripts/bootstrap_validation_env.sh', 'scripts/validate_all.sh', 'scripts/lib/result_ledger.py', 'scripts/lib/governance_lifecycle/adapter.py', 'scripts/generate_lifecycle_pilot_validation.py', 'scripts/generate_lifecycle_pilot_actions.py', 'scripts/lib/governance_lifecycle/operating_acceptance.py', 'scripts/lib/governance_lifecycle/pilot_actions.py', 'scripts/lib/governance_lifecycle/personal_probe.py', 'scripts/lib/governance_lifecycle/live_admission.py', 'scripts/lib/governance_lifecycle/live_evidence.py', 'scripts/lib/governance_lifecycle/store.py', 'scripts/lib/governance_lifecycle/contracts.py', 'scripts/run_lifecycle_pilot_update.py', 'scripts/publish_operational_update.py', 'scripts/validate_governance_lifecycle_ledger.py', '.github/workflows/lifecycle-pilot-update.yml', '.github/workflows/governance-ci.yml', 'schemas/governance-lifecycle-pilot-action-request.schema.json', 'schemas/governance-lifecycle-pilot-action-receipt.schema.json', 'schemas/governance-lifecycle-operating-acceptance.schema.json', 'docs/operations/evidence/governance-lifecycle-live-operation.md')

class LifecycleOperatingAcceptance:

    def __init__(self, root, context, *, path_factory):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.REQUEST_PATH = REQUEST_PATH
        self.CAPTURES = CAPTURES
        self.INDEX = INDEX
        self.REPORT = REPORT
        self.STATEMENT_PATH = STATEMENT_PATH
        self.MANIFEST_PATHS = MANIFEST_PATHS

    def manifest(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        return {name: hashlib.sha256((self.path_factory(repo) / name).read_bytes()).hexdigest() for name in MANIFEST_PATHS}

    def request(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        value = self.context.adapter.strict_json((self.path_factory(repo) / REQUEST_PATH).read_bytes())
        self.context.contracts.schema_validator('operating-acceptance').validate(value)
        self.context.contracts.require(set(value['implementation_manifest']) == set(MANIFEST_PATHS), 'Acceptance implementation scope differs')
        profile = self.context.admission.load_operating(repo)
        binding = self.context.preparation.validate_preparation(repo)['binding']
        self.context.contracts.require(value['operating_profile_ref'] == self.context.preparation.revision_ref(profile) and value['role_binding_ref'] == self.context.preparation.revision_ref(binding), 'Acceptance profile or role revision differs')
        self.context.contracts.require(value['required_subject_id'] == binding['assignments']['role_registry_owner'], 'Named acceptance subject differs')
        return value

    def assess(self, request, comments, *, captured_at, previous_comments=()):
        self.context.contracts.schema_validator('operating-acceptance').validate(request)
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
        root = self.path_factory(repo)
        expected = self.request(root)
        directory = root / CAPTURES
        self.context.contracts.require(not directory.is_symlink(), 'Acceptance capture directory cannot be a symlink')
        result = []
        for n, path in enumerate(sorted(directory.iterdir()) if directory.exists() else [], 1):
            self.context.contracts.require(path.is_file() and (not path.is_symlink()) and (path.name == f'{n:08d}.json'), 'Acceptance capture sequence or type differs')
            snapshot = self.context.adapter.strict_json(path.read_bytes())
            self.context.contracts.require(snapshot['request'] == expected and snapshot['capture_method'] == self.context.provider.capture_method, 'Acceptance capture source or request differs')
            self.context.contracts.require(snapshot['previous_comments'] == self.prior_comments(result), 'Acceptance capture loses prior statement history')
            self.context.provider.replay_bound_snapshot(snapshot, assessor=self.assess)
            self.context.contracts.require(not result or self.context.contracts.timestamp(snapshot['result']['captured_at']) >= self.context.contracts.timestamp(result[-1]['result']['captured_at']), 'Acceptance capture time regressed')
            result.append(snapshot)
        return result

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
        roles = self.context.actions.project_actions(repo)['roles_active']
        return {'status': status, 'implementation_matches': unchanged, 'roles_active': roles, 'effective': status == 'confirmed' and unchanged and roles, 'request_digest': self.context.contracts.canonical_digest(value), 'capture_digest': self.context.contracts.canonical_digest(history[-1]) if history else None, 'captured_at': history[-1]['result']['captured_at'] if history else None}

    def projection(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        candidate = self.context.actions.project_actions(repo)
        acceptance = self.effective(repo)
        return {'schema_version': '0.1.0', 'index_type': 'governance-lifecycle-live-pilot', 'official_state': acceptance['effective'], 'live_activation_approved': acceptance['effective'], 'enforcement': 'report_only', 'scope': self.context.admission.load_operating(repo)['scope'], 'operating_acceptance': acceptance, 'candidate_projection_digest': self.context.contracts.canonical_digest(candidate), 'evidence_as_of': candidate['as_of'], 'as_of': max(filter(None, (candidate['as_of'], acceptance['captured_at'])), default=None), 'finding_state': candidate['finding_state'] if acceptance['effective'] else 'inactive', 'counts': candidate['counts'], 'active_decision_ref': candidate['active_decision_ref'] if acceptance['effective'] else None, 'active_closure_ref': candidate['active_closure_ref'] if acceptance['effective'] else None, 'promotion_basis': 'Explicit LD-07 acceptance of the separate pilot validation projection; source receipts remain unchanged', 'limitation': 'Manual report-only pilot. No automatic remediation, baseline change or other consumer state update.'}

    def render(self, index):
        acceptance = index['operating_acceptance']
        return '\n'.join(['# GitHub Lifecycle Pilot Operation', '', f"Operating acceptance: **{acceptance['status']}**. Effective: **{str(acceptance['effective']).lower()}**.", f"Implementation matches the acceptance request: `{str(acceptance['implementation_matches']).lower()}`.", f"Finding state: `{index['finding_state']}`. Pilot state as of `{index['as_of']}`; evidence as of `{index['evidence_as_of']}`.", f"Receipts: {index['counts']['receipts']}; action records: {index['counts']['actions']}.", '', 'The report reflects retained captures. Recheck GitHub before any new operational proposal.', index['promotion_basis'] + '.', index['limitation'], ''])

    def validate(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.path_factory(repo)
        index = self.projection(root)
        self.context.contracts.require(self.context.adapter.strict_json((root / INDEX).read_bytes()) == index, 'Live pilot index differs')
        self.context.contracts.require((root / REPORT).read_text() == self.render(index), 'Live pilot report differs')
        statement_body = self.context.personal.statement_body
        expected = self.statement_template(self.request(root), statement_body)
        self.context.contracts.require((root / STATEMENT_PATH).read_text() == expected, 'Operating acceptance statement template differs')
        return index

    def statement_template(self, value, body):
        return '# Persönliche Betriebsabnahme LD-07\n\nBitte zuerst den vollständigen Antrag und den Betriebsleitfaden prüfen. Diese Erklärung gibt den beschriebenen manuellen GRS-002-Piloten im Report-only-Modus frei. Behebung und Abschluss benötigen weiterhin eigene persönliche Erklärungen.\n\nDiskussion: ' + self.context.provider.discussion_url(value['repository_id'], value['discussion_number']) + '\n\n```text\n' + body(value) + '```\n\nDie benannte Person gibt den Kommentar selbst ab. Codex darf ihn vorbereiten, aber nicht stellvertretend posten.\n'
