"""Source-bound completeness audit. Mapping and declared evidence are not authority."""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

from jsonschema import Draft202012Validator, ValidationError
from lib.attestation_files import parent as held_parent
from lib.portable.contracts import ROOT
from lib.portable.runtime import read_json, source_digest
from lib.result_bytes import strict_json
from lib.v2_boundary import safe_source

V1_REFERENCE='6b557fefe295b58272d2271326576ca3a3687197'
PACKAGED_EVIDENCE='config/axiom-v2-parity-evidence'
MAX_RECEIPT=2*1024**2
MAX_MATRIX=4*1024**2
PUBLIC_FIELDS={'evidence_kind','v1_reference','evidence_sources','authority_transferred',
               'independent_human_approval','official_acceptance','production_approval'}


def git_read(root, *args):
    env={**os.environ,'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1',
         'GIT_CONFIG_COUNT':'0','GIT_TERMINAL_PROMPT':'0','GIT_ASKPASS':'/bin/false',
         'GIT_NO_REPLACE_OBJECTS':'1','GIT_NO_LAZY_FETCH':'1','GIT_ALLOW_PROTOCOL':''}
    for key in list(env):
        if key in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_CONFIG_PARAMETERS','GIT_TEMPLATE_DIR') or key.startswith('GIT_TRACE'):
            env.pop(key)
    result=subprocess.run(['git','-c','safe.directory='+str(Path(root).resolve()),
        '-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','protocol.allow=never',*args],
        cwd=root,env=env,capture_output=True,timeout=120)
    if result.returncode:raise ValueError('v1_reference_not_available')
    return result.stdout


def inventory(reference):
    """Parse frozen source only; never import or execute V1 code."""
    entries=[];workflows=[]
    for raw in git_read(reference,'ls-tree','-r','-z',V1_REFERENCE).split(b'\0'):
        if not raw:continue
        meta,name=raw.split(b'\t',1);mode,kind,blob=meta.decode().split();name=name.decode()
        script=name.startswith('scripts/') and (name.endswith('.sh') or
            (name.count('/')==1 and name.endswith('.py')) or
            (name.startswith('scripts/publishing/') and name.endswith(('.mjs','.py'))))
        workflow=name.startswith('.github/workflows/') and name.endswith(('.yaml','.yml'))
        if not script and not workflow:continue
        if kind!='blob' or mode not in ('100644','100755'):raise ValueError('unsupported_v1_scope_entry')
        source=git_read(reference,'cat-file','blob',blob)
        row={'v1_path':name,'v1_git_blob':blob,'v1_sha256':hashlib.sha256(source).hexdigest(),'mode':mode}
        if script:
            symbols=[];options=[];actions=[]
            if name.endswith('.py'):
                tree=ast.parse(source)
                symbols=sorted(n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)))
                for node in ast.walk(tree):
                    if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in ('add_argument','add_parser'):
                        strings=[a.value for a in node.args if isinstance(a,ast.Constant) and isinstance(a.value,str)]
                        (options if node.func.attr=='add_argument' else actions).extend(strings)
            row.update(declared_symbols=symbols,cli_options=sorted(set(options)),declared_actions=sorted(set(actions)))
        (entries if script else workflows).append(row)
    catalogue=git_read(reference,'show',V1_REFERENCE+':docs/operations/guides/repository-function-catalog.md').decode()
    areas=[{'id':f'FP-{int(n):02}','title':title} for n,title in re.findall(r'^## (\d+)\. (.+)$',catalogue,re.M)]
    return entries,workflows,areas


def require_frozen_scope(matrix, reference):
    entries,workflows,areas=inventory(reference)
    for key,actual in (('entrypoints',entries),('ci_workflows',workflows),('areas',areas)):
        identity='id' if key=='areas' else 'v1_path'
        records=matrix[key]
        if len({r[identity] for r in records})!=len(records):raise ValueError('duplicate_functional_parity_subject')
        expected={r[identity]:r for r in actual}
        if {r[identity] for r in records}!=set(expected):raise ValueError('functional_parity_scope_changed')
        for row in records:
            if any(row[k]!=v for k,v in expected[row[identity]].items()):raise ValueError('functional_parity_reference_changed')


def metadata_bytes(root,name,limit):
    """Hold a canonical directory and bounded ordinary metadata file."""
    if not name or Path(name).name!=name or name in ('.','..') or '\\' in name or any(ord(c)<32 for c in name):
        raise ValueError('unsafe_functional_parity_metadata_name')
    requested=Path(root)
    if requested.is_symlink():raise ValueError('unsafe_functional_parity_evidence')
    root=requested.resolve()
    try:parent=held_parent(root/name)
    except OSError:raise ValueError('functional_parity_evidence_missing_or_unsafe') from None
    if parent is None:raise ValueError('functional_parity_evidence_missing')
    try:
        directory=os.fstat(parent)
        fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        try:
            before=os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>limit:
                raise ValueError('functional_parity_evidence_regular_bounded_file_required')
            raw=bytearray()
            while chunk:=os.read(fd,min(65536,limit+1-len(raw))):
                raw.extend(chunk)
                if len(raw)>limit:raise ValueError('functional_parity_evidence_byte_budget')
            after=os.fstat(fd);entry=os.stat(name,dir_fd=parent,follow_symlinks=False)
            fields=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode','st_nlink')
            if any(getattr(before,k)!=getattr(row,k) for row in (after,entry) for k in fields):
                raise ValueError('functional_parity_evidence_changed_during_read')
            current=os.stat(root,follow_symlinks=False)
            if not stat.S_ISDIR(current.st_mode) or (current.st_dev,current.st_ino)!=(directory.st_dev,directory.st_ino):
                raise ValueError('functional_parity_evidence_directory_changed')
            return bytes(raw)
        finally:os.close(fd)
    except OSError:raise ValueError('functional_parity_evidence_missing_or_unsafe') from None
    finally:os.close(parent)


def receipt_bytes(root,name):return metadata_bytes(root,name,MAX_RECEIPT)


def evidence_checked(ref,subject,root,*,runtime=None,public=False,original=None,implementation=None):
    if root is None:raise ValueError('functional_parity_evidence_required')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,100}',ref['id']):raise ValueError('unsafe_functional_parity_evidence_id')
    data=receipt_bytes(root,ref['id']+'.json')
    if hashlib.sha256(data).hexdigest()!=ref['sha256']:raise ValueError('functional_parity_evidence_digest_changed')
    receipt=strict_json(data)
    try:Draft202012Validator(read_json(ROOT/'schemas/axiom-v2-parity-receipt.schema.json')).validate(receipt)
    except ValidationError:raise ValueError('invalid_functional_parity_evidence_metadata') from None
    if (receipt.get('schema_version')!=1 or receipt.get('subject')!=subject or receipt.get('kind')!=ref['kind']
            or receipt.get('passed') is not True or receipt.get('runtime_source_digest')!=(runtime or source_digest())):
        raise ValueError('functional_parity_evidence_binding_failed')
    expected={key:value for key,value in (('original_source_sha256',original),('implementation_source_sha256',implementation)) if value is not None}
    if public and not (PUBLIC_FIELDS|set(expected))<=set(receipt):raise ValueError('functional_parity_public_metadata_required')
    if any(key in receipt and receipt[key]!=value for key,value in expected.items()):raise ValueError('functional_parity_evidence_source_changed')
    return receipt


def implementation_checked(root,identity):
    path,separator,symbol=identity.partition(':')
    target=safe_source(root,path)
    if not target.is_file():raise ValueError('functional_parity_implementation_missing')
    if target.suffix=='.py':
        installed=read_json(root/'config/axiom-v2-distribution.json')['python_files']
        if path not in installed:raise ValueError('functional_parity_implementation_not_installed')
        if separator and symbol not in {n.name for n in ast.walk(ast.parse(target.read_text()))
                                        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}:
            raise ValueError('functional_parity_symbol_missing')
    else:
        from lib.v2_source import selected_paths
        if path not in selected_paths(root):raise ValueError('functional_parity_implementation_not_installed')
    return hashlib.sha256(target.read_bytes()).hexdigest()


def audit(root, *, reference=None, evidence_root=None):
    root=Path(root).resolve()
    raw=metadata_bytes(root/'config','axiom-v2-functional-parity.json',MAX_MATRIX)
    matrix=strict_json(raw)
    try:Draft202012Validator(read_json(root/'schemas/axiom-v2-functional-parity.schema.json')).validate(matrix)
    except ValidationError:raise ValueError('invalid_functional_parity_matrix') from None
    if {a['id'] for a in matrix['areas']}!={f'FP-{n:02}' for n in range(1,23)}:
        raise ValueError('functional_parity_area_scope_changed')
    runtime=source_digest();receipt_count=0
    selected_evidence=root/PACKAGED_EVIDENCE if evidence_root is None else evidence_root
    source_verified=False
    if reference is not None:
        require_frozen_scope(matrix,reference);source_verified=True
    groups={name:matrix[name] for name in ('areas','entrypoints','ci_workflows','operating_workflows')}
    for name,rows in groups.items():
        identities=[r.get('id',r.get('v1_path')) for r in rows]
        if len(identities)!=len(set(identities)):raise ValueError('duplicate_functional_parity_subject')
        for row in rows:
            if row['state']!='verified':continue
            if name=='areas':
                if any(not row[key] for key in ('v2_capabilities','positive_tests','negative_tests','installed_evidence','comparison_evidence')):
                    raise ValueError('functional_parity_area_evidence_incomplete')
                # An area cannot pass while an executable or operating counterpart remains pending.
                if any(r['state']!='verified' for key in ('entrypoints','ci_workflows','operating_workflows') for r in groups[key]):
                    raise ValueError('functional_parity_area_has_unverified_execution')
            else:
                if name!='operating_workflows' and not row['v2_implementation']:
                    raise ValueError('functional_parity_implementation_missing')
                implementation=implementation_checked(root,row['v2_implementation']) if name!='operating_workflows' else None
                kinds={r['kind'] for r in row['evidence']}
                if not {'positive','negative','installed'}<=kinds:
                    raise ValueError('functional_parity_execution_evidence_incomplete')
                for ref in row['evidence']:
                    evidence_checked(ref,row.get('id',row.get('v1_path')),selected_evidence,runtime=runtime,
                        public=evidence_root is None,original=row.get('v1_sha256'),implementation=implementation)
                    receipt_count+=1
    if source_digest()!=runtime:raise ValueError('functional_parity_program_changed')
    counts={key:dict(Counter(r['state'] for r in rows)) for key,rows in groups.items()}
    complete=source_verified and all(row['state']=='verified' for rows in groups.values() for row in rows)
    return {'schema_version':1,'goal_id':matrix['goal_id'],'v1_reference':matrix['v1_reference'],
        'matrix_sha256':hashlib.sha256(raw).hexdigest(),
        'source_scope_verified':source_verified,'scope_counts':{k:len(v) for k,v in groups.items()},
        'states':counts,'functional_parity_complete':complete,'authority_transferred':False,
        'runtime_source_digest':runtime,'evidence_receipts_checked':receipt_count,
        'evidence_directory_source':'packaged' if evidence_root is None else 'operator',
        'evidence_assertions_independently_authenticated':False,
        'evidence_kind':'declared_technical_parity_evidence',
        'remaining':[r.get('id',r.get('v1_path')) for rows in groups.values() for r in rows if r['state']!='verified']}
