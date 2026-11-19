"""Byte/command/source consistency of retained native compliance observations."""
from pathlib import Path
import hashlib
import re
import sys
import zipfile

from control_evaluation import POLICY_QUERIES
from lib.result_bytes import safe_bytes, strict_json
from lib.runtime_package import relative, MAX_MEMBERS, MAX_MEMBER, MAX_TOTAL
from lib.validation_generated_effects import GENERATED, checked_change
from lib.portable.contracts import ROOT
from lib.functional_parity import git_read
from lib.portable.runtime import approved_opa_hashes


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def stream_files(root, outcome, *, kind, limit=8*1024**2):
    values = {}
    if set(outcome['outputs']) != {'stdout','stderr'}:
        raise ValueError('compliance_native_stream_set_changed')
    for name, row in outcome['outputs'].items():
        if row['path'] != kind+'-'+name+'.bin':
            raise ValueError('compliance_closed_native_stream_required')
        raw = safe_bytes(Path(root)/row['path'], limit=limit)
        if pin(raw) != {k:row[k] for k in ('bytes','sha256')}:
            raise ValueError('compliance_native_stream_bytes_changed')
        values[name] = raw
    return values


def preflight_files(root, result, events):
    outcome=result['preflight']
    if (outcome['command']!=['/bin/bash','./scripts/validate_all.sh','--check-tools']
            or type(outcome['returncode']) is not int or outcome['returncode']!=0
            or outcome['wall_seconds_limit']!=120 or outcome['stream_byte_limit']!=8*1024**2
            or [e for e in events if e.get('kind')=='compliance-preflight']!=[
                {'kind':'compliance-preflight','phase':'intent'},
                {'kind':'compliance-preflight','phase':'finished','outcome':outcome}]):
        raise ValueError('compliance_complete_toolchain_preflight_changed')
    return stream_files(Path(root)/'work/native',outcome,kind='preflight')


def package_source(root, header):
    """Read frozen current source data only, never a program from the archive."""
    package = Path(root)/'input.zip'
    if (git_read(ROOT,'rev-parse','HEAD').decode().strip()!=header['source_revision']
            or git_read(ROOT,'rev-parse','HEAD^{tree}').decode().strip()!=header['source_tree']):
        raise ValueError('compliance_retained_package_not_current_product')
    trusted={}
    for entry in filter(None,git_read(ROOT,'ls-tree','-r','-l','-z',header['source_revision']).split(b'\0')):
        metadata,name=entry.split(b'\t',1);mode,kind,oid,size=metadata.decode().split()
        if kind!='blob' or mode not in ('100644','100755'):
            raise ValueError('compliance_current_product_regular_tree_required')
        trusted[name.decode()]={'mode':mode,'git_blob':oid,'size':int(size)}
    with package.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest() != header['package_sha256']:
            raise ValueError('compliance_retained_package_changed')
    with zipfile.ZipFile(package) as archive:
        entries = archive.infolist()
        if (len(entries) > MAX_MEMBERS or sum(e.file_size for e in entries) > MAX_TOTAL
                or len({e.filename for e in entries}) != len(entries)
                or any(e.file_size > MAX_MEMBER for e in entries)
                or archive.getinfo('manifest.json').file_size > 16*1024**2):
            raise ValueError('compliance_retained_package_budget')
        manifest = strict_json(archive.read('manifest.json'))
        if (manifest['source_commit'] != header['source_revision'] or manifest['source_tree'] != header['source_tree']
                or manifest['prepared_dependencies'] is not True or manifest['opa'] is None):
            raise ValueError('compliance_retained_package_source_changed')
        if manifest['opa']['sha256'] not in approved_opa_hashes('1.18.2'):
            raise ValueError('compliance_retained_package_opa_not_pinned')
        files, modes = {}, {}
        for row in manifest['files']:
            relative(row['path'])
            if row['path'].startswith('source/'):
                name = row['path'][7:]; relative(name)
                if name in files or row['mode'] not in ('100644','100755'):
                    raise ValueError('compliance_package_source_rows_changed')
                if trusted.get(name)!={k:row[k] for k in ('mode','git_blob','size')}:
                    raise ValueError('compliance_package_source_not_whole_current_tree')
                raw = archive.read(row['path'])
                if len(raw) != row['size'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
                    raise ValueError('compliance_package_source_bytes_changed')
                if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw,usedforsecurity=False).hexdigest()!=row['git_blob']:
                    raise ValueError('compliance_package_source_git_blob_changed')
                files[name] = raw; modes[name] = row['mode']
        if set(files)!=set(trusted):
            raise ValueError('compliance_package_source_not_whole_current_tree')
    return manifest, files, modes


def check_opa(root, header, selected, result, manifest, source_files):
    rows = result['opa_observations']
    source = Path(result['execution_source_root']); label = result['input_label']
    policy = str(source/'policies/opa')
    queries = [['opa','eval','-f','json','-d',policy,'-i',label,q] for q in POLICY_QUERIES.values()]
    expected = [['opa','version'],['opa','check',policy],*queries,*queries]
    if len(rows) > len(expected) or result['execution'] == 'complete' and len(rows) != len(expected):
        raise ValueError('compliance_whole_opa_command_count_changed')
    policies = {n:hashlib.sha256(raw).hexdigest() for n,raw in source_files.items() if n.startswith('policies/opa/')}
    for name,sha in policies.items():
        if hashlib.sha256(safe_bytes(Path(root)/'work/opa/frozen'/name)).hexdigest()!=sha:
            raise ValueError('compliance_frozen_policy_bytes_changed')
    if result['input_sha256'] is not None:
        raw=safe_bytes(Path(root)/'work/control-input.json')
        if (hashlib.sha256(raw).hexdigest()!=result['input_sha256']
                or safe_bytes(Path(root)/'work/opa/frozen/input.json')!=raw):
            raise ValueError('compliance_frozen_control_input_changed')
    outputs = []
    for index,row in enumerate(rows,1):
        if (row['sequence'] != index or row['declared_command'] != expected[index-1]
                or row['tool_sha256'] != manifest['opa']['sha256'] or row['policy_files'] != policies
                or row['input_sha256'] != result['input_sha256']
                or row['input_present'] != (result['input_sha256'] is not None)
                or row['tool_path'] != str(Path(root)/'work/admitted/opa')):
            raise ValueError('compliance_opa_input_policy_tool_or_order_changed')
        area = Path(root)/'work/opa'/('native-'+str(index)); native = row['native_outcome']
        frozen = Path(root)/'work/opa/frozen'
        command = [row['tool_path'],'version'] if index == 1 else (
            [row['tool_path'],'check',str(frozen/'policies/opa')] if index == 2 else
            [row['tool_path'],'eval','-f','json','-d',str(frozen/'policies/opa'),'-i',str(frozen/'input.json'),expected[index-1][-1]])
        if native['command'] != command or native['wall_limit_seconds'] != 60 or native['stream_limit_bytes'] != 8*1024**2:
            raise ValueError('compliance_opa_actual_command_or_budget_changed')
        translated = {'outputs':native['streams']}
        values = stream_files(area, translated, kind='controller')
        outputs.append({'returncode':native['exit_code'], **{k:v.decode().replace('\r\n','\n').replace('\r','\n') for k,v in values.items()}})
    return outputs


def unit_files(root, result, before, modes):
    work = Path(root)/'work'; source = work/'admitted/source'
    outcome = result['unit_outcome']
    if outcome is None:
        return dict(before), dict(modes), None
    if (outcome['command'] != [sys.executable,'-B','-m','unittest','discover','-s','tests']
            or outcome['returncode'] not in (0,1) or outcome['wall_seconds_limit'] != 3600
            or outcome['stream_byte_limit'] != 8*1024**2):
        raise ValueError('compliance_whole_unit_command_or_budget_changed')
    values = stream_files(work/'native',outcome,kind='unit-tests')
    matches = list(re.finditer(rb'^Ran ([0-9]+) tests? in ([0-9.]+)s\s*$',values['stderr'],re.M))
    if (not matches or int(matches[-1][1]) != result['unit_statistics']['tests_run']
            or float(matches[-1][2]) != result['unit_statistics']['seconds']):
        raise ValueError('compliance_whole_unit_count_changed')
    suffix = values['stderr'][matches[-1].end():]
    summary = re.search(rb'^(OK(?: \(skipped=([0-9]+)\))?|FAILED \([^\n]+\))$',suffix,re.M)
    if not summary or (outcome['returncode']==0) != summary[1].startswith(b'OK'):
        raise ValueError('compliance_whole_unit_status_changed')
    skipped = re.search(rb'skipped=([0-9]+)',summary[1])
    if (int(skipped[1]) if skipped else 0) != result['unit_statistics']['skipped']:
        raise ValueError('compliance_whole_unit_skip_count_changed')
    after = dict(before); result_modes = dict(modes)
    metadata = work/'unit-generated-effects'
    old_dir, new_dir = metadata/'before', metadata/'after'
    actual = {p.relative_to(old_dir).as_posix() for p in old_dir.rglob('*') if p.is_file()}
    if actual != {p.relative_to(new_dir).as_posix() for p in new_dir.rglob('*') if p.is_file()} or actual-GENERATED:
        raise ValueError('compliance_unit_metadata_membership_changed')
    example = hashlib.sha256(before['docs/examples/evidence-attestation.example.json']).hexdigest()
    for name in actual:
        old,new = safe_bytes(old_dir/name),safe_bytes(new_dir/name)
        if before[name] != old:
            raise ValueError('compliance_unit_sequential_source_baseline_changed')
        checked_change(name,old,new,source,example); after[name]=new
    if result['viewer_projection'] is not None:
        projection = result['viewer_projection']
        code=('from pathlib import Path; import sys,json; '
            'sys.path.insert(0,str(Path.cwd()/"scripts")); '
            'from lib.viewer_app import project_data; '
            'sys.stdout.write(json.dumps(project_data(Path.cwd()),ensure_ascii=False,indent=2)+"\\n")')
        if projection['returncode'] != 0 or projection['command'] != [sys.executable,'-B','-c',code]:
            raise ValueError('compliance_unit_projection_command_changed')
        raw = stream_files(work/'native',projection,kind='viewer-projection')['stdout']
        name = 'generated/viewer/app/data.json'
        if safe_bytes(work/'unit-generated-artifacts'/name,limit=8*1024**2) != raw or type(strict_json(raw)) is not dict:
            raise ValueError('compliance_unit_complete_viewer_payload_changed')
        after[name]=raw; result_modes[name]='100644'
    return after,result_modes,values


def final_source(root, result, files, modes):
    expected = {n:{**pin(raw),'mode':modes[n]} for n,raw in files.items()}
    if expected != result['final_source_files']:
        raise ValueError('compliance_final_source_effects_changed')
    source = Path(root)/'work/admitted/source'
    members=[p for p in source.rglob('*') if p.relative_to(source).parts[0]!='.git']
    if any(p.is_symlink() for p in members):
        raise ValueError('compliance_final_source_symlink')
    actual = {p.relative_to(source).as_posix() for p in members
              if p.is_file() and p.relative_to(source).parts[0] != '.git'}
    if actual != set(files):
        raise ValueError('compliance_final_source_membership_changed')
    for name,raw in files.items():
        path = source/name
        if (safe_bytes(path) != raw or ('100755' if path.stat().st_mode & 0o111 else '100644') != modes[name]):
            raise ValueError('compliance_final_source_bytes_or_mode_changed')
