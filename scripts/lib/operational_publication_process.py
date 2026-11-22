"""Whole original process-result replay; no Git, network, clock or filesystem effects."""
from types import SimpleNamespace
import codecs,hashlib,json
from lib.personal_channel_process import process_value,context
from lib.documentation_reconciliation_git import signal_diagnostic
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

FIELDS={'schema_version','specification','transport','stdin','effective_encoding','original_error','signal_context','Git_before','Git_after','effect_claim','remote_binding','native_working_directory'}
EFFECT={'native_process_result_observed':True,'external_completion_independently_proven':False,'effects_repeated_during_replay':False,'automatic_retry_or_rollback':False}
def same(a,b):return json.dumps(a,sort_keys=True,ensure_ascii=True,allow_nan=False)==json.dumps(b,sort_keys=True,ensure_ascii=True,allow_nan=False)
def fail(message):raise IntegrityError('operational_publisher_'+message)
def raw_blob(blob,ref,limit):
    if type(ref) is not dict or set(ref)!={'sha256','bytes'} or type(ref['bytes']) is not int or not 0<=ref['bytes']<=limit:fail('raw_stream_reference_changed')
    raw=blob(ref)
    if type(raw) is not bytes or len(raw)!=ref['bytes'] or hashlib.sha256(raw).hexdigest()!=ref['sha256']:fail('raw_stream_binding_changed')
    return raw

def value(wire,spec,profile,blob):
    if type(wire) is not dict or set(wire)!=FIELDS or type(wire['schema_version']) is not int or wire['schema_version']!=1 or not same(wire['specification'],spec) or not same(wire['effect_claim'],EFFECT):fail('whole_process_wire_changed')
    profile.validate_binding(spec,wire['remote_binding'],wire['native_working_directory'])
    before=context(wire['Git_before']);after=context(wire['Git_after'])
    if before!=after:fail('Git_directory_replaced')
    transport=wire['transport'];codec=wire['effective_encoding']
    if type(transport) is not dict:fail('transport_object_changed')
    profile.validate_program(transport.get('program'))
    if spec['text']:
        if type(codec) is not str or not codec or len(codec)>128:fail('codec_changed')
        try:codecs.lookup(codec)
        except LookupError:fail('codec_unknown')
    elif codec is not None:fail('binary_codec_changed')
    if spec['input'] is None:
        if wire['stdin'] is not None:fail('unexpected_stdin')
    elif codec is None or raw_blob(blob,wire['stdin'],1024**2)!=spec['input'].encode(codec):fail('stdin_changed')
    transport_spec={**spec,'kind':'git-run','text':False}
    if type(transport) is not dict or not same(transport.get('specification'),transport_spec):fail('binary_transport_binding_changed')
    adapter=SimpleNamespace(actual_arguments=lambda ignored,selected:profile.actual_arguments(spec,selected))
    try:
        result=process_value(transport,transport_spec,adapter,blob,emit_stderr=lambda ref:fail('captured_stderr_cannot_be_inherited'),stream_limits=(16*1024**2,256*1024))
        out=result.stdout.decode(codec).replace('\r\n','\n').replace('\r','\n') if spec['text'] else result.stdout
        err=result.stderr.decode(codec).replace('\r\n','\n').replace('\r','\n') if spec['text'] else result.stderr
        if result.returncode and spec['check']:
            message=signal_diagnostic(wire['signal_context'],result.returncode,spec['original_arguments']) if result.returncode<0 else f"Command '{spec['original_arguments']}' returned non-zero exit status {result.returncode}."
            if result.returncode>0 and wire['signal_context'] is not None:fail('unexpected_signal_context')
            raise RetainedOutputError('CalledProcessError',message)
        if wire['signal_context'] is not None:fail('unused_signal_context')
    except RetainedOutputError as error:
        if not same(wire['original_error'],{'type':error.original_type,'message':error.original_message}):fail('original_error_changed')
        raise
    except UnicodeError as error:
        if not same(wire['original_error'],{'type':type(error).__name__,'message':str(error)}):fail('original_decode_error_changed')
        raise
    if wire['original_error'] is not None:fail('unexpected_original_error')
    return SimpleNamespace(args=spec['original_arguments'],returncode=result.returncode,stdout=out,stderr=err)

class ReplayPublisherProcess:
    def __init__(self,owner,profile):self.owner,self.profile,self.calls=owner,profile,0;self.observations=[]
    def run(self,command,**options):
        self.calls+=1
        if self.calls>1024:fail('process_call_budget')
        spec=self.profile.request(list(command),options);ok,wire=self.owner.outcome('operational-publisher-process',spec,'json')
        if not ok:fail('native_capture_incomplete')
        try:result=value(wire,spec,self.profile,self.owner.blob)
        except (RetainedOutputError,UnicodeError):self.observations.append(observation(wire));raise
        self.observations.append(observation(wire));return result


def observation(wire):
    spec=wire['specification'];frame=wire['transport'];command=spec['original_arguments']
    write=spec['kind']=='post' or command[1] in ('fetch','switch','reset','add','push','-c')
    return {'original_arguments':command,'kind':spec['kind'],'write_requested':write,'started':frame['observation']['started'],'terminal_observed':frame['observation']['terminal_observed'],
        'returncode':frame['returncode'],'original_error':wire['original_error'],'remote_binding':wire['remote_binding'],
        'native_working_directory':wire['native_working_directory'],'raw_stdin':wire['stdin'],'raw_stdout':frame['stdout'],'raw_stderr':frame['stderr'],**EFFECT}
