"""Exact frozen original receipt APIs/main on real files and Git, with explicit test clock."""
import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from jsonschema import Draft202012Validator, FormatChecker, ValidationError


def load(native, metadata, directory):
    metadata=Path(metadata);directory=Path(directory);contract=json.loads((directory/'contract.json').read_text())
    assert contract['v1_reference']=='6b557fefe295b58272d2271326576ca3a3687197'
    for name,sha in contract['metadata_source_sha256'].items():assert hashlib.sha256((metadata/name).read_bytes()).hexdigest()==sha
    record=directory/'record_agent_review.py.txt';assert hashlib.sha256(record.read_bytes()).hexdigest()==contract['record_main_sha256']
    scope={'ROOT':native.repository,'SCHEMA':json.loads((metadata/'receipt-schema.json').read_text()),
        'Path':Path,'os':os,'json':json,'datetime':datetime,'timezone':timezone,'Counter':Counter,
        'Draft202012Validator':Draft202012Validator,'FormatChecker':FormatChecker,'ValidationError':ValidationError,
        'check_results':native.review.check_results,'digest':native.review.digest,'git_output':native.review.git_output,
        'normalize_path':native.review.normalize_path,'argparse':argparse,'sys':sys}
    names={'private_destination','validate_receipt','build_receipt','write_receipt','append_review_usage','load_review_usage','summarize_review_usage'}
    tree=ast.parse((metadata/'agent_receipts.py.txt').read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names];assert len(nodes)==len(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(metadata/'agent_receipts.py.txt'),'exec'),scope)
    main=next(n for n in ast.parse(record.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='main')
    exec(compile(ast.Module(body=[main],type_ignores=[]),str(record),'exec'),scope)
    original_main=scope['main']
    def run(arguments,*,recorded_at):
        class Clock:
            @classmethod
            def now(cls,tz):return datetime.fromisoformat(recorded_at.replace('Z','+00:00')).astimezone(tz)
        scope['datetime']=Clock
        try:return original_main(list(map(str,arguments)))
        finally:scope['datetime']=datetime
    return SimpleNamespace(**{name:scope[name] for name in names},main=run)
