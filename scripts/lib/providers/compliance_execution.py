"""Parent-owned fixed whole-compliance worker and private request/outcome files."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys

from lib import compliance_operation as contract
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT
from lib.providers.attestation_verification import executable
from lib.providers.product_test_worker import retain_package, supervise
from lib.result_bytes import safe_bytes, strict_json

WORKER = 'scripts/lib/providers/compliance_worker.py'
OWN_MODULE = 'scripts/lib/providers/compliance_execution.py'


def write_private(path, value):
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))+'\n').encode()
    with Path(path).open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    Path(path).chmod(0o600)
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def execute(root, header, selected, package):
    from lib.v2_application import instance
    contract.binding(header); contract.options(selected)
    actual, settings = instance(header['instance_root'])
    if (settings['development'] or str(ROOT) != header['product_source_root']
            or any(settings[k] != header[k] for k in ('node_id','runtime_source_digest','source_revision'))
            or git_read(ROOT,'rev-parse','HEAD^{tree}').decode().strip() != header['source_tree']):
        raise ValueError('complete_compliance_current_installed_parent_required')
    for name in (OWN_MODULE, WORKER):
        if (ROOT/name).read_bytes() != git_read(ROOT, 'show', header['source_revision']+':'+name):
            raise ValueError('committed_complete_compliance_parent_required')
    root = Path(root)
    packet = contract.request({'binding': header, 'options': selected,
        'record_root': str(root), 'package': str(root/'input.zip')})
    if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077 or list(root.iterdir()):
        raise ValueError('fresh_private_complete_compliance_operation_required')
    captured = retain_package(package, header['package_sha256'], root/'input.zip')
    request_pin = write_private(root/'request.json', packet)
    supervision = root/'supervision'; supervision.mkdir(mode=0o700)
    tools = supervision/'tools'; tools.mkdir(mode=0o700)
    native = {}
    for name in ('git','node','openssl'):
        found = shutil.which(name)
        if found is None:
            raise ValueError('complete_compliance_parent_tool_missing')
        path, pin = executable(found); native[name] = {'path': path, 'sha256': pin}
        (tools/name).symlink_to(path)
    environment = {'PATH': os.pathsep.join([str(tools), str(Path(sys.executable).parent),
                       '/usr/bin','/bin','/usr/sbin','/sbin']),
        'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1',
        'PIP_NO_INDEX':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1',
        'GIT_CONFIG_COUNT':'0','GIT_TERMINAL_PROMPT':'0','GIT_ASKPASS':'/bin/false'}
    command = [sys.executable, '-I', '-B', str(ROOT/WORKER), str(root/'request.json')]
    write_private(supervision/'intent.json', {'binding':header,'command':command,
        'package':captured,'request':request_pin,'tools':native,
        'OS_network_or_process_tree_isolation_attested':False, **contract.AUTHORITY})
    outcome = supervise(command, Path('/'), environment, supervision)
    if outcome['exit_code'] not in (0,1,2):
        raise ValueError('complete_compliance_worker_abnormal_exit')
    if instance(actual)[1] != settings:
        raise ValueError('complete_compliance_parent_instance_changed')
    for row in native.values():
        if executable(row['path']) != (row['path'],row['sha256']):
            raise ValueError('complete_compliance_parent_tool_changed')
    raw = safe_bytes(root/'request.json',limit=64*1024)
    if len(raw) != request_pin['bytes'] or hashlib.sha256(raw).hexdigest() != request_pin['sha256']:
        raise ValueError('complete_compliance_request_changed')
    write_private(supervision/'outcome.json', outcome)
    return outcome


def supervision(root, packet):
    """Check recorded parent bytes; never claim independent execution authentication."""
    root = Path(root); contract.request(packet)
    area = root/'supervision'
    intent = strict_json(safe_bytes(area/'intent.json',limit=64*1024))
    outcome = strict_json(safe_bytes(area/'outcome.json',limit=64*1024))
    if intent['binding'] != packet['binding'] or intent['command'][-1] != str(root/'request.json'):
        raise ValueError('complete_compliance_supervision_binding_changed')
    if intent['package']!={'path':'input.zip','bytes':(root/'input.zip').stat().st_size,
                          'sha256':packet['binding']['package_sha256']}:
        raise ValueError('complete_compliance_parent_package_pin_changed')
    if (intent['command'][:3] != [sys.executable,'-I','-B']
            or intent['command'][3] != str(ROOT/WORKER)
            or outcome.get('command') != intent['command']
            or type(outcome.get('exit_code')) is not int or outcome['exit_code'] not in (0,1,2)
            or outcome.get('wall_limit_seconds') != 4200 or outcome.get('stream_limit_bytes') != 65536
            or intent.get('OS_network_or_process_tree_isolation_attested') is not False
            or any(type(intent.get(k)) is not type(v) or intent[k] != v for k,v in contract.AUTHORITY.items())):
        raise ValueError('complete_compliance_supervision_outcome_changed')
    for name in ('stdout','stderr'):
        row = outcome['streams'][name]
        if row['path'] != 'controller-'+name+'.bin':
            raise ValueError('complete_compliance_closed_worker_stream_required')
        raw = safe_bytes(area/row['path'],limit=65536)
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('complete_compliance_parent_stream_changed')
    request_raw = safe_bytes(root/'request.json',limit=64*1024)
    if intent['request'] != {'bytes':len(request_raw),'sha256':hashlib.sha256(request_raw).hexdigest()}:
        raise ValueError('complete_compliance_parent_request_pin_changed')
    return outcome
