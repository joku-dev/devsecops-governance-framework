"""Finite GET-only acquisition and inert source capture for the legacy profile."""
from copy import deepcopy
from datetime import datetime, timezone
from fnmatch import fnmatchcase
import json
import os
from pathlib import Path

from lib.private_credentials import check_private_file
from lib.provider_errors import AccessFailure
from lib.providers.self_security_capture import request_paths
from lib.providers.transports import Reader
from lib.providers.validation_worktree import directory, file_bytes, signature
from lib.result_bytes import safe_bytes
from lib.validation_files import relative

MAX_SOURCE = 16 * 1024**2
MAX_CAPTURE = 32 * 1024**2


def repository_default():
    return os.environ.get('GITHUB_REPOSITORY', 'joku-dev/devsecops-governance-framework')


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def capture_source(source):
    source = Path(source)
    if source.is_symlink():
        raise ValueError('ordinary_security_source_required')
    root = source.resolve(strict=True)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    before = os.fstat(fd)
    data = {}
    def read(parent, name, label):
        relative(label)
        if len(data) >= 1024:
            raise ValueError('security_source_count_budget')
        data[label] = file_bytes(parent, name)
        if sum(map(len, data.values())) > MAX_CAPTURE:
            raise ValueError('security_source_byte_budget')
    try:
        with directory(fd, '.github') as configuration:
            if configuration is not None:
                with directory(configuration, 'workflows') as workflows:
                    if workflows is not None:
                        names = sorted(os.listdir(workflows))
                        if len(names) > 10000:
                            raise ValueError('security_source_membership_budget')
                        for name in names:
                            if fnmatchcase(name, '*.y*ml'):
                                read(workflows, name, '.github/workflows/' + name)
                        if names != sorted(os.listdir(workflows)):
                            raise ValueError('security_source_membership_changed')
                for name in ('CODEOWNERS', 'dependabot.yml'):
                    try:
                        os.stat(name, dir_fd=configuration, follow_symlinks=False)
                    except FileNotFoundError:
                        continue
                    read(configuration, name, '.github/' + name)
        if (signature(before) != signature(os.fstat(fd))
                or signature(before) != signature(os.stat(root, follow_symlinks=False))):
            raise ValueError('security_source_root_changed')
        return {name: data[name] for name in sorted(data)}
    finally:
        os.close(fd)


class SecurityAPI:
    """Configured public SaaS endpoint; credentials never enter retained rows.

    Errors are bounded transport codes, not untrusted gh stderr. The legacy
    normalization consumes those visible endpoint-specific errors unchanged.
    """
    def __init__(self, repository, *, token_file=None, on_intent=None, on_result=None):
        self.paths = request_paths(repository)
        token = ''
        if token_file is not None:
            check_private_file(token_file)
            token = safe_bytes(token_file, limit=16384).decode('utf-8').strip()
            if not token or any(ord(c) < 33 or ord(c) > 126 for c in token):
                raise ValueError('invalid_security_read_token')
        self.reader = Reader('https://api.github.com', token, budget=7)
        self.on_intent, self.on_result = on_intent, on_result
        self.rows = []

    def __call__(self, path):
        index = len(self.rows)
        if index >= len(self.paths) or path != self.paths[index]:
            raise ValueError('security_native_request_outside_profile')
        if self.on_intent is not None:
            self.on_intent({'sequence': index + 1, 'method': 'GET', 'path': path})
        try:
            response, error = self.reader.get('/' + path), None
        except AccessFailure as failure:
            response, error = None, path + ': ' + failure.code
        row = {'sequence': index + 1, 'method': 'GET', 'path': path,
               'response': response, 'error': error}
        if len(json.dumps(row, allow_nan=False).encode()) > 5 * 1024**2:
            raise ValueError('security_native_response_budget')
        self.rows.append(deepcopy(row))
        if self.on_result is not None:
            self.on_result(deepcopy(row))
        return deepcopy(response), error


class ReplaySecurityAPI:
    """Exact ordered captured facts; no fresh HTTP or provenance assertion."""
    def __init__(self, repository, rows):
        self.paths, self.rows, self.position = request_paths(repository), deepcopy(rows), 0
        if not isinstance(rows, list) or len(rows) != 7:
            raise ValueError('security_native_response_count')

    def __call__(self, path):
        index = self.position
        if index >= 7 or path != self.paths[index]:
            raise ValueError('security_replay_request_changed')
        row = self.rows[index]
        if (not isinstance(row, dict)
                or set(row) != {'sequence', 'method', 'path', 'response', 'error'}
                or type(row['sequence']) is not int or row['sequence'] != index + 1
                or row['method'] != 'GET' or row['path'] != path
                or row['error'] is not None and (
                    not isinstance(row['error'], str) or not row['error'].startswith(path + ': '))):
            raise ValueError('security_replay_response_changed')
        if len(json.dumps(row, allow_nan=False).encode()) > 5 * 1024**2:
            raise ValueError('security_native_response_budget')
        self.position += 1
        return deepcopy(row['response']), row['error']

    def finish(self):
        if self.position != 7:
            raise ValueError('security_replay_response_unused')
