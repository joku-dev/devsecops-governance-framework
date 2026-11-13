from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.dispatch_governance_agents import build_dispatch
from scripts.lib import agent_execution as execution
from scripts.lib.agent_review import changed_files, digest, prepare_plan
from tests.agent_harness import test_agent_receipts as fixtures


class AgentExecutionTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.AgentReceiptTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root
        source=Path(__file__).resolve().parents[2]
        shutil.copytree(source/'.codex',self.root/'.codex')
        self.fixture.fixture.git('add','.')
        self.fixture.fixture.git('-c','user.name=Test','-c','user.email=test@example.invalid',
                                 '-c','commit.gpgsign=false','commit','-m','provider adapters')
        paths=changed_files(self.root,self.fixture.base)
        self.plan=prepare_plan(self.root,build_dispatch(paths),'Synthetic read-only review',base_ref=self.fixture.base)
        self.validations=self.fixture.fixture.completed(self.plan)['validations']
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output=Path(self.temp.name)/'run'
        self.calls=[]

    def provider(self,command,prompt,directory,timeout):
        payload=json.loads(prompt)
        task=payload['task']
        self.calls.append(payload)
        schema=json.loads((directory/'response.schema.json').read_text())
        response={'role_id':task['role_id'],'status':'completed','summary':'Synthetic fixture review only',
                  'outputs':{key:'Synthetic fixture output' for key in task['required_output']},
                  'reviewed_paths':task['scope'],'reviewed_roles':schema['properties']['reviewed_roles']['const'],
                  'findings':[]}
        (directory/'response.json').write_text(json.dumps(response))
        events=[{'type':'thread.started','thread_id':'synthetic-thread'},
                {'type':'turn.completed','usage':{'input_tokens':10,'cached_input_tokens':2,'output_tokens':3}}]
        (directory/'events.jsonl').write_text('\n'.join(json.dumps(e) for e in events)+'\n')
        return 0,False

    def run_fake(self,**kwargs):
        with patch.dict(os.environ,{'CI':''}), patch.object(execution,'_execute_command',side_effect=self.provider):
            return execution.run_reviews(self.root,self.plan,self.output,execute=True,validations=self.validations,**kwargs)

    def test_preparation_never_invokes_provider_and_keeps_private_artifacts(self):
        with patch.object(execution,'_execute_command') as provider:
            manifest=execution.run_reviews(self.root,self.plan,self.output)
        provider.assert_not_called()
        self.assertFalse(manifest['provider_invoked'])
        self.assertEqual(manifest['mode'],'prepare_only')
        self.assertEqual(self.output.stat().st_mode & 0o777,0o700)
        result=json.loads((self.output/'results.json').read_text())
        self.assertTrue(all(r['status']=='pending' for r in result['reviews']))
        command=json.loads((self.output/self.plan['reviews'][0]['role_id']/'command.json').read_text())
        self.assertEqual(command[command.index('--sandbox')+1],'read-only')
        self.assertEqual(command[command.index('-a')+1],'never')
        self.assertIn('--ignore-user-config',command)
        self.assertIn('--ephemeral',command)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',command)
        self.assertEqual((self.output/'execution.json').stat().st_mode & 0o777,0o600)

    def test_specialists_precede_steward_and_exact_results_are_bound(self):
        manifest=self.run_fake(parallel_specialists=2)
        self.assertTrue(manifest['completion']['eligible_for_human_review'])
        self.assertEqual(self.calls[-1]['task']['role_id'],'repo-steward')
        specialists=self.calls[-1]['specialist_results']
        self.assertEqual(len(specialists),len(self.plan['reviews'])-1)
        final=manifest['roles'][-1]
        self.assertEqual(final['specialist_result_digests'],{r['role_id']:digest(r) for r in specialists})
        self.assertTrue(manifest['provider_invoked'])
        self.assertIsNone(final['observed_model'])
        self.assertEqual(final['requested_model'],'gpt-6-astra')
        self.assertEqual(final['usage']['output_tokens'],3)
        results=json.loads((self.output/'results.json').read_text())
        self.assertTrue(all(r['execution_kind']=='subagent' for r in results['reviews']))
        self.assertFalse(manifest['completion']['independent_human_approval'])

    def test_no_validation_outcome_is_invented(self):
        with patch.dict(os.environ,{'CI':''}), patch.object(execution,'_execute_command',side_effect=self.provider):
            manifest=execution.run_reviews(self.root,self.plan,self.output,execute=True)
        self.assertFalse(manifest['completion']['eligible_for_human_review'])
        results=json.loads((self.output/'results.json').read_text())
        self.assertTrue(all(v['status']=='not_run' for v in results['validations']))

    def test_failure_and_timeout_have_no_retry_or_final_synthesis(self):
        with patch.dict(os.environ,{'CI':''}), patch.object(execution,'_execute_command',return_value=(-15,True)) as provider:
            manifest=execution.run_reviews(self.root,self.plan,self.output,execute=True)
        self.assertEqual(provider.call_count,len(self.plan['reviews'])-1)
        self.assertFalse(manifest['completion']['eligible_for_human_review'])
        results=json.loads((self.output/'results.json').read_text())
        self.assertEqual(results['reviews'][-1]['status'],'skipped')
        self.assertTrue(all(t['timed_out'] for t in manifest['roles']))

    def test_invalid_provider_response_remains_failed(self):
        def invalid(command,prompt,directory,timeout):
            (directory/'response.json').write_text('{"role_id":"wrong-role"}')
            return 0,False
        with patch.dict(os.environ,{'CI':''}), patch.object(execution,'_execute_command',side_effect=invalid):
            manifest=execution.run_reviews(self.root,self.plan,self.output,execute=True)
        self.assertFalse(manifest['completion']['eligible_for_human_review'])
        self.assertEqual(len(manifest['roles']),len(self.plan['reviews'])-1)

    def test_explicit_live_execution_is_refused_in_ci(self):
        with patch.dict(os.environ,{'CI':'true'}), patch.object(execution,'_execute_command') as provider:
            with self.assertRaisesRegex(ValueError,'not allowed in CI'):
                execution.run_reviews(self.root,self.plan,self.output,execute=True)
        provider.assert_not_called()

    def test_existing_output_and_excessive_limits_are_rejected(self):
        for kwargs in ({'parallel_specialists':4},{'timeout_seconds':601}):
            with self.assertRaises(ValueError):
                execution.run_reviews(self.root,self.plan,self.output,**kwargs)
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError,'new private directory'):
            execution.run_reviews(self.root,self.plan,self.output)

    def test_source_mutation_aborts_without_reverting_changes(self):
        def mutating(command,prompt,directory,timeout):
            value=self.provider(command,prompt,directory,timeout)
            (self.root/'README.md').write_text('Concurrent edit must survive')
            return value
        with patch.dict(os.environ,{'CI':''}), patch.object(execution,'_execute_command',side_effect=mutating):
            with self.assertRaisesRegex(ValueError,'clean committed'):
                execution.run_reviews(self.root,self.plan,self.output,execute=True)
        self.assertEqual((self.root/'README.md').read_text(),'Concurrent edit must survive')
        self.assertTrue((self.output/'execution.json').exists())
        self.assertNotIn('completion',json.loads((self.output/'execution.json').read_text()))

    def test_local_timeout_terminates_the_process_group(self):
        self.output.mkdir()
        with patch.object(execution.subprocess,'Popen') as factory, patch.object(execution.os,'killpg') as kill:
            process=factory.return_value
            process.pid=12345
            process.returncode=-15
            process.communicate.side_effect=subprocess.TimeoutExpired('fixture',1)
            process.wait.return_value=-15
            code,timed_out=execution._execute_command(['fixture'],'private prompt',self.output,1)
        self.assertEqual(code,-15)
        self.assertTrue(timed_out)
        kill.assert_called_once_with(12345,signal.SIGTERM)
        self.assertTrue(factory.call_args.kwargs['start_new_session'])
