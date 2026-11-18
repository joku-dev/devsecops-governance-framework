"""Fingerprint-bound unchanged V1 record builders, writers and native CLI bodies."""
import argparse
import ast
from contextlib import redirect_stderr,redirect_stdout
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import types
from urllib.parse import quote
from unittest.mock import patch

from jsonschema import Draft202012Validator


class Original:
    def __init__(self,fixtures,root):
        self.root=Path(root);self.sources={};contract=json.loads((Path(fixtures)/'contract.json').read_text())
        assert contract['v1_reference']=='6b557fefe295b58272d2271326576ca3a3687197'
        for name,row in contract['sources'].items():
            raw=(Path(fixtures)/row['file']).read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw,usedforsecurity=False).hexdigest()==row['git_blob']
            self.sources[name]=raw
        self.ledger=types.ModuleType('original_intake_ledger');exec(compile(self.sources['scripts/lib/result_ledger.py'],'unchanged_original_result_ledger','exec'),self.ledger.__dict__)
        self.identifiers=types.ModuleType('original_intake_identifiers');exec(compile(self.sources['scripts/lib/identifiers.py'],'unchanged_original_identifiers','exec'),self.identifiers.__dict__)
        self.http=types.ModuleType('original_intake_https');exec(compile(self.sources['scripts/lib/secure_http.py'],'unchanged_original_https','exec'),self.http.__dict__)
        self.modules={}
        for kind,file in [('attempt','record_collection_attempt.py'),('event','record_intake_event.py'),('retry','prepare_collection_attempt_retry.py')]:
            scope={'Path':Path,'argparse':argparse,'datetime':datetime,'timezone':timezone,'hashlib':hashlib,
                'json':json,'os':os,'sys':sys,'re':re,'Draft202012Validator':Draft202012Validator,
                'ROOT':self.root,'ATTEMPT_ROOT':self.root/'status/collection-attempts','EVENT_ROOT':self.root/'status/intake-events',
                'CONFLICT_ROOT':self.root/('status/intake-conflicts/collection-attempts' if kind=='attempt' else 'status/intake-conflicts/intake-events'),
                'SCHEMA_PATH':self.root/'schemas/evidence-collection-attempt.schema.json',
                'write_collection_attempt_append_only':self.ledger.write_collection_attempt_append_only,
                'write_intake_event_append_only':self.ledger.write_intake_event_append_only,
                'sanitize_timestamp':self.identifiers.sanitize_timestamp,'slugify_repository':self.identifiers.slugify_repository}
            if kind=='attempt':
                tree=ast.parse(self.sources['scripts/intake_github_actions_run.py'])
                nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in ('api_repo_path','github_get_json')) or (isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='DEFAULT_API_URL' for x in n.targets))]
                assert len(nodes)==3;scope.update(quote=quote,get_json_https=self.http.get_json_https)
                exec(compile(ast.Module(body=nodes,type_ignores=[]),'unchanged_original_native_metadata','exec'),scope)
            tree=ast.parse(self.sources['scripts/'+file]);nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.Assign))]
            nodes=[n for n in nodes if not isinstance(n,ast.Assign) or not any(isinstance(t,ast.Name) and t.id in ('ROOT','ATTEMPT_ROOT','EVENT_ROOT','CONFLICT_ROOT','SCHEMA_PATH') for t in n.targets)]
            exec(compile(ast.Module(body=nodes,type_ignores=[]),'unchanged_original_'+file,'exec'),scope);self.modules[kind]=scope

    def run(self,kind,args,*,at,run=None,error=None,environment=None,native_transport=False):
        instant=datetime.fromisoformat(at.replace('Z','+00:00'))
        class Clock(datetime):
            @classmethod
            def now(cls,zone=None):return instant.astimezone(zone) if zone is not None else instant.replace(tzinfo=None)
        scope=self.modules[kind];out=io.StringIO();err=io.StringIO()
        def get(url,token):
            if error is not None:raise error
            return deepcopy(run)
        changes={'datetime':Clock}
        if kind=='attempt' and not native_transport:changes['github_get_json']=get
        with patch.dict(scope,changes),patch.object(sys,'argv',['original-'+kind,*map(str,args)]),patch.dict(os.environ,environment or {},clear=True),redirect_stdout(out),redirect_stderr(err):
            code=scope['main']()
        return code,out.getvalue().encode(),err.getvalue().encode()

    def schema_files(self):
        for name,raw in self.sources.items():
            if name.startswith('schemas/'):
                path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)


def snapshot(root):
    base=Path(root)/'status'
    return {p.relative_to(root).as_posix():p.read_bytes() for p in sorted(base.rglob('*')) if p.is_file()} if base.exists() else {}
