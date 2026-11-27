"""Whole original material self-security publication over explicit paths/process/API ports."""
from __future__ import annotations
import copy, json, re
REPORT_JSON = 'generated/reports/governance-repository-security.json'
VIEWER_DATA = 'generated/viewer/app/data.json'
ALLOWED_PATHS = {REPORT_JSON, 'generated/reports/governance-repository-security.md'}
VIEWER_PROJECTED_KEYS = ('repository_id', 'observed_at', 'profile_version', 'enforcement', 'overall_status', 'summary', 'risk_statement', 'criteria', 'next_steps', 'decision_boundary')

class SelfSecurityPublisher:

    def __init__(self, root, *, path_factory, process, api, profile, environment):
        self.root, self.Path, self.process, self.provider_api = (root, path_factory, process, api)
        self.profile, self.environment = (profile, environment)

    def git(self, root: self.Path, *args: str, check: bool=True) -> subprocess.CompletedProcess[str]:
        return self.process.run(['git', *args], cwd=root, text=True, capture_output=True, check=check)

    def normalized_report(self, report: dict) -> dict:
        """Remove observation time while retaining all security-relevant values."""
        result = copy.deepcopy(report)
        result.pop('observed_at', None)
        if isinstance(result.get('observation'), dict):
            result['observation'].pop('observed_at', None)
        return result

    def materially_equal(self, current: dict, previous: dict) -> bool:
        return self.normalized_report(current) == self.normalized_report(previous)

    def blocking_api_errors(self, report: dict) -> list[str]:
        observation = report.get('observation', {})
        errors = observation.get('api_errors', []) if isinstance(observation, dict) else []
        repository = observation.get('repository', {}) if isinstance(observation, dict) else {}
        ruleset_protection_confirmed = isinstance(repository, dict) and repository.get('branch_protected') is True
        return [error for error in errors if not (ruleset_protection_confirmed and isinstance(error, str) and error.endswith(self.profile.expected_legacy_protection_404))]

    def validate_viewer_projection(self, root: self.Path) -> None:
        report = json.loads((root / REPORT_JSON).read_text(encoding='utf-8'))
        viewer = json.loads((root / VIEWER_DATA).read_text(encoding='utf-8'))
        projection = viewer.get('repository_security')
        if not isinstance(projection, dict):
            raise ValueError('Viewer data has no repository_security projection')
        expected = {key: report[key] for key in VIEWER_PROJECTED_KEYS}
        actual = {key: projection.get(key) for key in VIEWER_PROJECTED_KEYS}
        if actual != expected:
            raise ValueError('Viewer self-security projection does not match the generated report')
        if projection.get('source_file') != REPORT_JSON:
            raise ValueError('Viewer self-security projection has an unexpected source file')

    def changed_paths(self, root: self.Path) -> list[str]:
        changed = set(self.git(root, 'diff', '--name-only', '--no-renames', '-z', 'HEAD').stdout.split('\x00'))
        changed.update(self.git(root, 'ls-files', '--others', '--exclude-standard', '-z').stdout.split('\x00'))
        changed.discard('')
        selected = []
        for path in sorted(changed):
            if path not in ALLOWED_PATHS:
                if path.startswith('generated/'):
                    continue
                raise ValueError(f'Self-security refresh contains an out-of-scope change: {path}')
            candidate = root / path
            for parent in (candidate, *candidate.parents):
                if parent == root:
                    break
                if parent.is_symlink():
                    raise ValueError(f'Self-security refresh contains a symlink: {path}')
            selected.append(path)
        return selected

    def report_at(self, root: self.Path, ref: str) -> dict | None:
        result = self.git(root, 'show', f'{ref}:{REPORT_JSON}', check=False)
        if result.returncode != 0:
            return None
        return json.loads(result.stdout)

    def open_refresh_pr(self, repository: str, api=None) -> dict | None:
        if api is None:
            api = self.provider_api
        endpoint = self.profile.open_pr_endpoint(repository)
        result = api('GET', endpoint)
        if not isinstance(result, list):
            raise ValueError(self.profile.literal('7d80622b54dd065d'))
        if len(result) > 1:
            raise ValueError('More than one open self-security refresh PR exists')
        return result[0] if result else None

    def write_outputs(self, root: self.Path, outputs: dict[str, bytes]) -> None:
        for path, content in outputs.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

    def publish(self, root: self.Path, *, repository: str, run_id: str, attempt: str, api=None) -> dict | None:
        if api is None:
            api = self.provider_api
        if not re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise ValueError('Invalid repository')
        if not re.fullmatch('[1-9][0-9]*', run_id) or not re.fullmatch('[1-9][0-9]*', attempt):
            raise ValueError('Workflow run ID and attempt must be positive integers')
        paths = self.changed_paths(root)
        if not paths:
            print('No self-security files changed.')
            return None
        if REPORT_JSON not in paths:
            raise ValueError('Self-security report JSON was not regenerated')
        current = json.loads((root / REPORT_JSON).read_text(encoding='utf-8'))
        api_errors = self.blocking_api_errors(current)
        if api_errors:
            raise ValueError(self.profile.incomplete_observation(api_errors))
        outputs = {path: (root / path).read_bytes() for path in paths}
        self.git(root, 'fetch', 'origin', 'main')
        self.git(root, 'merge-base', '--is-ancestor', 'HEAD', 'refs/remotes/origin/main')
        existing_pr = self.open_refresh_pr(repository, api)
        comparison_ref = 'HEAD'
        if existing_pr:
            remote = self.git(root, 'ls-remote', '--exit-code', '--heads', 'origin', f'refs/heads/{self.profile.branch}', check=False)
            if remote.returncode != 0:
                raise ValueError('Open self-security refresh PR has no remote branch')
            self.git(root, 'fetch', 'origin', self.profile.branch)
            comparison_ref = f'refs/remotes/origin/{self.profile.branch}'
        elif self.git(root, 'ls-remote', '--exit-code', '--heads', 'origin', f'refs/heads/{self.profile.branch}', check=False).returncode == 0:
            raise ValueError('Stale self-security refresh branch exists without an open PR')
        previous = self.report_at(root, comparison_ref)
        if previous is not None and self.materially_equal(current, previous):
            print('No material self-security change; observation timestamp is not proposed.')
            return None
        self.git(root, 'reset', '--hard', 'HEAD')
        self.git(root, 'clean', '-fd', '--', 'generated')
        if existing_pr:
            self.git(root, 'switch', '-C', self.profile.branch, f'refs/remotes/origin/{self.profile.branch}')
            self.git(root, '-c', 'user.name=' + self.profile.author_name, '-c', 'user.email=' + self.profile.author_email, '-c', 'commit.gpgsign=false', 'merge', '--no-edit', 'refs/remotes/origin/main')
        else:
            self.git(root, 'switch', '-c', self.profile.branch, 'refs/remotes/origin/main')
        self.write_outputs(root, outputs)
        staged_candidates = self.changed_paths(root)
        if not staged_candidates or not set(staged_candidates).issubset(ALLOWED_PATHS):
            raise ValueError('Self-security refresh produced no valid allowlisted change')
        self.git(root, 'add', '--', *staged_candidates)
        staged = set(self.git(root, 'diff', '--cached', '--name-only', '-z').stdout.strip('\x00').split('\x00'))
        if staged != set(staged_candidates):
            raise ValueError('Staged self-security refresh does not match its allowlist')
        self.git(root, '-c', 'user.name=' + self.profile.author_name, '-c', 'user.email=' + self.profile.author_email, '-c', 'commit.gpgsign=false', 'commit', '-m', 'Propose self-security status refresh')
        head = self.git(root, 'rev-parse', 'HEAD').stdout.strip()
        self.git(root, 'push', 'origin', f'HEAD:refs/heads/{self.profile.branch}')
        run_url = self.profile.run_url(repository, run_id, attempt)
        body = self.profile.review_body(run_id, attempt, head, run_url)
        if existing_pr:
            pr = api('PATCH', self.profile.pull_endpoint(repository, existing_pr['number']), {'title': 'Review current repository self-security status', 'body': body})
        else:
            pr = api('POST', self.profile.pull_endpoint(repository), {'title': 'Review current repository self-security status', 'head': self.profile.branch, 'base': 'main', 'body': body})
        if not isinstance(pr, dict) or not pr.get('html_url'):
            raise ValueError(self.profile.literal('d2b8ccbdc58d95ff'))
        print(f"Self-security review: {pr['html_url']}", flush=True)
        for workflow in self.profile.check_workflows:
            payload = {'ref': self.profile.branch}
            if workflow == 'dependency-review.yml':
                payload['inputs'] = {'base_ref': 'main', 'head_ref': self.profile.branch}
            api('POST', self.profile.workflow_endpoint(repository, workflow), payload)
        for output, value in ((self.profile.output_key, f"pull_request_url={pr['html_url']}\nbranch={self.profile.branch}\nmaterial_change=true\n"), (self.profile.summary_key, f"Self-security review: {pr['html_url']}\n")):
            if self.environment.get(output):
                with self.Path(self.environment[output]).open('a', encoding='utf-8') as stream:
                    stream.write(value)
        return pr

    def main(self) -> int:
        if self.environment.get(self.profile.ref_key) != 'refs/heads/main':
            raise SystemExit('Self-security publication must run from protected main')
        self.validate_viewer_projection(self.root)
        self.publish(self.root, repository=self.environment[self.profile.repository_key], run_id=self.environment[self.profile.run_id_key], attempt=self.environment[self.profile.attempt_key])
        return 0
