"""Execute fingerprinted original V1 metadata functions, never inspected consumer code."""
import ast
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import re
from jsonschema import Draft202012Validator, FormatChecker, ValidationError


def load(directory):
    root=Path(directory);contract=json.loads((root/'contract.json').read_text())
    assert contract['v1_reference']=='6b557fefe295b58272d2271326576ca3a3687197'
    for name,sha in contract['source_sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha
    scope={'hashlib':hashlib,'html':html,'json':json,'re':re,'Counter':Counter,'Path':Path,
           'Draft202012Validator':Draft202012Validator,'FormatChecker':FormatChecker,'ValidationError':ValidationError,
           'SCHEMA':json.loads((root/'receipt-schema.json').read_text()),
           'START':'<!-- agent-review-receipt:start -->','END':'<!-- agent-review-receipt:end -->'}
    selected={'agent_review':['digest'],'agent_routing':['normalize_path'],
              'agent_receipts':['validate_receipt','summarize_review_usage'],
              'agent_review_status':['receipt_block','parse_receipt','render_status','inspect_pr']}
    for source,names in selected.items():
        path=root/(source+'.py.txt');tree=ast.parse(path.read_bytes())
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        assert len(nodes)==len(names)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),scope)
    def status(event,subject):
        scope['committed_scope']=lambda root,base,head:(subject['merge_base_commit'],subject['changed_paths'])
        scope['expected_reviews']=lambda root,head,paths:subject['proposed'] if head==subject['head_commit'] else subject['target']
        return scope['inspect_pr'](None,event)
    scope['status_with_declared_inputs']=status
    return contract,scope


def seal(value,old):
    value['receipt_id']=old['digest']({k:value[k] for k in ('plan_digest','results_digest')})
    value.pop('receipt_digest',None);value['receipt_digest']=old['digest'](value)
    old['validate_receipt'](value);return value


def receipt(old,*,identity='first',eligible=True,kind='role_lens'):
    value={'schema_version':'1.0.0','plan_digest':hashlib.sha256(('plan/'+identity).encode()).hexdigest(),
           'results_digest':hashlib.sha256(('results/'+identity).encode()).hexdigest(),
           'head_commit':'a'*40,'base_commit':'c'*40,'changed_paths':['docs/example.md','model/controls/example.yaml'],
           'roles':[{'role_id':name,'status':'completed' if eligible else 'pending','execution_kind':kind,'execution_declared':eligible} for name in ['evidence-and-intake','repo-steward']],
           'validations':[{'command':command,'status':'passed' if eligible else 'not_run'} for command in ['git diff --check','python3 -m unittest discover -s tests']],
           'finding_counts':{state:{severity:0 for severity in ['low','medium','high','critical']} for state in ['open','resolved']},
           'eligible_for_human_review':eligible,'evidence_kind':'self_reported_review_evidence','independent_human_approval':False,
           'recorded_at':'2026-11-17T12:00:00.123456+00:00'}
    return seal(value,old)


def subject():
    selection={'roles':['evidence-and-intake','repo-steward'],'validations':['git diff --check','python3 -m unittest discover -s tests']}
    return {'head_commit':'a'*40,'target_commit':'b'*40,'merge_base_commit':'c'*40,
            'changed_paths':['docs/example.md','model/controls/example.yaml'],
            'target':json.loads(json.dumps(selection)),'proposed':json.loads(json.dumps(selection))}


def event(description,scope):
    return {'pull_request':{'base':{'sha':scope['target_commit']},'head':{'sha':scope['head_commit']},'body':description}}
