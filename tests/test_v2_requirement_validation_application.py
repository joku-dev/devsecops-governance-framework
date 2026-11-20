"""Actual local source/history capture and complete no-native reconstruction."""
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import threading
import warnings
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts'),str(ROOT/'tests')]
from test_v2_requirement_validation import WholeRequirementValidation, OrdinaryData, History, ORIGINAL, PATHS
from lib.requirement_validation_application import check, inspect, run, PROFILE
from lib.requirement_validation_context import validate
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
from lib.providers.sbom_export_storage import read_record, encode
from lib.providers.requirement_validation_source import History as NativeHistory


class WholePrivateRequirementChecks(WholeRequirementValidation):
    # The original whole-decision matrix runs in its own test class only.
    __unittest_skip__ = False
    def setUp(self):
        super().setUp()
        self.instance = self.root.parent/'instance';self.instance.mkdir(mode=0o700)
        self.node = {'node_id':'e'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),
                     'runtime_source_digest':source_digest()}
        self.options = {'source_worktree':str(self.root),'base_ref':None}

    def test_complete_actual_source_retention_replay_without_source_or_native_and_whole_original(self):
        expected = self.compare()
        receipt,result = check(self.options,self.instance,self.node)
        self.assertEqual(receipt['state'],'complete');self.assertEqual(result,expected)
        request,source,retained,events,blob,closed = read_record(receipt['record_root'])
        self.assertEqual([row['kind'] for row in events],['opened','execution-intent','source-trace','terminal'])
        self.assertFalse(any(row.get('action')=='requirement_history' for row in events))
        self.assertEqual(retained['touched_files'],{})
        for p in self.root.rglob('*'):
            if p.is_file():p.unlink()
        with patch('subprocess.Popen',side_effect=AssertionError('No native program in retained reconstruction')), \
             patch('lib.providers.requirement_validation_source.Source',side_effect=AssertionError('No current data tree in replay')):
            self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        with self.assertRaisesRegex(ValueError,'foreign_node'):
            inspect(receipt['record_root'],node={**self.node,'node_id':'f'*32})

    def test_actual_original_failure_wires_and_captured_json_exception(self):
        for name,raw in [('model/requirements/governance-requirement-catalog.yaml',b'null'),
                         ('docs/governance/review-packets/OPA-DSCB-2026-001/review.json',b'not JSON')]:
            with self.subTest(name=name):
                p=self.root/name;saved=p.read_bytes();p.write_bytes(raw);expected=self.compare()
                receipt,result=check(self.options,self.instance,self.node)
                self.assertEqual(receipt['state'],'complete');self.assertEqual(result,expected)
                self.assertEqual(result['exit_code'],1)
                self.assertEqual(inspect(receipt['record_root'])['original_exit_code'],1);p.write_bytes(saved)

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.root),*args],stderr=subprocess.STDOUT)

    def initialize_history(self, algorithm='sha1'):
        self.git('init','-q','--template=','--object-format='+algorithm,'-b','main')
        self.git('config','user.name','Private test fixture');self.git('config','user.email','test@example.invalid')
        self.git('config','commit.gpgsign','false');self.git('add','.')
        self.git('-c','core.hooksPath=/dev/null','commit','-qm','Explicit fixture data only')
        return self.git('rev-parse','HEAD').decode().strip()

    def original_native(self, base):
        stdout,stderr=io.StringIO(),io.StringIO()
        with patch.object(ORIGINAL,'ROOT',self.root),patch.multiple(ORIGINAL,**{k:self.root/n for k,n in PATHS.items()}),patch.object(sys,'argv',['original']+([] if base is None else ['--base-ref',base])),redirect_stdout(stdout),redirect_stderr(stderr):
            try:code,error=ORIGINAL.main(),None
            except Exception as failure:code,error=1,{'type':type(failure).__name__,'message':str(failure)}
        return {'exit_code':code,'stdout':stdout.getvalue(),'stderr':stderr.getvalue(),'kernel_exception':error}

    def test_actual_git_previous_existence_three_dot_and_full_working_fallback(self):
        base=self.initialize_history()
        self.change('model/requirements/governance-requirement-catalog.yaml',lambda v:v['requirements'][0]['revisions'][0].update(title='history rewrite'))
        # New normative file is visible to original fallback only when no merge
        # base can be found. Existing three-dot excludes uncommitted changes.
        policy=self.root/'policies/opa/unregistered.rego';policy.write_text('package fixture\n')
        self.git('add','.');self.git('-c','core.hooksPath=/dev/null','commit','-qm','Changed data for original history test')
        receipt,result=check({**self.options,'base_ref':base},self.instance,self.node)
        self.assertEqual(receipt['state'],'complete');self.assertEqual(result['exit_code'],1)
        self.assertEqual(result,self.original_native(base))
        self.assertIn('immutable requirement revision changed',result['stderr'])
        self.assertIn('new or changed normative artifact requires an effective GRQ mapping',result['stderr'])
        self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        request,source,retained,events,blob,closed=read_record(receipt['record_root'])
        queries=[row['arguments'] for row in events if row.get('action')=='requirement_history']
        self.assertTrue(any(row['action']=='previous' for row in queries));self.assertTrue(any(row['action']=='changed' for row in queries))
        # A genuinely absent local base preserves the original None/empty
        # outcomes, while still retaining both failed diff attempts.
        absent,bad=check({**self.options,'base_ref':'missing-reference'},self.instance,self.node)
        self.assertEqual(absent['state'],'complete');self.assertEqual(bad,self.original_native('missing-reference'));self.assertTrue(inspect(absent['record_root'])['retained_declared_replay_consistent'])
        orphan=self.git('commit-tree','-m','Independent private data root',self.git('rev-parse',base+'^{tree}').decode().strip()).decode().strip()
        receipt,result=check({**self.options,'base_ref':orphan},self.instance,self.node)
        self.assertEqual(receipt['state'],'complete');self.assertEqual(result,self.original_native(orphan))
        _,_,_,events,blob,_=read_record(receipt['record_root'])
        intents={row['operation']:row for row in events if row.get('action')=='requirement_history'}
        outcomes=[json.loads(blob(row['value'])) for row in events if row.get('kind')=='returned' and intents[row['operation']]['arguments']['action']=='changed']
        self.assertEqual([r['completed_successfully'] for r in outcomes[0]],[False,True])
        self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_actual_sha256_history_and_release_existence_equal_whole_original(self):
        base=self.initialize_history('sha256');self.assertEqual(len(base),64)
        path=self.root/'releases/test/file.json';path.parent.mkdir(parents=True);path.write_text('{}')
        self.git('add','.');self.git('commit','-qm','Private published-artifact fixture')
        base=self.git('rev-parse','HEAD').decode().strip();path.write_text('{"changed":true}')
        self.git('add','.');self.git('commit','-qm','Alter immutable data fixture')
        receipt,result=check({**self.options,'base_ref':base},self.instance,self.node)
        self.assertEqual(receipt['state'],'complete');self.assertEqual(result,self.original_native(base))
        self.assertIn('published release artifact changed:',result['stderr'])
        self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_native_data_alias_special_private_paths_and_state_overlap_are_not_admitted(self):
        source=self.root/'model/requirements/governance-requirement-catalog.yaml';raw=source.read_bytes();source.unlink()
        target=self.root.parent/'catalog-target';target.write_bytes(raw);source.symlink_to(target)
        receipt,result=check(self.options,self.instance,self.node)
        self.assertEqual(receipt['state'],'incomplete');self.assertEqual(receipt['exit_code'],2)
        self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        with self.assertRaisesRegex(ValueError,'state_overlaps'):
            check({**self.options,'source_worktree':str(self.root.parent)},self.instance,self.node)
        self.assertFalse((self.root/'state').exists())

    def test_private_cli_check_legacy_inspect_and_portable_replay(self):
        stdout=io.StringIO()
        with redirect_stdout(stdout):
            code=run(['check','--profile',PROFILE,'--source-worktree',str(self.root)],self.instance,self.node)
        self.assertEqual(code,0);receipt=json.loads(stdout.getvalue())
        for command in ('inspect','replay'):
            stdout=io.StringIO()
            with redirect_stdout(stdout):
                code=run([command,'--record',receipt['record_root']],*([] if command=='replay' else [self.instance,self.node]))
            self.assertEqual(code,0);self.assertTrue(json.loads(stdout.getvalue())['retained_declared_replay_consistent'])
        expected=self.compare();stdout=io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(run(['check','--profile',PROFILE,'--source-worktree',str(self.root),'--format','legacy'],self.instance,self.node),0)
        self.assertEqual(stdout.getvalue(),expected['stdout'])

    def test_record_source_trace_result_authority_and_blob_tampering_are_rejected(self):
        for name in ('result.json','source.json','request.json','trace-blob'):
            with self.subTest(name=name):
                receipt,_=check(self.options,self.instance,self.node);root=Path(receipt['record_root'])
                if name=='trace-blob':
                    _,_,_,events,_,_=read_record(root);p=root/'blobs'/events[-2]['trace']['sha256'];p.write_bytes(p.read_bytes()+b' ')
                else:
                    p=root/name;value=json.loads(p.read_bytes())
                    if name=='result.json':value['official_acceptance']=True
                    elif name=='source.json':value['source_digest']='0'*64
                    else:value['base_ref']='forged'
                    p.write_text(json.dumps(value))
                with self.assertRaises((ValueError,KeyError,TypeError)):inspect(root)

    def reseal(self,root,events,*,replacement=None):
        if replacement is not None:
            old,raw=replacement;ref={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
            path=root/'blobs'/ref['sha256'];path.write_bytes(raw);path.chmod(0o600)
            for row in events:
                if row.get('kind')=='source-trace' and row['trace']==old:row['trace']=ref
                if row.get('kind')=='returned' and row['value']==old:row['value']=ref
            (root/'blobs'/old['sha256']).unlink()
        previous='0'*64
        for index,value in enumerate(events):
            raw=encode({'sequence':index,'previous':previous,'value':value})
            (root/'events'/f'{index:04}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
        result=json.loads((root/'result.json').read_bytes());result['event_tip']=previous;result['event_count']=len(events)
        (root/'result.json').write_bytes(encode(result))

    def test_coherently_rehashed_impossible_stat_and_unused_trace_cannot_be_original_exception(self):
        for attack in ('stat','extra','order'):
            with self.subTest(attack=attack):
                receipt,_=check(self.options,self.instance,self.node);root=Path(receipt['record_root'])
                _,_,_,events,blob,_=read_record(root);ref=events[-2]['trace'];trace=json.loads(blob(ref))
                if attack=='stat':
                    row=next(row for row in trace if row['action']=='stat' and row['value'] and row['value']['kind']=='directory')
                    row['value']['kind']='file'
                elif attack=='extra':trace.append(trace[-1])
                else:trace[0],trace[1]=trace[1],trace[0]
                self.reseal(root,events,replacement=(ref,encode(trace)))
                with self.assertRaises(ValueError):inspect(root)

    def test_coherently_rehashed_history_command_and_missing_fallback_are_rejected(self):
        base=self.initialize_history()
        for attack in ('arguments','fallback'):
            with self.subTest(attack=attack):
                receipt,_=check({**self.options,'base_ref':base if attack=='arguments' else 'missing'},self.instance,self.node)
                root=Path(receipt['record_root']);_,_,_,events,blob,_=read_record(root)
                intents={row['operation']:row for row in events if row.get('action')=='requirement_history'}
                row=next(row for row in events if row.get('kind')=='returned' and (attack=='arguments' or intents[row['operation']]['arguments']['action']=='changed'))
                ref=row['value'];outcome=json.loads(blob(ref))
                if attack=='arguments':outcome[0]['arguments'][0]='status'
                else:outcome.pop()
                self.reseal(root,events,replacement=(ref,encode(outcome)))
                with self.assertRaises(ValueError):inspect(root)

    def test_external_schema_retrieval_is_refused_without_network_or_local_URI_access(self):
        schema=self.root/'schemas/governance-requirement-catalog.schema.json'
        for uri in ('https://example.invalid/forbidden.json','file:///etc/passwd'):
            with self.subTest(uri=uri):
                schema.write_text(json.dumps({'$ref':uri}))
                with patch('urllib.request.urlopen',side_effect=AssertionError('No implicit resource acquisition')):
                    receipt,result=check(self.options,self.instance,self.node)
                    self.assertEqual(receipt['state'],'complete');self.assertEqual(result['exit_code'],1)
                    self.assertIsNotNone(result['kernel_exception'])
                    self.assertEqual(inspect(receipt['record_root'])['original_exit_code'],1)

    def test_explicit_external_schema_bytes_preserve_actual_V1_HTTP_evaluation_and_replay(self):
        owner=self
        bodies={'schema':{'type':'object','required':['catalog_id','requirements']},
                'child':{'type':'string'}}
        requests=[]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                raw=json.dumps(bodies[self.path[1:].removesuffix('.json')]).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        self.addCleanup(worker.join,2);self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        origin='http://127.0.0.1:'+str(server.server_port)
        schema=self.root/'schemas/governance-requirement-catalog.schema.json'
        schema.write_text(json.dumps({'$ref':origin+'/schema.json'}))
        local=self.root.parent/'selected-resource.json'
        for value in ({'type':'object','required':['catalog_id','requirements']},{'type':'string'}):
            with self.subTest(resource=value):
                bodies['schema']=value;local.write_text(json.dumps(value))
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore',DeprecationWarning)
                    expected=self.original_native(None)
                old_count=len(requests)
                with patch('urllib.request.urlopen',side_effect=AssertionError('No implicit resource request in V2')):
                    receipt,result=check({**self.options,'schema_resource':[(origin+'/schema.json',str(local))]},self.instance,self.node)
                    self.assertEqual(receipt['state'],'complete');self.assertEqual(result,expected)
                    local.unlink()
                    with patch('subprocess.Popen',side_effect=AssertionError('No program in resource replay')):
                        self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
                self.assertEqual(len(requests),old_count)
        self.assertGreaterEqual(len(requests),2)

    def test_unused_resources_are_not_read_and_nested_references_use_only_selected_bytes(self):
        root_schema=self.root/'schemas/governance-requirement-catalog.schema.json'
        base='https://example.invalid/schema/'
        outer=self.root.parent/'outer-resource.json';child=self.root.parent/'child-resource.json'
        outer.write_text(json.dumps({'$id':base+'outer.json','type':'object','properties':{'catalog_id':{'$ref':'child.json'}}}))
        child.write_text(json.dumps({'type':'string'}))
        unused=self.root.parent/'never-read-resource'
        root_schema.write_text(json.dumps({'$ref':base+'outer.json'}))
        resources=[(base+'outer.json',str(outer)),(base+'child.json',str(child)),(base+'unused.json',str(unused))]
        with patch('urllib.request.urlopen',side_effect=AssertionError('No implicit nested request')):
            receipt,result=check({**self.options,'schema_resource':resources},self.instance,self.node)
            self.assertEqual(receipt['state'],'complete');self.assertEqual(result['exit_code'],0)
            self.assertFalse(unused.exists());outer.unlink();child.unlink()
            self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        _,_,_,events,blob,_=read_record(receipt['record_root']);trace=json.loads(blob(events[-2]['trace']))
        self.assertEqual([r['path'] for r in trace if r.get('action')=='resource'],[base+'outer.json',base+'child.json'])
        with self.assertRaisesRegex(ValueError,'schema_resource_invalid'):
            check({**self.options,'schema_resource':[(base+'same',str(unused)),(base+'same',str(unused))]},self.instance,self.node)

# Avoid rerunning the inherited complete decision matrix in this native class.
for _name in tuple(WholeRequirementValidation.__dict__):
    if _name.startswith('test_') and _name not in WholePrivateRequirementChecks.__dict__:
        setattr(WholePrivateRequirementChecks,_name,None)

del WholeRequirementValidation

if __name__=='__main__':unittest.main()
