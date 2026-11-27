"""Separate personal operating acceptance for demo operation-readiness."""
from pathlib import Path
import hashlib
import subprocess

from .adapter import strict_json,json_bytes
from .contracts import ROOT,canonical_digest,require,timestamp
from .consumer_admission import load_operating
from .live_preparation import revision_ref
from .consumer_contracts import validate_preparation,schema_validator,MODEL
from .personal_probe import assess_bound_comments,collect_bound,replay_bound_snapshot,comment_identity
from .consumer_actions import project_actions

REQUEST_PATH=MODEL+'/acceptance.json'
CAPTURES='governance/consumer-lifecycle/acceptance'
INDEX='status/governance-consumer-lifecycle.json'
REPORT='generated/reports/governance-consumer-lifecycle.md'
STATEMENT_PATH='generated/reports/consumer-lifecycle-acceptance-statement.md'
MANIFEST_PATHS=('.github/workflows/consumer-lifecycle-guard.yml',
 '.github/workflows/consumer-lifecycle-update.yml',
 'docs/operations/evidence/consumer-lifecycle-operation.md',
 'requirements-validation.txt',
 'schemas/governance-consumer-acceptance.schema.json',
 'schemas/governance-consumer-action-receipt.schema.json',
 'schemas/governance-consumer-action-request.schema.json',
 'schemas/governance-consumer-profile.schema.json',
 'schemas/governance-consumer-receipt.schema.json',
 'schemas/governance-consumer-roles.schema.json',
 'schemas/governance-lifecycle-action-index.schema.json',
 'schemas/governance-lifecycle-action-transaction.schema.json',
 'schemas/governance-lifecycle-architecture-source.schema.json',
 'schemas/governance-lifecycle-candidate-context.schema.json',
 'schemas/governance-lifecycle-candidates.schema.json',
 'schemas/governance-lifecycle-closure-index.schema.json',
 'schemas/governance-lifecycle-closure-transaction.schema.json',
 'schemas/governance-lifecycle-closure-v0.2.schema.json',
 'schemas/governance-lifecycle-closure.schema.json',
 'schemas/governance-lifecycle-common.schema.json',
 'schemas/governance-lifecycle-decision-v0.2.schema.json',
 'schemas/governance-lifecycle-decision.schema.json',
 'schemas/governance-lifecycle-devsecops-source.schema.json',
 'schemas/governance-lifecycle-event-v0.2.schema.json',
 'schemas/governance-lifecycle-event.schema.json',
 'schemas/governance-lifecycle-exception-index.schema.json',
 'schemas/governance-lifecycle-exception-profile.schema.json',
 'schemas/governance-lifecycle-exception-transaction.schema.json',
 'schemas/governance-lifecycle-exception.schema.json',
 'schemas/governance-lifecycle-index.schema.json',
 'schemas/governance-lifecycle-live-profile-preparation.schema.json',
 'schemas/governance-lifecycle-observation.schema.json',
 'schemas/governance-lifecycle-operating-acceptance.schema.json',
 'schemas/governance-lifecycle-overview.schema.json',
 'schemas/governance-lifecycle-personal-channel-probe.schema.json',
 'schemas/governance-lifecycle-pilot-action-receipt.schema.json',
 'schemas/governance-lifecycle-pilot-action-request.schema.json',
 'schemas/governance-lifecycle-pilot-operating.schema.json',
 'schemas/governance-lifecycle-pilot-receipt.schema.json',
 'schemas/governance-lifecycle-pilot-role-binding.schema.json',
 'schemas/governance-lifecycle-profile.schema.json',
 'schemas/governance-lifecycle-remediation-v0.2.schema.json',
 'schemas/governance-lifecycle-remediation.schema.json',
 'schemas/governance-lifecycle-transaction.schema.json',
 'scripts/bootstrap_validation_env.sh',
 'scripts/lib/governance_lifecycle/__init__.py',
 'scripts/lib/governance_lifecycle/adapter.py',
 'scripts/lib/governance_lifecycle/architecture_candidates.py',
 'scripts/lib/governance_lifecycle/candidates.py',
 'scripts/lib/governance_lifecycle/closure.py',
 'scripts/lib/governance_lifecycle/consumer_acceptance.py',
 'scripts/lib/governance_lifecycle/consumer_actions.py',
 'scripts/lib/governance_lifecycle/consumer_admission.py',
 'scripts/lib/governance_lifecycle/consumer_contracts.py',
 'scripts/lib/governance_lifecycle/consumer_evidence.py',
 'scripts/lib/governance_lifecycle/contracts.py',
 'scripts/lib/governance_lifecycle/decisions.py',
 'scripts/lib/governance_lifecycle/devsecops_candidates.py',
 'scripts/lib/governance_lifecycle/exceptions.py',
 'scripts/lib/governance_lifecycle/kernel.py',
 'scripts/lib/governance_lifecycle/live_admission.py',
 'scripts/lib/governance_lifecycle/live_evidence.py',
 'scripts/lib/governance_lifecycle/live_preparation.py',
 'scripts/lib/governance_lifecycle/operating_acceptance.py',
 'scripts/lib/governance_lifecycle/personal_probe.py',
 'scripts/lib/governance_lifecycle/pilot_actions.py',
 'scripts/lib/governance_lifecycle/store.py',
 'scripts/lib/governance_lifecycle/synthetic.py',
 'scripts/lib/governance_lifecycle/synthetic_actions.py',
 'scripts/lib/governance_lifecycle/synthetic_exceptions.py',
 'scripts/publish_consumer_lifecycle.py',
 'scripts/run_consumer_lifecycle.py',
 'scripts/validate_all.sh',
 'scripts/validation-toolchain.env')


def manifest(repo=ROOT):
    return {name:hashlib.sha256((Path(repo)/name).read_bytes()).hexdigest() for name in MANIFEST_PATHS}


def request(repo=ROOT):
    value=strict_json((Path(repo)/REQUEST_PATH).read_bytes())
    schema_validator('operating-acceptance').validate(value)
    require(set(value['implementation_manifest'])==set(MANIFEST_PATHS),'Acceptance implementation scope differs')
    profile=load_operating(repo);binding=validate_preparation(repo)['binding']
    require(value['operating_profile_ref']==revision_ref(profile) and value['role_binding_ref']==revision_ref(binding),'Acceptance profile or role revision differs')
    require(value['required_subject_id']==binding['assignments']['role_registry_owner'],'Named acceptance subject differs')
    return value


def assess(request,comments,*,captured_at,previous_comments=()):
    schema_validator('operating-acceptance').validate(request)
    result=assess_bound_comments(request,comments,captured_at=captured_at,previous_comments=previous_comments)
    result['record_type']='lifecycle-operating-acceptance-result'
    result['operating_acceptance_granted']=result['status']=='confirmed'
    return result


def prior_comments(captures):
    records={}
    for capture in captures:
        for comment in capture['result']['relevant_comments']:records.setdefault(comment['id'],comment)
    return list(records.values())


def captures(repo=ROOT):
    root=Path(repo); expected=request(root); directory=root/CAPTURES
    require(not directory.is_symlink(),'Acceptance capture directory cannot be a symlink')
    result=[]
    for n,path in enumerate(sorted(directory.iterdir()) if directory.exists() else [],1):
        require(path.is_file() and not path.is_symlink() and path.name==f'{n:08d}.json','Acceptance capture sequence or type differs')
        snapshot=strict_json(path.read_bytes())
        require(set(snapshot)=={'request','result','issue_response','comment_pages_before','comment_pages_after','previous_comments','capture_method'}, 'Consumer acceptance snapshot fields differ')
        require(snapshot['request']==expected and snapshot['capture_method']=='github_api_get_via_gh','Acceptance capture source or request differs')
        require(snapshot['previous_comments']==prior_comments(result),'Acceptance capture loses prior statement history')
        replay_bound_snapshot(snapshot,assessor=assess)
        require(not result or timestamp(snapshot['result']['captured_at'])>=timestamp(result[-1]['result']['captured_at']),'Acceptance capture time regressed')
        result.append(snapshot)
    return result


def collect(repo=ROOT,*,fetch=None,captured_at=None):
    root=Path(repo);value=request(root);history=captures(root)
    options={'fetch':fetch} if fetch is not None else {}
    return collect_bound(value,assessor=assess,previous_comments=prior_comments(history),captured_at=captured_at,**options)


def capture(repo=ROOT):
    root=Path(repo); history=captures(root);snapshot=collect(root)
    require(snapshot['result']['status']!='waiting_for_personal_statement','Personal consumer operating statement is still missing')
    destination=root/CAPTURES/f'{len(history)+1:08d}.json'
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as stream:stream.write(json_bytes(snapshot))
    return snapshot


def proof(snapshot):
    result=snapshot['result']
    return {key:result[key] for key in ('request_digest','status','last_statement_id','issues')} | {
        'comments':[comment_identity(c) for c in result['relevant_comments']]}


def effective(repo=ROOT):
    value=request(repo);history=captures(repo)
    status=history[-1]['result']['status'] if history else 'waiting_for_personal_acceptance'
    unchanged=value['implementation_manifest']==manifest(repo)
    roles=project_actions(repo)['roles_active']
    return {'status':status,'implementation_matches':unchanged,'roles_active':roles,
        'effective':status=='confirmed' and unchanged and roles,
        'request_digest':canonical_digest(value),'capture_digest':canonical_digest(history[-1]) if history else None,
        'captured_at':history[-1]['result']['captured_at'] if history else None}


def verify_provider(repo=ROOT,*,fetch=None):
    history=captures(repo)
    require(bool(history),'No retained operating acceptance exists')
    latest=collect(repo,fetch=fetch)
    require(proof(latest)==proof(history[-1]),'Operating acceptance changed or was withdrawn at GitHub; capture the correction first')
    require(effective(repo)['effective'],'Personal operating acceptance is not effective')
    verify_required_guard(fetch=fetch)
    return latest


def verify_required_guard(*,fetch=None):
    from .live_evidence import github_get
    rules=strict_json((fetch or github_get)('repos/joku-dev/devsecops-governance-framework/rules/branches/main'))
    require(isinstance(rules,list),'Effective main rules must be a list')
    required=any(rule.get('type')=='required_status_checks'
        and rule.get('parameters',{}).get('strict_required_status_checks_policy') is True
        and any(check.get('context')=='Consumer Lifecycle Guard' and check.get('integration_id')==15368
                for check in rule['parameters'].get('required_status_checks',[]))
        for rule in rules)
    require(required,'Consumer Lifecycle Guard must be a strict required GitHub Actions check on main')


def verify_new_captures(repo,base_ref,*,fetch=None,checked_at=None):
    root=Path(repo);history=captures(root)
    old=set(subprocess.check_output(['git','ls-tree','-r','--name-only',base_ref,'--',CAPTURES],cwd=root,text=True).splitlines())
    count=0
    for n,snapshot in enumerate(history,1):
        if f'{CAPTURES}/{n:08d}.json' in old:continue
        latest=collect(root,fetch=fetch,captured_at=checked_at)
        require(proof(latest)==proof(snapshot),'New operating acceptance differs from GitHub')
        require(timestamp(snapshot['result']['captured_at'])<=timestamp(latest['result']['captured_at']),'Operating acceptance capture is future-dated')
        if snapshot['result']['status']=='confirmed':
            require(request(root)['implementation_manifest']==manifest(root),'Implementation changed after acceptance request')
        count+=1
    # A new official projection must not rely on an old operating snapshot after
    # the person withdraws it. Recheck even when no new acceptance capture is added.
    index=projection(root)
    if index['live_activation_approved']:
        previous=subprocess.run(['git','show',f'{base_ref}:{INDEX}'],cwd=root,capture_output=True)
        if previous.returncode or previous.stdout!=(root/INDEX).read_bytes():
            verify_provider(root,fetch=fetch)
    return count


def projection(repo=ROOT):
    candidate=project_actions(repo);acceptance=effective(repo)
    return {'schema_version':'0.1.0','index_type':'governance-consumer-lifecycle-pilot',
        'official_state':acceptance['effective'],'live_activation_approved':acceptance['effective'],
        'enforcement':'report_only','scope':load_operating(repo)['scope'],'operating_acceptance':acceptance,
        'candidate_projection_digest':canonical_digest(candidate),'evidence_as_of':candidate['as_of'],
        'as_of':max(filter(None,(candidate['as_of'],acceptance['captured_at'])),default=None),
        'finding_state':candidate['finding_state'] if acceptance['effective'] else 'inactive',
        'counts':candidate['counts'],'active_decision_ref':candidate['active_decision_ref'] if acceptance['effective'] else None,
        'active_closure_ref':candidate['active_closure_ref'] if acceptance['effective'] else None,
        'promotion_basis':'Explicit consumer operating acceptance of the separate pilot validation projection; source receipts remain unchanged',
        'limitation':'Manual report-only operation_readiness pilot for the neutral demo only; no automatic remediation, waivers or baseline changes.'}


def render(index):
    acceptance=index['operating_acceptance']
    return '\n'.join(['# Consumer Operation-Readiness Lifecycle','',
        f"Operating acceptance: **{acceptance['status']}**. Effective: **{str(acceptance['effective']).lower()}**.",
        f"Implementation matches the acceptance request: `{str(acceptance['implementation_matches']).lower()}`.",
        f"Finding state: `{index['finding_state']}`. Pilot state as of `{index['as_of']}`; evidence as of `{index['evidence_as_of']}`.",
        f"Receipts: {index['counts']['receipts']}; action records: {index['counts']['actions']}.",'',
        'The report reflects retained captures. Recheck GitHub before any new operational proposal.',
        index['promotion_basis']+'.',index['limitation'],''])


def validate(repo=ROOT):
    root=Path(repo); index=projection(root)
    require(strict_json((root/INDEX).read_bytes())==index,'Live pilot index differs')
    require((root/REPORT).read_text()==render(index),'Live pilot report differs')
    from .personal_probe import statement_body
    expected=statement_template(request(root),statement_body)
    require((root/STATEMENT_PATH).read_text()==expected,'Operating acceptance statement template differs')
    return index


def statement_template(value,body):
    return ('# Persönliche Consumer-Betriebsabnahme\n\n'
        'Bitte zuerst den vollständigen Antrag und den Betriebsleitfaden prüfen. '
        'Diese Erklärung gibt den beschriebenen manuellen Operation-Readiness-Piloten im Report-only-Modus frei. '
        'Behebung und Abschluss benötigen weiterhin eigene persönliche Erklärungen.\n\n'
        f"Diskussion: https://github.com/{value['repository_id']}/pull/{value['discussion_number']}\n\n"
        '```text\n'+body(value)+'```\n\n'
        'Die benannte Person gibt den Kommentar selbst ab. Codex darf ihn vorbereiten, aber nicht stellvertretend posten.\n')


def generate(repo=ROOT):
    root=Path(repo); index=projection(root)
    (root/INDEX).write_bytes(json_bytes(index));(root/REPORT).write_text(render(index))
    from .personal_probe import statement_body
    (root/STATEMENT_PATH).write_text(statement_template(request(root),statement_body))


def validate_publication(repo,base_ref):
    from .consumer_admission import VALIDATION_LEDGER,verify_new_receipts
    from .consumer_actions import ACTION_LEDGER,verify_new_actions
    root=Path(repo)
    check_prefix(root,base_ref)
    index=validate(root)
    verify_new_receipts(root,base_ref);verify_new_actions(root,base_ref);verify_new_captures(root,base_ref)
    if index['live_activation_approved']:
        verify_provider(root)
    else:
        old=set(subprocess.check_output(['git','ls-tree','-r','--name-only',base_ref,'--',VALIDATION_LEDGER,ACTION_LEDGER],cwd=root,text=True).splitlines())
        from .store import load_transactions
        for path in (root/VALIDATION_LEDGER/'transactions').glob('*.json'):
            require(str(path.relative_to(root)) in old,'Inactive consumer cannot publish a new observation')
        for action in load_transactions(root/ACTION_LEDGER):
            name=f"{ACTION_LEDGER}/transactions/{action['sequence']:08d}-{action['transaction_id'].split(':')[1]}.json"
            if name not in old:
                require(action['outcome']!='eligible_for_pilot' or action['request']['body']['kind'] in ('withdrawal','role_withdrawal'),
                        'Inactive consumer cannot publish an action grant')
    return index


def check_prefix(repo,base_ref):
    root=Path(repo).resolve()
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',base_ref,'--',
        'governance/consumer-lifecycle',MODEL],cwd=root,text=True).splitlines()
    for name in paths:
        path=root/name
        require(path.is_file() and not any(p.is_symlink() for p in (path,*path.parents)), 'Missing or symlinked accepted consumer history')
        before=subprocess.check_output(['git','show',base_ref+':'+name],cwd=root)
        require(path.read_bytes()==before,'Accepted consumer history or model was rewritten: '+name)
    return len(paths)
