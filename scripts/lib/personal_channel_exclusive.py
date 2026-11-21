"""Pure reconstruction of the original exclusive buffered binary capture output."""
import hashlib
from lib.requirement_review_output import snapshot,RetainedOutputError
from lib.requirement_validation_replay import IntegrityError
from lib.synthetic_lifecycle_io import path_spec
from lib.validation_files import MAX_FILE

def fail(reason):raise IntegrityError('personal_exclusive_'+reason)

class RetainedExclusive:
    def __init__(self,owner,path,label):
        self.owner,self.path,self.label=owner,path,label
        self.spec=path_spec(path,label,owner.cwd);self.before=None;self.opened=None
        self.closed=False;self.writes=0;self.accepted=b'';self.possible=b'';self.write_failed=False

    def bind(self,frame,before):
        self.owner.output.anchor(frame,self.path);self.owner.output.prior(self.path,before)
        snapshot(before,self.owner.blob);self.before=before

    def arguments(self,stage,payload):
        return {'selection':self.spec,'mode':'xb','stage':stage,'payload':payload}

    def validate(self,wire,stage,raw=None):
        fields={'stage','snapshot','opened_file','closed','result','failure'}
        if type(wire) is not dict or set(wire)!=fields or wire['stage']!=stage:fail('stage_changed')
        after=wire['snapshot'];snapshot(after,self.owner.blob)
        opened,closed,result,error=(wire[k] for k in ('opened_file','closed','result','failure'))
        if type(closed) is not bool:fail('closed_state_changed')
        if stage=='write':
            if self.writes or type(raw) is not bytes or len(raw)>MAX_FILE:fail('original_single_write_changed')
            self.writes+=1
            if error is None:
                if type(result) is not int or not 0<=result<=len(raw):fail('write_return_changed')
                self.accepted=self.possible=raw[:result]
            else:self.write_failed=True;self.possible=raw
        elif raw is not None or stage not in ('open','close'):fail('operation_changed')
        if opened is None:
            if stage!='open' or error is None or after!=self.before or not closed or result is not None:fail('unopened_change')
        else:
            if (type(opened) is not dict or set(opened)!={'mode','identity'} or self.before['kind']!='missing'
                    or after['kind']!='file' or type(opened['mode']) is not int or opened['mode']!=after['mode']
                    or opened['mode']&~0o666 or type(opened['identity']) is not list or len(opened['identity'])!=2
                    or any(type(n) is not int or n<0 for n in opened['identity']) or opened['identity']!=after['identity']):fail('exclusive_file_identity_changed')
            if stage!='open' and self.opened is None or self.opened is not None and opened!=self.opened:fail('descriptor_changed')
            actual=self.owner.blob(after['content'])
            if stage=='open' and actual:fail('open_wrote_bytes')
            if not self.possible.startswith(actual):fail('written_prefix_changed')
            if stage=='close' and error is None and not self.write_failed and actual!=self.accepted:fail('successful_close_bytes_changed')
            if error is None and ((stage in ('open','write') and closed) or (stage=='close' and not closed)):fail('successful_stream_state_changed')
            if stage=='close' and not closed:fail('close_observation_incomplete')
            self.opened=opened;self.owner.touched[self.path]=after
            self.owner.output.invalidate([self.path],parents=stage=='open')
        if error is None:
            if stage!='write' and result is not None:fail('stage_return_changed')
        else:
            if result is not None or type(error) is not dict:fail('failure_changed')
            from lib.synthetic_lifecycle_output import ReplayOutput
            ReplayOutput.failure(self.owner.output,error,{'exception':error.get('type'),'message':error.get('message')})
        self.owner.output.observed[self.path]=after;self.closed=closed
        if error is not None:raise RetainedOutputError(error['type'],error['message'])
        if stage=='close' and self.writes and not self.write_failed:
            self.owner.files[self.path]=after['content']
            self.owner.writes.append({'path':self.path,'label':self.label,'payload':after['content']})
        return result

    def __enter__(self):
        if self.closed:raise ValueError('I/O operation on closed file.')
        return self
    def __exit__(self,*error):self.close()
    def write(self,raw):
        if self.closed:raise ValueError('write to closed file')
        if type(raw) is not bytes or len(raw)>MAX_FILE or self.writes:fail('original_single_write_required')
        return self.stage('write',raw)
    def close(self):
        if not self.closed:return self.stage('close')

class ReplayExclusive(RetainedExclusive):
    def __init__(self,owner,path,label):
        super().__init__(owner,path,label);owner.output.admit(path,label)
        before=owner.row()
        if type(before) is not dict or set(before)!={'kind','selection','anchor','snapshot'} or before['kind']!='personal-exclusive-before' or before['selection']!=self.spec:fail('preimage_changed')
        self.bind(before['anchor'],before['snapshot']);self.stage('open')
    def stage(self,stage,raw=None):
        payload=None if raw is None else {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        if raw is not None and self.owner.blob(payload)!=raw:fail('requested_bytes_changed')
        ok,wire=self.owner.outcome('personal-exclusive-output',self.arguments(stage,payload),'json')
        if not ok:fail('capture_incomplete')
        return self.validate(wire,stage,raw)
