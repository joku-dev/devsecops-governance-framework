"""Explicit own-source POSIX suite effects before and after dependencies exist."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import sys

from lib.validation_suite import Observation,PROFILE
from lib.v2_source import active_fingerprints,selected_paths
from lib.providers.environment_bootstrap_native import normalized,private_parent
from lib.providers.environment_bootstrap_storage import read_private,document,AUTHORITY
from lib.providers.environment_bootstrap_process import BootstrapProcesses
from lib.providers.environment_lease import shared_environment_lease
from lib.providers.opa_bootstrap import select_tool
from lib.providers.validation_suite_storage import SuiteJournal,SuiteSink,raw_new

ROOT=Path(__file__).resolve().parents[3]
REQUIRED=frozenset(('scripts/run_axiom_v2_validation_suite.py','scripts/lib/validation_suite.py',
    'scripts/lib/validation_suite_application.py','scripts/lib/validation_suite_ports.py',
    'scripts/lib/providers/validation_suite_native.py','scripts/lib/providers/validation_suite_storage.py',
    'scripts/lib/providers/validation_suite_full.py','scripts/lib/providers/environment_lease.py',
    'scripts/lib/provenance_validation.py'))
QUERY=('from importlib.metadata import PackageNotFoundError,version\nfrom pathlib import Path\nimport sys\nerrors=[]\n'
       'for requirement in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():\n'
       ' if not requirement or requirement.startswith("#"):continue\n'
       ' package,expected=requirement.split("==",1)\n'
       ' try:actual=version(package)\n'
       ' except PackageNotFoundError:\n  errors.append(f"{package} is not installed");continue\n'
       ' if actual!=expected:errors.append(f"{package}=={actual}; expected {expected}")\n'
       'if errors:raise SystemExit("Validation dependency mismatch:\\n- "+"\\n- ".join(errors))\n')


def status(code):return 128-code if code<0 else code


class NativeSuite:
    def __init__(self,options):
        self.options=dict(options);self.full=None;self.lease=None
        self.target=normalized(options['environment']);self.python=self.target/'bin/python';self.opa=self.target/'bin/opa'
        self.options['environment']=self.target
        state=normalized(options.get('state_directory') or self.target.parent/'.axiom-validation-suite-records')
        paths=[self.target,state]
        for name in ('instance','package'):
            if options.get(name) is not None:self.options[name]=normalized(options[name])
        if self.options.get('instance') is not None:paths.append(self.options['instance'])
        for path in paths:
            if path==ROOT or path.is_relative_to(ROOT) or ROOT.is_relative_to(path):raise ValueError('validation_suite_paths_outside_product_required')
        for i,path in enumerate(paths):
            for other in paths[i+1:]:
                if path.is_relative_to(other) or other.is_relative_to(path):raise ValueError('validation_suite_separate_paths_required')
        if options.get('development') and not options['check_tools']:raise ValueError('validation_suite_full_committed_source_required')
        if not options['check_tools'] and not re.fullmatch('[a-f0-9]{64}',options.get('sha256') or ''):
            raise ValueError('validation_suite_exact_package_pin_required')
        private_parent(state)
        self.fingerprints=active_fingerprints(ROOT)
        if not REQUIRED<=set(selected_paths(ROOT)):raise ValueError('validation_suite_source_closure_not_registered')
        self.toolchain=(ROOT/'scripts/validation-toolchain.env').read_bytes()
        self.requirements=(ROOT/'requirements-validation.txt').read_bytes()
        pins=dict(line.split('=',1) for line in self.toolchain.decode().splitlines() if line and not line.startswith('#'))
        self.expected_opa_version=pins['OPA_VERSION']
        self.arguments=['--check-tools'] if options['check_tools'] else []
        request={'profile':PROFILE,'arguments':self.arguments,'environment':str(self.target),
            'expected_opa_version':self.expected_opa_version,'check_tools':options['check_tools'],
            'development':options.get('development',False),'instance':None if options.get('instance') is None else str(self.options['instance']),
            'package':None if options.get('package') is None else str(self.options['package']),
            'package_sha256':options.get('sha256'),'at':options.get('at'),
            'parent_record':None if options.get('parent_record') is None else str(options['parent_record'])}
        self.journal=SuiteJournal(state,request,{'source_root':str(ROOT),'active_fingerprints':self.fingerprints})
        raw_new(self.journal.root/'requirements-validation.txt',self.requirements)
        raw_new(self.journal.root/'validation-toolchain.env',self.toolchain)
        self.native=BootstrapProcesses(self.journal);self.sink=SuiteSink()
        if options['output']!='legacy':
            print(json.dumps({'state':'admission','record_root':str(self.journal.root),**AUTHORITY}),file=sys.stderr,flush=True)
        self.environment={'PATH':os.pathsep.join([str(self.target/'bin'),os.environ.get('PATH','/usr/bin:/bin'),'/usr/bin','/bin']),
            'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1','PYTHONNOUSERSITE':'1',
            'PIP_CONFIG_FILE':'/dev/null','PIP_DISABLE_PIP_VERSION_CHECK':'1','PIP_NO_INDEX':'1',
            'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_COUNT':'0',
            'GIT_TERMINAL_PROMPT':'0','GIT_ASKPASS':'/bin/false','GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_ALLOW_PROTOCOL':''}

    def checkpoint(self):
        if active_fingerprints(ROOT)!=self.fingerprints:raise ValueError('validation_suite_product_changed_during_operation')

    def native_run(self,kind,command,*,cwd=None,timeout=120):
        value=self.native.run(kind,[str(v) for v in command],cwd=ROOT if cwd is None else cwd,
            environment=self.environment,timeout=timeout)
        raw={name:read_private(self.journal.root/row['path'],8*1024**2) for name,row in value['streams'].items()}
        return Observation(status(value['exit_code']),**raw)

    def handoff_if_needed(self):
        # Source admission is a separate technical phase, not a replayed V1 step.
        self.journal.begin_admission('source-and-environment')
        try:
            git=shutil.which('git')
            if git is None:raise ValueError('validation_suite_own_git_source_required')
            result=self.native_run('source_status',[git,'-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','safe.directory='+str(ROOT),'-C',ROOT,'status','--porcelain','--untracked-files=all'])
            if result.returncode or result.stdout.strip() and not self.options.get('development'):
                raise ValueError('validation_suite_clean_source_or_explicit_development_required')
            self.source_revision=self.native_run('source_revision',[git,'-C',ROOT,'rev-parse','HEAD']).stdout.decode().strip()
            if not re.fullmatch('[a-f0-9]{40}',self.source_revision):raise ValueError('validation_suite_source_revision_invalid')
            if (self.target/'bin').is_symlink():raise ValueError('validation_suite_environment_bin_alias_forbidden')
            present=all(p.is_file() and os.access(p,os.X_OK) for p in (self.python,self.opa))
            if present:
                self.lease=shared_environment_lease(self.target,prefix='validation_suite')
                if Path(sys.prefix).resolve()!=self.target:
                    if self.options.get('parent_record'):raise ValueError('validation_suite_virtual_environment_prefix_mismatch')
                    self.journal.append({'kind':'python-handoff-intent','interpreter':str(self.python),'HTTP_or_validation_readiness_observed':False})
                    command=[str(self.python),'-I','-B',str(ROOT/'scripts/run_axiom_v2_validation_suite.py'),'--environment',str(self.target),'--state-directory',str(self.journal.root.parent),'--output',self.options['output'],'--parent-record',str(self.journal.root)]
                    if self.options['check_tools']:command+=['--check-tools']
                    if self.options.get('development'):command+=['--development']
                    for name in ('instance','package','sha256','at'):
                        if self.options.get(name) is not None:command+=['--'+name,str(self.options[name])]
                    os.set_inheritable(self.lease,True)
                    os.execve(self.python,command,self.environment)
                    raise RuntimeError('validation_suite_exec_unexpectedly_returned')
                parent=self.options.get('parent_record')
                if parent is not None:
                    parent=normalized(parent);request=document(read_private(parent/'request.json'));source=document(read_private(parent/'source.json'))
                    if request['environment']!=str(self.target) or source!={'source_root':str(ROOT),'active_fingerprints':self.fingerprints}:
                        raise ValueError('validation_suite_python_handoff_binding_changed')
                probe=self.native_run('environment_prefix',[self.python,'-I','-B','-c','import sys,json;print(json.dumps({"prefix":sys.prefix,"base_prefix":sys.base_prefix}))'])
                data=json.loads(probe.stdout)
                if probe.returncode or data['prefix']==data['base_prefix'] or Path(data['prefix']).resolve()!=self.target:
                    raise ValueError('validation_suite_virtual_environment_prefix_mismatch')
        finally:self.journal.end_admission()

    def perform(self,action):
        self.checkpoint()
        if action=='require_tools':
            present=all(p.is_file() and os.access(p,os.X_OK) for p in (self.python,self.opa))
            return Observation(0) if present else Observation(1,b'',('Validation environment is incomplete: '+str(self.target)+'\nRun: ./scripts/bootstrap_validation_env.sh\n').encode())
        if action=='opa_version':
            tool=select_tool(ROOT/'scripts/validation-toolchain.env',ROOT/'scripts/opa-download-sources.json')
            if self.opa.is_symlink() or hashlib.sha256(self.opa.read_bytes()).hexdigest()!=tool.sha256:
                raise ValueError('validation_suite_pinned_policy_tool_required')
            native=self.native_run('policy_version',[self.opa,'version'])
            # Preserve actual host awk semantics, including CR/interior-LF data.
            awk=shutil.which('awk',path=self.environment['PATH'])
            if awk is None:raise ValueError('validation_suite_version_parser_unavailable')
            incoming=self.journal.root/'policy-version-input.bin';raw_new(incoming,native.stdout)
            parsed=self.native_run('policy_version_parser',[awk,'/^Version:/ {print $2}',incoming])
            return Observation(parsed.returncode or native.returncode,parsed.stdout,native.stderr+parsed.stderr)
        if action=='dependency_versions':
            return self.native_run('dependency_versions',[self.python,'-I','-B','-c',QUERY,self.journal.root/'requirements-validation.txt'])
        if action=='dependency_consistency':return self.native_run('dependency_consistency',[self.python,'-I','-B','-m','pip','check'])
        if self.full is None:
            from lib.providers.validation_suite_full import FullSuite
            self.full=FullSuite(self)
        if action=='opa_check':
            self.full.backend.checkpoint()
            value=self.native_run('policy_check',[self.opa,'check',self.full.backend.root/'policies/opa'],cwd=self.full.backend.root)
            self.full.backend.checkpoint();return value
        if action not in ('runtime_validation','repository_validation','provenance_validation','unit_tests'):
            raise ValueError('validation_suite_action_unsupported')
        result=getattr(self.full,action)();self.checkpoint()
        return Observation(status(result['returncode']),result['stdout'],result['stderr'])

    def finish(self,state,code,*,error=None):
        report={'profile':PROFILE,'state':state,'original_exit_code':code,'source_revision':getattr(self,'source_revision',None),
            'full_default_requested':not self.options['check_tools'],'full_unit_discovery_observed':bool(self.full and self.full.backend.unit_outcome),
            'unit_statistics':None if self.full is None else self.full.backend.unit_statistics,
            'exception_type':None if error is None else type(error).__name__,
            'diagnostics':[] if error is None else [str(error) if isinstance(error,ValueError) and re.fullmatch('[a-z][a-z0-9_]{0,100}',str(error)) else 'validation_suite_execution_incomplete'],
            'package_contents_attested':False,'native_execution_authenticated':False}
        return self.journal.finish(report,self.sink.bytes())
    def close(self):
        if self.lease is not None:os.close(self.lease);self.lease=None
    def __enter__(self):return self
    def __exit__(self,*ignored):self.close()
