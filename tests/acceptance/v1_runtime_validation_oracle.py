"""Whole unchanged frozen V1 CLI in an isolated trusted fixture directory."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


REFERENCE = '6b557fefe295b58272d2271326576ca3a3687197'
PROGRAMS = {
    'scripts/validate_runtime_governance.py',
    'scripts/generate_architecture_traceability_csv.py',
    'scripts/generate_architecture_governance_report.py',
    'scripts/generate_end_to_end_governance_report.py',
}


def fixtures(directory):
    directory = Path(directory)
    contract = json.loads((directory / 'contract.json').read_text())
    assert contract['v1_reference'] == REFERENCE and set(contract['sources']) == PROGRAMS
    output = {}
    for kind in ('sources', 'data'):
        output[kind] = {}
        for name, row in contract[kind].items():
            path = directory / row['file']
            assert path.resolve().is_relative_to(directory.resolve()) and not path.is_symlink()
            raw = path.read_bytes()
            assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
            assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['git_blob']
            output[kind][name] = raw
    output['membership'] = contract['membership']
    return output


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for scope in ('architecture', 'schemas', 'policies', 'generated')
            if (root / scope).exists() for p in sorted((root / scope).rglob('*')) if p.is_file()}


class Original:
    def __init__(self, directory, root):
        self.contract = fixtures(directory)
        self.root = Path(root).resolve()
        for name, raw in self.contract['sources'].items():
            path = self.root / name
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.write_bytes(raw); path.chmod(0o600)

    def write_data(self, files):
        for name, raw in files.items():
            path = self.root / name
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.write_bytes(raw); path.chmod(0o600)

    def run(self, *, opa):
        environment = {**os.environ, 'PATH': '' if opa is None else str(Path(opa).parent)}
        value = subprocess.run([sys.executable, str(self.root / 'scripts/validate_runtime_governance.py')],
            cwd=self.root, env=environment, capture_output=True, timeout=120)
        return value.returncode, value.stdout, value.stderr, snapshot(self.root)
