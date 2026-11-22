"""Closed process and UTC-clock observations; replay never reads a provider or runs tools."""
import codecs,hashlib,re
from datetime import datetime,timezone
from pathlib import PurePosixPath
from types import SimpleNamespace
from lib.requirement_review_output import RetainedOutputError
from lib.requirement_validation_replay import IntegrityError
from lib.documentation_reconciliation_git import signal_diagnostic

MAX_STDOUT=8*1024**2
MAX_STDERR=256*1024
MAX_CALLS=1024

def fail(reason):raise IntegrityError('personal_transport_'+reason)

def context(value):
    if (type(value) is not dict or set(value)!={'identity','mode','uid'}
            or type(value['identity']) is not list or len(value['identity'])!=2
            or any(type(n) is not int or n<0 for n in value['identity'])
            or type(value['mode']) is not int or not 0<=value['mode']<=0o777 or value['mode']&0o022
            or type(value['uid']) is not int or value['uid']<0):fail('source_context_changed')
    return value

def process_value(wire,spec,profile,blob,*,emit_stderr,stream_limits=(MAX_STDOUT,MAX_STDERR)):
    if type(stream_limits) is not tuple or len(stream_limits)!=2 or type(stream_limits[0]) is not int or not 0<stream_limits[0]<=16*1024**2 or type(stream_limits[1]) is not int or stream_limits[1]!=MAX_STDERR:fail("stream_profile_changed")
    fields={'schema_version','specification','actual_arguments','program','source_before','source_after',
            'returncode','stdout','stderr','start_error','original_error','signal_context','effective_encoding','observation'}
    if type(wire) is not dict or set(wire)!=fields or type(wire['schema_version']) is not int or wire['schema_version']!=1 or wire['specification']!=spec:fail('wire_changed')
    before=context(wire['source_before']);after=context(wire['source_after'])
    if before!=after:fail('source_moved')
    identity=wire['program'];selected=None
    if identity is not None:
        keys={'label','resolved','sha256','bytes','mode','uid','identity'}
        if (type(identity) is not dict or set(identity)!=keys or type(identity['label']) is not str or not identity['label']
                or len(identity['label'])>8192 or '\0' in identity['label'] or type(identity['resolved']) is not str
                or not identity['resolved'].startswith('/') or str(PurePosixPath(identity['resolved']))!=identity['resolved']
                or '..' in PurePosixPath(identity['resolved']).parts or PurePosixPath(identity['resolved']).is_relative_to(PurePosixPath(spec['source_root']))
                or type(identity['sha256']) is not str or re.fullmatch('[a-f0-9]{64}',identity['sha256']) is None
                or type(identity['bytes']) is not int or not 0<identity['bytes']<=256*1024**2
                or type(identity['mode']) is not int or not 0<=identity['mode']<=0o777 or identity['mode']&0o022 or not identity['mode']&0o111
                or type(identity['uid']) is not int or identity['uid'] not in (0,before['uid'])
                or type(identity['identity']) is not list or len(identity['identity'])!=2 or any(type(n) is not int or n<0 for n in identity['identity'])):fail('program_identity_changed')
        selected=identity['label']
    if wire['actual_arguments']!=profile.actual_arguments(spec,selected):fail('actual_arguments_changed')
    raw=[]
    for name,limit in zip(('stdout','stderr'),stream_limits):
        ref=wire[name]
        if type(ref) is not dict or set(ref)!={'sha256','bytes'} or type(ref['bytes']) is not int or not 0<=ref['bytes']<=limit:fail('stream_changed')
        value=blob(ref)
        if type(value) is not bytes or len(value)!=ref['bytes'] or hashlib.sha256(value).hexdigest()!=ref['sha256']:fail('stream_binding_changed')
        raw.append(value)
    observation=wire['observation']
    flags={'started','terminal_observed','returncode','timed_out','stream_budget_exceeded','cleanup_signal_permission_denied','cleanup_absence_check','OS_network_or_process_tree_isolation_attested'}
    if (type(observation) is not dict or set(observation)!=flags
            or any(type(observation[k]) is not bool for k in flags-{'returncode','cleanup_absence_check'})
            or observation['stream_budget_exceeded'] or observation['OS_network_or_process_tree_isolation_attested']):fail('observation_changed')
    from lib.provider_ports import native_cleanup_observation_valid
    if not native_cleanup_observation_valid({**observation,'process_started':observation['started']}):fail('cleanup_unproven')
    code,start,error=wire['returncode'],wire['start_error'],wire['original_error']
    if type(error) not in (dict,type(None)):fail('original_error_changed')
    if spec['text']:
        codec=wire['effective_encoding']
        if type(codec) is not str or not codec or len(codec)>128:fail('text_encoding_changed')
        try:codecs.lookup(codec)
        except LookupError:fail('text_encoding_unknown')
    elif wire['effective_encoding'] is not None:fail('unexpected_text_encoding')
    if start is not None:
        if (code is not None or error is not None or wire['signal_context'] is not None
                or observation['started'] or observation['terminal_observed'] or observation['returncode'] is not None or observation['timed_out'] or any(raw)
                or type(start) is not dict or set(start)!={'type','message','errno','strerror','filename'}):fail('start_error_changed')
        from lib.workbook_import_io import READ_ERRORS
        if start['type'] not in READ_ERRORS or type(start['errno']) is not int or type(start['strerror']) is not str or start['filename'] not in (None,spec['original_arguments'][0]):fail('start_error_identity_changed')
        expected=READ_ERRORS[start['type']](start['errno'],start['strerror'],start['filename'])
        if str(expected)!=start['message']:fail('start_error_diagnostic_changed')
        raise RetainedOutputError(start['type'],start['message'])
    if (identity is None or type(code) is not int or not -255<=code<=255 or not observation['started']
            or not observation['terminal_observed'] or type(observation['returncode']) is not int or observation['returncode']!=code):fail('terminal_changed')
    if observation['timed_out'] and spec['kind'] in ('git-tree','git-run','git-checked-run'):fail('git_capture_deadline_is_not_original_verdict')
    run_capture=spec['kind'] in ('git-run','git-checked-run','opa-checked-run')
    unchecked_run=spec['kind']=='git-run'
    if run_capture and spec['text'] is not False:fail('binary_run_capture_required')
    if raw[1] and not run_capture:emit_stderr(wire['stderr'])
    if observation['timed_out']:
        if wire['signal_context'] is not None:fail('timeout_signal_conflict')
        expected={'type':'TimeoutExpired','message':f"Command '{spec['original_arguments']}' timed out after {spec['timeout']} seconds"}
    elif unchecked_run:
        if wire['signal_context'] is not None:fail('run_signal_context_not_used')
        expected=None
    elif code:
        if code<0:message=signal_diagnostic(wire['signal_context'],code,spec['original_arguments'])
        else:
            if wire['signal_context'] is not None:fail('unexpected_signal_context')
            message=f"Command '{spec['original_arguments']}' returned non-zero exit status {code}."
        expected={'type':'CalledProcessError','message':message}
    else:
        if wire['signal_context'] is not None:fail('unexpected_signal_context')
        expected=None
    # check_output(text=True) decodes stdout before check=True raises; stderr
    # is inherited as raw bytes and is never translated or normalized here.
    value=raw[0].decode(wire['effective_encoding']).replace('\r\n','\n').replace('\r','\n') if spec['text'] and not observation['timed_out'] else raw[0]
    if error!=expected:fail('original_error_diagnostic_changed')
    if error is not None:raise RetainedOutputError(error['type'],error['message'])
    if run_capture:
        return SimpleNamespace(args=spec['original_arguments'],returncode=code,stdout=raw[0],stderr=raw[1])
    return value

def clock_value(value):
    if type(value) is not dict or set(value)!={'schema_version','clock','value'} or type(value['schema_version']) is not int or value['schema_version']!=1 or value['clock']!='UTC-seconds' or type(value['value']) is not str or re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ',value['value']) is None:fail('clock_changed')
    try:at=datetime.fromisoformat(value['value'].replace('Z','+00:00'))
    except ValueError:fail('clock_invalid')
    if at.tzinfo!=timezone.utc or at.isoformat().replace('+00:00','Z')!=value['value']:fail('clock_noncanonical')
    return value['value']

class ReplayPersonalTransport:
    def __init__(self,owner,root,profile,*,emit_stderr,stream_limits=(MAX_STDOUT,MAX_STDERR)):
        self.owner,self.root,self.profile,self.emit_stderr=owner,str(root),profile,emit_stderr;self.calls=0;self.stream_limits=stream_limits
    def request(self,kind,args):
        self.calls+=1
        if self.calls>MAX_CALLS:fail('operation_budget')
        spec=self.profile.request(kind,args,self.root,self.owner.cwd)
        ok,wire=self.owner.outcome('personal-read-process',spec,'json')
        if not ok:fail('process_capture_incomplete')
        return process_value(wire,spec,self.profile,self.owner.blob,emit_stderr=self.emit_stderr,stream_limits=self.stream_limits)
    def fetch(self,endpoint):return self.request('get',{'endpoint':endpoint})
    def check_output(self,command,*,cwd,text):return self.request('git-tree',{'command':command,'cwd':str(cwd),'text':text})
    def clock(self):
        ok,wire=self.owner.outcome('personal-capture-clock',{'format':'UTC-seconds'},'json')
        if not ok:fail('clock_capture_incomplete')
        return clock_value(wire)
