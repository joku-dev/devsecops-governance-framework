"""Actual bounded committed Git observations; no target checkout/program execution."""
import hashlib
from pathlib import Path
import re
from lib.review_git import git
from lib.review_planning import canonical_paths, contracts, routing_reasons

SHA=re.compile(r'(?:[a-f0-9]{40}|[a-f0-9]{64})')
MAX_TREE_ENTRIES=10000


def exact_commit(root, value):
    if not isinstance(value,str) or not SHA.fullmatch(value):raise ValueError('review_exact_committed_revision_required')
    if git(root,'rev-parse','--verify','--end-of-options',value+'^{commit}').decode().strip()!=value:raise ValueError('review_exact_committed_revision_required')
    return value


def tree_rows(raw):
    if not isinstance(raw,bytes) or raw and not raw.endswith(b'\0'):raise ValueError('invalid_review_committed_tree')
    if raw and any(not entry for entry in raw.split(b'\0')[:-1]):raise ValueError('invalid_review_committed_tree')
    entries=raw.split(b'\0');rows={}
    if len(entries)>MAX_TREE_ENTRIES+1:raise ValueError('review_committed_tree_entry_budget')
    for entry in filter(None,entries):
        header,name=entry.split(b'\t',1);mode,kind,blob=header.decode().split();name=name.decode('utf-8')
        canonical_paths([name])
        if name in rows or not SHA.fullmatch(blob):raise ValueError('invalid_review_committed_tree')
        rows[name]={'mode':mode,'kind':kind,'blob':blob}
    return rows


def scope_paths(raw):
    if not isinstance(raw,bytes) or raw and not raw.endswith(b'\0'):raise ValueError('invalid_review_committed_scope')
    if raw and any(not entry for entry in raw.split(b'\0')[:-1]):raise ValueError('invalid_review_committed_scope')
    paths=sorted(p.decode('utf-8') for p in raw.split(b'\0') if p);canonical_paths(paths)
    return paths


def snapshot(root, revision, profile):
    listing=git(root,'ls-tree','-r','-z',revision,'--',*profile['roots']);rows=tree_rows(listing)
    selected={name:row for name,row in rows.items() if any(re.fullmatch(pattern,name) for pattern in profile['patterns'])}
    if len(selected)>profile['max_files']:raise ValueError('review_committed_contract_count_budget')
    raw={};files={}
    for name,row in sorted(selected.items()):
        if row['mode'] not in ('100644','100755') or row['kind']!='blob':raise ValueError('review_committed_regular_contract_required')
        size=int(git(root,'cat-file','-s',row['blob']).decode())
        if not 0<=size<=profile['max_file_bytes']:raise ValueError('review_committed_contract_byte_budget')
        value=git(root,'cat-file','blob',row['blob'],limit=profile['max_file_bytes'])
        algorithm=hashlib.sha1 if len(row['blob'])==40 else hashlib.sha256
        if len(value)!=size or algorithm(b'blob '+str(len(value)).encode()+b'\0'+value,usedforsecurity=False).hexdigest()!=row['blob']:raise ValueError('review_committed_blob_integrity_changed')
        raw[name]=value;files[name]={**row,'bytes':size,'sha256':hashlib.sha256(value).hexdigest()}
    # V1's committed PR observer requires roles/skills/routing, not an execution protocol.
    roles,routing,_=contracts(raw,require_protocol=False)
    return {'tree':git(root,'rev-parse',revision+'^{tree}').decode().strip(),'files':files},raw,listing


def selection(raw, paths):
    roles,routing,_=contracts(raw,require_protocol=False);selected=routing_reasons(paths,routing)
    return {'roles':sorted(set(selected)-{'repo-steward'})+(['repo-steward'] if selected else []),
        'validations':sorted({command for role in selected for command in roles[role]['validations']})}


def subject(facts, raw, profile):
    if not isinstance(facts,dict) or set(facts)!={'schema_version','target_commit','head_commit','merge_base_commit','changed_paths','target','proposed'} or type(facts['schema_version']) is not int or facts['schema_version']!=1:raise ValueError('invalid_review_committed_facts')
    for name in ('target_commit','head_commit','merge_base_commit'):
        if not isinstance(facts[name],str) or not SHA.fullmatch(facts[name]):raise ValueError('invalid_review_committed_revision')
    if len({len(facts[name]) for name in ('target_commit','head_commit','merge_base_commit')})!=1:raise ValueError('review_committed_object_format_mismatch')
    if any(not isinstance(facts[side],dict) or set(facts[side])!={'tree','files'} or not isinstance(facts[side]['files'],dict) for side in ('target','proposed')):raise ValueError('invalid_review_committed_snapshot')
    if set(raw)!={'scope.bin','target-tree.bin','proposed-tree.bin'}|{side+'/'+name for side in ('target','proposed') for name in facts[side]['files']}:raise ValueError('review_committed_input_members_changed')
    paths=scope_paths(raw['scope.bin'])
    if paths!=facts['changed_paths']:raise ValueError('review_committed_scope_changed')
    result={key:facts[key] for key in ('target_commit','head_commit','merge_base_commit','changed_paths')}
    for side in ('target','proposed'):
        snapshot=facts[side]
        if not isinstance(snapshot['tree'],str) or not SHA.fullmatch(snapshot['tree']) or len(snapshot['tree'])!=len(facts['head_commit']):raise ValueError('invalid_review_committed_snapshot')
        rows=tree_rows(raw[side+'-tree.bin']);selected={name:row for name,row in rows.items() if any(re.fullmatch(pattern,name) for pattern in profile['patterns'])}
        if set(selected)!=set(snapshot['files']) or len(selected)>profile['max_files']:raise ValueError('review_committed_contract_members_changed')
        contracts_raw={}
        for name,row in snapshot['files'].items():
            if not isinstance(row,dict) or set(row)!={'mode','kind','blob','bytes','sha256'} or type(row['bytes']) is not int or not 0<=row['bytes']<=profile['max_file_bytes']:raise ValueError('invalid_review_committed_file_record')
            value=raw[side+'/'+name]
            if row!=dict(selected[name],bytes=len(value),sha256=hashlib.sha256(value).hexdigest()) or row['mode'] not in ('100644','100755') or row['kind']!='blob' or len(value)>profile['max_file_bytes']:raise ValueError('review_committed_contract_bytes_changed')
            if len(row['blob'])!=len(facts['head_commit']):raise ValueError('review_committed_object_format_mismatch')
            algorithm=hashlib.sha1 if len(row['blob'])==40 else hashlib.sha256
            if algorithm(b'blob '+str(len(value)).encode()+b'\0'+value,usedforsecurity=False).hexdigest()!=row['blob']:raise ValueError('review_committed_blob_integrity_changed')
            contracts_raw[name]=value
        result[side]=selection(contracts_raw,paths)
    return result


def observe(repository, base, head, profile):
    root=Path(repository).resolve()
    if Path(git(root,'rev-parse','--show-toplevel').decode().strip()).resolve()!=root:raise ValueError('review_repository_root_required')
    exact_commit(root,base);exact_commit(root,head)
    ancestor=git(root,'merge-base',base,head).decode().strip()
    diff=git(root,'diff','--name-only','--no-renames','--no-ext-diff','--no-textconv','--no-relative','-z',ancestor,head)
    paths=scope_paths(diff)
    facts={'schema_version':1,'target_commit':base,'head_commit':head,'merge_base_commit':ancestor,'changed_paths':paths};raw={'scope.bin':diff}
    for side,revision in [('target',base),('proposed',head)]:
        facts[side],files,listing=snapshot(root,revision,profile);raw[side+'-tree.bin']=listing;raw.update({side+'/'+name:value for name,value in files.items()})
    subject(facts,raw,profile);return facts,raw


def capture(repository, base, head, profile):
    facts,raw=observe(repository,base,head,profile)
    if observe(repository,base,head,profile)!=(facts,raw):raise ValueError('review_committed_target_changed_during_capture')
    return facts,raw
