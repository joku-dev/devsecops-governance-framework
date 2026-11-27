"""Isolated policy branches with explicit stand-ins; full-model tests are separate.

These cases do not claim schema or provider validation. The complete helper AST
is independently matched to V1, and the execution suite uses its actual models.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.operating_publication_validation import OperatingPublicationValidation
from lib.repository_lifecycle.contracts import LifecycleContracts,ContractError
VALIDATION='governance/lifecycle/live-validation';ACTIONS='governance/lifecycle/pilot-actions'
class PublicationValidationPolicy(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name);(self.root/VALIDATION/'transactions').mkdir(parents=True);self.trace=[];self.actions=[];self.old=[];self.index={'live_activation_approved':False,'explicit_policy_fixture':True};self.fail=None
  def call(name,result=None):
   def invoke(*args):
    self.trace.append(name)
    if self.fail==name:raise ContractError('explicit original helper failure')
    return result() if callable(result) else result
   return invoke
  self.context=NS(admission=NS(VALIDATION_LEDGER=VALIDATION),actions=NS(ACTION_LEDGER=ACTIONS,load_context=call('unused-load-context')),contracts=NS(require=lambda condition,message:LifecycleContracts.require(None,condition,message)),lifecycle_pilot_validation=NS(validate=call('validate-receipts')),lifecycle_pilot_actions=NS(validate=call('validate-actions')),operating=NS(validate=call('validate-operating',lambda:self.index)),store=NS(load_transactions=call('load-actions',lambda:self.actions)))
  def tree(command,*,cwd,text):
   self.trace.append('two-ledger-tree');self.assertEqual(command,['git','ls-tree','-r','--name-only','explicit-base','--',VALIDATION,ACTIONS]);self.assertEqual(cwd,self.root);self.assertIs(text,True);return '\n'.join(self.old)
  self.program=OperatingPublicationValidation(self.context,path_factory=Path,prefix=NS(check_accepted_prefix=call('accepted-prefix')),receipts=NS(verify_new_receipts=call('fresh-receipts')),actions=NS(verify_new_actions=call('fresh-actions')),operating=NS(verify_new_captures=call('fresh-operating'),verify_provider=call('provider')),git=NS(check_output=tree))
 def action(self,kind,outcome='eligible_for_pilot'):return {'sequence':1,'transaction_id':'sha256:explicit-fixture','outcome':outcome,'request':{'body':{'kind':kind}}}
 def test_inactive_new_positive_grants_fail_but_permission_reducing_outcomes_are_allowed(self):
  for kind in ('decision','progress','closure'):
   with self.subTest(grant=kind):
    self.actions=[self.action(kind)]
    with self.assertRaisesRegex(ContractError,'Inactive pilot cannot publish an action grant'):self.program.validate_publication(self.root,'explicit-base')
  for kind,outcome in [('withdrawal','eligible_for_pilot'),('role_withdrawal','eligible_for_pilot'),('decision','withdrawn'),('closure','needs_clarification')]:
   with self.subTest(reducing=(kind,outcome)):
    self.actions=[self.action(kind,outcome)];self.assertIs(self.program.validate_publication(self.root,'explicit-base'),self.index)
 def test_inactive_historical_positive_grant_is_not_reclassified_as_new(self):
  self.actions=[self.action('decision')];self.old=[ACTIONS+'/transactions/00000001-explicit-fixture.json'];self.assertIs(self.program.validate_publication(self.root,'explicit-base'),self.index);self.assertNotIn('provider',self.trace)
 def test_failed_fresh_receipt_stops_later_helpers_and_inactive_tree_scan(self):
  self.fail='fresh-receipts'
  with self.assertRaisesRegex(ContractError,'explicit original helper failure'):self.program.validate_publication(self.root,'explicit-base')
  self.assertEqual(self.trace,['accepted-prefix','validate-receipts','validate-actions','validate-operating','fresh-receipts'])
 def test_active_branch_rechecks_provider_last_without_scanning_inactive_ledgers(self):
  self.index['live_activation_approved']=True;self.assertIs(self.program.validate_publication(self.root,'explicit-base'),self.index);self.assertEqual(self.trace,['accepted-prefix','validate-receipts','validate-actions','validate-operating','fresh-receipts','fresh-actions','fresh-operating','provider'])
if __name__=='__main__':unittest.main(verbosity=2)
