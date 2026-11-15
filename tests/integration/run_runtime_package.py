#!/usr/bin/env python3
"""Prepare/evaluate the exact package under an OS network deny policy, using local wheels."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.runtime_package import build,admit,digest,git,text_json
from lib.portable.contracts import canonical_digest
from lib.portable.runtime import evaluate
from test_portable_runtime import Files,context,AT


def isolation():
    if platform.system()=='Darwin':
        if not Path('/usr/bin/sandbox-exec').is_file():raise ValueError('native_network_isolation_unavailable')
        return ['/usr/bin/sandbox-exec','-p','(version 1)(allow default)(deny network*)'],'macOS sandbox-exec deny network*'
    if platform.system()=='Linux' and os.geteuid()==0 and os.environ.get('GITHUB_ACTIONS')=='true':
        if not shutil.which('unshare'):raise ValueError('native_network_isolation_unavailable')
        return ['unshare','--net','--'],'Linux unshare network namespace with no external interfaces'
    raise ValueError('requires_explicit_local_mac_or_disposable_root_github_linux_test')


def run(command):
    result=subprocess.run(command,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},capture_output=True,text=True,timeout=600)
    if result.returncode:raise ValueError('offline_integration_command_failed: '+result.stderr[-1000:])
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--wheelhouse',type=Path,required=True)
    parser.add_argument('--opa',type=Path,required=True)
    parser.add_argument('--revision')
    parser.add_argument('--allow-isolated-test',action='store_true',required=True)
    args=parser.parse_args();os.umask(0o077)
    prefix,policy=isolation();directory=args.output_root.resolve();directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    revision=args.revision or git(ROOT,'rev-parse','HEAD').decode().strip()
    archive=directory/'runtime.zip'
    metadata=build(ROOT,revision,archive,opa=args.opa,wheelhouse=args.wheelhouse)
    manifest=admit(archive,metadata['sha256'],directory/'admitted')
    # The control must fail with an OS permission/no-route error, not a mere timeout.
    probe=('import errno,socket\ntry:\n socket.create_connection(("1.1.1.1",443),timeout=1)\n'
           'except OSError as error:\n assert error.errno in (errno.EPERM,errno.EACCES,errno.ENETUNREACH,errno.EHOSTUNREACH),repr(error)\n'
           'else:\n raise AssertionError("external network was available")\n')
    run([*prefix,sys.executable,'-c',probe])
    environment=directory/'venv'
    run([*prefix,sys.executable,str(ROOT/'scripts/package_governance_runtime.py'),'prepare-environment',
        '--root',str(directory/'admitted'),'--package',str(archive),'--sha256',metadata['sha256'],
        '--destination',str(environment),'--python',str(Path(sys._base_executable))])
    fixture=Files('runTest');fixture.setUp();cases=[]
    try:
        ctx=context();ctx_path=directory/'context.json';ctx_path.write_text(json.dumps(ctx))
        for name in ('pass','fail'):
            if name=='fail':
                fixture.scan.update(max_severity='critical',findings=[{'id':'synthetic-critical','severity':'critical'}]);fixture.write_scan()
            payload,subjects=fixture.evidence(ctx)
            expected=evaluate(ctx,payload,subjects,opa=args.opa,at=AT)
            input_path=directory/(name+'-input.json');input_path.write_text(json.dumps({'payload':payload,'subjects':subjects}))
            output=directory/(name+'-result.json')
            run([*prefix,str(environment/'bin/python'),'-B',str(directory/'admitted/source/scripts/governance_runtime.py'),
                'evaluate','--context',str(ctx_path),'--input',str(input_path),'--output',str(output),
                '--opa',str(environment/'bin/opa'),'--at',AT])
            actual=json.loads(output.read_text());assert actual==expected and actual['decision']==name
            cases.append({'decision':name,'canonical_result_sha256':canonical_digest(actual),'exact_reference_match':True})
    finally:fixture.doCleanups()
    result={'schema_version':1,'source_commit':manifest['source_commit'],'source_tree':manifest['source_tree'],
        'package_sha256':metadata['sha256'],'network_policy':policy,'network_control_probe_denied':True,
        'ambient_provider_environment':False,'package_files':metadata['files'],'system':platform.system(),
        'machine':platform.machine(),'python':platform.python_version(),'cases':cases,
        'scanner_databases_prepared':False,'actual_vm_updated':False}
    (directory/'report.json').write_text(text_json(result));print(text_json(result));return 0


if __name__=='__main__':raise SystemExit(main())
