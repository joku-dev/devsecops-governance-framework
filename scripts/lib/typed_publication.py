"""Complete typed publisher extension in an isolated original publisher namespace."""
from __future__ import annotations
from lib.operational_publication import OperationalPublisher, LEDGERS as BASE_LEDGERS, SCOPES as BASE_SCOPES
ADDITIONAL_LEDGERS = ('status/measured-security-results/', 'status/measured-l1-results/', 'status/control-evidence-assurance/')
LEDGERS = (*BASE_LEDGERS, *ADDITIONAL_LEDGERS)
SCOPES = {**BASE_SCOPES, 'typed-evidence': (*BASE_SCOPES['typed-evidence'], *ADDITIONAL_LEDGERS)}

class TypedEvidencePublisher(OperationalPublisher):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.LEDGERS = tuple(BASE_LEDGERS)
        self.SCOPES = {key: tuple(paths) for (key, paths) in BASE_SCOPES.items()}

    def allowed(self, path: str, scope: str) -> bool:
        return any((path.startswith(item) if item.endswith('/') else path == item for item in self.SCOPES[scope]))

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
            if path.startswith(self.LEDGERS):
                existing = self.process.run(['git', 'cat-file', '-e', f'HEAD:{path}'], cwd=root, capture_output=True, check=False)
                if existing.returncode == 0:
                    raise ValueError(f'Historical evidence is append-only: {path}')
            selected.append(path)
        return selected

    def configure(self) -> None:
        self.LEDGERS = (*self.LEDGERS, *ADDITIONAL_LEDGERS)
        self.SCOPES['typed-evidence'] = (*self.SCOPES['typed-evidence'], *ADDITIONAL_LEDGERS)

    def main(self) -> int:
        self.configure()
        return super().main()
