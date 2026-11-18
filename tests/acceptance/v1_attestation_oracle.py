"""Fingerprint-bound original attestation functions/CLI, never inspected target code."""
import argparse
import ast
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import types
from unittest.mock import patch


class Original:
    def __init__(self,fixtures,root):
        self.fixtures=Path(fixtures);contract=json.loads((self.fixtures/'contract.json').read_text())
        assert contract['v1_reference']=='6b557fefe295b58272d2271326576ca3a3687197'
        sources={}
        for name,row in contract['sources'].items():
            raw=(self.fixtures/row['file']).read_bytes()
            assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw,usedforsecurity=False).hexdigest()==row['git_blob']
            sources[name]=raw
        self.module=types.ModuleType('original_attestation_helper')
        exec(compile(sources['scripts/lib/evidence_attestation.py'],'unchanged_original_attestation_helper','exec'),self.module.__dict__)
        tree=ast.parse(sources['scripts/verify_evidence_attestation.py']);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main'];assert len(nodes)==1
        scope={'Path':Path,'argparse':argparse,'datetime':datetime,'timezone':__import__('datetime').timezone,'json':json,
            'ROOT':Path(root),'assess_attestation':self.module.assess_attestation,'load_trust_roots':self.module.load_trust_roots}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'unchanged_original_attestation_cli','exec'),scope);self.main=scope['main'];self.scope=scope

    def cli(self,arguments,*,at=None):
        class Clock:
            @staticmethod
            def now(zone):return datetime.fromisoformat(at.replace('Z','+00:00'))
        with patch.object(sys,'argv',['verify_evidence_attestation.py',*map(str,arguments)]):
            if at is not None:
                with patch.dict(self.scope,{'datetime':Clock}):return self.main()
            return self.main()
