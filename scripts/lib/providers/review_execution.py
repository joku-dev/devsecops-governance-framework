"""Explicit local review files and native read-only CLI process projection."""
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import stat
import subprocess
import time
import tomllib

PROFILES = ('legacy-codex-role-review-v1',)
MAX_STREAM = 10 * 1024**2
MAX_FILE = 16 * 1024**2
MAX_TOTAL = 512 * 1024**2
MAX_FILES = 3000


def profile(name):
    if name not in PROFILES: raise ValueError('unsupported_review_execution_profile')
    return {'provider':'codex','adapter_template':'.codex/agents/{role}.toml'}


def adapter(raw, name):
    profile(name)
    if not isinstance(raw,bytes) or len(raw)>MAX_FILE: raise ValueError('review_execution_adapter_budget')
    try: value=tomllib.loads(raw.decode('utf-8'))
    except (tomllib.TOMLDecodeError,UnicodeError): raise ValueError('invalid_review_execution_adapter') from None
    if not all(isinstance(value.get(k),str) and value[k].strip() for k in ('model','model_reasoning_effort','developer_instructions')):
        raise ValueError('review_execution_explicit_adapter_required')
    if any(len(value[k].encode())>65536 for k in ('model','model_reasoning_effort')):
        raise ValueError('review_execution_adapter_argument_budget')
    return {'requested_model':value['model'],'instructions':value['developer_instructions'],
        'reasoning':value['model_reasoning_effort']}


def command(repository, configuration, role_directory, name):
    profile(name)
    return ['codex','--no-daemon','-a','never','exec','--ignore-user-config','--ephemeral',
        '--sandbox','read-only','--model',configuration['requested_model'],
        '-c','model_reasoning_effort='+json.dumps(configuration['reasoning']),
        '--output-schema',str(Path(role_directory)/'response.schema.json'),
        '--output-last-message',str(Path(role_directory)/'response.json'),'--json','--cd',str(repository),'-']


def observations(raw, name):
    profile(name);model=usage=None
    if raw is None: return {'model':model,'usage':usage}
    if not isinstance(raw,bytes) or len(raw)>MAX_STREAM: raise ValueError('review_execution_event_budget')
    for line in raw.decode('utf-8').splitlines():
        try: event=json.loads(line)
        except json.JSONDecodeError: continue
        # Preserve the original normal event wire and declared identity semantics.
        if event.get('type') in ('thread.started','turn.started') and isinstance(event.get('model'),str):model=event['model']
        if event.get('type')=='turn.completed' and isinstance(event.get('usage'),dict):
            values=event['usage']
            if all(type(values.get(k)) is int and values[k]>=0 for k in ('input_tokens','cached_input_tokens','output_tokens')):
                usage=usage or {k:0 for k in ('input_tokens','cached_input_tokens','output_tokens')}
                for key in usage:usage[key]+=values[key]
    return {'model':model,'usage':usage}


class OutputDirectory:
    """One newly created private directory, held by descriptor through the run."""
    def __init__(self, path, excluded):
        raw=Path(path).expanduser()
        if raw.is_symlink():raise ValueError('review_execution_output_symlink_forbidden')
        self.path=raw.resolve()
        if any(self.path.is_relative_to(Path(p).resolve()) for p in excluded):raise ValueError('review_execution_output_outside_checkouts_required')
        if any(part.casefold()=='.git' for part in self.path.parts):raise ValueError('review_execution_git_output_forbidden')
        if self.path.exists():raise ValueError('review_execution_fresh_output_required')
        parent=os.open(self.path.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            for part in self.path.parent.parts[1:]:
                try:following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
                except FileNotFoundError:
                    try:os.mkdir(part,0o700,dir_fd=parent)
                    except FileExistsError:pass
                    following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
                os.close(parent);parent=following
            try:os.mkdir(self.path.name,0o700,dir_fd=parent)
            except FileExistsError:raise ValueError('review_execution_fresh_output_required') from None
            self.fd=os.open(self.path.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
        finally:os.close(parent)
        self.identity=(os.fstat(self.fd).st_dev,os.fstat(self.fd).st_ino)
        self.check()

    def check(self):
        row=os.stat(self.path,follow_symlinks=False)
        if not stat.S_ISDIR(row.st_mode) or (row.st_dev,row.st_ino)!=self.identity or row.st_uid!=os.geteuid() or row.st_mode&0o077:
            raise ValueError('review_execution_output_directory_changed')

    def parent(self, name):
        self.check();parts=name.split('/')
        if not 1<=len(parts)<=2 or any(not p or p in ('.','..') or '\\' in p or '\0' in p for p in parts):raise ValueError('invalid_review_execution_output_member')
        return (os.dup(self.fd) if len(parts)==1 else os.open(parts[0],os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.fd)),parts[-1]

    def mkdir(self, role):
        parent,name=self.parent(role)
        try:os.mkdir(name,0o700,dir_fd=parent)
        finally:os.close(parent)

    def write(self, name, value):
        parent,leaf=self.parent(name)
        try:
            fd=os.open(leaf,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
            with os.fdopen(fd,'wb') as stream:
                # Original serialization occurs after exclusive creation: partial
                # preparation failures therefore retain their actual empty file.
                raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode('utf-8')
                if len(raw)>MAX_FILE:raise ValueError('review_execution_native_output_budget')
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
        finally:os.close(parent)

    def read(self, name, limit=MAX_FILE):
        parent,leaf=self.parent(name)
        try:
            try:fd=os.open(leaf,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
            except FileNotFoundError:return None
            try:
                before=os.fstat(fd)
                if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_uid!=os.geteuid() or before.st_mode&0o077:raise ValueError('review_execution_private_regular_output_required')
                if before.st_size>limit:raise ValueError('review_execution_native_output_budget')
                with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(limit+1)
                after=os.fstat(fd)
                if len(raw)>limit or any(getattr(before,k)!=getattr(after,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode','st_nlink')):raise ValueError('review_execution_output_changed_during_read')
                return raw
            finally:os.close(fd)
        finally:os.close(parent)

    def snapshot(self):
        self.check();files={};total=0
        for first in sorted(os.listdir(self.fd)):
            row=os.stat(first,dir_fd=self.fd,follow_symlinks=False)
            if stat.S_ISDIR(row.st_mode):
                if row.st_uid!=os.geteuid() or row.st_mode&0o077:raise ValueError('review_execution_private_role_directory_required')
                fd=os.open(first,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.fd)
                try:names=[first+'/'+name for name in sorted(os.listdir(fd))]
                finally:os.close(fd)
            else:names=[first]
            for name in names:
                raw=self.read(name)
                if raw is None:raise ValueError('review_execution_output_changed_during_read')
                total+=len(raw);files[name]=raw
                if total>MAX_TOTAL or len(files)>MAX_FILES:raise ValueError('review_execution_output_total_budget')
        self.check();return files

    def close(self):os.close(self.fd)


def _stop(process):
    try:os.killpg(process.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        process.wait()
    # A terminated CLI may otherwise leave descendants writing after admission.
    try:os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError:pass


def execute(argv, prompt, output, role, timeout, name, on_start):
    """Bounded native process, no shell and no configurable executable surface."""
    profile(name)
    if argv[:8]!=['codex','--no-daemon','-a','never','exec','--ignore-user-config','--ephemeral','--sandbox'] or argv[8]!='read-only':
        raise ValueError('review_execution_read_only_command_required')
    if not isinstance(prompt,str) or len(prompt.encode())>MAX_FILE:raise ValueError('review_execution_prompt_budget')
    output.check();parent,unused=output.parent(role+'/events.jsonl');process=None;error=None;code=None;timed_out=started=False
    try:
        out=os.open('events.jsonl',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
        try:err=os.open('stderr.log',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
        except BaseException:os.close(out);raise
        with os.fdopen(out,'wb') as stdout,os.fdopen(err,'wb') as stderr:
            executable=shutil.which('codex')
            if executable is None:raise FileNotFoundError('review_provider_executable_unavailable')
            process=subprocess.Popen(argv,executable=executable,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                start_new_session=True,umask=0o077)
            started=True;on_start();payload=memoryview(prompt.encode('utf-8'));sent=0;counts={'out':0,'err':0};deadline=time.monotonic()+timeout
            with selectors.DefaultSelector() as selector:
                for stream,label in [(process.stdout,'out'),(process.stderr,'err')]:os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,label)
                os.set_blocking(process.stdin.fileno(),False);selector.register(process.stdin,selectors.EVENT_WRITE,'in')
                while selector.get_map():
                    if time.monotonic()>=deadline:timed_out=True;break
                    # A completed parent may leave pipes held by descendants.
                    # Stop the owned group immediately rather than wait for a
                    # descendant to finish writing after the parent has exited.
                    if process.poll() is not None:_stop(process)
                    try:response=os.stat('response.json',dir_fd=parent,follow_symlinks=False)
                    except FileNotFoundError:response=None
                    if response is not None and (not stat.S_ISREG(response.st_mode) or response.st_nlink!=1 or response.st_size>1024**2):
                        raise ValueError('review_execution_response_budget')
                    for key,_ in selector.select(min(.1,max(0,deadline-time.monotonic()))):
                        if key.data=='in':
                            try:sent+=os.write(key.fileobj.fileno(),payload[sent:sent+65536])
                            except BrokenPipeError:sent=len(payload)
                            if sent==len(payload):selector.unregister(key.fileobj);process.stdin.close()
                        else:
                            raw=os.read(key.fileobj.fileno(),65536)
                            if not raw:selector.unregister(key.fileobj);continue
                            counts[key.data]+=len(raw)
                            if counts[key.data]>MAX_STREAM:raise ValueError('review_execution_stream_budget')
                            (stdout if key.data=='out' else stderr).write(raw)
            if timed_out:_stop(process)
            else:
                try:process.wait(timeout=max(.001,deadline-time.monotonic()))
                except subprocess.TimeoutExpired:timed_out=True;_stop(process)
            code=process.returncode
    except Exception as exc:error=type(exc).__name__
    finally:
        if process is not None:
            _stop(process)
            if code is None:code=process.returncode
            for stream in (process.stdin,process.stdout,process.stderr):
                if stream is not None and not stream.closed:stream.close()
        os.close(parent)
    return {'process_started':started,'exit_code':code,'timed_out':timed_out,'error_type':error}
