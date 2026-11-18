"""Unchanged fingerprint-bound V1 runner; controlled synthetic executable only."""
import ast
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import types
from unittest.mock import patch
from jsonschema import ValidationError

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('execution_original_planning',HERE/'v1_review_planning_oracle.py')
planning=importlib.util.module_from_spec(spec);spec.loader.exec_module(planning)


class OriginalExecution(planning.OriginalReview):
    def __init__(self,root,fixtures):
        fixtures=Path(fixtures)
        super().__init__(fixtures/'v2-review-planning',fixtures/'v2-review-metadata',root)
        self.directory=fixtures/'v2-review-execution'
        contract=json.loads((self.directory/'contract.json').read_text())
        assert contract['v1_reference']=='6b557fefe295b58272d2271326576ca3a3687197'
        for row in contract['sources'].values():
            raw=(self.directory/row['file']).read_bytes()
            assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw,usedforsecurity=False).hexdigest()==row['v1_git_blob']
        def module(name):
            value=types.ModuleType(self.package+'.'+name);value.__package__=self.package
            sys.modules[value.__name__]=value;self.modules.append(value.__name__);return value
        receipts=module('agent_receipts');receipts.__dict__.update(Path=Path,os=os,json=json)
        tree=ast.parse((self.directory/'agent_receipts.py.txt').read_bytes())
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('write_private_artifact','private_destination')]
        assert len(nodes)==2;exec(compile(ast.Module(body=nodes,type_ignores=[]),'original_receipt_functions','exec'),receipts.__dict__)
        adapter=module('agent_codex');exec(compile((self.directory/'agent_codex.py.txt').read_bytes(),'original_adapter','exec'),adapter.__dict__)
        self.execution=module('agent_execution');exec(compile((self.directory/'agent_execution.py.txt').read_bytes(),'original_runner','exec'),self.execution.__dict__)
        self.cli={'Path':Path,'ROOT':Path(root),'json':json,'sys':sys,'argparse':__import__('argparse'),
            'ValidationError':ValidationError,'run_reviews':self.execution.run_reviews}
        tree=ast.parse((self.directory/'run_agent_reviews.py.txt').read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main']
        assert len(nodes)==1;exec(compile(ast.Module(body=nodes,type_ignores=[]),'original_cli','exec'),self.cli)

    def native_clock(self,manifest):
        """Bind native nondeterministic values to candidate observations, not normalize wires."""
        from contextlib import ExitStack
        rows=manifest['roles'];ids=iter([manifest['run_id']]+[r['run_id'] for r in rows])
        dates=iter([r[k] for r in rows for k in ('started_at','completed_at')])
        durations=iter([v for r in rows for v in (0,r['elapsed_seconds'])])
        class Clock:
            @staticmethod
            def now(zone):return datetime.fromisoformat(next(dates))
        stack=ExitStack()
        stack.enter_context(patch.object(self.execution,'uuid',types.SimpleNamespace(uuid4=lambda:types.SimpleNamespace(hex=next(ids)))))
        stack.enter_context(patch.object(self.execution,'datetime',Clock))
        stack.enter_context(patch.object(self.execution,'time',types.SimpleNamespace(monotonic=lambda:next(durations))))
        return stack


def snapshot(root):
    return {path.relative_to(root).as_posix():path.read_bytes() for path in sorted(Path(root).rglob('*')) if path.is_file()}
