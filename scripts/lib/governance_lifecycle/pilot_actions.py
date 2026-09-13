"""Action-bound GitHub proof and reproducible pilot validation; no operational activation."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import subprocess

from .adapter import strict_json
from .contracts import ROOT, canonical_digest, require, schema_validator, timestamp
from .kernel import transaction_ref
from .live_admission import VALIDATION_LEDGER, load_operating, replay_receipts
from .live_preparation import validate_preparation, revision_ref
from .personal_probe import assess_bound_comments, collect_bound, replay_bound_snapshot, comment_identity
from .store import load_transactions, publish_transaction, writer_lock

ACTION_LEDGER='governance/lifecycle/pilot-actions'


def assess_action_comments(request,comments,*,captured_at,previous_comments=()):
    schema_validator('pilot-action-request').validate(request)
    result=assess_bound_comments(request,comments,captured_at=captured_at,previous_comments=previous_comments)
    result['record_type']='lifecycle-pilot-action-consent-result'
    return result


def prior_statements(actions,request):
    records={}
    for action in actions:
        if action['request']==request:
            for comment in action['snapshot']['result']['relevant_comments']:
                records.setdefault(comment['id'],comment)
    return list(records.values())


def proof_projection(snapshot):
    result=snapshot['result']
    return {k:result[k] for k in ('request_digest','status','last_statement_id','issues')} | {
        'comments':[comment_identity(c) for c in result['relevant_comments']]}


def resolve(ref,records):
    result=next((r for r in records if transaction_ref(r)==ref),None)
    require(result is not None,'Referenced immutable record is missing or differs')
    return result


def fresh(receipt,at,profile):
    require(receipt['outcome']=='eligible_for_pilot','Quarantined evidence cannot authorize an action')
    age=(timestamp(at)-timestamp(receipt['source']['observed_at'])).total_seconds()
    require(0<=age<=profile['operating_policy']['maximum_age_seconds'],'Action evidence is stale or future-dated')


def state_at(receipts,actions):
    """Project only already validated actions and receipts, retaining closed/revoked history."""
    state={'decision':None,'progress':None,'closure':None,'roles_active':True,'withdrawn':set(),'reopened':False}
    for action in actions:
        request=action['request']; body=request['body']; kind=body['kind']
        if action['outcome'] in ('withdrawn','needs_clarification'):
            for old in actions:
                if old['request']==request and old['outcome']=='eligible_for_pilot':
                    state['withdrawn'].add(old['transaction_id'])
        elif action['outcome']=='eligible_for_pilot':
            if kind=='decision':
                if state['decision']:state['withdrawn'].add(state['decision']['transaction_id'])
                state.update(decision=action,progress=None,closure=None)
            elif kind=='progress':state['progress']=action
            elif kind=='closure':state['closure']=action
            elif kind=='withdrawal':state['withdrawn'].add(body['target_ref']['id'])
            elif kind=='role_withdrawal':state['roles_active']=False
    if state['decision'] and state['decision']['transaction_id'] in state['withdrawn']:
        state.update(decision=None,progress=None,closure=None)
    if state['progress'] and state['progress']['transaction_id'] in state['withdrawn']:
        state.update(progress=None,closure=None)
    if state['closure'] and state['closure']['transaction_id'] in state['withdrawn']:
        state['closure']=None
    if not state['roles_active']:
        state.update(decision=None,progress=None,closure=None)
    if state['closure']:
        passed=resolve(state['closure']['request']['body']['passing_ref'],receipts)
        if any(r['outcome']=='eligible_for_pilot' and r['criterion']['status']=='fail'
               and timestamp(r['source']['observed_at'])>timestamp(passed['source']['observed_at']) for r in receipts):
            state.update(decision=None,progress=None,closure=None,reopened=True)
    return state


def required_role(request,actions):
    kind=request['body']['kind']
    if kind=='closure':return 'closure_approver'
    if kind=='role_withdrawal':return 'role_registry_owner'
    if kind=='withdrawal':
        target=resolve(request['body']['target_ref'],actions)
        require(target['request']['body']['kind'] in ('decision','closure'),'Only a decision or closure can be withdrawn')
        return target['request']['required_role']
    return 'remediation_decider'


def validate_context(request,profile,binding,receipts,actions,*,at,allow_historical=False):
    schema_validator('pilot-action-request').validate(request)
    require(request['operating_profile_ref']==revision_ref(profile),'Action operating profile differs')
    require(request['role_binding_ref']==revision_ref(binding),'Action role binding differs')
    role=required_role(request,actions)
    require(request['required_role']==role and binding['status']=='confirmed'
            and binding['assignments'][role]==request['required_subject_id'],'Action role or appointed subject differs')
    require(timestamp(request['created_at'])<=timestamp(at),'Request predates no valid capture time')
    if allow_historical:return
    state=state_at(receipts,actions)
    require(state['roles_active'],'Pilot roles have been withdrawn')
    require(bool(receipts) and request['expected_receipt_head']==transaction_ref(receipts[-1]),'Stale evidence head')
    require(request['expected_action_head']==(transaction_ref(actions[-1]) if actions else None),'Stale action head')
    require(request['expected_revision']==len(receipts)+len(actions),'Stale finding revision')
    head_time=max([r['recorded_at'] for r in receipts]+[a['recorded_at'] for a in actions])
    require(timestamp(request['created_at'])>=timestamp(head_time),'Request predates bound state revision')
    body=request['body']; kind=body['kind']
    if kind in ('withdrawal','role_withdrawal'):return
    require(not any(r['outcome']=='quarantined' for r in receipts),'Unresolved evidence conflict prevents actions')
    failures=[r for r in receipts if r['criterion']['status']=='fail']
    require(bool(failures),'A real eligible failure is required; PASS cannot create a finding')
    latest=max(receipts,key=lambda r:(r['source']['observed_at'],r['transaction_id']))
    if kind=='decision':
        require(state['closure'] is None,'Finding is closed')
        failed=resolve(body['failure_ref'],receipts)
        require(failed==max(failures,key=lambda r:r['source']['observed_at']),'Decision must bind latest failure')
        fresh(failed,at,profile)
        require(body['supersedes_ref']==(transaction_ref(state['decision']) if state['decision'] else None),'Decision predecessor differs')
        require(timestamp(body['plan']['target_at'])>=timestamp(at),'Decision deadline predates consent capture')
        require(body['plan']['owner_id'] in {s['subject_id'] for s in binding['subjects']},'Remediation owner is not appointed in this pilot')
    elif kind in ('progress','closure'):
        require(state['closure'] is None and state['decision'] is not None,'No active decision for an open finding')
        require(body['decision_ref']==transaction_ref(state['decision']),'Action references an inactive decision')
        if kind=='progress':
            expected='in_progress' if state['progress'] is None else 'completed' if state['progress']['request']['body']['progress']=='in_progress' else None
            require(body['progress']==expected,'Invalid remediation progress transition')
        else:
            require(state['progress'] is not None and state['progress']['request']['body']['progress']=='completed','Remediation is not completed')
            require(body['progress_ref']==transaction_ref(state['progress']),'Closure progress revision differs')
            passed=resolve(body['passing_ref'],receipts)
            require(passed==latest and passed['criterion']['status']=='pass','Closure requires the latest eligible PASS')
            fresh(passed,at,profile)
            require(all(timestamp(r['source']['observed_at'])<timestamp(passed['source']['observed_at']) for r in failures),'PASS must follow every failure')
            require(timestamp(passed['source']['observed_at'])>=timestamp(state['progress']['recorded_at']),'PASS predates completed remediation')
            require(all(timestamp(r['source']['observed_at'])<=timestamp(state['progress']['recorded_at']) for r in failures),'Failure postdates remediation')


def prepare_action(snapshot,profile,binding,receipts,actions,*,recorded_at,expected_sequence):
    request=snapshot['request']
    require(snapshot['capture_method'] in ('github_api_get_via_gh','injected_test_transport'),'Unknown capture transport')
    result=replay_bound_snapshot(snapshot,assessor=assess_action_comments)
    same=[a for a in actions if a['request']==request]
    if same and proof_projection(snapshot)==proof_projection(same[-1]['snapshot']):return None
    require(type(expected_sequence) is int and expected_sequence==len(actions),'Stale action sequence')
    require(snapshot['previous_comments']==prior_statements(actions,request),'Prior personal statements omitted or changed')
    status=result['status']
    require(status in ('confirmed','rejected','revoked','needs_clarification'),'Personal action statement is missing')
    historical=bool(same) and status in ('rejected','revoked','needs_clarification')
    require(status!='needs_clarification' or historical,'Malformed initial consent cannot create an action')
    require(status!='revoked' or historical,'Revocation must reference a retained consent')
    validate_context(request,profile,binding,receipts,actions,at=recorded_at,allow_historical=historical)
    if not historical:
        require(timestamp(result['relevant_comments'][-1]['created_at'])>=timestamp(request['created_at']),'Consent predates request')
    require(timestamp(result['captured_at'])<=timestamp(recorded_at),'Action predates provider capture')
    require(all(timestamp(recorded_at)>=timestamp(a['recorded_at']) for a in actions),'Action clock regressed')
    require(all(timestamp(recorded_at)>=timestamp(r['recorded_at']) for r in receipts),'Action predates receipt head')
    outcome={'confirmed':'eligible_for_pilot','rejected':'withdrawn' if same else 'rejected','revoked':'withdrawn','needs_clarification':'needs_clarification'}[status]
    transaction={'schema_version':'0.1.0','record_type':'lifecycle-pilot-action-receipt','environment':'live_pilot_validation',
        'official_state':False,'live_activation_approved':False,'sequence':len(actions)+1,
        'previous_ref':transaction_ref(actions[-1]) if actions else None,'recorded_at':recorded_at,
        'request':deepcopy(request),'snapshot':deepcopy(snapshot),'outcome':outcome,
        'receipt_head_at_recording':transaction_ref(receipts[-1])}
    transaction['transaction_id']='transaction:'+canonical_digest(transaction)
    schema_validator('pilot-action-receipt').validate(transaction)
    return transaction


def replay_actions(receipts,actions,profile,binding):
    receipts=replay_receipts(receipts,profile)
    history=[]; last_receipt_count=0
    for action in actions:
        schema_validator('pilot-action-receipt').validate(action)
        receipt=resolve(action['receipt_head_at_recording'],receipts)
        count=receipt['sequence']; require(count>=last_receipt_count,'Action receipt history regressed')
        require(all(timestamp(r['recorded_at'])>=timestamp(action['recorded_at']) for r in receipts[count:]),'Later receipt predates action history')
        expected=prepare_action(action['snapshot'],profile,binding,receipts[:count],history,
            recorded_at=action['recorded_at'],expected_sequence=len(history))
        require(expected is not None and expected==action,'Action receipt chain or projection differs')
        history.append(action);last_receipt_count=count
    return history


def load_context(repo=ROOT):
    root=Path(repo); profile=load_operating(root); binding=validate_preparation(root)['binding']
    receipts=load_transactions(root/VALIDATION_LEDGER)
    actions=replay_actions(receipts,load_transactions(root/ACTION_LEDGER),profile,binding)
    return profile,binding,receipts,actions


def collect_action(request,repo=ROOT,*,fetch=None,captured_at=None):
    profile,binding,receipts,actions=load_context(repo)
    schema_validator('pilot-action-request').validate(request)
    # Context is checked after capture too. Historical statements may be withdrawn
    # after closure, newer evidence or a role withdrawal without granting authority.
    options={'fetch':fetch} if fetch is not None else {}
    snapshot=collect_bound(request,assessor=assess_action_comments,previous_comments=prior_statements(actions,request),
        captured_at=captured_at,**options)
    prepare_action(snapshot,profile,binding,receipts,actions,recorded_at=snapshot['result']['captured_at'],expected_sequence=len(actions))
    return snapshot


def append_action_snapshot(repo,snapshot,*,recorded_at,expected_sequence):
    root=Path(repo)
    # The caller already collected fresh provider evidence; the merge gate repeats
    # that check. Two ledgers are read under the same order as any receipt append.
    with writer_lock(root/VALIDATION_LEDGER),writer_lock(root/ACTION_LEDGER):
        profile,binding,receipts,actions=load_context(root)
        action=prepare_action(snapshot,profile,binding,receipts,actions,recorded_at=recorded_at,expected_sequence=expected_sequence)
        if action is None:return {'outcome':'duplicate','transaction_ref':None}
        publish_transaction(root/ACTION_LEDGER/'transactions',action)
        return {'outcome':action['outcome'],'transaction_ref':transaction_ref(action)}


def verify_new_actions(repo,base_ref,*,fetch=None,checked_at=None):
    root=Path(repo);profile,binding,receipts,actions=load_context(root)
    old=set(subprocess.check_output(['git','ls-tree','-r','--name-only',base_ref,'--',ACTION_LEDGER],cwd=root,text=True).splitlines())
    options={'fetch':fetch} if fetch is not None else {}; checked=0
    for action in actions:
        name=f"{ACTION_LEDGER}/transactions/{action['sequence']:08d}-{action['transaction_id'].split(':')[1]}.json"
        if name in old:continue
        request=action['request']
        require(action['snapshot']['capture_method']=='github_api_get_via_gh','New action requires an actual GitHub capture')
        fresh_snapshot=collect_bound(request,assessor=assess_action_comments,previous_comments=action['snapshot']['previous_comments'],captured_at=checked_at,**options)
        require(proof_projection(fresh_snapshot)==proof_projection(action['snapshot']),'New action differs from independently retrieved personal statement')
        now=fresh_snapshot['result']['captured_at']
        require(timestamp(action['recorded_at'])<=timestamp(now),'Action claims future recording time')
        # Every new grant must still bind the accepted evidence head at merge.
        if action['outcome']=='eligible_for_pilot' and request['body']['kind'] not in ('withdrawal','role_withdrawal'):
            require(action['receipt_head_at_recording']==transaction_ref(receipts[-1]),'New action is stale against merged evidence')
            prior=actions[:action['sequence']-1]
            validate_context(request,profile,binding,receipts,prior,at=now)
            # Recheck active prerequisite decisions and progress, never infer their
            # continued validity from an old capture when granting a new action.
            state=state_at(receipts,prior)
            for dependency in (state['decision'],state['progress']):
                if dependency is None:continue
                live=collect_bound(dependency['request'],assessor=assess_action_comments,
                    previous_comments=prior_statements(prior,dependency['request']),captured_at=checked_at,**options)
                require(proof_projection(live)==proof_projection(dependency['snapshot']),'Action prerequisite was changed or withdrawn at the provider')
        checked+=1
    return checked


def project_actions(repo=ROOT):
    profile,binding,receipts,actions=load_context(repo); state=state_at(receipts,actions)
    failures=[r for r in receipts if r['outcome']=='eligible_for_pilot' and r['criterion']['status']=='fail']
    conflicted=any(r['outcome']=='quarantined' for r in receipts)
    status='no_finding' if not failures else 'needs_clarification' if conflicted else 'closed' if state['closure'] else 'open'
    return {'schema_version':'0.1.0','index_type':'lifecycle-pilot-action-validation','official_state':False,'live_activation_approved':False,
        'enforcement':'report_only','profile_ref':revision_ref(profile),'role_binding_ref':revision_ref(binding),
        'as_of':max([r['recorded_at'] for r in receipts]+[a['recorded_at'] for a in actions],default=None),
        'revision':len(receipts)+len(actions),'receipt_head_ref':transaction_ref(receipts[-1]) if receipts else None,
        'action_head_ref':transaction_ref(actions[-1]) if actions else None,'finding_state':status,'roles_active':state['roles_active'],
        'active_decision_ref':transaction_ref(state['decision']) if state['decision'] else None,
        'active_closure_ref':transaction_ref(state['closure']) if state['closure'] and not conflicted else None,
        'counts':{'receipts':len(receipts),'actions':len(actions),'failures':len(failures),'quarantined':sum(r['outcome']=='quarantined' for r in receipts)},
        'action_refs':[transaction_ref(a) for a in actions],
        'limitation':'Action eligibility validation only. LD-07 and an explicitly scoped operational publisher remain required.'}
