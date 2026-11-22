"""Whole original operational publisher over explicit path, process, API and gate ports."""
from __future__ import annotations
import re
LEDGERS = ('governance/lifecycle/live-validation/transactions/', 'governance/lifecycle/pilot-actions/transactions/', 'generated/reports/lifecycle-operating-acceptance/', 'governance/lifecycle/synthetic-closure/transactions/', 'status/results/', 'status/architecture-results/', 'status/typed-evidence-results/', 'status/collection-attempts/', 'status/intake-events/', 'status/intake-conflicts/')
COMMON = ('status/collection-attempts/', 'status/intake-events/', 'status/intake-conflicts/', 'status/intake-health.json', 'generated/graph/governance-graph.json', 'generated/reports/blocking-mode-alignment.json', 'generated/reports/blocking-readiness.json', 'generated/reports/multi-consumer-readiness.json', 'generated/reports/multi-consumer-readiness.md', 'generated/reports/replay-triage.json', 'generated/reports/replay-triage.md', 'generated/viewer/status-viewer.html')
SCOPES = {'lifecycle-pilot': ('governance/lifecycle/live-validation/transactions/', 'governance/lifecycle/pilot-actions/transactions/', 'generated/reports/lifecycle-operating-acceptance/', 'status/governance-lifecycle-live-validation.json', 'generated/reports/governance-lifecycle-live-validation.md', 'status/governance-lifecycle-pilot-actions.json', 'generated/reports/governance-lifecycle-pilot-actions.md', 'status/governance-lifecycle-live.json', 'generated/reports/governance-lifecycle-live.md'), 'lifecycle-synthetic': ('governance/lifecycle/synthetic-closure/transactions/', 'status/governance-lifecycle-closure-index.json', 'generated/reports/governance-lifecycle-pilot.md', 'status/governance-lifecycle-overview.json', 'generated/reports/governance-lifecycle-overview.md', 'generated/viewer/governance-lifecycle-viewer.html'), 'devsecops': COMMON + ('status/results/', 'status/repository-results-index.json'), 'architecture': COMMON + ('status/architecture-results/', 'status/architecture-results-index.json'), 'typed-evidence': COMMON + ('status/typed-evidence-results/', 'status/typed-evidence-results-index.json'), 'portfolio': ('generated/reports/portfolio-onboarding-status.json', 'generated/reports/portfolio-onboarding-status.md')}

class OperationalPublisher:

    def __init__(self, root, *, path_factory, process, api, gates, profile, environment, argument_parser, argv):
        self.root, self.Path, self.process, self.provider_api = (root, path_factory, process, api)
        self.gates, self.profile, self.environment, self.argument_parser, self.argv = (gates, profile, environment, argument_parser, list(argv))

    def git(self, root: self.Path, *args: str) -> str:
        result = self.process.run(['git', *args], cwd=root, text=True, capture_output=True, check=True)
        return result.stdout

    def allowed(self, path: str, scope: str) -> bool:
        return any((path.startswith(item) if item.endswith('/') else path == item for item in SCOPES[scope]))

    def selected_paths(self, root: self.Path, scope: str) -> list[str]:
        changed = set(self.git(root, 'diff', '--name-only', '--no-renames', '-z', 'HEAD').split('\x00'))
        changed.update(self.git(root, 'ls-files', '--others', '--exclude-standard', '-z').split('\x00'))
        changed.discard('')
        selected = []
        for path in sorted(changed):
            if not self.allowed(path, scope):
                if path.startswith('generated/'):
                    continue
                raise ValueError(f'Operational update contains an out-of-scope change: {path}')
            candidate = root / path
            for parent in (candidate, *candidate.parents):
                if parent == root:
                    break
                if parent.is_symlink():
                    raise ValueError(f'Operational update contains a symlink: {path}')
            if path.startswith(LEDGERS):
                existing = self.process.run(['git', 'cat-file', '-e', f'HEAD:{path}'], cwd=root, capture_output=True, check=False)
                if existing.returncode == 0:
                    raise ValueError(f'Historical evidence is append-only: {path}')
            selected.append(path)
        return selected

    def publish(self, root: self.Path, *, scope: str, repository: str, run_id: str, attempt: str, api=None) -> dict | None:
        if api is None:
            api = self.provider_api
        if scope not in SCOPES or not re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise ValueError('Invalid scope or repository')
        if not re.fullmatch('[1-9][0-9]*', run_id) or not re.fullmatch('[1-9][0-9]*', attempt):
            raise ValueError('Workflow run ID and attempt must be positive integers')
        paths = self.selected_paths(root, scope)
        if not paths:
            print('No operational changes to propose.')
            return None
        self.git(root, 'fetch', 'origin', 'main')
        self.git(root, 'merge-base', '--is-ancestor', 'HEAD', 'refs/remotes/origin/main')
        if scope == 'lifecycle-pilot':
            validate_publication = self.gates.validate_publication
            validate_publication(root, self.git(root, 'rev-parse', 'refs/remotes/origin/main').strip())
        if scope == 'lifecycle-synthetic':
            check_accepted_prefix, validate_pilot = (self.gates.check_accepted_prefix, self.gates.validate_pilot)
            check_accepted_prefix(root, self.git(root, 'rev-parse', 'refs/remotes/origin/main').strip())
            validate_pilot(root)
            validate_overview = self.gates.validate_overview
            overview = validate_overview(root)
            validate_viewer = self.gates.validate_viewer
            validate_viewer(root, overview=overview)
        branch = f'automation/{scope}/{run_id}-{attempt}'
        self.git(root, 'switch', '-c', branch)
        self.git(root, 'reset', '--mixed', 'HEAD')
        self.git(root, 'add', '--', *paths)
        staged = self.git(root, 'diff', '--cached', '--name-only', '-z').strip('\x00').split('\x00')
        if set(staged) != set(paths) or not all((self.allowed(path, scope) for path in staged)):
            raise ValueError('Staged operational update does not match its allowlist')
        self.git(root, '-c', 'user.name=' + self.profile.author_name, '-c', 'user.email=' + self.profile.author_email, '-c', 'commit.gpgsign=false', 'commit', '-m', f'Propose {scope} operational update')
        head = self.git(root, 'rev-parse', 'HEAD').strip()
        self.git(root, 'push', 'origin', f'HEAD:refs/heads/{branch}')
        run_url = self.profile.run_url(repository, run_id, attempt)
        pr = api(self.profile.pulls_endpoint(repository), {'title': f'Review {scope} operational update (run {run_id}, attempt {attempt})', 'head': branch, 'base': 'main', 'body': self.profile.review_body(scope, run_id, attempt, head, run_url)})
        print(f"Opened operational review: {pr['html_url']}", flush=True)
        for output, text in ((self.profile.output_key, f"pull_request_url={pr['html_url']}\nbranch={branch}\n"), (self.profile.summary_key, f"Operational review: {pr['html_url']}\n")):
            if self.environment.get(output):
                with self.Path(self.environment[output]).open('a', encoding='utf-8') as stream:
                    stream.write(text)
        for workflow in self.profile.check_workflows:
            api(self.profile.workflow_endpoint(repository, workflow), {'ref': branch})
        return pr

    def main(self) -> int:
        parser = self.argument_parser(description=self.profile.description)
        parser.add_argument('--scope', required=True, choices=SCOPES)
        args = parser.parse_args(self.argv)
        if self.environment.get(self.profile.ref_key) != 'refs/heads/main':
            parser.error('Operational publication must run from the protected main workflow')
        self.publish(self.root, scope=args.scope, repository=self.environment[self.profile.repository_key], run_id=self.environment[self.profile.run_id_key], attempt=self.environment[self.profile.attempt_key])
        return 0
