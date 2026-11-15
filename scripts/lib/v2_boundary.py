"""Enforce the reviewed V2 core/provider split without executing inspected code."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re

PROVIDER_WORDS={'github','github-actions','gitlab','gitlab-ci','bamboo','bitbucket-dc'}
NETWORK_IMPORTS=('urllib.request','urllib.error','http.client','requests','httpx','aiohttp',
                 'github','gitlab','atlassian','boto3')
LEGACY_IMPORTS=('lib.consumer_github','lib.consumer_intake','lib.consumer_publisher',
                'lib.governance_lifecycle','lib.portable.adapters','lib.portable_intake.operations',
                'lib.portable_intake.transport','lib.portable_intake.assurance')


def safe_source(root, name):
    path=Path(name)
    if (not isinstance(name,str) or path.is_absolute() or '..' in path.parts
            or str(path)!=name or '\\' in name or ':' in name):
        raise ValueError('invalid_v2_boundary_path')
    source=root/path
    if (source.is_symlink() or not source.resolve().is_relative_to(root)
            or any((root.joinpath(*path.parts[:i])).is_symlink() for i in range(1,len(path.parts)))):
        raise ValueError('unsafe_v2_boundary_source')
    return source


def imports(tree, source_name=None):
    package=source_name.removeprefix('scripts/').removesuffix('.py').split('/')[:-1] if source_name else []
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for alias in node.names:yield alias.name
        elif isinstance(node,ast.ImportFrom):
            prefix='.'.join(package[:len(package)-node.level+1]) if node.level and source_name else ''
            module='.'.join(filter(None,(prefix,node.module)))
            yield module
            for alias in node.names:
                if alias.name!='*':yield module+'.'+alias.name


def local_dependencies(root, name):
    """Include package initializers and imports inside functions as well."""
    tree=ast.parse((root/name).read_text(),filename=name)
    found=set()
    for module in imports(tree,name):
        parts=module.split('.')
        candidates=['scripts/'+module.replace('.','/')+'.py']
        candidates.extend('scripts/'+'/'.join(parts[:i])+'/__init__.py' for i in range(1,len(parts)+1))
        for candidate in candidates:
            if safe_source(root,candidate).is_file():found.add(candidate)
    return found


def violations(name, source, *, pattern_definitions=False):
    """No provider access, environment mapping, SDK or old client in neutral code."""
    tree=ast.parse(source,filename=name)
    findings=[]
    for module in imports(tree,name):
        if any(module==p or module.startswith(p+'.') for p in (*NETWORK_IMPORTS,*LEGACY_IMPORTS,'lib.providers')):
            findings.append({'path':name,'code':'provider_import_in_core','detail':module})
    docstrings={id(node.value) for parent in ast.walk(tree) if isinstance(parent,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))
                for node in parent.body[:1] if isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant)}
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in ('__import__','eval','exec'):
            findings.append({'path':name,'line':node.lineno,'code':'dynamic_execution_in_core'})
        if pattern_definitions:continue
        if not isinstance(node,ast.Constant) or not isinstance(node.value,str) or id(node) in docstrings:continue
        value=node.value
        if (value in PROVIDER_WORDS or value in ('gh','curl','wget') or value.startswith(('gh ','GITHUB_','GITLAB_','bamboo_','CI_'))
                or re.search(r'https?://(?:api\.)?(?:github\.com|gitlab\.com|bitbucket\.org)',value)
                or value.startswith(('/repos/','/projects/','/rest/api/','/rest/branch-permissions/'))):
            findings.append({'path':name,'line':node.lineno,'code':'provider_literal_in_core','detail':value[:100]})
    return findings


def validate_boundaries(root):
    root=Path(root).resolve()
    policy=json.loads((root/'config/axiom-v2-boundaries.json').read_text())
    if (set(policy)!={'schema_version','core_files','composition','adapters','compatibility_facades','browser_core','verification'}
            or policy['schema_version']!=2 or not policy['core_files'] or not policy['composition']):
        raise ValueError('invalid_v2_boundary_contract')
    groups=[policy[k] for k in ('core_files','composition','compatibility_facades','browser_core','verification')]
    names=[name for group in groups for name in group]
    if len(names)!=len(set(names)):raise ValueError('overlapping_v2_boundaries')
    for name in names:
        if not safe_source(root,name).is_file():raise ValueError('missing_v2_boundary_source')
    adapter=safe_source(root,policy['adapters'])
    if not adapter.is_dir():raise ValueError('missing_v2_provider_adapters')
    findings=[]
    visited=set();pending=list(policy['core_files'])
    while pending:
        name=pending.pop()
        if name in visited or name in policy['composition'] or name.startswith(policy['adapters']+'/'):continue
        visited.add(name)
        findings.extend(violations(name,safe_source(root,name).read_text(),pattern_definitions=name in policy['verification']))
        pending.extend(local_dependencies(root,name))
    # Import facades may alias only an adapter module. No hidden old implementation.
    for name in policy['compatibility_facades']:
        tree=ast.parse((root/name).read_text())
        if any(module!='sys' and module!='lib.providers' and not module.startswith('lib.providers.') for module in imports(tree)):
            findings.append({'path':name,'code':'implementation_in_compatibility_facade'})
        if any(isinstance(node,(ast.FunctionDef,ast.ClassDef,ast.AsyncFunctionDef)) for node in ast.walk(tree)):
            findings.append({'path':name,'code':'implementation_in_compatibility_facade'})
    for name in policy['browser_core']:
        source=(root/name).read_text()
        if re.search(r'github(?:\\?\.)com|api\.github|GITHUB_',source,re.I):
            findings.append({'path':name,'code':'provider_host_in_browser_core'})
    return {'schema_version':2,'core_files_checked':len(visited),'core_closure':sorted(visited),
            'adapter_files':len(list(adapter.glob('*.py'))),'findings':findings,'passed':not findings}
