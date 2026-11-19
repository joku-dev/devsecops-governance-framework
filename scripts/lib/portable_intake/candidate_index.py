"""Bounded read model of declared candidates, never an official latest-result index."""
from __future__ import annotations
import json
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
from lib.portable.contracts import canonical_digest,endpoint,repository_key,valid_id
from .bundle import read_json,timestamp
from .controller import task_key
from lib.provider_ports import run_link,branch,validate_candidate_composition
from .publisher import path_for

ROOT=Path(__file__).resolve().parents[3]


def validate_candidate(document):
    schema=json.loads((ROOT/'schemas/intake-candidate-v1.schema.json').read_text())
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(document)
    scm,ci=document['scm'],document['ci']
    if any(not valid_id(value) for value in (scm['native_id'],scm['path'],ci['run_id'],ci['job_id'])):
        raise ValueError('candidate_identity_missing')
    if endpoint(scm['instance'])!=scm['instance'] or endpoint(ci['instance'])!=ci['instance']:
        raise ValueError('candidate_instance_not_canonical')
    if any(not part or part in ('.','..') or any(ord(c)<33 or c in '\\?#' for c in part) for part in scm['path'].split('/')):
        raise ValueError('candidate_repository_path_invalid')
    validate_candidate_composition(scm['provider'],ci['provider'])
    locator={k:ci[k] for k in ('run_id','job_id','attempt')}
    if repository_key(scm)!=document['repository_key'] or task_key({'scm':scm,'ci':ci},locator)!=document['native_execution_key']:
        raise ValueError('candidate_identity_digest_mismatch')
    if document['run_url']!=run_link({'scm':scm,'ci':ci}):raise ValueError('candidate_run_link_mismatch')
    revision=document['revision'];branch(revision['branch'])
    if revision['mode']=='branch' and (revision['tested']!=revision['source'] or revision['target'] is not None or document['event']=='pull_request'):
        raise ValueError('candidate_revision_context_mismatch')
    if revision['mode']!='branch' and document['event']!='pull_request':raise ValueError('candidate_event_context_mismatch')
    if revision['mode']=='merge-result' and (revision['target'] is None or revision['tested'] in (revision['source'],revision['target'])):
        raise ValueError('candidate_merge_revision_incomplete')
    timestamp(document['generated_at'])
    return document


def build_index(root,*,limit=50000,byte_limit=128*1024**2):
    root=Path(root).resolve();source=root/'status/portable/v2/candidates'
    def documents():
        total=0;count=0
        if any(path.is_symlink() for path in (root/'status',root/'status/portable',root/'status/portable/v2',source)) or not source.resolve().is_relative_to(root):
            raise ValueError('candidate_source_symlink')
        for visited,path in enumerate(source.rglob('*') if source.exists() else [],start=1):
            if visited>3*limit+4:raise ValueError('candidate_index_budget_exceeded')
            if path.is_symlink():raise ValueError('candidate_member_symlink')
            if path.is_dir():continue
            count+=1;size=path.stat().st_size;total+=size
            if count>limit or size>65536 or total>byte_limit:raise ValueError('candidate_index_budget_exceeded')
            if path.suffix!='.json':raise ValueError('unexpected_candidate_member')
            yield str(path.relative_to(root)),read_json(path)
    return build_from_documents(documents())


def build_from_documents(documents):
    """Complete original projection from bounded decoded candidate inputs."""
    histories={};latest={};count=0
    for relative,document in documents:
        count+=1
        document=validate_candidate(document)
        if relative!=path_for(document):raise ValueError('candidate_path_identity_mismatch')
        kind='pull_request' if document['event']=='pull_request' else 'manual' if document['event'] in ('manual','schedule','unknown') else 'branch'
        record={'path':relative,'content_digest':canonical_digest(document),'context':kind,
                'mainline_proven':False,'native_verification_performed':False,'candidate':document}
        repo=document['repository_key'];histories.setdefault(repo,[]).append(record)
        # No native PR ID/default-branch proof in the public envelope. Keep PR executions
        # separate; never roll distinct PRs into a fictitious current-main result.
        scope={'repository':repo,'kind':kind,'branch':document['revision']['branch'],
               'execution':document['native_execution_key'] if kind=='pull_request' else None}
        slot=canonical_digest(scope)
        if slot not in latest or (timestamp(document['generated_at']),relative)>(timestamp(latest[slot]['candidate']['generated_at']),latest[slot]['path']):
            latest[slot]=record
    return {'schema_version':1,'classification':'declared_candidate_read_model','official_acceptance':False,
        'blocks_merge':None,'native_verification_performed':False,'candidate_count':count,
        'repositories':{key:sorted(rows,key=lambda r:(timestamp(r['candidate']['generated_at']),r['path'])) for key,rows in sorted(histories.items())},
        'latest_candidate_by_context':dict(sorted(latest.items()))}
