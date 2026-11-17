"""Bounded, explicit physical-directory source observations; never execute inspected code."""
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from lib.providers.source_inspection import (INTEGRATION_CI_PATTERNS, ONBOARDING_CI_PATTERNS,
    ONBOARDING_SURFACE_PATTERNS, SUPPLY_CHAIN_PATTERNS, integration_from_texts)

PROFILES=('legacy-worktree-signatures-v1',)
MAX_NODES=100000;MAX_DEPTH=64;MAX_PATH=4096;MAX_NAMES=8*1024**2
MAX_FILE=16*1024**2;MAX_TEXT=64*1024**2;MAX_FACTS=16*1024**2
KINDS=('integration','onboarding','all')
PRESENCE={'readme_present':'README.md','project_manifest_present':'pyproject.toml',
    'ci_supply_chain_script_present':'scripts/check_factory_ci_supply_chain.py'}


def profile(name):
    if name not in PROFILES:raise ValueError('unknown_local_source_observation_profile')
    return {'kind':'local-worktree-source-signatures-v1','profile':name,'source_signature_only':True,'working_tree_used':True}


def path_name(name):
    if not isinstance(name,str) or not name or name.startswith('/') or '\0' in name or any(p in ('','.','..') for p in name.split('/')):
        raise ValueError('invalid_local_source_path')
    try:length=len(name.encode('utf-8'))
    except UnicodeError:raise ValueError('invalid_local_source_path_encoding') from None
    if length>MAX_PATH or len(name.split('/'))>MAX_DEPTH:raise ValueError('local_source_path_budget')
    return name


@lru_cache(maxsize=128)
def pattern_regex(pattern):
    parts=['^'];index=0
    while index<len(pattern):
        if pattern[index:index+3]=='**/':parts.append('(?:.*/)?');index+=3
        elif pattern[index:index+2]=='**':parts.append('.*');index+=2
        elif pattern[index]=='*':parts.append('[^/]*');index+=1
        elif pattern[index]=='?':parts.append('[^/]');index+=1
        else:parts.append(re.escape(pattern[index]));index+=1
    return re.compile(''.join(parts)+'$',re.DOTALL)


def matches(pattern,name):return bool(pattern_regex(pattern).fullmatch(name))


def directory(root,name=''):
    # Walk every component from the filesystem root without following links.
    path=Path(root).absolute();fd=os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for component in (*path.parts[1:],*filter(None,name.split('/'))):
            following=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=following
        return fd
    except BaseException:
        os.close(fd);raise


def inventory(root,kind):
    counts=[0,0];nodes=[]
    def visit(fd,parent):
        before=os.fstat(fd)
        with os.scandir(fd) as entries:
            for entry in entries:
                name=path_name(parent+'/'+entry.name if parent else entry.name);info=entry.stat(follow_symlinks=False)
                counts[0]+=1;counts[1]+=len(name.encode())
                if counts[0]>MAX_NODES or counts[1]>MAX_NAMES:raise ValueError('local_source_inventory_budget')
                mode=info.st_mode;typ='directory' if stat.S_ISDIR(mode) else 'file' if stat.S_ISREG(mode) else 'symlink' if stat.S_ISLNK(mode) else 'special'
                nodes.append({'path':name,'kind':typ})
                if typ=='directory' and (kind!='integration' or name in ('.github','.github/workflows')):
                    child=os.open(entry.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
                    try:
                        check=os.fstat(child)
                        if (check.st_dev,check.st_ino)!=(info.st_dev,info.st_ino):raise ValueError('local_source_directory_changed')
                        visit(child,name)
                    finally:os.close(child)
        after=os.fstat(fd)
        if any(getattr(before,k)!=getattr(after,k) for k in ('st_dev','st_ino','st_mtime_ns','st_ctime_ns')):raise ValueError('local_source_directory_changed')
    fd=directory(root,'')
    try:visit(fd,'')
    finally:os.close(fd)
    return nodes


def selections(nodes,kind):
    if kind not in KINDS:raise ValueError('unknown_local_source_inspection_kind')
    if not isinstance(nodes,list) or len(nodes)>MAX_NODES:raise ValueError('local_source_inventory_budget')
    seen={};files=[];names=0
    patterns=INTEGRATION_CI_PATTERNS if kind=='integration' else (*INTEGRATION_CI_PATTERNS,*ONBOARDING_CI_PATTERNS,*SUPPLY_CHAIN_PATTERNS,*(p for group in ONBOARDING_SURFACE_PATTERNS.values() for p in group))
    prefixes=[p[:n] for p in patterns for n,c in enumerate(p) if c=='/' and '**' not in p[:n]]
    for row in nodes:
        if not isinstance(row,dict) or set(row)!={'path','kind'}:raise ValueError('invalid_local_source_node')
        name=path_name(row['path']);typ=row['kind'];names+=len(name.encode())
        if names>MAX_NAMES or name in seen or typ not in ('directory','file','symlink','special'):raise ValueError('invalid_local_source_membership')
        parent=name.rpartition('/')[0]
        if parent and seen.get(parent)!='directory':raise ValueError('local_source_parent_membership_changed')
        if kind=='integration' and parent not in ('','.github','.github/workflows'):raise ValueError('local_source_scope_changed')
        if typ=='symlink' and (any(matches(p,name) for p in (*patterns,*prefixes)) or (kind!='integration' and name in PRESENCE.values())):
            raise ValueError('selected_local_source_symlink_forbidden')
        seen[name]=typ
        if typ=='file':files.append(name)
    def selected(patterns):
        values=[];known=set()
        for pattern in patterns:
            for name in files:
                if name not in known and matches(pattern,name):known.add(name);values.append(name)
        return values
    ci=selected(INTEGRATION_CI_PATTERNS)
    if kind=='integration':return ci,None,set(ci)
    surface={key:sorted(selected(patterns),key=lambda p:tuple(p.split('/'))) for key,patterns in ONBOARDING_SURFACE_PATTERNS.items()}
    surface.update({key:name in seen for key,name in PRESENCE.items()})
    surface['supply_chain_artifact_present']=bool(selected(SUPPLY_CHAIN_PATTERNS))
    onboard_ci=sorted(selected(ONBOARDING_CI_PATTERNS),key=lambda p:tuple(p.split('/')))
    return ci,(surface,onboard_ci),set(ci)|set(onboard_ci)|set(surface['security_docs'][:8])


def regular_bytes(root,name):
    path_name(name);parent,_,leaf=name.rpartition('/');fd=directory(root,parent)
    try:source=os.open(leaf,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    finally:os.close(fd)
    try:
        before=os.fstat(source)
        if not stat.S_ISREG(before.st_mode) or before.st_size>MAX_FILE:raise ValueError('local_source_regular_file_budget')
        with os.fdopen(source,'rb',closefd=False) as stream:raw=stream.read(MAX_FILE+1)
        after=os.fstat(source)
        if len(raw)>MAX_FILE or any(getattr(before,k)!=getattr(after,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode')):raise ValueError('local_source_file_changed')
        return raw
    finally:os.close(source)


def validate(observation,texts):
    if not isinstance(observation,dict) or set(observation)!={'schema_version','profile','inspection_kind','nodes','text_files'} or type(observation['schema_version']) is not int or observation['schema_version']!=1:
        raise ValueError('invalid_local_source_observation')
    profile(observation['profile']);ci,surface,expected=selections(observation['nodes'],observation['inspection_kind'])
    if not isinstance(texts,dict) or set(texts)!=expected or not isinstance(observation['text_files'],dict) or set(observation['text_files'])!=expected:raise ValueError('local_source_text_membership_changed')
    total=0
    for name,raw in texts.items():
        row=observation['text_files'][name]
        if not isinstance(raw,bytes) or len(raw)>MAX_FILE:raise ValueError('local_source_text_budget')
        total+=len(raw)
        if total>MAX_TEXT:raise ValueError('local_source_text_budget')
        if not isinstance(row,dict) or set(row)!={'bytes','sha256'} or type(row['bytes']) is not int or row['bytes']!=len(raw) or row['sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('local_source_text_changed')
    if len(json.dumps(observation,ensure_ascii=False,allow_nan=False).encode())>MAX_FACTS:raise ValueError('local_source_facts_budget')
    return ci,surface


def capture(root,kind,profile_name):
    profile(profile_name)
    if kind not in KINDS:raise ValueError('unknown_local_source_inspection_kind')
    root=Path(root).expanduser().absolute()
    if any(p.is_symlink() for p in (root,*root.parents)):raise ValueError('local_source_root_symlink_forbidden')
    if not root.is_dir():raise ValueError('local_source_directory_required')
    nodes=inventory(root,kind);ci,surface,selected=selections(nodes,kind);texts={};total=0
    for name in sorted(selected):
        raw=regular_bytes(root,name);total+=len(raw)
        if total>MAX_TEXT:raise ValueError('local_source_text_budget')
        texts[name]=raw
    if inventory(root,kind)!=nodes:raise ValueError('local_source_changed_during_capture')
    value={'schema_version':1,'profile':profile_name,'inspection_kind':kind,'nodes':nodes,'text_files':{name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in texts.items()}}
    validate(value,texts);return value,texts


def facts(observation,texts,*,product_label,target_label,at):
    ci,surfaces=validate(observation,texts)
    def decoded(name):
        try:return texts[name].decode('utf-8').replace('\r\n','\n').replace('\r','\n')
        except UnicodeDecodeError:return ''
    integration_text=[]
    for name in ci:
        try:integration_text.append((name,texts[name].decode('utf-8').replace('\r\n','\n').replace('\r','\n')))
        except UnicodeDecodeError:pass
    integration=integration_from_texts(ci,integration_text,product_label=product_label,target_label=target_label,at=at)
    if surfaces is None:return {'integration':integration,'surface':None,'onboarding_ci_files':[],'onboarding_ci_text':''}
    surface,onboard_ci=surfaces;surface['secrets_scan_support']='secrets' in '\n'.join(decoded(name).lower() for name in surface['security_docs'][:8])
    return {'integration':integration,'surface':surface,'onboarding_ci_files':onboard_ci,'onboarding_ci_text':'\n'.join(decoded(name) for name in onboard_ci)}
