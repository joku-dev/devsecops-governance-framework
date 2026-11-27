"""Whole original accepted-prefix checks over explicit context, filesystem and Git ports."""
import re

class AcceptedPrefix:

    def __init__(self, context, *, path_factory, transport):
        self.context, self.Path, self.transport = (context, path_factory, transport)

    def git(self, repo, *args):
        return self.transport.check_output(['git', *args], cwd=repo, text=True)

    def check_accepted_prefix(self, repo, base_ref):
        """Preserve every accepted blob; merged union is separately replayed for forks."""
        self.context.contracts.require(re.fullmatch('[a-f0-9]{40}', base_ref) is not None, 'Base must be an immutable Git SHA')
        self.context.contracts.require(base_ref != '0' * 40, 'An existing accepted base is required')
        self.git(repo, 'cat-file', '-e', base_ref + '^{commit}')
        tracked = self.git(repo, 'ls-files', '--', *self.context.ledger.input_ledger_paths).splitlines()
        for name in tracked:
            self.context.contracts.require(re.fullmatch('(?:' + '|'.join((re.escape(p) for p in self.context.ledger.input_ledger_paths)) + ')/transactions/[0-9]{8,}-[a-f0-9]{64}\\.json', name) is not None, 'Only published transactions may be tracked in the ledger')
        entries = self.git(repo, 'ls-tree', '-r', base_ref, '--', *self.context.ledger.input_ledger_paths).splitlines()
        for entry in entries:
            metadata, name = entry.split('\t', 1)
            mode, kind, digest = metadata.split()
            self.context.contracts.require(mode == '100644' and kind == 'blob', 'Unexpected accepted ledger file type')
            path = self.Path(repo) / name
            self.context.contracts.require(path.is_file() and (not path.is_symlink()), 'Accepted transaction deleted or replaced')
            self.context.contracts.require(self.git(repo, 'hash-object', '--', str(path)).strip() == digest, 'Accepted transaction modified')
        if any((name.split('\t', 1)[1].startswith((self.context.ledger.LEDGER_PATH + '/', self.context.ledger.PILOT_LEDGER_PATH + '/', self.context.ledger.EXCEPTION_LEDGER_PATH + '/')) for name in entries)):
            before = self.git(repo, 'rev-parse', base_ref + ':' + self.context.ledger.PROFILE_PATH).strip()
            after = self.git(repo, 'hash-object', '--', self.context.ledger.PROFILE_PATH).strip()
            self.context.contracts.require(before == after, 'Accepted profile requires an explicit versioned migration')
        snapshot = self.transport.run(['git', 'cat-file', '-e', base_ref + ':' + self.context.ledger.EXCEPTION_PROFILE_PATH], cwd=repo, capture_output=True)
        if snapshot.returncode == 0:
            path = self.Path(repo) / self.context.ledger.EXCEPTION_PROFILE_PATH
            self.context.contracts.require(path.is_file() and (not path.is_symlink()), 'Accepted exception profile deleted or replaced')
            before = self.git(repo, 'rev-parse', base_ref + ':' + self.context.ledger.EXCEPTION_PROFILE_PATH).strip()
            self.context.contracts.require(self.git(repo, 'hash-object', '--', str(path)).strip() == before, 'Exception profile requires a versioned migration')
        for entry in self.git(repo, 'ls-tree', '-r', base_ref, '--', self.context.preparation.PREPARATION_PATH, self.context.admission.OPERATING_PATH, 'model/governance/lifecycle/personal-channel', 'generated/reports/lifecycle-personal-channel', 'model/governance/lifecycle/operating-acceptance', 'model/governance/lifecycle/action-requests', 'generated/reports/lifecycle-operating-acceptance').splitlines():
            metadata, name = entry.split('\t', 1)
            mode, kind, digest = metadata.split()
            self.context.contracts.require(mode == '100644' and kind == 'blob', 'Unexpected accepted preparation file type')
            path = self.Path(repo) / name
            self.context.contracts.require(path.is_file() and (not path.is_symlink()), 'Accepted preparation deleted or replaced')
            self.context.contracts.require(self.git(repo, 'hash-object', '--', str(path)).strip() == digest, 'Accepted preparation requires a new immutable revision')
        return len(entries)
