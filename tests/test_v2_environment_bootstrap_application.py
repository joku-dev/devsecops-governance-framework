"""A final source invalidation cannot become a second terminal mismatch or success."""
from pathlib import Path
import json,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.environment_bootstrap import BootstrapFailure
from lib import environment_bootstrap_application as application
from lib.providers.environment_bootstrap_storage import BootstrapJournal,inspect

class FinalCheckpointOutcome(unittest.TestCase):
    def test_after_returned_phases_source_invalidation_has_durable_incomplete_reason(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary).resolve();directory.chmod(0o700)
            class Session:
                def __init__(self,profile,options):
                    self.journal=BootstrapJournal(directory,{'profile':profile},{'kind':'explicit_controlled_port_fixture'})
                def perform(self,action):return action=='environment_python_executable' if action=='environment_python_executable' else None
                def checkpoint(self):raise BootstrapFailure('bootstrap_source_changed_during_operation')
                def finish(self,value,*,code=None):
                    return {**self.journal.finish({**value,'code':code}),'diagnostics':[] if code is None else [code]}
                def __enter__(self):return self
                def __exit__(self,*ignored):self.journal.close()
            with patch.object(application,'open_environment_bootstrap',Session):
                value=application.execute('source-intake-environment-v1',{})
            self.assertEqual(value['exit_code'],2)
            self.assertEqual(value['state'],'incomplete')
            self.assertEqual(value['diagnostics'],['bootstrap_source_changed_during_operation'])
            root=Path(value['record_root']);result=json.loads((root/'result.json').read_bytes())
            self.assertEqual(result['state'],'incomplete')
            self.assertEqual(result['code'],'bootstrap_source_changed_during_operation')
            events=[json.loads(line)['payload'] for line in (root/'events.jsonl').read_bytes().splitlines()]
            self.assertEqual(events[-1]['kind'],'finished')
            self.assertFalse(any(e.get('state')=='failed' for e in events))
            self.assertFalse(any(e['kind'].startswith('native-') for e in events))
            self.assertEqual(inspect(root)['declared_result'],'incomplete')
            self.assertFalse(value['official_acceptance'])

if __name__=='__main__':unittest.main()
