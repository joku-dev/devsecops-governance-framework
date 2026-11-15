"""Exact tracked source plus optional prepared tools; admission never downloads dependencies."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import platform
import re
import shutil
import subprocess
import tempfile
import zipfile

from lib.safe_archive import safe_extract_zip

MAX_MEMBERS=20000
MAX_MEMBER=256*1024**2
MAX_TOTAL=2*1024**3


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def text_json(value):return json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False)+'\n'


def json_document(data):
    def unique(pairs):
        value={}
        for key,item in pairs:
            if key in value:raise ValueError('duplicate_package_json_key')
            value[key]=item
        return value
    return json.loads(data,object_pairs_hook=unique)


def relative(name):
    path=PurePosixPath(name)
    if (not isinstance(name,str) or not name or str(path)!=name or path.is_absolute() or '..' in path.parts
            or '.git' in path.parts or '\\' in name or ':' in name or any(ord(c)<32 for c in name)):
        raise ValueError('unsafe_package_path')
    return name


def git(root,*args,input=None):
    env={**os.environ,'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1','GIT_TERMINAL_PROMPT':'0',
         'GIT_ASKPASS':'/bin/false','GIT_CONFIG_COUNT':'0'}
    for name in list(env):
        if name in ('GIT_CONFIG_PARAMETERS','GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_TEMPLATE_DIR') or name.startswith('GIT_TRACE'):
            env.pop(name)
    result=subprocess.run(['git','-c','safe.directory='+str(Path(root).resolve()),'-c','core.hooksPath=/dev/null',
        '-c','core.fsmonitor=false','-c','protocol.allow=never',*args],cwd=root,env=env,input=input,capture_output=True,timeout=300)
    if result.returncode:raise ValueError('package_git_operation_failed')
    return result.stdout


def tracked(root,revision):
    if not re.fullmatch('[a-f0-9]{40}',revision):raise ValueError('exact_source_revision_required')
    rows=[]
    for raw in git(root,'ls-tree','-r','-l','-z',revision).split(b'\0'):
        if not raw:continue
        metadata,name=raw.split(b'\t',1);mode,kind,oid,size=metadata.decode().split()
        name=relative(name.decode())
        if (name.split('/')[0] in ('.local','.aws','.ssh') or Path(name).name=='.env'
                or Path(name).suffix in ('.pem','.key') or Path(name).name=='.DS_Store'):
            raise ValueError('tracked_private_file_prevents_exact_package')
        if mode not in ('100644','100755') or kind!='blob':raise ValueError('unsupported_package_git_entry')
        size=int(size)
        if not 0<=size<=MAX_MEMBER:raise ValueError('package_source_member_limit')
        rows.append({'path':name,'mode':mode,'git_blob':oid,'size':size})
    if not rows or len(rows)>MAX_MEMBERS-100 or sum(row['size'] for row in rows)>MAX_TOTAL//2:
        raise ValueError('package_source_limit')
    return rows


def opa_tool(source,system,machine):
    from install_validation_opa import select_tool
    return select_tool(Path(source)/'scripts/validation-toolchain.env',Path(source)/'scripts/opa-download-sources.json',
                       system=system,machine=machine)


def build(root,revision,destination,*,opa=None,wheelhouse=None,system=None,machine=None,workbench=False):
    """The revision, not the working tree, selects source. No release tag is changed."""
    root,destination=Path(root),Path(destination)
    rows=tracked(root,revision);system=system or platform.system();machine=machine or platform.machine()
    if destination.exists() or destination.is_symlink():raise ValueError('fresh_package_destination_required')
    manifest={'schema_version':1,'source_commit':revision,'source_tree':git(root,'rev-parse',revision+'^{tree}').decode().strip(),
        'target':{'system':system,'machine':machine},'files':[],
        'locks':['requirements-validation.lock']+(['requirements-source-document-intake.lock'] if workbench else []),
        'opa':None,'prepared_dependencies':False}
    with tempfile.TemporaryDirectory(prefix='axiom-package-build-') as temporary:
        staging=Path(temporary)
        for row in rows:
            data=git(root,'cat-file','blob',row['git_blob'])
            if len(data)!=row['size']:raise ValueError('source_blob_size_changed')
            name='source/'+row['path'];path=staging/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            manifest['files'].append({**row,'path':name,'sha256':hashlib.sha256(data).hexdigest()})
        commit=git(root,'cat-file','commit',revision);(staging/'commit.raw').write_bytes(commit)
        manifest['files'].append({'path':'commit.raw','mode':'100644','size':len(commit),'sha256':hashlib.sha256(commit).hexdigest()})
        tool=opa_tool(staging/'source',system,machine)
        if opa:
            if Path(opa).is_symlink() or digest(opa)!=tool.sha256:raise ValueError('package_opa_checksum_mismatch')
            shutil.copyfile(opa,staging/'opa')
            manifest['files'].append({'path':'opa','mode':'100755','size':Path(opa).stat().st_size,'sha256':tool.sha256})
            manifest['opa']={'asset':tool.asset,'version':tool.version,'sha256':tool.sha256}
        if wheelhouse:
            accepted=set();required=set();provided=set()
            for lock in manifest['locks']:
                content=(staging/'source'/lock).read_text()
                accepted.update(re.findall(r'--hash=sha256:([a-f0-9]{64})',content))
                required.update((re.sub('[-_.]+','-',name.lower()),version) for name,version in re.findall(r'^([a-zA-Z0-9_.-]+)==([^\s]+)',content,re.M))
            wheels=sorted(Path(wheelhouse).glob('*.whl'))
            if not wheels:raise ValueError('prepared_wheels_missing')
            for wheel in wheels:
                if wheel.is_symlink() or not re.fullmatch(r'[a-zA-Z0-9_.+\-]+\.whl',wheel.name):raise ValueError('unsafe_package_wheel')
                checksum=digest(wheel)
                if checksum not in accepted:raise ValueError('wheel_not_in_source_hash_lock')
                distribution,version=wheel.name.split('-')[:2]
                provided.add((re.sub('[-_.]+','-',distribution.lower()),version))
                name='wheels/'+wheel.name;target=staging/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(wheel,target)
                manifest['files'].append({'path':name,'mode':'100644','size':wheel.stat().st_size,'sha256':checksum})
            if required-provided:raise ValueError('offline_wheel_set_incomplete')
        manifest['prepared_dependencies']=bool(opa and wheelhouse)
        if sum(row['size'] for row in manifest['files'])>MAX_TOTAL:raise ValueError('package_total_limit')
        with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_STORED) as archive:
            for name in ['manifest.json',*sorted(row['path'] for row in manifest['files'])]:
                info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16
                archive.writestr(info,text_json(manifest).encode() if name=='manifest.json' else (staging/name).read_bytes())
    destination.chmod(0o600)
    return {'sha256':digest(destination),'source_commit':revision,'source_tree':manifest['source_tree'],
            'prepared_dependencies':manifest['prepared_dependencies'],'files':len(manifest['files'])}


def admit(package,expected_sha256,destination):
    """Package hash is an out-of-band trust pin; self-declared manifests are insufficient."""
    package,destination=Path(package),Path(destination)
    if (not re.fullmatch('[a-f0-9]{64}',expected_sha256) or package.is_symlink()
            or package.stat().st_size>MAX_TOTAL+16*1024**2 or digest(package)!=expected_sha256):
        raise ValueError('package_checksum_mismatch')
    if destination.exists() or destination.is_symlink():raise ValueError('fresh_package_root_required')
    # A failed admission leaves only the explicit private candidate for inspection.
    destination.mkdir(mode=0o700,parents=True)
    safe_extract_zip(package,destination,max_members=MAX_MEMBERS,max_member_bytes=MAX_MEMBER,max_total_bytes=MAX_TOTAL)
    if (destination/'manifest.json').stat().st_size>16*1024**2:raise ValueError('package_manifest_limit')
    manifest=json_document((destination/'manifest.json').read_text())
    if (set(manifest)!={'schema_version','source_commit','source_tree','target','files','locks','opa','prepared_dependencies'}
            or manifest['schema_version']!=1 or not re.fullmatch('[a-f0-9]{40}',manifest['source_commit'])
            or not re.fullmatch('[a-f0-9]{40}',manifest['source_tree'])):raise ValueError('invalid_package_manifest')
    names=[];index=[]
    for row in manifest['files']:
        name=relative(row['path']);names.append(name)
        if (not name.startswith(('source/','wheels/')) and name not in ('commit.raw','opa')):
            raise ValueError('unsupported_package_member')
        if (type(row['size']) is not int or not 0<=row['size']<=MAX_MEMBER
                or not re.fullmatch('[a-f0-9]{64}',row['sha256'])):raise ValueError('invalid_package_member_record')
        if row['mode'] not in ('100644','100755'):raise ValueError('invalid_package_mode')
        path=destination/name
        if not path.is_file() or path.is_symlink() or path.stat().st_size!=row['size'] or digest(path)!=row['sha256']:
            raise ValueError('package_member_digest_mismatch')
        path.chmod(0o755 if row['mode']=='100755' else 0o644)
        if name.startswith('source/'):
            source_name=relative(name.removeprefix('source/'))
            index.append((row,source_name))
    actual={str(path.relative_to(destination)) for path in destination.rglob('*') if path.is_file()}
    if len(set(names))!=len(names) or actual!=set(names)|{'manifest.json'}:raise ValueError('package_member_set_mismatch')
    source=destination/'source';git(source,'init','--template=','-q')
    records=[]
    for row,name in index:
        blob=git(source,'hash-object','-w','--stdin',input=(source/name).read_bytes()).decode().strip()
        if blob!=row.get('git_blob'):raise ValueError('package_git_blob_mismatch')
        records.append((row['mode']+' '+blob+'\t'+name+'\0').encode())
    git(source,'update-index','-z','--index-info',input=b''.join(records))
    if git(source,'write-tree').decode().strip()!=manifest['source_tree']:raise ValueError('package_tree_mismatch')
    revision=git(source,'hash-object','-t','commit','-w','--stdin',input=(destination/'commit.raw').read_bytes()).decode().strip()
    if revision!=manifest['source_commit']:raise ValueError('package_original_commit_mismatch')
    # No parent objects or network fetch are needed for this exact shallow source snapshot.
    (source/'.git/shallow').write_text(revision+'\n');git(source,'update-ref','HEAD',revision)
    if git(source,'rev-parse','HEAD^{tree}').decode().strip()!=manifest['source_tree']:
        raise ValueError('package_commit_tree_mismatch')
    for path in (source/'.git',*(source/'.git').rglob('*')):path.chmod(0o755 if path.is_dir() else 0o644)
    (destination/'admission.json').write_text(text_json({'schema_version':1,'package_sha256':expected_sha256,
        'source_commit':revision,'source_tree':manifest['source_tree']}))
    return manifest


def prepare_environment(admitted,venv,python,*,package,expected_sha256):
    """Prepared core runtime only: --no-index and pinned OPA; no public fallback."""
    admitted,venv=Path(admitted),Path(venv)
    if admitted.is_symlink():raise ValueError('unsafe_admitted_root')
    admitted=admitted.resolve()
    if (not re.fullmatch('[a-f0-9]{64}',expected_sha256) or Path(package).is_symlink() or digest(package)!=expected_sha256):
        raise ValueError('package_checksum_mismatch')
    with zipfile.ZipFile(package) as archive:
        if archive.getinfo('manifest.json').file_size>16*1024**2:raise ValueError('package_manifest_limit')
        original_manifest=json_document(archive.read('manifest.json'))
    manifest=json_document((admitted/'manifest.json').read_text())
    admission=json_document((admitted/'admission.json').read_text())
    if (manifest!=original_manifest or admission['package_sha256']!=expected_sha256
            or admission['source_commit']!=manifest['source_commit'] or admission['source_tree']!=manifest['source_tree']):
        raise ValueError('admitted_package_binding_changed')
    expected_files={row['path'] for row in manifest['files']}|{'manifest.json','admission.json'}
    actual_files={str(path.relative_to(admitted)) for path in admitted.rglob('*') if path.is_file()
                  and not path.is_relative_to(admitted/'source/.git')}
    if actual_files!=expected_files:raise ValueError('admitted_file_set_changed')
    if not manifest['prepared_dependencies'] or not manifest['opa'] or not (admitted/'wheels').is_dir():
        raise ValueError('offline_dependencies_not_prepared')
    if venv.exists() or venv.is_symlink():raise ValueError('fresh_runtime_environment_required')
    target=manifest['target'];tool=opa_tool(admitted/'source',target['system'],target['machine'])
    host=opa_tool(admitted/'source',platform.system(),platform.machine())
    if tool.asset!=host.asset or digest(admitted/'opa')!=tool.sha256:raise ValueError('offline_opa_target_or_hash_mismatch')
    if manifest['opa']!={'asset':tool.asset,'version':tool.version,'sha256':tool.sha256}:raise ValueError('offline_opa_manifest_mismatch')
    locks=manifest['locks']
    if locks not in (['requirements-validation.lock'],['requirements-validation.lock','requirements-source-document-intake.lock']):
        raise ValueError('unsupported_offline_lock_set')
    # Recheck source bytes before executing pip or any supplied OPA binary.
    for row in manifest['files']:
        path=admitted/relative(row['path'])
        if path.is_symlink() or any(p.is_symlink() for p in path.parents) or digest(path)!=row['sha256']:
            raise ValueError('admitted_content_changed')
    if git(admitted/'source','rev-parse','HEAD').decode().strip()!=admission['source_commit']:
        raise ValueError('admitted_source_changed')
    result=subprocess.run([str(python),'-m','venv',str(venv)],capture_output=True,timeout=120,umask=0o022)
    if result.returncode:raise ValueError('offline_venv_creation_failed')
    command=[str(venv/'bin/python'),'-m','pip','--isolated','--disable-pip-version-check','install','--no-index','--no-cache-dir',
             '--find-links',str(admitted/'wheels'),'--require-hashes']
    for lock in locks:command.extend(['-r',str(admitted/'source'/lock)])
    result=subprocess.run(command,capture_output=True,timeout=300,umask=0o022)
    if result.returncode:raise ValueError('offline_locked_dependencies_unavailable')
    shutil.copyfile(admitted/'opa',venv/'bin/opa');(venv/'bin/opa').chmod(0o755)
    result=subprocess.run([str(venv/'bin/opa'),'version'],capture_output=True,text=True,timeout=30)
    if result.returncode or not re.search(r'^Version:\s*'+re.escape(tool.version)+r'\s*$',result.stdout,re.M):
        raise ValueError('offline_opa_version_mismatch')
    receipt={**admission,'python':subprocess.check_output([str(venv/'bin/python'),'--version'],text=True).strip(),
             'opa_version':tool.version,'prepared_offline':True,'scanner_databases_prepared':False}
    (venv/'axiom-runtime.json').write_text(text_json(receipt))
    return receipt
