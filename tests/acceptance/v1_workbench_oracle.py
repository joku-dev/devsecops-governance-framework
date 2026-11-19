"""Whole unchanged trusted V1 Workbench/helper modules; explicit fixture paths/clock."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


def load(directory, root):
    directory = Path(directory); root = Path(root)
    contract = json.loads((directory/'contract.json').read_bytes())
    assert contract['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
    def module(name, filename):
        raw = (directory/filename).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == contract['files'][filename]['sha256']
        value = ModuleType(name); value.__file__ = str(directory/filename)
        with patch.dict('sys.modules', {name: value}):
            exec(compile(raw, value.__file__, 'exec'), value.__dict__)
        return value
    source = module('lib.source_document_text', 'source_document_text.py.txt')
    with patch.dict('sys.modules', {'lib.source_document_text': source}):
        delta = module('generate_source_document_requirement_delta', 'generate_source_document_requirement_delta.py.txt')
        process = module('generate_source_document_process_status', 'generate_source_document_process_status.py.txt')
        with patch.dict('sys.modules', {'generate_source_document_requirement_delta': delta,
                                      'generate_source_document_process_status': process}):
            workbench = module('frozen_workbench', 'serve_governance_workbench.py.txt')
    # Rebind only original absolute path constants to the same explicit fixture.
    # No function body/AST is edited; original main/native publisher do not run.
    for value in (delta, process, workbench):
        old = value.ROOT
        for name, path in list(vars(value).items()):
            if isinstance(path, Path) and path.is_relative_to(old):
                setattr(value, name, root/path.relative_to(old))
    return workbench, delta, process


class Clock:
    @classmethod
    def now(cls, tz):
        return datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc).astimezone(tz)
