"""Additive provider observations; none assign a role or accept an operation.

Native actors, native review participation and governance authority are separate.
The accepted GitHub self-security entrypoint is deliberately not redirected here.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

import yaml

from lib.portable.contracts import canonical_digest, endpoint, repository_key, valid_id
from lib.consumer_github import AccessFailure
from .operations import SCM
from .transport import encoded

ROOT = Path(__file__).resolve().parents[3]
PROVIDERS = {'github', 'gitlab', 'bitbucket-dc'}
SHA = re.compile(r'(?:[a-f0-9]{40}|[a-f0-9]{64})\Z')


def subject(provider, issuer, native_id, kind):
    if provider not in PROVIDERS or kind not in {'user','bot','group','application'} or not valid_id(native_id):
        raise ValueError('invalid_provider_subject')
    value={'provider':provider,'issuer':endpoint(issuer),'native_id':native_id,'kind':kind}
    return {**value,'subject_key':canonical_digest(value)}


def role_candidate(actor, role_id, scm, revision):
    expected=subject(*(actor[k] for k in ('provider','issuer','native_id','kind')))
    if actor!=expected or actor['provider']!=scm['provider'] or actor['issuer']!=endpoint(scm['instance']):
        raise ValueError('subject_issuer_binding_mismatch')
    if not isinstance(role_id,str) or not re.fullmatch(r'[a-z][a-z0-9-]{1,79}',role_id) or not SHA.fullmatch(revision):
        raise ValueError('invalid_candidate_role_binding')
    return {'schema_version':1,'status':'candidate','subject':actor,'role_id':role_id,
            'repository_key':repository_key(scm),'source_revision':revision,'live_authority':False,
            'personal_consent':False,'operating_acceptance':False}


def check_reader(scm, reader):
    """A configured API path may differ; credentials may never cross issuer origins."""
    repository_key(scm)
    if scm['provider'] not in PROVIDERS:raise ValueError('unsupported_assurance_provider')
    api=urlsplit(reader.base)
    origin=endpoint(api.scheme+'://'+api.netloc)
    permitted=endpoint(scm['instance'])
    if origin!=permitted and not (permitted=='https://github.com' and origin=='https://api.github.com'):
        raise ValueError('assurance_api_issuer_mismatch')
    if api.query or api.fragment or api.username or api.password:raise ValueError('unsafe_assurance_api')


def capture_reviews(scm, reader, change_id, revision):
    """GET-only bounded observations, with exact native commit binding where exposed."""
    check_reader(scm,reader)
    if not SHA.fullmatch(revision) or not valid_id(change_id):raise ValueError('invalid_review_target')
    adapter=SCM(scm,reader);adapter.check_identity();provider=scm['provider']
    route=adapter.route+('/merge_requests/' if provider=='gitlab' else '/pull-requests/' if provider=='bitbucket-dc' else '/pulls/')+encoded(change_id)
    before=reader.get(route);normalized=adapter.normalize(before)
    if normalized['id']!=change_id or normalized['sha']!=revision:raise ValueError('review_revision_changed')
    rows=[]
    if provider=='github':
        for item in reader.pages(route+'/reviews',limit=10):
            if len(rows)>=1000:raise ValueError('review_capture_limit')
            user=item['user'];kind='bot' if user.get('type')=='Bot' else 'user' if user.get('type')=='User' else 'application'
            rows.append({'subject':subject(provider,scm['instance'],str(user['id']),kind),
                'native_review_id':str(item['id']),'native_state':item['state'],
                'revision_bound':item.get('commit_id')==revision})
    elif provider=='gitlab':
        approval=reader.get(route+'/approvals')
        for item in approval.get('approved_by',[]):
            if len(rows)>=1000:raise ValueError('review_capture_limit')
            user=item['user']
            # This response does not establish which SHA the approval was made on.
            rows.append({'subject':subject(provider,scm['instance'],str(user['id']),'bot' if user.get('bot') is True else 'user'),
                'native_review_id':None,'native_state':'APPROVED','revision_bound':False})
    else:
        for item in before.get('reviewers',[]):
            if len(rows)>=1000:raise ValueError('review_capture_limit')
            user=item['user']
            rows.append({'subject':subject(provider,scm['instance'],str(user['id']),'user' if user.get('type')=='NORMAL' else 'application'),
                'native_review_id':None,'native_state':item.get('status','UNKNOWN'),
                'revision_bound':item.get('lastReviewedCommit')==revision})
    after=adapter.normalize(reader.get(route))
    if (after['sha'],after['state'])!=(normalized['sha'],normalized['state']):raise ValueError('review_changed_during_capture')
    # Latest event per actor only. Dismissals/changes requested cannot inherit a prior approval.
    latest={row['subject']['subject_key']:row for row in rows}
    observed=sum(row['revision_bound'] and row['native_state']=='APPROVED' for row in latest.values())
    return {'schema_version':1,'status':'candidate','repository_key':repository_key(scm),'revision':revision,
        'change_id':change_id,'observations':rows,'latest_bound_approval_participants':observed,
        'role_approval':False,'personal_consent':False,'operating_acceptance':False,'live_authority':False}


def legacy_module():
    spec=importlib.util.spec_from_file_location('axiom_private_github_security',ROOT/'scripts/assess_governance_repository_security.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def capture_security(scm,reader,revision,observed_at):
    """Preserve the approved criterion meanings; absent evidence never becomes pass."""
    check_reader(scm,reader)
    if not SHA.fullmatch(revision):raise ValueError('invalid_security_revision')
    adapter=SCM(scm,reader);adapter.check_identity();metadata=reader.get(adapter.route)
    definitions=yaml.safe_load((ROOT/'model/controls/governance-repository-security.yaml').read_text())
    values={};errors=[];related={};provider=scm['provider']
    if provider=='github':
        # Local static facts only describe THIS installed source. Never execute a fetched checkout.
        installed=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        clean=not subprocess.check_output(['git','status','--porcelain=v1','-z','--untracked-files=all','--',
                                          '.github','scripts','model/controls','releases'],cwd=ROOT)
        default=metadata.get('default_branch')
        if not clean or installed!=revision or default!='main' or adapter.branch_sha('main')!=revision:
            errors.append('installed_source_or_legacy_main_profile_mismatch')
        else:
            module=legacy_module()  # private module state; accepted module/globals stay unchanged
            def get(path):
                try:return reader.get('/'+path),None
                except AccessFailure as error:return None,str(error)
            module.gh_api=get
            observation=module.collect_live(scm['path'],observed_at)
            errors.extend(observation['api_errors'])
            if not errors:values=module.observed_values(observation)
    elif provider=='gitlab':
        default=metadata.get('default_branch')
        if isinstance(default,str) and default:
            branch=reader.get(adapter.route+'/repository/branches/'+encoded(default))
            if branch.get('name')!=default or branch.get('commit',{}).get('id')!=revision:
                raise ValueError('security_default_branch_revision_mismatch')
            if type(branch.get('protected')) is bool:values['default_branch_protected']=branch['protected']
        related={'pipeline_success_merge_setting':metadata.get('only_allow_merge_if_pipeline_succeeds'),
                 'all_discussions_resolved_setting':metadata.get('only_allow_merge_if_all_discussions_are_resolved')}
    else:
        default=reader.get(adapter.route+'/default-branch')
        if default.get('latestCommit')!=revision:raise ValueError('security_default_branch_revision_mismatch')
        related={'default_branch_observed':True}
        # Permission/merge-check plugins and editions require explicit equivalence acceptance.
    criteria=[]
    for definition in definitions['criteria']:
        value=values.get(definition['key'])
        available=type(value) is bool
        criteria.append({**definition,'observed':value if available else None,
            'capability':'available' if available else 'unavailable' if errors or provider=='github' else 'requires_equivalence_review',
            'status':'pass' if available and value==definition['expected'] else 'fail' if available else 'not_proven'})
    return {'schema_version':1,'status':'candidate','repository_key':repository_key(scm),'revision':revision,
        'observed_at':observed_at,'profile_id':definitions['profile_id'],'profile_version':definitions['version'],
        'profile_sha256':canonical_digest(definitions),'criteria':criteria,'related_native_capabilities':related,
        'observation_errors':errors,'live_authority':False,'official_acceptance':False,'blocks_merge':None}
