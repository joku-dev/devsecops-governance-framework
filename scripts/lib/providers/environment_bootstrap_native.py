"""Owned validation/source-intake environment actions before Python dependencies.

Only reviewed own-source locks and the explicit pinned policy-tool adapter are
used. A caller-selected interpreter/environment is operator configuration, never
inferred from an inspected consumer. No service, publisher or approval is started.
"""
from pathlib import Path
import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
from urllib.parse import urlsplit

from lib.environment_bootstrap import BootstrapFailure, PROFILES
from lib.v2_source import active_fingerprints, selected_paths
from lib.providers.opa_bootstrap import select_tool, locations
from lib.providers.environment_bootstrap_storage import (BootstrapJournal,
    owned_directory, write_new, read_private, encoded, document, inspect)
from lib.providers.environment_bootstrap_process import BootstrapProcesses

ROOT = Path(__file__).resolve().parents[3]
SOURCE_FILES = ('requirements-validation.txt','requirements-validation.lock',
    'requirements-source-document-intake.lock','scripts/validation-toolchain.env',
    'scripts/opa-download-sources.json','scripts/install_validation_opa.py',
    'scripts/lib/__init__.py','scripts/lib/providers/__init__.py',
    'scripts/lib/opa_bootstrap_ports.py','scripts/lib/providers/opa_bootstrap.py')
REQUIRED_CODE = frozenset(('scripts/bootstrap_axiom_v2_environment.py',
    'scripts/lib/environment_bootstrap.py','scripts/lib/environment_bootstrap_application.py',
    'scripts/lib/environment_bootstrap_ports.py',
    'scripts/lib/providers/environment_bootstrap_native.py',
    'scripts/lib/providers/environment_bootstrap_storage.py',
    'scripts/lib/providers/environment_bootstrap_process.py',*SOURCE_FILES[5:]))
INTERPRETER_QUERY = ('import json,sys;print(json.dumps({"version":list(sys.version_info[:3]),'
    '"prefix":sys.prefix,"base_prefix":sys.base_prefix,"executable":sys.executable}))')
NETWORK_KEYS = frozenset(('PIP_INDEX_URL','PIP_EXTRA_INDEX_URL','PIP_TRUSTED_HOST',
    'PIP_CERT','PIP_CLIENT_CERT','PIP_PROXY','PIP_TIMEOUT','PIP_RETRIES',
    'HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy',
    'SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE'))


def normalized(value):
    raw = Path(value).expanduser().absolute()
    for count in range(1,len(raw.parts)+1):
        if Path(*raw.parts[:count]).is_symlink():
            raise BootstrapFailure('bootstrap_path_symlink_forbidden')
    return Path(os.path.abspath(raw))


def private_parent(path):
    path.mkdir(parents=True,mode=0o700,exist_ok=True)
    return owned_directory(path)


def raw_new(path, raw):
    if type(raw) is not bytes or len(raw)>1024*1024:
        raise ValueError('bootstrap_source_input_budget')
    path.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
    fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    try:
        view=memoryview(raw)
        while view:
            count=os.write(fd,view)
            if count<=0:raise OSError('bootstrap_source_input_short_write')
            view=view[count:]
        os.fsync(fd)
    finally:os.close(fd)


class NativeEnvironmentSession:
    """One explicit operation and shared local target lock; no automatic resume."""
    def __init__(self, profile, options):
        if profile not in PROFILES:raise BootstrapFailure('bootstrap_profile_unsupported')
        self.profile=profile;self.options=options;self.closed=False;self.lock_fd=None
        self.journal=None;self.native=None;self.tools={};self.distributions={};self.messages=[]
        self.target=normalized(options['environment'])
        self.development=bool(options.get('development',False))
        if self.target==ROOT or ROOT.is_relative_to(self.target):
            raise BootstrapFailure('bootstrap_environment_cannot_replace_source')
        if self.target.is_relative_to(ROOT):
            if (not self.development or self.target.parent!=ROOT
                    or self.target.name not in ('.venv-validation','.venv-source-document-intake')
                    or (ROOT/'.git/info/sparse-checkout').exists()):
                raise BootstrapFailure('bootstrap_environment_outside_product_required')
        if self.target.exists():
            row=self.target.stat()
            if not self.target.is_dir() or row.st_uid!=os.geteuid() or row.st_mode&0o022:
                raise BootstrapFailure('bootstrap_owned_environment_required')
            if any(self.target.iterdir()) and not (self.target/'pyvenv.cfg').is_file():
                raise BootstrapFailure('bootstrap_existing_environment_not_recognized')
        self.target.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
        state=options.get('state_directory')
        if state is None:
            state=(ROOT/'.local/environment-bootstrap-records' if self.target.is_relative_to(ROOT)
                   else self.target.parent/'.axiom-bootstrap-records')
        self.state=normalized(state)
        if self.state.is_relative_to(self.target) or self.target.is_relative_to(self.state):
            raise BootstrapFailure('bootstrap_state_must_be_separate_from_environment')
        if self.state.is_relative_to(ROOT) and not self.development:
            raise BootstrapFailure('bootstrap_state_outside_product_required')
        private_parent(self.state)
        selected=set(selected_paths(ROOT))
        if not REQUIRED_CODE<=selected:
            raise BootstrapFailure('bootstrap_execution_closure_not_registered')
        self.fingerprints=active_fingerprints(ROOT)
        self.captured={}
        for name in SOURCE_FILES:
            path=ROOT/name
            if path.is_symlink() or path.stat().st_size>1024*1024:
                raise BootstrapFailure('bootstrap_source_input_invalid')
            raw=path.read_bytes()
            if hashlib.sha256(raw).hexdigest()!=self.fingerprints[name]:
                raise BootstrapFailure('bootstrap_source_input_changed')
            self.captured[name]=raw
        wheelhouse=options.get('wheelhouse')
        self.wheelhouse=None if wheelhouse is None else normalized(wheelhouse)
        if options.get('offline') and (self.wheelhouse is None or not self.wheelhouse.is_dir()):
            raise BootstrapFailure('bootstrap_offline_wheelhouse_required')
        self.cache=normalized(options.get('opa_cache') or (self.target.parent/'.axiom-bootstrap-opa-cache'))
        self.expected={}
        for line in self.captured['requirements-validation.txt'].decode().splitlines():
            if line and not line.startswith('#'):
                if not re.fullmatch(r'[A-Za-z0-9_.-]+==[^\s=]+',line):
                    raise BootstrapFailure('bootstrap_unpinned_own_requirements')
                name,version=line.split('==',1);self.expected[name]=version
        if self.profile=='source-intake-environment-v1':
            match=re.search(rb'^pypdf==([^\s]+)',self.captured['requirements-source-document-intake.lock'],re.M)
            if match is None:raise BootstrapFailure('bootstrap_source_intake_pin_missing')
            self.expected={'pypdf':match[1].decode()}
        mirror=options.get('opa_mirror','')
        if mirror:
            parsed=urlsplit(mirror)
            if (parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password
                    or parsed.query or parsed.fragment or any(ord(c)<33 for c in mirror)):
                raise BootstrapFailure('bootstrap_credential_free_https_mirror_required')
        self.request={'profile':profile,'environment':str(self.target),
            'selected_python':options['python'],'offline':bool(options.get('offline')),
            'wheelhouse':None if self.wheelhouse is None else str(self.wheelhouse),
            'opa_cache':str(self.cache),'opa_mirror':options.get('opa_mirror',''),
            'attempts':options.get('attempts',3),'timeout':options.get('timeout',120),
            'development':self.development,'package_content_integrity_reverified':False}
        input_rows={name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
                    for name,raw in self.captured.items()}
        source={'kind':'own_registered_bootstrap_source','source_root':str(ROOT),
            'active_fingerprints':self.fingerprints,'captured_inputs':input_rows,
            'independent_source_authentication':False}
        self._lock()
        try:
            self.journal=BootstrapJournal(self.state,self.request,source)
            self._record_lock_owner()
            for name,raw in self.captured.items():raw_new(self.journal.root/'inputs'/name,raw)
            self.native=BootstrapProcesses(self.journal)
            self.environment={'PATH':os.environ.get('PATH','/usr/bin:/bin'),
                'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1',
                'PIP_CONFIG_FILE':'/dev/null','PIP_DISABLE_PIP_VERSION_CHECK':'1',
                'PIP_NO_CACHE_DIR':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1',
                'GIT_CONFIG_COUNT':'0','GIT_TERMINAL_PROMPT':'0','GIT_ASKPASS':'/bin/false',
                'GIT_NO_REPLACE_OBJECTS':'1','GIT_NO_LAZY_FETCH':'1','GIT_ALLOW_PROTOCOL':''}
            for name in NETWORK_KEYS:
                if name in os.environ:self.environment[name]=os.environ[name]
        except BaseException:
            self.close();raise

    def _lock(self):
        import stat
        name='.axiom-bootstrap-'+hashlib.sha256(str(self.target).encode()).hexdigest()[:24]+'.lock'
        self.lock_path=self.target.parent/name
        fd=os.open(self.lock_path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            row=os.fstat(fd)
            if not stat.S_ISREG(row.st_mode) or row.st_uid!=os.geteuid() or row.st_nlink!=1 or row.st_mode&0o077:
                raise BootstrapFailure('bootstrap_private_target_lock_required')
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if row.st_size:
                if row.st_size>16384:raise BootstrapFailure('bootstrap_previous_operation_owner_invalid')
                raw=os.read(fd,16385)
                previous=document(raw)
                if (set(previous)!={'schema_version','target','record_root'}
                        or type(previous['schema_version']) is not int or previous['schema_version']!=1
                        or previous['target']!=str(self.target) or type(previous['record_root']) is not str):
                    raise BootstrapFailure('bootstrap_previous_operation_owner_invalid')
                # A free flock proves only that the coordinator released its
                # descriptor. It does not prove a former child stopped or that
                # interrupted environment writes can be resumed safely.
                try:retained=inspect(normalized(previous['record_root']))
                except (ValueError,OSError,TypeError,KeyError) as error:
                    raise BootstrapFailure('bootstrap_previous_operation_inspection_required') from error
                if retained['declared_result'] not in ('complete','failed') or retained['incomplete_native_captures']:
                    raise BootstrapFailure('bootstrap_previous_operation_incomplete')
        except BaseException:
            os.close(fd);raise
        self.lock_fd=fd

    def _record_lock_owner(self):
        raw=encoded({'schema_version':1,'target':str(self.target),'record_root':str(self.journal.root)})
        os.lseek(self.lock_fd,0,os.SEEK_SET)
        os.ftruncate(self.lock_fd,0)
        remaining=memoryview(raw)
        while remaining:
            count=os.write(self.lock_fd,remaining)
            if count<=0:raise OSError('bootstrap_target_owner_short_write')
            remaining=remaining[count:]
        os.fsync(self.lock_fd)
        parent=os.open(self.lock_path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(parent)
        finally:os.close(parent)

    def checkpoint(self):
        if active_fingerprints(ROOT)!=self.fingerprints:
            raise BootstrapFailure('bootstrap_source_changed_during_operation')

    def _run(self,kind,command,timeout=120):
        value=self.native.run(kind,command,cwd=self.target.parent,
            environment=self.environment,timeout=timeout)
        if value['exit_code']!=0:
            raise BootstrapFailure('bootstrap_'+kind+'_failed')
        return value

    def _json(self,value):
        raw=read_private(self.journal.root/value['streams']['stdout']['path'])
        return document(raw)

    def _interpreter(self,executable,*,venv=False):
        data=self._json(self._run('interpreter_probe',[str(executable),'-I','-B','-c',INTERPRETER_QUERY],30))
        if (set(data)!={'version','prefix','base_prefix','executable'} or type(data['version']) is not list
                or len(data['version'])!=3 or any(type(n)is not int for n in data['version'])
                or data['version'][:2]<[3,11]):
            raise BootstrapFailure('bootstrap_interpreter_version_unsupported')
        if venv and (Path(data['prefix']).resolve()!=self.target or data['prefix']==data['base_prefix']):
            raise BootstrapFailure('bootstrap_virtual_environment_prefix_mismatch')
        return data

    def preflight(self):
        found=shutil.which(self.options['python'])
        if found is None:raise BootstrapFailure('bootstrap_interpreter_unavailable')
        # Keep a Venv invocation path; resolving it for execution would run pip
        # with the base interpreter and silently target the wrong environment.
        self.python=Path(found).absolute()
        self.base=self._interpreter(self.python)
        if self.profile=='validation-environment-v1':
            try:
                self.tool=select_tool(self.journal.root/'inputs/scripts/validation-toolchain.env',
                    self.journal.root/'inputs/scripts/opa-download-sources.json')
                locations(self.tool,self.request['opa_mirror'])
            except ValueError as error:
                code=('bootstrap_validation_platform_unsupported'
                    if str(error).startswith('Unsupported validation platform: ')
                    else 'bootstrap_policy_tool_configuration_invalid')
                raise BootstrapFailure(code) from error
            if not 1<=self.request['attempts']<=5 or not 1<=self.request['timeout']<=300:
                raise BootstrapFailure('bootstrap_policy_tool_limits_invalid')
            if not self.request['offline'] and shutil.which('curl') is None:
                raise BootstrapFailure('bootstrap_policy_transport_unavailable')
        git=shutil.which('git');self.source_identity={'source_revision':None,'source_tree':None,'source_worktree_clean':False}
        if git and (ROOT/'.git').exists():
            common=[str(Path(git).absolute()),'-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','safe.directory='+str(ROOT),'-C',str(ROOT)]
            result=self._run('source_git_identity',common+['rev-parse','HEAD','HEAD^{tree}'],30)
            rows=read_private(self.journal.root/result['streams']['stdout']['path']).decode().splitlines()
            if len(rows)!=2 or any(not re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}',r) for r in rows):
                raise BootstrapFailure('bootstrap_source_identity_invalid')
            status=self._run('source_git_status',common+['status','--porcelain','--untracked-files=all'],30)
            clean=read_private(self.journal.root/status['streams']['stdout']['path'])==b''
            self.source_identity={'source_revision':rows[0],'source_tree':rows[1],'source_worktree_clean':clean}
        if not self.development and not self.source_identity['source_worktree_clean']:
            raise BootstrapFailure('bootstrap_committed_source_or_explicit_development_required')

    def environment_python_executable(self):
        binary=self.target/'bin/python'
        if (self.target/'bin').is_symlink():raise BootstrapFailure('bootstrap_environment_bin_alias_forbidden')
        present=binary.is_file() and os.access(binary,os.X_OK)
        if present:self._interpreter(binary,venv=True)
        return bool(present)

    def create_environment(self):
        self._run('environment_creation',[str(self.python),'-I','-B','-m','venv',str(self.target)],180)
        self._interpreter(self.target/'bin/python',venv=True)

    def install_dependencies(self):
        self._interpreter(self.target/'bin/python',venv=True)
        name='requirements-validation.lock' if self.profile=='validation-environment-v1' else 'requirements-source-document-intake.lock'
        command=[str(self.target/'bin/python'),'-I','-B','-m','pip','--disable-pip-version-check','install','--require-hashes']
        if self.request['offline']:command+=['--no-index']
        if self.wheelhouse is not None:command+=['--find-links',str(self.wheelhouse)]
        command+=['--requirement',str(self.journal.root/'inputs'/name)]
        self._run('dependency_install',command,900)
        query='import importlib.metadata,json;print(json.dumps({n:importlib.metadata.version(n) for n in '+repr(list(self.expected))+'}))'
        self.distributions=self._json(self._run('dependency_versions',[str(self.target/'bin/python'),'-I','-B','-c',query],60))
        if self.distributions!=self.expected:raise BootstrapFailure('bootstrap_dependency_versions_mismatch')

    def ensure_policy_tool(self):
        program=self.journal.root/'inputs';script=program/'scripts/install_validation_opa.py'
        code=('import runpy,sys;sys.path.insert(0,'+repr(str(program/'scripts'))+');sys.argv='+
            repr([str(script),'--destination',str(self.target/'bin/opa'),'--cache',str(self.cache),
                  '--mirror',self.request['opa_mirror'],'--attempts',str(self.request['attempts']),
                  '--timeout',str(self.request['timeout']),*(['--offline'] if self.request['offline'] else [])])+\
            ';runpy.run_path(sys.argv[0],run_name="__main__")')
        self._run('policy_tool_install',[str(self.python),'-I','-S','-B','-c',code],1500)

    def verify_policy_tool_version(self):
        binary=self.target/'bin/opa'
        if binary.is_symlink() or not binary.is_file() or binary.stat().st_size>128*1024**2:
            raise BootstrapFailure('bootstrap_policy_tool_file_invalid')
        with binary.open('rb') as handle:sha=hashlib.file_digest(handle,'sha256').hexdigest()
        if sha!=self.tool.sha256:raise BootstrapFailure('bootstrap_policy_tool_checksum_mismatch')
        result=self._run('policy_tool_version',[str(binary),'version'],15)
        raw=read_private(self.journal.root/result['streams']['stdout']['path']).decode()
        if not re.search(r'^Version:\s*'+re.escape(self.tool.version)+r'\s*$',raw,re.M):
            raise BootstrapFailure('bootstrap_policy_tool_version_mismatch')
        self.tools={'policy_tool_version':self.tool.version,'policy_tool_sha256':sha}

    def check_dependency_consistency(self):
        self._run('dependency_consistency',[str(self.target/'bin/python'),'-I','-B','-m','pip','check'],120)

    def render_ready_message(self):
        label='Validation environment' if self.profile=='validation-environment-v1' else 'Source document intake environment'
        self.messages=[label+' ready: '+str(self.target)]

    def perform(self, action):
        actions={'preflight':self.preflight,'environment_python_executable':self.environment_python_executable,
            'create_environment':self.create_environment,'install_dependencies':self.install_dependencies,
            'ensure_policy_tool':self.ensure_policy_tool,'verify_policy_tool_version':self.verify_policy_tool_version,
            'check_dependency_consistency':self.check_dependency_consistency,'render_ready_message':self.render_ready_message}
        if action not in actions:raise BootstrapFailure('bootstrap_action_unsupported')
        self.checkpoint();value=actions[action]();self.checkpoint();return value

    def finish(self, result, *, code=None):
        values={**result,'profile':self.profile,'environment':str(self.target),
            'source_identity':getattr(self,'source_identity',None),'distributions':self.distributions,
            'tools':self.tools,'messages':self.messages,'package_content_integrity_reverified':False}
        if code is not None:values['code']=code
        return {**self.journal.finish(values),'environment':str(self.target),'distributions':self.distributions,
                'tools':self.tools,'diagnostics':[] if code is None else [code]}

    def close(self):
        if self.journal is not None:self.journal.close()
        if self.lock_fd is not None:
            os.close(self.lock_fd);self.lock_fd=None
        self.closed=True

    def __enter__(self):return self
    def __exit__(self,*ignored):self.close()
