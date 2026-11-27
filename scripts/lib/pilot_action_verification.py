"""Whole original new-action verification over explicit model, Git and GET ports."""
class PilotActionVerification:
    def __init__(self, context, *, path_factory, git):
        self.context,self.Path,self.git=context,path_factory,git

    def verify_new_actions(self,repo,base_ref,*,fetch=None,checked_at=None):
        root=self.Path(repo);profile,binding,receipts,actions=self.context.actions.load_context(root)
        old=set(self.git.check_output(['git','ls-tree','-r','--name-only',base_ref,'--',self.context.actions.ACTION_LEDGER],cwd=root,text=True).splitlines())
        options={'fetch':fetch} if fetch is not None else {}; checked=0
        for action in actions:
            name=f"{self.context.actions.ACTION_LEDGER}/transactions/{action['sequence']:08d}-{action['transaction_id'].split(':')[1]}.json"
            if name in old:continue
            request=action['request']
            self.context.contracts.require(action['snapshot']['capture_method']=='github_api_get_via_gh','New action requires an actual GitHub capture')
            fresh_snapshot=self.context.provider.collect_bound(request,assessor=self.context.actions.assess_action_comments,previous_comments=action['snapshot']['previous_comments'],captured_at=checked_at,**options)
            self.context.contracts.require(self.context.actions.proof_projection(fresh_snapshot)==self.context.actions.proof_projection(action['snapshot']),'New action differs from independently retrieved personal statement')
            now=fresh_snapshot['result']['captured_at']
            self.context.contracts.require(self.context.contracts.timestamp(action['recorded_at'])<=self.context.contracts.timestamp(now),'Action claims future recording time')
            # Every new grant must still bind the accepted evidence head at merge.
            if action['outcome']=='eligible_for_pilot' and request['body']['kind'] not in ('withdrawal','role_withdrawal'):
                self.context.contracts.require(action['receipt_head_at_recording']==self.context.kernel.transaction_ref(receipts[-1]),'New action is stale against merged evidence')
                prior=actions[:action['sequence']-1]
                self.context.actions.validate_context(request,profile,binding,receipts,prior,at=now)
                # Recheck active prerequisite decisions and progress, never infer their
                # continued validity from an old capture when granting a new action.
                state=self.context.actions.state_at(receipts,prior)
                for dependency in (state['decision'],state['progress']):
                    if dependency is None:continue
                    live=self.context.provider.collect_bound(dependency['request'],assessor=self.context.actions.assess_action_comments,
                        previous_comments=self.context.actions.prior_statements(prior,dependency['request']),captured_at=checked_at,**options)
                    self.context.contracts.require(self.context.actions.proof_projection(live)==self.context.actions.proof_projection(dependency['snapshot']),'Action prerequisite was changed or withdrawn at the provider')
            checked+=1
        return checked
