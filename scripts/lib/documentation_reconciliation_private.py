"""Original UTF-8 append over a finite private candidate, with closed replay.

This finite private model makes no native buffering or durability assertion.
The two payloads and options are the entire unchanged original program's use.
"""
import errno
from lib.requirement_validation_budget import InputAdmissionError
from lib.synthetic_lifecycle_projection import EMPTY,PRIVATE_MASK
from lib.validation_files import MAX_FILE,MAX_TOTAL


class PrivateAppend:
    def __init__(self,owner,path,label):
        self.owner,self.path,self.label=owner,path,label
        self.closed=False;self.pending=b''
        projection=owner.projection
        if projection is None:raise InputAdmissionError('documentation_private_append_projection_required')
        self.port=projection;self.spec,self.paths=projection.prepare(path,label)
        tree=projection.tree;tree.changed=[]
        def effect():
            tree.parent(path,label);before=tree.state(path)
            if before['kind']=='unreachable':tree.fail(errno.ENOTDIR,label)
            if before['kind']=='directory':tree.fail(errno.EISDIR,label)
            if before['kind']=='missing':
                tree.parent(path,label,write=True)
                tree.put(path,tree.fresh('file',0o666&~PRIVATE_MASK,EMPTY))
            elif not before['mode']&0o200:tree.fail(errno.EACCES,label)
            return None
        try:projection.perform('documentation-private-append-open',{'selection':self.spec,'mode':'a','encoding':'utf-8'},effect)
        finally:projection.finish_output(self.spec,self.paths)

    def __enter__(self):return self
    def __exit__(self,*exception):self.close()

    def write(self,text):
        if self.closed:raise ValueError('I/O operation on closed file.')
        if type(text) is not str:raise TypeError('write() argument must be str, not '+type(text).__name__)
        if text not in ('required=true\n','required=false\n') or self.pending:
            raise InputAdmissionError('documentation_original_single_append_required')
        payload=self.port.store(text.encode('utf-8'))
        def effect():self.pending=text.encode('utf-8');return len(text)
        return self.port.perform('documentation-private-append-write',{'selection':self.spec,'payload':payload},effect)

    def close(self):
        if self.closed:return
        tree=self.port.tree;tree.changed=[]
        def effect():
            current=tree.state(self.path)
            if current['kind']!='file':raise InputAdmissionError('documentation_private_append_file_changed')
            # Append is byte preserving: no attempt to decode the preimage.
            raw=tree.blob(current['content'])+self.pending
            if len(raw)>MAX_FILE or tree.total+len(self.pending)>MAX_TOTAL:
                raise InputAdmissionError('documentation_private_append_byte_budget')
            if self.pending:
                payload=self.port.store(raw);tree.total+=len(self.pending)
                tree.put(self.path,{**current,'content':payload})
                self.owner.files[self.path]=payload
                self.owner.writes.append({'path':self.path,'label':self.label,'payload':payload})
            self.pending=b'';self.closed=True
            return None
        try:return self.port.perform('documentation-private-append-close',{'selection':self.spec},effect)
        finally:self.port.finish_output(self.spec,self.paths)
