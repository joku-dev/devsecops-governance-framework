"""Explicit bounded local crypto observation; no network, keys generated or trust activation."""
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import selectors
import shutil
import signal
import stat
import subprocess
import tempfile
import time

PROFILES=('legacy-attestation-pilot-v1',)
MAX_STREAM=65536
MAX_BINARY=128*1024**2
TIMEOUT=15


def profile(name):
    if name not in PROFILES:raise ValueError('unsupported_attestation_profile')
    return {'registry':'model/evidence/evidence-trust-roots.yaml','tool':'openssl',
        'key_algorithm_enforced':False,'registry_dates_enforced':False}


def initial_observation():
    return {'attempted':False,'process_started':False,'tool_path':None,'tool_sha256':None,
        'returncode':None,'timed_out':False,'error_type':None,'failure_stage':None,'signature_valid':None,'reason':None}


def outcome(observation):
    if not observation['attempted']:raise ValueError('attestation_crypto_observation_required')
    if observation['error_type']=='FileNotFoundError' and not observation['process_started'] and observation['failure_stage'] in ('resolve_tool','start_process'):
        return False,'OpenSSL is unavailable; signature verification was not performed.'
    if observation['error_type'] is not None or observation['timed_out'] or not observation['process_started']:
        raise ValueError('attestation_crypto_execution_incomplete')
    valid=observation['returncode']==0
    return valid,'Ed25519 signature is valid.' if valid else 'Ed25519 signature is invalid.'


def executable(path):
    path=Path(path).resolve();fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>MAX_BINARY:raise ValueError('attestation_crypto_tool_budget')
        digest=hashlib.sha256();size=0
        while raw:=os.read(fd,1024**2):
            size+=len(raw)
            if size>MAX_BINARY:raise ValueError('attestation_crypto_tool_budget')
            digest.update(raw)
        after=os.fstat(fd)
        if any(getattr(before,k)!=getattr(after,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode')):
            raise ValueError('attestation_crypto_tool_changed')
        return str(path),digest.hexdigest()
    finally:os.close(fd)


def stop(process):
    try:os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    process.wait()


def verify(key,statement,signature,workarea,name,on_start):
    """Run only the fixed legacy verification command on private retained bytes."""
    selected=profile(name);observation=initial_observation();observation['attempted']=True
    stdout=bytearray();stderr=bytearray();process=None;stage='resolve_tool'
    try:
        stage='stage_inputs'
        if not isinstance(key,str) or len(key.encode('utf-8'))>65536 or not isinstance(statement,bytes) or len(statement)>1024**2 or not isinstance(signature,bytes) or len(signature)>16384:
            raise ValueError('attestation_crypto_input_budget')
        stage='resolve_tool'
        found=shutil.which(selected['tool'])
        if found is None:raise FileNotFoundError
        tool,digest=executable(found);observation.update(tool_path=tool,tool_sha256=digest)
        stage='stage_inputs'
        with tempfile.TemporaryDirectory(prefix='.crypto-',dir=workarea) as temporary:
            root=Path(temporary)
            for name,raw in [('key.pem',key.encode('utf-8')),('statement.json',statement),('signature.bin',signature)]:
                fd=os.open(root/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                with os.fdopen(fd,'wb') as stream:stream.write(raw)
            argv=[tool,'pkeyutl','-verify','-pubin','-rawin','-inkey',str(root/'key.pem'),'-in',str(root/'statement.json'),'-sigfile',str(root/'signature.bin')]
            stage='start_process';process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,umask=0o077)
            observation['process_started']=True;on_start(dict(observation));deadline=time.monotonic()+TIMEOUT
            stage='read_process'
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout,selectors.EVENT_READ,stdout);selector.register(process.stderr,selectors.EVENT_READ,stderr)
                    while selector.get_map():
                        if time.monotonic()>=deadline:observation['timed_out']=True;raise ValueError('attestation_crypto_timeout')
                        if process.poll() is not None:stop(process)
                        for key,_ in selector.select(min(.1,max(0,deadline-time.monotonic()))):
                            raw=os.read(key.fileobj.fileno(),65536)
                            if not raw:selector.unregister(key.fileobj);continue
                            remaining=MAX_STREAM-len(key.data);key.data.extend(raw[:remaining])
                            if len(raw)>remaining:raise ValueError('attestation_crypto_stream_budget')
                try:process.wait(timeout=max(.001,deadline-time.monotonic()))
                except subprocess.TimeoutExpired:observation['timed_out']=True;raise ValueError('attestation_crypto_timeout') from None
                observation['returncode']=process.returncode
            finally:
                stop(process)
                for stream in (process.stdout,process.stderr):stream.close()
            stage='recheck_tool'
            if executable(tool)!=(tool,digest):raise ValueError('attestation_crypto_tool_changed')
    except Exception as exc:observation.update(error_type=type(exc).__name__,failure_stage=stage)
    finally:
        if process is not None:
            with ExitStack() as cleanup:
                for stream in (process.stdout,process.stderr):
                    if stream is not None and not stream.closed:cleanup.callback(stream.close)
                stop(process)
                if observation['returncode'] is None:observation['returncode']=process.returncode
    try:observation['signature_valid'],observation['reason']=outcome(observation)
    except ValueError:pass
    return observation,bytes(stdout),bytes(stderr)
