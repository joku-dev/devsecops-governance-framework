"""Bounded read-only source/history capture; never run supplied source programs."""
from pathlib import Path
import os
from contextlib import contextmanager

from lib import repository_capture
from lib.requirement_validation_replay import decode_history
from lib.providers.operations_files import held_root, raw_file
from referencing.exceptions import NoSuchResource
from lib.providers.repository_data_io import RepositoryDataIO
from lib.providers.validation_worktree import signature
from lib.review_git import git
from lib.validation_files import MAX_FILE, MAX_TOTAL

MAX_CALLS = 20000


class Source(RepositoryDataIO):
    def __init__(self, root, trace, record, resources=()):
        root = Path(root).expanduser().absolute()
        if root.is_symlink(): raise ValueError('requirement_source_alias_forbidden')
        self.root = root
        with held_root(root) as fd:
            value = os.fstat(fd)
            self.identity = (value.st_dev, value.st_ino, value.st_mode)
        self.resources={row['uri']:row['label'] for row in resources}
        self.trace, self.record, self.total = trace, record, 0
        self.observed = {}

    def parts(self, name):
        parts = super().parts(name)
        if name and repository_capture.private_name(name):
            raise ValueError('requirement_private_source_not_admitted')
        return parts

    @contextmanager
    def opened(self):
        with held_root(self.root) as fd:
            before = os.fstat(fd)
            if (before.st_dev, before.st_ino, before.st_mode) != self.identity:
                raise ValueError('requirement_source_identity_changed')
            yield fd
            if signature(before) != signature(os.fstat(fd)):
                raise ValueError('requirement_source_changed_during_read')

    def call(self, action, name, effect):
        if len(self.trace) >= MAX_CALLS:
            self.record.capture_incomplete=True
            raise ValueError('requirement_source_call_budget')
        row = {'kind': 'source', 'action': action, 'path': name}
        try:
            value = effect()
            if action == 'stat' and value and value['kind'] in ('symlink', 'other'):
                raise ValueError('requirement_source_link_or_special_not_admitted')
            if action in ('read','resource'):
                self.total += len(value)
                if self.total > MAX_TOTAL: raise ValueError('requirement_source_total_budget')
                stored = {'blob': self.record.blob(value)}
            else: stored = value
            # A repeated source operation must observe the same bytes/facts.
            key = (action, name)
            if key in self.observed and stored != self.observed[key]:
                raise ValueError('requirement_source_changed_between_reads')
            self.observed[key] = stored
        except (ValueError, OSError) as error:
            if isinstance(error,ValueError): self.record.capture_incomplete=True
            row['failure'] = {'type': type(error).__name__, 'message': str(error),
                'errno': getattr(error, 'errno', None), 'strerror': getattr(error, 'strerror', None),
                'filename': getattr(error, 'filename', None)}
            self.trace.append(row)
            raise
        row['value'] = stored
        self.trace.append(row)
        return value

    def stat(self, name):
        return self.call('stat', name, lambda: super(Source, self).stat(name))

    def read(self, name):
        return self.call('read', name, lambda: super(Source, self).read(name))

    def entries(self, name):
        return self.call('entries', name, lambda: super(Source, self).entries(name))


    def resource(self, uri):
        if uri not in self.resources:
            raise NoSuchResource(ref=uri)
        path=Path(self.resources[uri])
        def effect():
            with held_root(path.parent) as root:
                return raw_file(root,path.name)
        return self.call('resource',uri,effect)


class History:
    def __init__(self, source, trace, record):
        self.source, self.trace, self.record = Path(source), trace, record

    def observe(self, action, base, path=None):
        if len(self.trace) >= MAX_CALLS:
            self.record.capture_incomplete=True
            raise ValueError('requirement_source_call_budget')
        request = {'action': action, 'base': base, 'path': path}
        commands = history_commands(action,base,path)
        token = self.record.sequence
        def effect():
            rows = []
            for arguments in commands:
                # The fixed group intent is durable before each bounded read.
                try: raw = git(self.source, *arguments, limit=MAX_FILE)
                except ValueError as error:
                    if str(error) != 'review_local_git_read_failed': raise
                    rows.append({'arguments': list(arguments), 'completed_successfully': False, 'stdout': None})
                else:
                    rows.append({'arguments': list(arguments), 'completed_successfully': True, 'stdout': self.record.blob(raw)})
                    break
            return rows
        try:
            rows = self.record.perform('requirement_history', request, effect)
        except Exception:
            self.record.capture_incomplete = True
            raise
        finally:
            self.trace.append({'kind': 'history', 'operation': token, **request})
        return decode_history(action, rows, lambda ref: (self.record.blobs / ref['sha256']).read_bytes())

    def previous(self, base, path): return self.observe('previous', base, path)
    def existed(self, base, path): return self.observe('existed', base, path)
    def changed(self, base): return self.observe('changed', base)



def history_commands(action,base,path=None):
    commands = {'previous': [('show', base + ':' + path)] if path is not None else [],
                'existed': [('cat-file', '-e', base + ':' + path)] if path is not None else [],
                'changed': [('diff', '--no-ext-diff', '--no-textconv', '--name-only', base + '...HEAD'),
                            ('diff', '--no-ext-diff', '--no-textconv', '--name-only', base)]}
    if action not in commands or not commands[action]:
        raise ValueError('requirement_history_action_not_selected')
    return commands[action]
