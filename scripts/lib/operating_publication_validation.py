"""Whole original publication precondition; validation grants no publishing authority."""
class OperatingPublicationValidation:
    def __init__(self, context, *, path_factory, prefix, receipts, actions, operating, git):
        self.context,self.Path=context,path_factory
        self.prefix,self.receipts,self.actions,self.operating,self.git=prefix,receipts,actions,operating,git

    def validate_publication(self,repo,base_ref):
        check_accepted_prefix=self.prefix.check_accepted_prefix
        VALIDATION_LEDGER,verify_new_receipts=self.context.admission.VALIDATION_LEDGER,self.receipts.verify_new_receipts
        ACTION_LEDGER,load_context,verify_new_actions=self.context.actions.ACTION_LEDGER,self.context.actions.load_context,self.actions.verify_new_actions
        validate_receipts=self.context.lifecycle_pilot_validation.validate
        validate_actions=self.context.lifecycle_pilot_actions.validate
        root=self.Path(repo);check_accepted_prefix(root,base_ref)
        validate_receipts(root);validate_actions(root);index=self.context.operating.validate(root)
        verify_new_receipts(root,base_ref);verify_new_actions(root,base_ref);self.operating.verify_new_captures(root,base_ref)
        if index['live_activation_approved']:
            self.operating.verify_provider(root)
        else:
            old=set(self.git.check_output(['git','ls-tree','-r','--name-only',base_ref,'--',VALIDATION_LEDGER,ACTION_LEDGER],cwd=root,text=True).splitlines())
            load_transactions=self.context.store.load_transactions
            for path in (root/VALIDATION_LEDGER/'transactions').glob('*.json'):
                self.context.contracts.require(str(path.relative_to(root)) in old,'Inactive pilot cannot publish a new observation')
            for action in load_transactions(root/ACTION_LEDGER):
                name=f"{ACTION_LEDGER}/transactions/{action['sequence']:08d}-{action['transaction_id'].split(':')[1]}.json"
                if name not in old:
                    self.context.contracts.require(action['outcome']!='eligible_for_pilot' or action['request']['body']['kind'] in ('withdrawal','role_withdrawal'),'Inactive pilot cannot publish an action grant')
        return index
