"""Closed, explicit original local-Git calls; no native execution in replay."""
from types import SimpleNamespace
import codecs,hashlib,json,re
from pathlib import PurePosixPath
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError
from lib.synthetic_lifecycle_io import path_spec

MAX_STREAM=256*1024
SAFETY=['--no-optional-locks','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','protocol.allow=never']

SIGNALS={
    'Linux':dict(enumerate(('SIGHUP','SIGINT','SIGQUIT','SIGILL','SIGTRAP','SIGABRT',
        'SIGBUS','SIGFPE','SIGKILL','SIGUSR1','SIGSEGV','SIGUSR2','SIGPIPE','SIGALRM',
        'SIGTERM','SIGSTKFLT','SIGCHLD','SIGCONT','SIGSTOP','SIGTSTP','SIGTTIN','SIGTTOU',
        'SIGURG','SIGXCPU','SIGXFSZ','SIGVTALRM','SIGPROF','SIGWINCH','SIGIO','SIGPWR','SIGSYS'),1)),
    'Darwin':dict(enumerate(('SIGHUP','SIGINT','SIGQUIT','SIGILL','SIGTRAP','SIGABRT',
        'SIGEMT','SIGFPE','SIGKILL','SIGBUS','SIGSEGV','SIGSYS','SIGPIPE','SIGALRM',
        'SIGTERM','SIGURG','SIGSTOP','SIGTSTP','SIGCONT','SIGCHLD','SIGTTIN','SIGTTOU',
        'SIGIO','SIGXCPU','SIGXFSZ','SIGVTALRM','SIGPROF','SIGWINCH','SIGINFO','SIGUSR1','SIGUSR2'),1))}
SIGNALS['Linux'].update({34:'SIGRTMIN',64:'SIGRTMAX'})

def signal_diagnostic(context,code,command):
    if (type(context) is not dict or set(context)!={'implementation','version','system'}
            or context['implementation']!='cpython' or type(context['system']) is not str or context['system'] not in SIGNALS
            or type(context['version']) is not list or len(context['version'])!=3
            or any(type(n) is not int or n<0 for n in context['version'])
            or context['version'][0]!=3 or context['version'][1]<10
            or type(code) is not int or not -(64 if context['system']=='Linux' else 31)<=code<0):
        failure('signal_context_changed')
    number=-code;name=SIGNALS[context['system']].get(number)
    label=f'<Signals.{name}: {number}>' if name is not None else f'unknown signal {number}'
    return f"Command '{command}' died with {label}."

def request(command,options,root):
    if type(command) is not list or not command or any(type(v) is not str or len(v)>8192 or '\0' in v for v in command):
        raise InputAdmissionError('documentation_original_git_arguments_required')
    if options!={'cwd':root,'check':True,'capture_output':True,'text':True}:
        raise InputAdmissionError('documentation_original_git_options_required')
    if not (command==['git','ls-files','*.md'] or len(command)==5
            and command[:4]==['git','diff','--name-only','--diff-filter=ACDMR']):
        raise InputAdmissionError('documentation_original_git_command_required')
    if command[1]=='diff' and command[4].startswith('-'):
        raise InputAdmissionError('documentation_git_read_selector_required')
    label=str(root);path_spec(label,label,label)
    return {'command':command,'cwd':label,'check':True,'capture_output':True,'text':True}

def actual_arguments(label,command):
    return [label,*SAFETY,*command[1:],*(['--no-ext-diff','--no-textconv'] if command[1]=='diff' else [])]

def failure(message):raise IntegrityError('documentation_git_'+message)

def value(wire,args,blob):
    fields={'schema_version','command','cwd','actual_arguments','program','source_before','source_after',
            'effective_encoding','returncode','stdout','stderr','start_error','return_error','signal_context','observation'}
    if type(wire) is not dict or set(wire)!=fields or type(wire['schema_version']) is not int or wire['schema_version']!=1:
        failure('wire_changed')
    if wire['command']!=args['command'] or wire['cwd']!=args['cwd']:failure('intent_binding_changed')
    program=wire['program']
    if program is not None:
        keys={'label','resolved','sha256','bytes','mode','uid','identity'}
        if (type(program) is not dict or set(program)!=keys or type(program['label']) is not str
                or type(program['resolved']) is not str or not program['resolved'].startswith('/')
                or type(program['sha256']) is not str or re.fullmatch('[a-f0-9]{64}',program['sha256']) is None
                or any(type(program[k]) is not int for k in ('bytes','mode','uid')) or not 0<program['bytes']<=256*1024**2
                or not 0<=program['mode']<=0o777 or not program['mode']&0o111 or program['mode']&0o022
                or program['uid']<0 or type(program['identity']) is not list or len(program['identity'])!=2
                or any(type(n) is not int or n<0 for n in program['identity'])):failure('program_identity_changed')
    label='git' if program is None else program['label']
    if wire['actual_arguments']!=actual_arguments(label,args['command']):failure('actual_arguments_changed')
    for context in (wire['source_before'],wire['source_after']):
        if (type(context) is not dict or set(context)!={'identity','mode','uid'} or type(context['identity']) is not list
                or len(context['identity'])!=2 or any(type(n) is not int or n<0 for n in context['identity'])
                or type(context['mode']) is not int or not 0<=context['mode']<=0o777 or context['mode']&0o022
                or type(context['uid']) is not int or context['uid']<0):failure('source_identity_changed')
    if wire['source_before']!=wire['source_after']:failure('source_moved')
    if program is not None:
        resolved=PurePosixPath(program['resolved'])
        if (str(resolved)!=program['resolved'] or '..' in resolved.parts
                or resolved.is_relative_to(PurePosixPath(args['cwd']))
                or program['uid'] not in (0,wire['source_before']['uid'])
                or not program['label'] or len(program['label'])>8192 or '\0' in program['label']):failure('program_source_or_owner_changed')
    codec=wire['effective_encoding']
    if type(codec) is not str or not codec or len(codec)>128:failure('codec_changed')
    try:codecs.lookup(codec)
    except LookupError:failure('codec_unknown')
    raw=[]
    for key in ('stdout','stderr'):
        ref=wire[key]
        if type(ref) is not dict or set(ref)!={'sha256','bytes'} or type(ref['bytes']) is not int or not 0<=ref['bytes']<=MAX_STREAM:failure('raw_stream_changed')
        data=blob(ref)
        if type(data) is not bytes or len(data)!=ref['bytes'] or hashlib.sha256(data).hexdigest()!=ref['sha256']:failure('raw_stream_binding_changed')
        raw.append(data)
    observation=wire['observation']
    flags={'started','terminal_observed','returncode','timed_out','stream_budget_exceeded','OS_network_or_process_tree_isolation_attested'}
    if type(observation) is not dict or set(observation)!=flags or any(type(observation[k]) is not bool for k in flags-{'returncode'}):failure('process_observation_changed')
    if observation['timed_out'] or observation['stream_budget_exceeded'] or observation['OS_network_or_process_tree_isolation_attested']:failure('process_limit_or_authority_changed')
    code=wire['returncode'];start=wire['start_error'];returned=wire['return_error'];context=wire['signal_context']
    if (code is None or type(code) is int and code>=0) and context is not None:failure('unexpected_signal_context')
    if start is not None:
        if (code is not None or returned is not None or observation['started'] or observation['terminal_observed']
                or observation['returncode'] is not None or any(raw) or type(start) is not dict
                or set(start)!={'type','message'} or start['type'] not in ('OSError','FileNotFoundError','PermissionError','NotADirectoryError','IsADirectoryError')
                or type(start['message']) is not str or len(start['message'])>65536):failure('start_error_changed')
        raise RetainedOutputError(start['type'],start['message'])
    if (type(code) is not int or not -255<=code<=255 or not observation['started'] or not observation['terminal_observed']
            or type(observation['returncode']) is not int or observation['returncode']!=code or program is None):failure('terminal_changed')
    if code==0 and returned is not None:failure('unexpected_return_error')
    if code and (type(returned) is not dict or set(returned)!={'type','message'} or returned['type']!='CalledProcessError'
                 or type(returned['message']) is not str or len(returned['message'])>65536):failure('return_error_changed')
    # Decode the original text result even for nonzero exits: subprocess does
    # decoding before check=True raises CalledProcessError.
    stdout,stderr=[data.decode(codec).replace('\r\n','\n').replace('\r','\n') for data in raw]
    if code:
        if (type(returned) is not dict or set(returned)!={'type','message'} or returned['type']!='CalledProcessError'
                or type(returned['message']) is not str or len(returned['message'])>65536):failure('return_error_changed')
        if code>0 and returned['message']!=f"Command '{args['command']}' returned non-zero exit status {code}.":failure('return_error_diagnostic_changed')
        if code<0 and returned['message']!=signal_diagnostic(context,code,args['command']):failure('signal_diagnostic_changed')
        raise RetainedOutputError('CalledProcessError',returned['message'])
    if returned is not None:failure('unexpected_return_error')
    return SimpleNamespace(stdout=stdout,stderr=stderr,returncode=code)

class ReplayGit:
    def __init__(self,owner,root):self.owner,self.root,self.calls=owner,root,0
    def error_type(self,error):
        if not isinstance(error,re.error):return type(error).__name__
        row=self.owner.row()
        if type(row) is not dict or set(row)!={'kind','implementation','version','regex_error_type'} or row['kind']!='documentation-original-regex-context' or row['implementation']!='cpython':failure('regex_context_changed')
        version=row['version']
        if type(version) is not list or len(version)!=3 or any(type(n) is not int or n<0 for n in version) or version[0]!=3 or not 10<=version[1]<=99:failure('regex_runtime_changed')
        expected='PatternError' if version[1]>=13 else 'error'
        if row['regex_error_type']!=expected:failure('regex_type_runtime_changed')
        return expected
    def run(self,command,**options):
        args=request(command,options,self.root);self.calls+=1
        if self.calls>32:failure('operation_budget')
        expected={'kind':'intent','operation':self.owner.position,'action':'documentation-local-git','arguments':args}
        if (self.owner.position>=self.owner.limit or json.dumps(self.owner.events[self.owner.position],sort_keys=True,separators=(',',':'))
                !=json.dumps(expected,sort_keys=True,separators=(',',':'))):failure('typed_intent_changed')
        ok,wire=self.owner.outcome('documentation-local-git',args,'json')
        if not ok:failure('incomplete_process_capture')
        return value(wire,args,self.owner.blob)
