"""Independent test-only oracle: exact frozen V1 sources, never consumer code."""
import base64
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

REFERENCE_SHA256 = {
    'check_repo_governance_integration.py.txt': 'e9ee576e413613fb1611cd0819c0acf7d9e8af448e3c2e9fb257752c32d2d34d',
    'check_repository_onboarding_readiness.py.txt': 'de4a798f7c7c3a1c212fd48a0cae2bf0bfbcdeb06794ac15297b7879be4e8828'}


def load_fixture(directory):
    directory = Path(directory); value = json.loads((directory / 'cases.json').read_text())
    assert value['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
    for name, expected in REFERENCE_SHA256.items():
        assert value['reference_files'][name]['sha256'] == expected
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected
    return value


def git(root, *arguments):
    environment = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null',
                       GIT_TERMINAL_PROMPT='0', GIT_AUTHOR_DATE='2026-11-15T12:00:00+00:00',
                       GIT_COMMITTER_DATE='2026-11-15T12:00:00+00:00')
    return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
        '-C', str(root), *arguments], env=environment, stderr=subprocess.PIPE).decode().strip()


def make_repository(root, case):
    root = Path(root).resolve(); root.mkdir(mode=0o700)
    for name, value in case['files'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts and '.git' not in Path(name).parts
        path = root / name; path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(base64.b64decode(value['base64'], validate=True) if isinstance(value, dict) else value.encode())
    git(root, 'init', '--initial-branch=main'); git(root, 'config', 'user.name', 'Synthetic Oracle')
    git(root, 'config', 'user.email', 'synthetic@example.invalid'); git(root, 'config', 'core.autocrlf', 'false')
    git(root, 'add', '--all'); git(root, 'commit', '-m', 'Synthetic source-only reference')
    return git(root, 'rev-parse', 'HEAD')


def original_files(fixtures, oracle, target, repository_id, at, *, canonical_order=False):
    fixtures = Path(fixtures); contract = load_fixture(fixtures)
    oracle = Path(oracle).resolve(); code = oracle / contract['product_label']; scripts = code / 'scripts'
    scripts.mkdir(mode=0o700, parents=True)
    for name in REFERENCE_SHA256: (scripts / name.removesuffix('.txt')).write_bytes((fixtures / name).read_bytes())
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None): return datetime.fromisoformat(at.replace('Z', '+00:00')).astimezone(tz or timezone.utc)
    def load(name):
        spec = importlib.util.spec_from_file_location('_original_' + name, scripts / name)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); module.datetime = Clock
        return module
    integration = load('check_repo_governance_integration.py')
    onboarding = load('check_repository_onboarding_readiness.py')
    if canonical_order:
        # The original V1 sources and main remain unchanged. This separate
        # reference supplies an explicitly ordered input iterator for the new
        # profile; it is not a claim about V1's native filesystem enumeration.
        original_iterator = integration.iter_ci_files
        integration.iter_ci_files = lambda root: iter(sorted(original_iterator(root),
            key=lambda path: path.relative_to(root).as_posix().encode('utf-8')))
    output = oracle / 'output'; output.mkdir(mode=0o700)
    first, second, markdown = output / 'integration.json', output / 'onboarding.json', output / 'onboarding.md'
    with patch.object(sys, 'argv', ['original-integration', '--target-repo', str(target), '--output-file', str(first)]), redirect_stdout(io.StringIO()):
        integration_exit = integration.main()
    with patch.object(sys, 'argv', ['original-onboarding', '--target-repo', str(target), '--repository-id', repository_id,
        '--output-json', str(second), '--output-md', str(markdown)]), redirect_stdout(io.StringIO()):
        onboarding_exit = onboarding.main()
    paths = contract['logical_outputs']
    return {paths['integration']: first.read_bytes(), paths['onboarding_json']: second.read_bytes(),
            paths['onboarding_markdown']: markdown.read_bytes()}, (integration_exit, onboarding_exit)
