"""Original first/repeat branch decisions and explicit stopped/incomplete evidence."""
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.workbench_startup import run,replay
from lib.environment_bootstrap import BootstrapFailure

class Observer:
    def __init__(self):self.events=[]
    def before(self,action):self.events.append(('intent',action));return action
    def after(self,token,value):self.events.append(('returned',token,value))
    def failed(self,token,code):self.events.append(('failed',token,code))

class StartupBranches(unittest.TestCase):
    def run_case(self,existing,*,fail=None,exit_code=0):
        observer=Observer()
        class Ports:
            rows=[]
            def perform(inner,action):
                self.assertEqual(observer.events[-1],('intent',action))
                if action==fail:
                    inner.rows.append({'action':action,'failure':'explicit_test_failure'})
                    raise BootstrapFailure('explicit_test_failure')
                value=existing if action=='environment_python_executable' else exit_code if action=='handoff_workbench' else None
                inner.rows.append({'action':action,'value':value});return value
        ports=Ports()
        if fail:
            with self.assertRaises(BootstrapFailure):run(ports,observer)
        else:self.assertEqual(run(ports,observer),exit_code)
        return observer,ports.rows
    def test_fresh_setup_precedes_environment_admission_and_handoff(self):
        _,rows=self.run_case(False)
        self.assertEqual([r['action'] for r in rows],['preflight','environment_python_executable','bootstrap_environment','admit_environment','admit_instance','handoff_workbench'])
        self.assertEqual(replay(rows),0)
    def test_existing_interpreter_never_updates_dependencies_on_startup(self):
        _,rows=self.run_case(True)
        self.assertNotIn('bootstrap_environment',[r['action'] for r in rows]);self.assertEqual(replay(rows),0)
    def test_every_known_phase_failure_stops_before_further_effects(self):
        for action in ('preflight','environment_python_executable','bootstrap_environment','admit_environment','admit_instance','handoff_workbench'):
            with self.subTest(action=action):
                observer,rows=self.run_case(False,fail=action)
                self.assertEqual(rows[-1]['action'],action);self.assertEqual(observer.events[-1],('failed',action,'explicit_test_failure'))
                with self.assertRaises(BootstrapFailure):replay(rows)
    def test_actual_native_nonzero_handoff_status_is_not_converted_to_success(self):
        _,rows=self.run_case(True,exit_code=23);self.assertEqual(replay(rows),23)
    def test_real_process_replacement_leaves_handoff_intent_without_ready_or_exit(self):
        observer=Observer()
        class Replaced(BaseException):pass
        class Ports:
            def perform(self,action):
                if action=='handoff_workbench':raise Replaced()
                return True if action=='environment_python_executable' else None
        with self.assertRaises(Replaced):run(Ports(),observer)
        self.assertEqual(observer.events[-1],('intent','handoff_workbench'))
        self.assertFalse(any(e[0] in ('ready','complete') for e in observer.events))
    def test_unknown_exception_is_not_invented_as_a_known_failure_or_retried(self):
        observer=Observer()
        class Ports:
            def perform(self,action):raise OSError('explicit storage failure')
        with self.assertRaises(OSError):run(Ports(),observer)
        self.assertEqual(observer.events,[('intent','preflight')])
    def test_wrong_port_boolean_type_is_rejected(self):
        observer=Observer()
        class Ports:
            def perform(self,action):return 1 if action=='environment_python_executable' else None
        with self.assertRaisesRegex(BootstrapFailure,'invalid_port_result'):run(Ports(),observer)
    def test_reordered_missing_or_unused_recorded_actions_are_rejected(self):
        _,rows=self.run_case(False)
        for changed in (rows[::-1],rows[:-1],rows+[{'action':'preflight','value':None}]):
            with self.subTest(changed=changed),self.assertRaises(ValueError):replay(changed)

if __name__=='__main__':unittest.main()
