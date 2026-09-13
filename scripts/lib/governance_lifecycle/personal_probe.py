"""Read-only verification of an explicit personal-channel probe, never lifecycle consent."""
from datetime import datetime, timezone
from pathlib import Path
import json

from .adapter import json_bytes, strict_json
from .contracts import canonical_digest, require, timestamp, schema_validator
from .live_admission import load_operating, replay_receipts, VALIDATION_LEDGER
from .live_evidence import github_get
from .live_preparation import validate_preparation, revision_ref
from .kernel import transaction_ref
from .store import load_transactions

MARKER = "CLG-PERSONAL-CONSENT/1\n"
STATEMENT = "Ich habe diese Anfrage persönlich geprüft und gebe diese Erklärung selbst ab; keine Automation handelt dabei für mich."


def statement_body(request, *, disposition="approve", supersedes_comment_id=None):
    require(disposition in ("approve", "reject", "revoke"), "Unknown personal disposition")
    return MARKER + json.dumps({"request_digest":canonical_digest(request), "disposition":disposition,
        "supersedes_comment_id":supersedes_comment_id, "statement":STATEMENT}, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def validate_request(request, repo, *, require_current_head=True):
    schema_validator("personal-channel-probe").validate(request)
    profile=load_operating(repo); prepared=validate_preparation(repo)
    require(request['operating_profile_ref']==revision_ref(profile), "Probe operating profile differs")
    require(request['role_binding_ref']==revision_ref(prepared['binding']), "Probe role binding differs")
    require(prepared['assignments'][request['required_role']]==request['required_subject_id'], "Probe appointed subject differs")
    history=replay_receipts(load_transactions(Path(repo)/VALIDATION_LEDGER),profile)
    require(any(request['receipt_head_ref']==transaction_ref(t) for t in history), "Probe receipt reference is missing")
    if require_current_head:
        require(request['receipt_head_ref']==transaction_ref(history[-1]), "Probe receipt head is no longer current")
    return prepared


def comment_identity(comment):
    return {k:comment.get(k) for k in ('id','body','issue_url','html_url','created_at','updated_at','performed_via_github_app')} | {
        'user':{k:comment['user'].get(k) for k in ('id','type')}}


def assess_comments(request, comments, *, captured_at, previous_comments=()):
    """Verify captured provider fields and the person's explicit self-attestation.

    GitHub authenticates an account, not physical human presence. This probe
    establishes no remediation/closure approval and cannot activate runtime.
    """
    schema_validator('personal-channel-probe').validate(request)
    expected_id=int(request['required_subject_id'].split(':')[1])
    issue_url=f"https://api.github.com/repos/{request['repository_id']}/issues/{request['discussion_number']}"
    page_url=f"https://github.com/{request['repository_id']}/pull/{request['discussion_number']}"
    digest=canonical_digest(request)
    ids=[c['id'] for c in comments]
    require(all(type(i) is int and i>0 for i in ids) and len(ids)==len(set(ids)), 'Duplicate or invalid comment identity')
    current={c['id']:c for c in comments}
    issues=[]; relevant=[]; unauthorized=[]; state='waiting_for_personal_statement'; head=None
    for old in previous_comments:
        new=current.get(old['id'])
        if new is None or comment_identity(new)!=comment_identity(old):
            issues.append({'comment_id':old['id'],'reason':'previous_statement_deleted_or_changed'})
    previous_time=None
    for comment in sorted(comments,key=lambda c:c['id']):
        body=comment.get('body','')
        if not isinstance(body,str):
            continue
        # GitHub's web comment form emits CRLF. Normalize only parsing input;
        # retained provider bytes and edit/deletion identity stay untouched.
        parse_body=body.replace('\r\n','\n')
        if not parse_body.startswith(MARKER):
            continue
        try:
            payload=strict_json(parse_body[len(MARKER):])
        except (ValueError,TypeError):
            if comment.get('user',{}).get('id')==expected_id:
                relevant.append(comment); issues.append({'comment_id':comment['id'],'reason':'malformed_personal_statement'})
            continue
        if not isinstance(payload,dict) or payload.get('request_digest')!=digest:
            continue
        if (comment.get('user',{}).get('id')!=expected_id or comment.get('user',{}).get('type')!='User'
                or 'performed_via_github_app' not in comment or comment['performed_via_github_app'] is not None):
            unauthorized.append(comment['id']); continue
        relevant.append(comment)
        try:
            require(comment['issue_url']==issue_url and comment['html_url']==page_url+f"#issuecomment-{comment['id']}", 'Wrong discussion')
            require(comment['created_at']==comment['updated_at'], 'Edited personal statement')
            issued=timestamp(comment['created_at'])
            require(timestamp(request['created_at'])<=issued<=timestamp(captured_at), 'Personal statement timestamp differs')
            require(previous_time is None or issued>=previous_time, 'Personal statement chronology differs')
            require(set(payload)=={'request_digest','disposition','supersedes_comment_id','statement'}, 'Unexpected statement fields')
            require(payload['statement']==STATEMENT, 'Explicit personal self-attestation required')
            require(payload['disposition'] in ('approve','reject','revoke'), 'Unknown disposition')
            predecessor=payload['supersedes_comment_id']
            require(predecessor is None or type(predecessor) is int, 'Invalid predecessor identity')
            require(predecessor==head, 'Personal statement must reference its predecessor')
            require(payload['disposition']!='revoke' or state=='confirmed', 'Only active confirmation can be revoked')
            state={'approve':'confirmed','reject':'rejected','revoke':'revoked'}[payload['disposition']]
            head=comment['id']; previous_time=issued
        except (ValueError,KeyError,TypeError) as error:
            issues.append({'comment_id':comment['id'],'reason':str(error)})
    return {'schema_version':'0.1.0','record_type':'lifecycle-personal-channel-probe-result',
        'request_digest':digest,'status':'needs_clarification' if issues else state,'last_statement_id':head,
        'relevant_comments':relevant,'unauthorized_comment_ids':unauthorized,'issues':issues,
        'captured_at':captured_at,'official_state':False,'live_activation_approved':False,
        'remediation_or_closure_authorized':False,'human_presence':'explicitly_self_attested_not_provider_attested'}


def collect_probe(request, *, repo, previous_comments=(), fetch=github_get, captured_at=None):
    validate_request(request,repo)
    endpoint=f"repos/{request['repository_id']}/issues/{request['discussion_number']}"
    issue_bytes=fetch(endpoint); issue=strict_json(issue_bytes)
    require(issue['number']==request['discussion_number'] and issue['html_url']==f"https://github.com/{request['repository_id']}/pull/{request['discussion_number']}"
            and bool(issue.get('pull_request')), 'Probe discussion is not the expected pull request')
    def read_comments():
        result=[]; raw=[]
        for page in range(1,11):
            data=fetch(endpoint+f'/comments?per_page=100&page={page}'); batch=strict_json(data)
            require(type(batch) is list, 'Expected comment page')
            result.extend(batch); raw.append(data.decode())
            if len(batch)<100:
                return result,raw
        raise ValueError('Personal discussion exceeds supported page count')
    before,raw_before=read_comments(); after,raw_after=read_comments()
    require(before==after,'Personal discussion changed during capture')
    at=captured_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    result=assess_comments(request,after,captured_at=at,previous_comments=previous_comments)
    return {'request':request,'result':result,'issue_response':issue_bytes.decode(),
        'comment_pages_before':raw_before,'comment_pages_after':raw_after,'previous_comments':list(previous_comments),
        'capture_method':'github_api_get_via_gh' if fetch is github_get else 'injected_test_transport'}


def replay_probe_snapshot(snapshot):
    request=snapshot['request']
    before=[c for page in snapshot['comment_pages_before'] for c in strict_json(page)]
    after=[c for page in snapshot['comment_pages_after'] for c in strict_json(page)]
    require(before==after,'Stored personal discussion changed during capture')
    issue=strict_json(snapshot['issue_response'])
    require(issue['number']==request['discussion_number'] and issue['html_url']==f"https://github.com/{request['repository_id']}/pull/{request['discussion_number']}"
            and bool(issue.get('pull_request')), 'Stored probe discussion differs')
    expected=assess_comments(request,after,captured_at=snapshot['result']['captured_at'],
        previous_comments=snapshot.get('previous_comments',[]))
    require(snapshot['result']==expected,'Stored probe projection differs')
    return expected
