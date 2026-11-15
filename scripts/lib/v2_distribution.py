"""Offline exact-source admission followed by a reviewed sparse V2 installation."""
from pathlib import Path
import hashlib
import json

from lib.runtime_package import admit, prepare_environment, git, text_json
from lib.v2_source import selected_paths, active_fingerprints, verify_active_scripts
from lib.v2_boundary import validate_boundaries


def restrict_source(source):
    source=Path(source).resolve()
    if git(source,'status','--porcelain','--untracked-files=all').strip():
        raise ValueError('clean_admitted_source_required')
    names=selected_paths(source)
    tracked=set(git(source,'ls-files','-z').decode().strip('\0').split('\0'))
    if not set(names)<=tracked:raise ValueError('untracked_v2_distribution_dependency')
    if any(any(c in name for c in ('*','?','[',']','!','#','\n','\r')) for name in names):
        raise ValueError('unsafe_v2_sparse_pattern')
    fingerprints=active_fingerprints(source)
    git(source,'sparse-checkout','set','--no-cone','--stdin',input=('\n'.join('/'+n for n in names)+'\n').encode())
    if active_fingerprints(source)!=fingerprints:raise ValueError('v2_sparse_content_changed')
    if git(source,'status','--porcelain','--untracked-files=all').strip():raise ValueError('v2_sparse_source_dirty')
    verify_source(source)
    return fingerprints


def verify_source(source):
    source=Path(source).resolve();verify_active_scripts(source)
    if not validate_boundaries(source)['passed']:raise ValueError('v2_architecture_boundary_failed')


def install(package,sha256,destination,python,*,port=8875):
    """Fresh private prefix only; never touches an existing service, key or state."""
    destination=Path(destination)
    if destination.exists() or destination.is_symlink():raise ValueError('fresh_v2_installation_required')
    # Reject symlink ancestors before creating a private prefix.
    if any(p.is_symlink() for p in destination.absolute().parents):raise ValueError('unsafe_v2_installation_path')
    destination.mkdir(mode=0o700,parents=True,exist_ok=False)
    destination=destination.resolve()
    manifest=admit(package,sha256,destination/'package')
    if manifest['locks']!=['requirements-validation.lock','requirements-source-document-intake.lock']:
        raise ValueError('v2_workbench_dependencies_required')
    prepare_environment(destination/'package',destination/'venv',python,package=package,expected_sha256=sha256)
    source=destination/'package/source'
    fingerprints=restrict_source(source)
    # Invoke the admitted revision with its own offline environment, not installer imports.
    import subprocess
    result=subprocess.run([str(destination/'venv/bin/python'),str(source/'scripts/axiom_v2.py'),
        '--instance',str(destination/'instance'),'init','--opa',str(destination/'venv/bin/opa'),'--port',str(port)],
        capture_output=True,timeout=120)
    if result.returncode:raise ValueError('admitted_v2_instance_initialization_failed')
    receipt={'schema_version':2,'product':'axiom-v2','source_commit':manifest['source_commit'],
             'source_tree':manifest['source_tree'],'package_sha256':sha256,'mode':'paused',
             'active_files':len(fingerprints),'active_digest':hashlib.sha256(text_json(fingerprints).encode()).hexdigest(),
             'isolated_environment':True,'services_started':False}
    receipt_path=destination/'installation.json';receipt_path.write_text(text_json(receipt));receipt_path.chmod(0o600)
    launcher=destination/'axiom-v2'
    # All variable paths are derived from this file, with no interpolated shell strings.
    launcher.write_text('#!/bin/sh\nset -eu\nAXIOM_V2_PREFIX=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        'exec "$AXIOM_V2_PREFIX/venv/bin/python" "$AXIOM_V2_PREFIX/package/source/scripts/axiom_v2.py" '
        '--instance "$AXIOM_V2_PREFIX/instance" "$@"\n')
    launcher.chmod(0o700)
    return receipt
