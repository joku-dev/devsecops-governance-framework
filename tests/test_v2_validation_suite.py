"""Whole fail-fast validation chain, parser quirks and strict outcome replay."""
from pathlib import Path
import io,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.validation_suite import (Observation,run,replay,mode,TOOL_PHASES,VALIDATOR_PHASES,USAGE)

class Sink:
    def __init__(self):self.streams={'stdout':io.BytesIO(),'stderr':io.BytesIO()}
    def write(self,name,raw):self.streams[name].write(raw)

class Journal:
    def __init__(self):self.pending=None;self.rows=[]
    def before(self,action):
        if self.pending is not None:raise ValueError('pending phase')
        self.pending=action;return action
    def after(self,token,wire):
        assert token==self.pending;self.rows.append({'action':token,'observation':wire});self.pending=None

class CompleteSuite(unittest.TestCase):
    def execute(self,arguments=(),*,failed=None,code=23,version=b'1.18.2\n',exception=None):
        journal=Journal();sink=Sink()
        class Ports:
            def perform(self,action):
                assert journal.pending==action
                if exception:raise exception
                if action==failed:return Observation(code,b'actual failing output\n',b'actual failing diagnostic\n')
                return Observation(0,version if action=='opa_version' else b'consistency\n' if action=='dependency_consistency' else b'')
        result=run(list(arguments),Ports(),journal,sink,environment_label='/operator/env',expected_opa_version='1.18.2')
        repeated=Sink();self.assertEqual(replay(list(arguments),journal.rows,repeated,environment_label='/operator/env',expected_opa_version='1.18.2'),result)
        self.assertEqual({k:v.getvalue() for k,v in sink.streams.items()},{k:v.getvalue() for k,v in repeated.streams.items()})
        return result,journal,sink
    def test_default_runs_every_original_validator_and_full_unit_discovery(self):
        code,journal,sink=self.execute();self.assertEqual(code,0)
        self.assertEqual([r['action'] for r in journal.rows],[*TOOL_PHASES,*VALIDATOR_PHASES])
        self.assertEqual(sink.streams['stdout'].getvalue(),b'consistency\nValidation toolchain ready (OPA 1.18.2).\n')
    def test_check_tools_never_runs_policy_validators_or_tests(self):
        code,journal,_=self.execute(['--check-tools']);self.assertEqual(code,0)
        self.assertEqual([r['action'] for r in journal.rows],list(TOOL_PHASES))
    def test_each_native_nonzero_short_circuits_every_later_phase(self):
        chain=[*TOOL_PHASES,*VALIDATOR_PHASES]
        for action in chain:
            with self.subTest(action=action):
                code,journal,sink=self.execute(failed=action)
                self.assertEqual(code,23);self.assertEqual([r['action'] for r in journal.rows],chain[:chain.index(action)+1])
                self.assertEqual(sink.streams['stderr'].getvalue(),b'actual failing diagnostic\n')
                if action=='opa_version':self.assertNotIn(b'actual failing output',sink.streams['stdout'].getvalue())
    def test_empty_argument_has_original_default_meaning(self):self.assertEqual(self.execute([''])[0],0)
    def test_help_precedes_extra_argument_check_and_never_opens_a_phase(self):
        for args in (['--help'],['-h'],['--help','ignored'],['-h','--unknown']):
            with self.subTest(args=args):
                code,journal,sink=self.execute(args);self.assertEqual(code,0);self.assertEqual(journal.rows,[]);self.assertEqual(sink.streams['stdout'].getvalue(),USAGE.encode())
    def test_unknown_or_extra_nonhelp_arguments_are_usage_two_before_tool_access(self):
        for args in (['--unknown'],['--check-tools','extra'],['','extra']):
            with self.subTest(args=args):
                code,journal,sink=self.execute(args);self.assertEqual(code,2);self.assertEqual(journal.rows,[]);self.assertEqual(sink.streams['stderr'].getvalue(),USAGE.encode())
    def test_version_comparison_preserves_cr_and_interior_lf(self):
        for raw in (b'',b'1.18.1\n',b'1.18.2\r\n',b'1.18.2\n1.18.2\n'):
            with self.subTest(raw=raw):
                code,journal,sink=self.execute(version=raw);self.assertEqual(code,1)
                self.assertEqual([r['action'] for r in journal.rows],['require_tools','opa_version'])
                self.assertIn(raw.rstrip(b'\n'),sink.streams['stderr'].getvalue())
    def test_only_trailing_newlines_are_removed_from_version_substitution(self):self.assertEqual(self.execute(version=b'1.18.2\n\n\n')[0],0)
    def test_unknown_native_or_capture_exception_leaves_intent_without_invented_failure(self):
        journal=Journal();sink=Sink()
        class Ports:
            def perform(self,action):raise OSError('explicit capture interruption')
        with self.assertRaises(OSError):run([],Ports(),journal,sink,environment_label='/env',expected_opa_version='1.18.2')
        self.assertEqual(journal.pending,'require_tools');self.assertEqual(journal.rows,[])
    def test_boolean_or_out_of_shell_range_status_and_untyped_streams_are_rejected(self):
        for row in (Observation(True),Observation(-15),Observation(256),Observation(0,'text'),Observation(0,b'',bytearray())):
            with self.subTest(row=row),self.assertRaises(ValueError):row.checked()
    def test_changed_order_missing_or_trailing_recorded_phases_are_rejected(self):
        _,journal,_=self.execute()
        for rows in (journal.rows[::-1],journal.rows[:-1],journal.rows+[journal.rows[-1]]):
            with self.subTest(rows=rows),self.assertRaises(ValueError):replay([],rows,Sink(),environment_label='/env',expected_opa_version='1.18.2')
    def test_base64_alphabet_padding_and_closed_observation_fields_are_enforced(self):
        row=Observation(0,b'a').wire()
        for change in ({**row,'stdout_base64':'YQ==\n'},{**row,'stdout_base64':'YR=='},{**row,'extra':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):Observation.from_wire(change)

if __name__=='__main__':unittest.main()
