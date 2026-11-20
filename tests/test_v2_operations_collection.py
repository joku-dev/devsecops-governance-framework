"""Whole original collector with controlled API reads and actual local fixtures."""
from copy import deepcopy
from datetime import datetime,timezone
import json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs,urlsplit
import yaml

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.operations_collection import collect,AcquisitionFailure
from lib.operations_reporting import build_report,render_markdown
from lib.self_security import assess
from lib.providers import operations_report_profile as profile
from lib.v2_boundary import violations
from test_v2_operations_reporting import OLD


class ControlledReads:
    """Fixture ports, not a real provider adapter or an independent collector."""
    def __init__(self,root,failures=None,runs=None,prs=None):
        self.root=root;self.failures=failures or {};self.runs=[] if runs is None else runs;self.prs=[] if prs is None else prs;self.calls=[]
    def answer(self,kind,value,*,native=False):
        self.calls.append(kind)
        if kind in self.failures:
            error=self.failures[kind]
            if native and isinstance(error,subprocess.SubprocessError):raise AcquisitionFailure(type(error).__name__)
            raise error
        return deepcopy(value)
    def original_command(self,args):
        if args[1:3]==['pr','list']:
            assert args[:3]==['gh','pr','list'] and args[args.index('--limit')+1]=='1000'
            return self.answer(('pull_requests',),self.prs)
        assert args[:2]==['gh','api']
        path=args[2].split('/fixture/repository/',1)[1]
        if path=='git/ref/heads/main':return self.answer(('main_head',),{'object':{'sha':'a'*40}})
        parsed=urlsplit(path);query=parse_qs(parsed.query)
        assert query['branch']==['main'] and query['per_page']==['100']
        name=parsed.path.split('/')[2]
        return self.answer(('workflow',name,query.get('event',[None])[0]),{'workflow_runs':self.runs})
    def main_reference(self,repository):
        assert repository=='fixture/repository';return self.answer(('main_head',),{'object':{'sha':'a'*40}},native=True)
    def workflow_queries(self,config):return profile.workflow_queries(config)
    def workflow_runs(self,repository,name,event):
        assert repository=='fixture/repository';return self.answer(('workflow',name,event),{'workflow_runs':self.runs},native=True)
    def pull_requests(self,repository):
        assert repository=='fixture/repository';return self.answer(('pull_requests',),self.prs,native=True)
    def registry(self):return yaml.safe_load((self.root/'status/application-repository-integrations.yaml').read_text())
    def index_domains(self):return profile.INDEXES
    def index(self,domain):return json.loads((self.root/'status'/profile.INDEXES[domain]).read_text())
    def records(self,directory):
        return [dict(json.loads(p.read_text()),_source_file=str(p.relative_to(self.root)))
                for p in sorted((self.root/'status'/directory).rglob('*.json'))]
    def security_observation(self,repository,at):
        assert repository=='fixture/repository'
        return {'observed_at':at,'repository':{'visibility':'public','default_branch':'main'},'api_errors':['HTTP 404']}
    def security(self,repository,at):
        model=yaml.safe_load((self.root/'model/controls/governance-repository-security.yaml').read_text())
        return assess(model,self.security_observation(repository,at))


class CompleteOperationsCollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'status').mkdir();(self.root/'model/controls').mkdir(parents=True)
        (self.root/'model/controls/governance-repository-security.yaml').write_bytes((ROOT/'model/controls/governance-repository-security.yaml').read_bytes())
        (self.root/'status/application-repository-integrations.yaml').write_text('integrations: []\n')
        for name in profile.INDEXES.values():(self.root/'status'/name).write_text('{"repositories":[]}')
        self.config=json.loads((ROOT/'.github/operations-report.json').read_bytes());self.config['repository']='fixture/repository'
        self.now=datetime(2026,11,15,12,tzinfo=timezone.utc)
    def compare(self,**scenario):
        old=ControlledReads(self.root,**scenario);new=ControlledReads(self.root,**scenario)
        with patch.object(OLD,'command_json',side_effect=old.original_command),patch.object(OLD,'collect_live',side_effect=old.security_observation):
            expected=OLD.collect(self.config,self.root,self.now)
        actual=collect(self.config,self.now,new)
        self.assertEqual(actual,expected);self.assertEqual(json.dumps(actual,indent=2),json.dumps(expected,indent=2))
        self.assertEqual(new.calls,old.calls)
        self.assertEqual(len(actual['security']['criteria']) if actual['security'] else 0,16 if actual['security'] else 0)
        return actual
    def test_whole_live_assembly_indexes_health_and_sixteen_security_criteria(self):
        value=self.compare();self.assertEqual(value['errors'],[]);self.assertIsNotNone(value['intake_health'])
        self.assertEqual(value['intake_health']['summary']['events']['total'],0)
    def test_transport_errors_and_bad_response_keys_preserve_each_source_and_continue(self):
        keys=[('main_head',),('pull_requests',),*[('workflow',name,event) for name,event in profile.workflow_queries(self.config).items()]]
        for key in keys:
            for error in (subprocess.CalledProcessError(1,['controlled-read']),subprocess.TimeoutExpired(['controlled-read'],60),KeyError('missing'),ValueError('invalid'),OSError('unavailable')):
                with self.subTest(key=key,error=type(error).__name__):
                    value=self.compare(failures={key:error});self.assertTrue(value['errors'])
    def test_exact_workflow_and_PR_cap_boundaries_are_observation_errors(self):
        value=self.compare(runs=[{}]*100,prs=[{}]*1000)
        self.assertEqual(len([e for e in value['errors'] if e['error']=='ResultLimitReached']),len(profile.workflow_queries(self.config))+1)
        self.assertFalse(self.compare(runs=[{}]*99,prs=[{}]*999)['errors'])
    def test_nonempty_source_records_preserve_full_health_lifecycle_metrics_and_report(self):
        def write(directory,name,value):
            path=self.root/'status'/directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
        for i,status in enumerate(('success','partial','failed')):
            write('intake-events',f'nested/{i}.json',{'status':status,'completed_at':'2026-11-15T11:00:00Z',
                'duration_ms':1000*(i+1),'repository_id':'owner/consumer','intake_type':'devsecops_governance',
                'evidence_type':'governance_result','collector':{'id':'fixture-collector','version':'1'}})
        for run,retryable in (('42',True),('43',False),('44',True)):
            write('collection-attempts',run+'.json',{'repository_id':'owner/consumer','source':{'run_id':run,'artifact_name':'evidence'},'errors':[{'retryable':retryable}]})
        write('results','resolved.json',{'repository_id':'owner/consumer','generated_at':'2026-11-15T11:00:00Z',
            'trust':{'capture':{'source':{'run_id':'44','artifact_name':'evidence'}}}})
        write('architecture-results','kept.json',{'repository_id':'owner/other','generated_at':'2026-11-15T11:00:00Z'})
        write('typed-evidence-results','kept.json',{'repository_id':'owner/third','generated_at':'2026-11-15T11:00:00Z'})
        for i in range(2):write('intake-conflicts',str(i)+'.json',{})
        (self.root/'status/application-repository-integrations.yaml').write_text('integrations:\n  - repository: owner/consumer\n')
        (self.root/'status/repository-results-index.json').write_text(json.dumps({'repositories':[{'repository_id':'owner/consumer','latest_result':{
            'pipeline_run_id':'42','generated_at':'2026-11-15T11:00:00Z','source_file':'status/results/resolved.json','status':'pass','pipeline_event':'push','branch':'main'}}]}))
        value=self.compare();health=value['intake_health']
        self.assertEqual(health['summary']['events']['total'],3)
        self.assertEqual(health['summary']['collection_attempts'],{'total':3,'open':1,'resolved':1,'permanent':1})
        self.assertEqual(health['summary']['intake_conflicts'],2)
        self.assertEqual(health['summary']['events']['duration_ms']['p95'],3000)
        self.assertEqual(health['latest_results'][0]['age_ms'],3600000)
        expected=OLD.build_report(value,self.config,self.now,'b'*40)
        actual=build_report(value,self.config,self.now,'b'*40,profile=profile)
        self.assertEqual(json.dumps(actual,indent=2),json.dumps(expected,indent=2))
        self.assertEqual(render_markdown(actual),OLD.render_markdown(expected))
    def test_missing_registry_and_each_index_keep_partial_health_and_errors(self):
        for name in ('application-repository-integrations.yaml',*profile.INDEXES.values()):
            path=self.root/'status'/name;raw=path.read_bytes();path.unlink()
            try:
                with self.subTest(name=name):
                    value=self.compare();self.assertTrue(value['errors'])
                    if name in profile.INDEXES.values():self.assertIsNone(value['intake_health'])
            finally:path.write_bytes(raw)
    def test_invalid_health_record_or_security_model_stays_a_visible_partial_observation(self):
        directory=self.root/'status/intake-events';directory.mkdir();path=directory/'bad.json';path.write_text('bad JSON')
        value=self.compare();self.assertIsNone(value['intake_health']);self.assertIn({'source':'intake_health','error':'JSONDecodeError'},value['errors'])
        path.unlink();model=self.root/'model/controls/governance-repository-security.yaml';model.unlink()
        value=self.compare();self.assertIsNone(value['security']);self.assertIn({'source':'security','error':'FileNotFoundError'},value['errors'])
    def test_collector_has_no_provider_or_environment_access(self):
        self.assertEqual(violations('scripts/lib/operations_collection.py',(ROOT/'scripts/lib/operations_collection.py').read_text()),[])
        with self.assertRaisesRegex(ValueError,'operations_unknown_transport_family'):AcquisitionFailure('ArbitraryNativeError')


if __name__=='__main__':unittest.main()
