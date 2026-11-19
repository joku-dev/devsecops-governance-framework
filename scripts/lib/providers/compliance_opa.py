"""Closed whole-policy check and ten full legacy queries on frozen own policies.

Only exact current committed product Rego is executable. Inspected repository
programs or operator-selected policy files are never used as a fallback.
"""
from pathlib import Path
from copy import deepcopy
import hashlib
import re

from control_evaluation import POLICY_QUERIES
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT
from lib.portable.runtime import approved_opa_hashes
from lib.providers.attestation_verification import executable
from lib.providers.product_test_worker import supervise
from lib.result_bytes import safe_bytes

MAX_INPUT = 16 * 1024**2
MAX_STREAM = 8 * 1024**2


class ComplianceOPA:
    def __init__(self, *, tool, source_revision, display_root, input_label,
                 input_bytes, workarea, on_event):
        if not callable(on_event):
            raise ValueError('compliance_opa_journal_required')
        if input_bytes is not None and (type(input_bytes) is not bytes or len(input_bytes) > MAX_INPUT):
            raise ValueError('bounded_compliance_input_bytes_required')
        self.tool = executable(tool)
        if self.tool[1] not in approved_opa_hashes('1.18.2'):
            raise ValueError('compliance_opa_checksum_mismatch')
        if source_revision != git_read(ROOT, 'rev-parse', 'HEAD').decode().strip():
            raise ValueError('compliance_opa_current_product_required')
        self.revision = source_revision
        self.display_root, self.input_label = Path(display_root), Path(input_label)
        if not self.display_root.is_absolute() or not self.input_label.is_absolute():
            raise ValueError('absolute_compliance_opa_labels_required')
        self.root = Path(workarea)
        if (self.root.exists() or self.root.is_symlink()
                or any(p.is_symlink() for p in self.root.parents)):
            raise ValueError('fresh_private_compliance_opa_workarea_required')
        self.root.mkdir(mode=0o700)
        self.frozen = self.root / 'frozen'; self.frozen.mkdir(mode=0o700)
        # None is an explicit failed/missing input observation. Preserve native
        # check/eval ordering instead of replacing every failed eval by an early
        # Python exception; the control reader later exposes its original error.
        self.files = {} if input_bytes is None else {'input.json': input_bytes}
        records = git_read(ROOT, 'ls-tree', '-r', '-z', source_revision, '--', 'policies/opa').split(b'\0')
        for record in filter(None, records):
            meta, name = record.split(b'\t', 1)
            mode, kind, oid = meta.decode().split()
            name = name.decode()
            if (kind != 'blob' or mode not in ('100644', '100755')
                    or not name.startswith('policies/opa/') or '..' in Path(name).parts):
                raise ValueError('ordinary_committed_compliance_policy_required')
            self.files[name] = git_read(ROOT, 'cat-file', 'blob', oid)
        if len(self.files) <= 1 or len(self.files) > 10000 or sum(map(len, self.files.values())) > 64 * 1024**2:
            raise ValueError('bounded_complete_compliance_policy_inventory_required')
        for name, raw in self.files.items():
            path = self.frozen / name
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(raw)
            path.chmod(0o600)
        self.on_event, self.observations = on_event, []
        version = self.observe([self.tool[0], 'version'], ['opa', 'version'])
        if version.returncode or re.search(r'^Version:\s*1\.18\.2\s*$', version.stdout, re.M) is None:
            raise ValueError('compliance_opa_version_mismatch')

    def check(self):
        if (executable(self.tool[0]) != self.tool
                or git_read(ROOT, 'rev-parse', 'HEAD').decode().strip() != self.revision):
            raise ValueError('compliance_opa_tool_or_product_changed')
        members = list(self.frozen.rglob('*'))
        if any(path.is_symlink() for path in members):
            raise ValueError('compliance_opa_frozen_symlink')
        physical = {path.relative_to(self.frozen).as_posix() for path in members if path.is_file()}
        if physical != set(self.files):
            raise ValueError('compliance_opa_frozen_membership_changed')
        for name, raw in self.files.items():
            path = self.frozen / name
            if any(p.is_symlink() for p in (path, *path.parents)) or safe_bytes(path, limit=MAX_INPUT) != raw:
                raise ValueError('compliance_opa_frozen_bytes_changed')

    def run(self, command):
        policy_label = str(self.display_root / 'policies/opa')
        if command == ['opa', 'check', policy_label]:
            actual = [self.tool[0], 'check', str(self.frozen / 'policies/opa')]
        elif (type(command) is list and len(command) == 9
                and command[:7] == ['opa', 'eval', '-f', 'json', '-d', policy_label, '-i']
                and command[7] == str(self.input_label) and command[8] in POLICY_QUERIES.values()):
            actual = [self.tool[0], 'eval', '-f', 'json', '-d', str(self.frozen / 'policies/opa'),
                      '-i', str(self.frozen / 'input.json'), command[8]]
        else:
            raise ValueError('unsupported_complete_compliance_opa_command')
        return self.observe(actual, command)

    def observe(self, actual, declared):
        from types import SimpleNamespace
        self.check()
        sequence = len(self.observations) + 1
        area = self.root / ('native-' + str(sequence)); area.mkdir(mode=0o700)
        row = {'sequence': sequence, 'declared_command': deepcopy(declared),
            'tool_path': self.tool[0], 'tool_sha256': self.tool[1],
            'input_present': 'input.json' in self.files,
            'input_sha256': None if 'input.json' not in self.files else hashlib.sha256(self.files['input.json']).hexdigest(),
            'policy_files': {n: hashlib.sha256(raw).hexdigest() for n, raw in self.files.items() if n != 'input.json'}}
        self.on_event({'kind': 'compliance-opa', 'phase': 'intent', 'observation': deepcopy(row)})
        self.observations.append(row)
        try:
            outcome = supervise(actual, self.frozen, {'PATH': '', 'LANG': 'C.UTF-8'}, area,
                                timeout=60, stream_limit=MAX_STREAM)
            self.check()
            row['native_outcome'] = outcome
            values = {}
            for name, descriptor in outcome['streams'].items():
                raw = safe_bytes(area / descriptor['path'], limit=MAX_STREAM)
                if len(raw) != descriptor['bytes'] or hashlib.sha256(raw).hexdigest() != descriptor['sha256']:
                    raise ValueError('compliance_opa_raw_stream_changed')
                values[name] = raw.decode().replace('\r\n', '\n').replace('\r', '\n')
            return SimpleNamespace(returncode=outcome['exit_code'], **values)
        except Exception as error:
            row['error_type'] = type(error).__name__
            raise
        finally:
            self.on_event({'kind': 'compliance-opa', 'phase': 'finished', 'observation': deepcopy(row)})
