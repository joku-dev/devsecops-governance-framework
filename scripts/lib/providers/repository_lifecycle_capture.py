"""Explicit legacy GitHub capture profile; offline consistency only.

This adapter retains original raw field, identity, URL, archive and comment
checks. It never fetches provider data, executes callers or grants this node
historical personal consent or operating authority.
"""
import hashlib
import io
import re
import zipfile
import yaml
from lib.repository_memory import RepositoryMemoryIO
from lib.repository_paths import RepositoryPaths
MARKER = 'CLG-PERSONAL-CONSENT/1\n'
STATEMENT = 'Ich habe diese Anfrage persönlich geprüft und gebe diese Erklärung selbst ab; keine Automation handelt dabei für mich.'
MAX_BYTES = 10 * 1024 * 1024

class LegacyRepositoryLifecycleCapture:
    capture_method = 'github_api_get_via_gh'

    def __init__(self, context, *, path_factory=None):
        self.context = context
        self.path_factory = path_factory if path_factory is not None else context.path_factory

    def subject_id(self, identifier):
        return f'github-user:{identifier}'

    def profile_url(self, login):
        return f'https://github.com/{login}'

    def discussion_url(self, repository, number):
        return f'https://github.com/{repository}/pull/{number}'

    def replay_embedded(self, files):
        namespace = RepositoryPaths('/retained/captured-provider-bytes', RepositoryMemoryIO(files))
        scoped = type(self)(self.context, path_factory=namespace.path)
        return scoped.replay_capture(namespace.root)

    def comment_identity(self, comment):
        return {k: comment.get(k) for k in ('id', 'body', 'issue_url', 'html_url', 'created_at', 'updated_at', 'performed_via_github_app')} | {'user': {k: comment['user'].get(k) for k in ('id', 'type')}}

    def assess_bound_comments(self, request, comments, *, captured_at, previous_comments=()):
        """Verify captured provider fields and the person's explicit self-attestation.

    GitHub authenticates an account, not physical human presence. This probe
    establishes no remediation/closure approval and cannot activate runtime.
    """
        expected_id = int(request['required_subject_id'].split(':')[1])
        issue_url = f"https://api.github.com/repos/{request['repository_id']}/issues/{request['discussion_number']}"
        page_url = f"https://github.com/{request['repository_id']}/pull/{request['discussion_number']}"
        digest = self.context.contracts.canonical_digest(request)
        ids = [c['id'] for c in comments]
        self.context.contracts.require(all((type(i) is int and i > 0 for i in ids)) and len(ids) == len(set(ids)), 'Duplicate or invalid comment identity')
        current = {c['id']: c for c in comments}
        issues = []
        relevant = []
        unauthorized = []
        state = 'waiting_for_personal_statement'
        head = None
        for old in previous_comments:
            new = current.get(old['id'])
            if new is None or self.comment_identity(new) != self.comment_identity(old):
                issues.append({'comment_id': old['id'], 'reason': 'previous_statement_deleted_or_changed'})
        previous_time = None
        for comment in sorted(comments, key=lambda c: c['id']):
            body = comment.get('body', '')
            if not isinstance(body, str):
                continue
            parse_body = body.replace('\r\n', '\n')
            if not parse_body.startswith(MARKER):
                continue
            try:
                payload = self.context.adapter.strict_json(parse_body[len(MARKER):])
            except (ValueError, TypeError):
                if comment.get('user', {}).get('id') == expected_id:
                    relevant.append(comment)
                    issues.append({'comment_id': comment['id'], 'reason': 'malformed_personal_statement'})
                continue
            if not isinstance(payload, dict) or payload.get('request_digest') != digest:
                continue
            if comment.get('user', {}).get('id') != expected_id or comment.get('user', {}).get('type') != 'User' or 'performed_via_github_app' not in comment or (comment['performed_via_github_app'] is not None):
                unauthorized.append(comment['id'])
                continue
            relevant.append(comment)
            try:
                self.context.contracts.require(comment['issue_url'] == issue_url and comment['html_url'] == page_url + f"#issuecomment-{comment['id']}", 'Wrong discussion')
                self.context.contracts.require(comment['created_at'] == comment['updated_at'], 'Edited personal statement')
                issued = self.context.contracts.timestamp(comment['created_at'])
                self.context.contracts.require(self.context.contracts.timestamp(request['created_at']) <= issued <= self.context.contracts.timestamp(captured_at), 'Personal statement timestamp differs')
                self.context.contracts.require(previous_time is None or issued >= previous_time, 'Personal statement chronology differs')
                self.context.contracts.require(set(payload) == {'request_digest', 'disposition', 'supersedes_comment_id', 'statement'}, 'Unexpected statement fields')
                self.context.contracts.require(payload['statement'] == STATEMENT, 'Explicit personal self-attestation required')
                self.context.contracts.require(payload['disposition'] in ('approve', 'reject', 'revoke'), 'Unknown disposition')
                predecessor = payload['supersedes_comment_id']
                self.context.contracts.require(predecessor is None or type(predecessor) is int, 'Invalid predecessor identity')
                self.context.contracts.require(predecessor == head, 'Personal statement must reference its predecessor')
                self.context.contracts.require(payload['disposition'] != 'revoke' or state == 'confirmed', 'Only active confirmation can be revoked')
                state = {'approve': 'confirmed', 'reject': 'rejected', 'revoke': 'revoked'}[payload['disposition']]
                head = comment['id']
                previous_time = issued
            except (ValueError, KeyError, TypeError) as error:
                issues.append({'comment_id': comment['id'], 'reason': str(error)})
        return {'schema_version': '0.1.0', 'record_type': 'lifecycle-personal-channel-probe-result', 'request_digest': digest, 'status': 'needs_clarification' if issues else state, 'last_statement_id': head, 'relevant_comments': relevant, 'unauthorized_comment_ids': unauthorized, 'issues': issues, 'captured_at': captured_at, 'official_state': False, 'live_activation_approved': False, 'remediation_or_closure_authorized': False, 'human_presence': 'explicitly_self_attested_not_provider_attested'}

    def replay_bound_snapshot(self, snapshot, *, assessor):
        request = snapshot['request']
        before = [c for page in snapshot['comment_pages_before'] for c in self.context.adapter.strict_json(page)]
        after = [c for page in snapshot['comment_pages_after'] for c in self.context.adapter.strict_json(page)]
        self.context.contracts.require(before == after, 'Stored personal discussion changed during capture')
        issue = self.context.adapter.strict_json(snapshot['issue_response'])
        self.context.contracts.require(issue['number'] == request['discussion_number'] and issue['html_url'] == f"https://github.com/{request['repository_id']}/pull/{request['discussion_number']}" and bool(issue.get('pull_request')), 'Stored probe discussion differs')
        expected = assessor(request, after, captured_at=snapshot['result']['captured_at'], previous_comments=snapshot.get('previous_comments', []))
        self.context.contracts.require(snapshot['result'] == expected, 'Stored probe projection differs')
        return expected

    def sha(self, data):
        return hashlib.sha256(data).hexdigest()

    def positive_id(self, value):
        self.context.contracts.require(type(value) is int and value > 0, 'Expected positive provider integer identity')
        return str(value)

    def verify_capture(self, profile, *, repository, run, workflow, artifact, archive, files, captured_at):
        """Check supplied metadata/bytes. Offline callers do not establish provider authenticity."""
        schema_validator = self.context.contracts.schema_validator
        schema_validator('live-profile-preparation').validate(profile)
        scope, source = (profile['scope'], profile['source'])
        repo_id = scope['github_repository_id']
        self.context.contracts.require(repository['id'] == repo_id and repository['full_name'] == scope['repository_id'], 'Repository identity differs')
        self.context.contracts.require(repository['default_branch'] == source['allowed_branch'], 'Default branch differs')
        self.positive_id(run['id'])
        self.positive_id(run['workflow_id'])
        self.context.contracts.require(run['repository']['id'] == repo_id and run['head_repository']['id'] == repo_id, 'Run repository or fork differs')
        self.context.contracts.require(run['head_branch'] == source['allowed_branch'] and run['event'] == source['allowed_event'], 'Only selected mainline pushes are supported')
        self.context.contracts.require(run['status'] == 'completed' and run['conclusion'] == 'success', 'Run is not successfully completed')
        self.context.contracts.require(type(run['run_attempt']) is int and run['run_attempt'] == 1, 'Rerun artifact-to-attempt binding is not supported')
        commit = run['head_sha']
        self.context.contracts.require(re.fullmatch('[a-f0-9]{40}', commit) is not None, 'Full run commit required')
        self.context.contracts.require(run['path'] == source['workflow_path'] and workflow['path'] == source['workflow_path'] and (workflow['id'] == run['workflow_id']), 'Workflow identity differs')
        self.positive_id(artifact['id'])
        self.context.contracts.require(artifact['name'] == source['artifact_name'] and artifact['expired'] is False, 'Artifact name or availability differs')
        self.context.contracts.require(type(artifact['size_in_bytes']) is int and 0 < artifact['size_in_bytes'] <= MAX_BYTES and (0 < len(archive) <= MAX_BYTES), 'Artifact exceeds supported size')
        self.context.contracts.require(artifact['digest'] == 'sha256:' + self.sha(archive), 'Raw archive digest differs from GitHub metadata')
        arun = artifact['workflow_run']
        self.context.contracts.require(arun['id'] == run['id'] and arun['repository_id'] == repo_id and (arun['head_repository_id'] == repo_id) and (arun['head_sha'] == commit) and (arun['head_branch'] == source['allowed_branch']), 'Artifact run association differs')
        self.context.contracts.require(set(files) == set(source['reference_files']), 'Pinned producer file set differs')
        for path, digest in source['reference_files'].items():
            self.context.contracts.require(self.sha(files[path]) == digest, 'Producer revision differs: ' + path)
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            members = bundle.infolist()
            expected = {source['report_path'], 'governance-repository-security.md'}
            self.context.contracts.require(len(members) == len(expected) and {m.filename for m in members} == expected, 'Unexpected or duplicate archive member')
            self.context.contracts.require(all((not m.is_dir() and m.file_size <= MAX_BYTES and (not m.flag_bits & 1) for m in members)), 'Unsupported archive member')
            report_bytes = bundle.read(source['report_path'])
        report = self.context.adapter.strict_json(report_bytes)
        schema_path = 'schemas/governance-repository-security-report.schema.json'
        self.context.contracts.validator_class(self.context.adapter.strict_json(files[schema_path]), format_checker=self.context.contracts.format_checker).validate(report)
        model = yaml.safe_load(files['model/controls/governance-repository-security.yaml'])
        self.context.contracts.require(report['repository_id'] == scope['repository_id'] and report['profile_id'] == model['profile_id'] and (report['profile_version'] == model['version']), 'Report source profile or repository differs')
        observation = report['observation']
        self.context.contracts.require(observation.get('synthetic', False) is False, 'Synthetic observation is not a live capture')
        self.context.contracts.require(observation['repository_id'] == scope['repository_id'] and observation['observed_at'] == report['observed_at'], 'Observation identity differs')
        start, observed, created, completed, captured = map(self.context.contracts.timestamp, (run['run_started_at'], report['observed_at'], artifact['created_at'], run['updated_at'], captured_at))
        self.context.contracts.require(start <= observed <= created <= completed <= captured, 'Producer observation/artifact timeline differs')
        self.context.contracts.require(captured < self.context.contracts.timestamp(artifact['expires_at']), 'Artifact is expired at capture time')
        definitions = {c['id']: c for c in model['criteria']}
        criteria = report['criteria']
        self.context.contracts.require(len(criteria) == len(definitions) and {c['id'] for c in criteria} == set(definitions), 'Criterion coverage differs')
        for criterion in criteria:
            definition = definitions[criterion['id']]
            self.context.contracts.require(all((criterion[k] == definition[k] for k in ('id', 'key', 'title', 'severity', 'expected'))), 'Criterion definition differs')
        criterion = next((c for c in criteria if c['id'] == 'GRS-002'))
        reviews = observation['repository']['required_approving_reviews']
        self.context.contracts.require(type(reviews) is int and reviews >= 0, 'Review count is missing or ambiguous')
        self.context.contracts.require(criterion['key'] == 'pull_request_review_required' and criterion['observed'] is (reviews >= 1) and (criterion['status'] == ('pass' if reviews >= 1 else 'fail')), 'GRS-002 contradicts captured review count')
        failures = [c for c in criteria if c['status'] == 'fail']
        expected_summary = {'criteria': len(criteria), 'pass': len(criteria) - len(failures), 'fail': len(failures), 'critical_failures': sum((c['severity'] == 'critical' for c in failures)), 'high_failures': sum((c['severity'] == 'high' for c in failures))}
        self.context.contracts.require(report['summary'] == expected_summary and report['overall_status'] == ('findings' if failures else 'pass'), 'Report summary differs')
        result = {'schema_version': '0.1.0', 'record_type': 'lifecycle-live-evidence-preflight', 'environment': 'diagnostic', 'official_state': False, 'enforcement': 'report_only', 'acceptance_status': 'not_evaluated', 'verification_scope': 'captured_metadata_and_bytes', 'captured_at': captured_at, 'profile_ref': self.context.preparation.revision_ref(profile), 'repository_id': scope['repository_id'], 'source': {'run_id': run['id'], 'run_attempt': run['run_attempt'], 'commit_id': commit, 'workflow_id': run['workflow_id'], 'workflow_path': source['workflow_path'], 'artifact_id': artifact['id'], 'artifact_sha256': self.sha(archive), 'report_sha256': self.sha(report_bytes), 'observed_at': report['observed_at'], 'age_seconds': int((captured - observed).total_seconds()), 'source_profile_version': report['profile_version'], 'verified_file_digests': {p: self.sha(b) for p, b in files.items()}}, 'criterion': {'id': 'GRS-002', 'resource': scope['resource'], 'status': criterion['status'], 'required_approving_reviews': reviews}, 'checks': {name: 'pass' for name in ('repository_identity', 'mainline_run_context', 'workflow_identity', 'first_attempt_binding', 'artifact_run_association', 'archive_integrity', 'pinned_producer_revision', 'source_profile_and_criterion', 'producer_timeline', 'report_consistency')}, 'remaining_acceptance': ['approved_trust_roots_and_custody_retention', 'approved_freshness_skew_and_replay_policy', 'durable_live_replay_and_conflict_acceptance', 'personal_consent_verifier', 'accountable_live_acceptance'], 'limits': ['captured_provider_metadata_is_not_independently_authenticated_by_offline_replay', 'branch_protection_is_observed_at_run_time_not_proven_for_every_instant_of_the_commit', 'source_api_errors_are_preserved_in_the_report', 'no_lifecycle_observation_or_state_transition']}
        return (result, report_bytes)

    def replay_capture(self, directory):
        """Recompute a saved capture without making any provider-authentication claim."""
        root = self.path_factory(directory)
        self.context.contracts.require(root.is_dir() and (not root.is_symlink()), 'Capture directory is required')
        self.context.contracts.require(all((not path.is_symlink() for path in root.rglob('*'))), 'Capture symlinks are not supported')
        recorded = self.context.adapter.strict_json((root / 'preflight.json').read_bytes())
        manifest = recorded['capture']['snapshot_sha256']
        self.context.contracts.require({str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} == set(manifest) | {'preflight.json'}, 'Capture inventory differs')
        for name, digest in manifest.items():
            self.context.contracts.require(not self.path_factory(name).is_absolute() and '..' not in self.path_factory(name).parts, 'Invalid capture path')
            self.context.contracts.require(self.sha((root / name).read_bytes()) == digest, 'Captured bytes differ: ' + name)

        def read(name):
            return self.context.adapter.strict_json((root / name).read_bytes())
        profile = read('profile.json')
        run, artifact = (read('run-before.json'), read('artifact-before.json'))
        self.context.contracts.require(read('run-after.json') == run and read('artifact-after.json') == artifact, 'Captured metadata race')
        expected, report_bytes = self.verify_capture(profile, repository=read('repository.json'), run=run, workflow=read('workflow.json'), artifact=artifact, archive=(root / 'artifact.zip').read_bytes(), files={p: (root / 'producer' / p).read_bytes() for p in profile['source']['reference_files']}, captured_at=recorded['captured_at'])
        self.context.contracts.require((root / 'report.json').read_bytes() == report_bytes, 'Report extraction differs')
        self.context.contracts.require({k: v for k, v in recorded.items() if k != 'capture'} == expected, 'Preflight projection differs')
        return expected
