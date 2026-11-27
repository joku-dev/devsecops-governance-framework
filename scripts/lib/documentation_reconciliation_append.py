"""Closed retained native append stages, exact prefix and inode observations."""
from lib.requirement_review_output import snapshot,RetainedOutputError
from lib.requirement_validation_replay import IntegrityError
from lib.synthetic_lifecycle_io import path_spec
from lib.validation_files import MAX_FILE

def fail(reason):raise IntegrityError('documentation_append_'+reason)

class RetainedAppend:
    def __init__(self,owner,path,label):
        self.owner,self.path,self.label=owner,path,label
        self.spec=path_spec(path,label,owner.cwd);self.closed=False;self.opened=None
        self.pending=b'';self.prior_raw=b'';self.before=None

    def bind(self,frame,before):
        self.owner.output.anchor(frame,self.path);self.owner.output.prior(self.path,before)
        self.before=before;snapshot(before,self.owner.blob)
        self.prior_raw=self.owner.blob(before['content']) if before['kind']=='file' else b''

    def arguments(self,stage,payload):
        return {'selection':self.spec,'stage':stage,'mode':'a','encoding':'utf-8','payload':payload}

    def validate(self,wire,stage,text=None):
        if type(wire) is not dict or set(wire)!={'stage','snapshot','opened_file','closed','result','failure'} or wire['stage']!=stage:
            fail('stage_changed')
        after=wire['snapshot'];snapshot(after,self.owner.blob)
        opened=wire['opened_file'];closed=wire['closed'];error=wire['failure'];result=wire['result']
        if type(closed) is not bool:fail('closed_state_changed')
        if opened is None:
            if stage!='open' or error is None or after!=self.before or not closed:fail('unopened_change')
        else:
            if (type(opened) is not dict or set(opened)!={'mode','identity'} or after['kind']!='file'
                    or type(opened['mode']) is not int or opened['mode']!=after['mode']
                    or type(opened['identity']) is not list or len(opened['identity'])!=2
                    or any(type(n) is not int or n<0 for n in opened['identity'])
                    or opened['identity']!=after['identity']):fail('opened_file_changed')
            if self.opened is not None and opened!=self.opened:fail('descriptor_changed')
            if self.before['kind'] not in ('missing','file'):fail('original_nonfile_opened')
            if self.before['kind']=='file' and (opened['identity']!=self.before['identity'] or opened['mode']!=self.before['mode']):fail('preimage_replaced')
            raw=self.owner.blob(after['content'])
            allowed=self.pending+(b'' if text is None else text.encode('utf-8'))
            if len(raw)>MAX_FILE or not raw.startswith(self.prior_raw) or raw[len(self.prior_raw):]!=allowed[:len(raw)-len(self.prior_raw)] or len(raw)-len(self.prior_raw)>len(allowed):fail('append_prefix_changed')
            if stage=='open' and raw!=self.prior_raw:fail('open_wrote_bytes')
            if stage=='close' and error is None and raw!=self.prior_raw+self.pending:fail('successful_close_incomplete')
            if stage in ('open','write') and error is None and closed or stage=='close' and error is None and not closed:fail('successful_stream_state_changed')
            self.opened=opened;self.owner.touched[self.path]=after
        if error is None:
            expected=len(text) if stage=='write' else None
            if type(result) is not type(expected) or result!=expected:fail('result_changed')
        else:
            if result is not None:fail('failed_result_changed')
            if type(error) is not dict:fail('failure_wire_changed')
            from lib.synthetic_lifecycle_output import ReplayOutput
            ReplayOutput.failure(self.owner.output,error,{'exception':error.get('type'),'message':error.get('message')})
        self.closed=closed
        self.owner.output.observed[self.path]=after
        if opened is not None:self.owner.output.invalidate([self.path],parents=self.before['kind']=='missing')
        if error is not None:raise RetainedOutputError(error['type'],error['message'])
        if stage=='write':self.pending+=text.encode('utf-8')
        if stage=='close' and self.pending:
            self.owner.files[self.path]=after['content'];self.owner.writes.append({'path':self.path,'label':self.label,'payload':after['content']})
        return result

    def __enter__(self):return self
    def __exit__(self,*exception):self.close()
    def write(self,text):
        if self.closed:raise ValueError('I/O operation on closed file.')
        if type(text) is not str or text not in ('required=true\n','required=false\n') or self.pending:fail('original_single_text_changed')
        return self.stage('write',text)
    def close(self):
        if not self.closed:return self.stage('close')

class ReplayAppend(RetainedAppend):
    def __init__(self,owner,path,label):
        super().__init__(owner,path,label);owner.output.admit(path,label)
        before=owner.row()
        if type(before) is not dict or set(before)!={'kind','selection','anchor','snapshot'} or before['kind']!='documentation-append-before' or before['selection']!=self.spec:fail('preimage_changed')
        self.bind(before['anchor'],before['snapshot']);self.stage('open')
    def stage(self,stage,text=None):
        payload=None
        if text is not None:
            import hashlib
            raw=text.encode('utf-8');payload={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
            if self.owner.blob(payload)!=raw:fail('requested_text_changed')
        ok,wire=self.owner.outcome('documentation-native-append',self.arguments(stage,payload),'json')
        if not ok:fail('observation_failed')
        return self.validate(wire,stage,text)
