"""Own-source POSIX Workbench first/repeated start, without ambient authority.

Only bounded admission/bootstrap probes are captured. The long-running server
replaces the coordinator and inherits a shared environment lease. An exec intent
is not an HTTP-ready, stopped, compliance or production-approval observation.
"""
from pathlib import Path
import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import sys

from lib.environment_bootstrap import BootstrapFailure
from lib.v2_source import active_fingerprints, selected_paths
from lib.providers.environment_bootstrap_native import (normalized,private_parent,
    INTERPRETER_QUERY,NETWORK_KEYS)
from lib.providers.environment_bootstrap_storage import (AUTHORITY,encoded,document,
    write_new,read_private,owned_directory,inspect as inspect_bootstrap)
from lib.providers.environment_bootstrap_process import BootstrapProcesses
from lib.providers.opa_bootstrap import select_tool

ROOT=Path(__file__).resolve().parents[3]
REQUIRED=frozenset(('scripts/start_axiom_v2_workbench.py','scripts/axiom_v2.py',
    'scripts/bootstrap_axiom_v2_environment.py','scripts/serve_governance_workbench.py',
    'scripts/lib/workbench_startup.py','scripts/lib/workbench_startup_application.py',
    'scripts/lib/workbench_startup_ports.py','scripts/lib/providers/workbench_startup_native.py'))


class StartupJournal:
    """Private exclusive fsynced phase/native records; never a liveness oracle."""
    def __init__(self,parent,request,source):
        owned_directory(parent)
        self.root=parent/secrets.token_hex(16);self.root.mkdir(mode=0o700)
        self.identity=self.root.stat()
        self.sequence=0;self.phase=None
        write_new(self.root/'request.json',request)
        write_new(self.root/'source.json',source)
        self.append({'kind':'opened',**AUTHORITY})
    def append(self,event):
        owned_directory(self.root)
        current=self.root.stat()
        if (current.st_dev,current.st_ino)!=(self.identity.st_dev,self.identity.st_ino):
            raise ValueError('workbench_startup_journal_replaced')
        if self.sequence>=128:raise ValueError('workbench_startup_event_budget')
        write_new(self.root/f'event-{self.sequence:04d}.json',event)
        self.sequence+=1
    def before(self,action):
        if self.phase is not None:raise ValueError('workbench_startup_phase_already_open')
        token=self.sequence
        self.append({'kind':'phase-intent','phase':token,'action':action})
        self.phase=token;return token
    def after(self,token,value):
        if self.phase!=token:raise ValueError('workbench_startup_phase_mismatch')
        self.append({'kind':'phase-returned','phase':token,'value':value});self.phase=None
    def failed(self,token,code):
        if self.phase!=token:raise ValueError('workbench_startup_phase_mismatch')
        self.append({'kind':'phase-failed','phase':token,'code':code});self.phase=None


class NativeStartup:
    def __init__(self,options):
        self.options=options;self.lease=None
        self.target=normalized(options['environment']);self.node=normalized(options['instance'])
        self.development=bool(options.get('development'))
        self.state=normalized(options.get('state_directory') or self.target.parent/'.axiom-workbench-starts')
        for path in (self.target,self.node,self.state):
            if path==ROOT or path.is_relative_to(ROOT) or ROOT.is_relative_to(path):
                raise BootstrapFailure('workbench_startup_paths_outside_product_required')
        for a,b in ((self.target,self.node),(self.target,self.state),(self.node,self.state)):
            if a.is_relative_to(b) or b.is_relative_to(a):
                raise BootstrapFailure('workbench_startup_separate_paths_required')
        if type(options['port']) is not int or not 1024<=options['port']<=65535:
            raise BootstrapFailure('workbench_startup_instance_port_required')
        if options.get('enable_pr') and (self.development or not options.get('publication_profile')):
            raise BootstrapFailure('workbench_startup_explicit_publication_profile_required')
        private_parent(self.state)
        self.fingerprints=active_fingerprints(ROOT)
        if not REQUIRED<=set(selected_paths(ROOT)):
            raise BootstrapFailure('workbench_startup_closure_not_registered')
        self.journal=StartupJournal(self.state,{
            'profile':'workbench-startup-v1','environment':str(self.target),'instance':str(self.node),
            'port':options['port'],'development':self.development,
            'publisher_requested':bool(options.get('enable_pr')),
            'source_package_contents_attested':False},
            {'source_root':str(ROOT),'active_fingerprints':self.fingerprints})
        self.native=BootstrapProcesses(self.journal)
        self.environment={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'LANG':'C.UTF-8',
            'PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1','PIP_CONFIG_FILE':'/dev/null',
            'PIP_DISABLE_PIP_VERSION_CHECK':'1','GIT_CONFIG_GLOBAL':'/dev/null',
            'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_COUNT':'0','GIT_TERMINAL_PROMPT':'0',
            'GIT_ASKPASS':'/bin/false','GIT_NO_REPLACE_OBJECTS':'1','GIT_NO_LAZY_FETCH':'1',
            'GIT_ALLOW_PROTOCOL':''}
        for name in NETWORK_KEYS:
            if name in os.environ:self.environment[name]=os.environ[name]
        self.python=self.target/'bin/python'
        print(json.dumps({'startup_record':str(self.journal.root),'state':'admission',
            'HTTP_readiness_observed':False,**AUTHORITY}),file=sys.stderr,flush=True)

    def checkpoint(self):
        if active_fingerprints(ROOT)!=self.fingerprints:
            raise BootstrapFailure('workbench_startup_source_changed')

    def _run(self,kind,command,timeout=60):
        outcome=self.native.run(kind,command,cwd=self.target.parent,
            environment=self.environment,timeout=timeout)
        if outcome['exit_code']!=0:raise BootstrapFailure('workbench_startup_'+kind+'_failed')
        return read_private(self.journal.root/outcome['streams']['stdout']['path'])

    def _own(self,script,arguments,*,interpreter=None,stdlib=False):
        code=('import runpy,sys;sys.path.insert(0,'+repr(str(ROOT/'scripts'))+
            ');sys.argv='+repr([str(ROOT/'scripts'/script),*arguments])+
            ';runpy.run_path(sys.argv[0],run_name="__main__")')
        return [str(interpreter or self.python),'-I',*(['-S'] if stdlib else []),'-B','-c',code]

    def preflight(self):
        self.target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        if self.target.exists():
            row=self.target.stat()
            if not stat.S_ISDIR(row.st_mode) or row.st_uid!=os.geteuid() or row.st_mode&0o022:
                raise BootstrapFailure('workbench_startup_owned_environment_required')
            if any(self.target.iterdir()) and not (self.target/'pyvenv.cfg').is_file():
                raise BootstrapFailure('workbench_startup_environment_unrecognized')
        if (self.target/'bin').is_symlink():
            raise BootstrapFailure('workbench_startup_environment_bin_alias_forbidden')
        git=shutil.which('git')
        if git is None or not (ROOT/'.git').exists():
            raise BootstrapFailure('workbench_startup_git_source_required')
        command=[str(Path(git).absolute()),'-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false',
            '-c','safe.directory='+str(ROOT),'-C',str(ROOT)]
        status=self._run('source_status',command+['status','--porcelain','--untracked-files=all'])
        if status.strip() and not self.development:
            raise BootstrapFailure('workbench_startup_clean_source_or_explicit_development_required')

    def environment_python_executable(self):
        return bool(self.python.is_file() and os.access(self.python,os.X_OK))

    def bootstrap_environment(self):
        base=shutil.which(self.options['python'])
        if base is None:raise BootstrapFailure('workbench_startup_base_interpreter_unavailable')
        args=['validation','--environment',str(self.target),'--python',str(Path(base).absolute()),
            '--attempts',str(self.options.get('attempts',3)),
            '--timeout',str(self.options.get('timeout',120))]
        for option in ('wheelhouse','opa_cache'):
            if self.options.get(option) is not None:
                args+=['--'+option.replace('_','-'),str(normalized(self.options[option]))]
        if self.options.get('opa_mirror'):args+=['--opa-mirror',self.options['opa_mirror']]
        for flag in ('offline','development'):
            if self.options.get(flag):args+=['--'+flag]
        report=document(self._run('environment_bootstrap',self._own('bootstrap_axiom_v2_environment.py',
            args,interpreter=Path(base).absolute(),stdlib=True),1800))
        if (report.get('state')!='complete' or report.get('exit_code')!=0
                or report.get('environment')!=str(self.target)):
            raise BootstrapFailure('workbench_startup_bootstrap_result_mismatch')
        self.journal.append({'kind':'environment-bootstrap-record','record_root':report['record_root']})

    def _lease(self):
        from lib.providers.environment_lease import shared_environment_lease
        self.lease=shared_environment_lease(self.target,prefix='workbench_startup')

    def admit_environment(self):
        self._lease()
        data=document(self._run('interpreter_probe',[str(self.python),'-I','-B','-c',INTERPRETER_QUERY]))
        if (type(data.get('prefix')) is not str or type(data.get('base_prefix')) is not str
                or data['prefix']==data['base_prefix'] or Path(data['prefix']).resolve()!=self.target
                or type(data.get('version')) is not list or len(data['version'])!=3
                or any(type(n) is not int for n in data['version']) or data['version'][:2]<[3,11]):
            raise BootstrapFailure('workbench_startup_virtual_environment_prefix_mismatch')
        pins={}
        for line in (ROOT/'requirements-validation.txt').read_text().splitlines():
            if line and not line.startswith('#'):
                if not re.fullmatch(r'[A-Za-z0-9_.-]+==[^\s=]+',line):
                    raise BootstrapFailure('workbench_startup_unpinned_own_requirements')
                name,version=line.split('==',1);pins[name]=version
        query='import importlib.metadata,json;print(json.dumps({n:importlib.metadata.version(n) for n in '+repr(list(pins))+'}))'
        if document(self._run('dependency_versions',[str(self.python),'-I','-B','-c',query]))!=pins:
            raise BootstrapFailure('workbench_startup_dependency_version_mismatch')
        self._run('dependency_consistency',[str(self.python),'-I','-B','-m','pip','check'])
        opa=self.target/'bin/opa'
        if opa.is_symlink() or not opa.is_file() or not os.access(opa,os.X_OK) or opa.stat().st_size>128*1024**2:
            raise BootstrapFailure('workbench_startup_policy_tool_invalid')
        tool=select_tool(ROOT/'scripts/validation-toolchain.env',ROOT/'scripts/opa-download-sources.json')
        with opa.open('rb') as stream:checksum=hashlib.file_digest(stream,'sha256').hexdigest()
        if checksum!=tool.sha256:raise BootstrapFailure('workbench_startup_policy_tool_checksum_mismatch')

    def admit_instance(self):
        if self.node.exists():
            owned_directory(self.node)
        if not self.node.exists():
            args=['--instance',str(self.node),'init','--port',str(self.options['port']),
                '--opa',str(self.target/'bin/opa')]
            if self.development:args+=['--development']
            self._run('instance_initialization',self._own('axiom_v2.py',args),120)
        # Exact source generation, tool, mode and caller-selected port must match;
        # an existing/partial/foreign instance is never silently reinitialized.
        query=('import sys;sys.path.insert(0,'+repr(str(ROOT/'scripts'))+');'
            'from lib.v2_application import instance; p,s=instance('+repr(str(self.node))+');'
            'assert s["port"]=='+repr(self.options['port'])+' and s["development"] is '+repr(self.development)+
            ' and s["opa"]=='+repr(str((self.target/'bin/opa').resolve()))+
            ',"workbench_startup_instance_profile_mismatch"')
        self._run('instance_admission',[str(self.python),'-I','-B','-c',query],120)

    def handoff_workbench(self):
        args=['--instance',str(self.node),'workbench']
        if self.options.get('enable_pr'):args+=['--enable-pr']
        if self.options.get('publication_profile'):
            args+=['--publication-profile',str(normalized(self.options['publication_profile']))]
        self.checkpoint()
        os.set_inheritable(self.lease,True)
        # Success does not return; same PID, native exit and signals preserved.
        os.execve(self.python,self._own('axiom_v2.py',args),self.environment)
        raise RuntimeError('workbench_startup_exec_unexpectedly_returned')

    def perform(self,action):
        methods={name:getattr(self,name) for name in ('preflight','environment_python_executable',
            'bootstrap_environment','admit_environment','admit_instance','handoff_workbench')}
        self.checkpoint();value=methods[action]();self.checkpoint();return value

    def diagnostic(self,code,state):
        self.journal.append({'kind':'coordinator-stopped','state':state,'code':code,
            'HTTP_readiness_observed':False,**AUTHORITY})
        print(json.dumps({'state':state,'diagnostics':[code],'startup_record':str(self.journal.root),
            **AUTHORITY}),file=sys.stderr,flush=True)

    def close(self):
        if self.lease is not None:os.close(self.lease);self.lease=None
    def __enter__(self):return self
    def __exit__(self,*ignored):self.close()
