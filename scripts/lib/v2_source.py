"""Reviewed active V2 file set, shared by sparse installations and drift checks."""
from pathlib import Path
import hashlib
import json

from lib.v2_boundary import safe_source


def selected_paths(root):
    root=Path(root).resolve()
    policy=json.loads(safe_source(root,'config/axiom-v2-distribution.json').read_text())
    if (set(policy)!={'schema_version','python_files','data_roots','data_files','retired_entrypoints'}
            or policy['schema_version']!=2 or not policy['python_files']):
        raise ValueError('invalid_v2_distribution_contract')
    paths=set(policy['python_files'])|set(policy['data_files'])
    if len(policy['python_files'])!=len(set(policy['python_files'])):
        raise ValueError('duplicate_v2_distribution_path')
    for directory in policy['data_roots']:
        target=safe_source(root,directory)
        if not target.is_dir():raise ValueError('missing_v2_distribution_data')
        for path in target.rglob('*'):
            if '__pycache__' in path.parts or path.name=='.DS_Store' or path.suffix=='.pyc':continue
            if path.is_symlink():raise ValueError('unsafe_v2_distribution_data')
            if path.is_file():paths.add(str(path.relative_to(root)))
    for name in paths:
        if not safe_source(root,name).is_file():raise ValueError('missing_v2_distribution_file')
    if paths&set(policy['retired_entrypoints']):raise ValueError('retired_v1_path_in_v2_distribution')
    return sorted(paths)


def active_fingerprints(root):
    prefixes=('scripts/','schemas/','model/','policies/','architecture/','releases/',
              'pipeline-baseline/','config/','infra/','.github/','.agents/',
              'docs/governance/source-documents/','docs/foundation/',
              'tests/fixtures/document-consistency-review-')
    return {name:hashlib.sha256(safe_source(Path(root).resolve(),name).read_bytes()).hexdigest()
            for name in selected_paths(root) if name.startswith(prefixes) or name.startswith('requirements')}


def verify_active_scripts(root):
    root=Path(root).resolve();selected=set(selected_paths(root))
    actual={str(p.relative_to(root)) for p in (root/'scripts').rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    expected={p for p in selected if p.startswith('scripts/')}
    if actual!=expected:raise ValueError('undeclared_v2_runtime_file')
