"""Exclusive binary capture in a finite private candidate; no native buffering claim."""
import errno
from lib.requirement_validation_budget import InputAdmissionError
from lib.synthetic_lifecycle_projection import EMPTY,PRIVATE_MASK
from lib.validation_files import MAX_FILE,MAX_TOTAL

class PrivateExclusive:
    def __init__(self,owner,path,label):
        self.owner,self.path,self.label=owner,path,label;self.closed=False;self.pending=None
        if owner.projection is None:raise InputAdmissionError('personal_private_projection_required')
        self.port=owner.projection;self.spec,self.paths=self.port.prepare(path,label)
        tree=self.port.tree;tree.changed=[]
        def effect():
            tree.parent(path,label);value=tree.state(path)
            if value['kind']=='unreachable':tree.fail(errno.ENOTDIR,label)
            if value['kind']!='missing':tree.fail(errno.EEXIST,label)
            tree.parent(path,label,write=True)
            tree.put(path,tree.fresh('file',0o666&~PRIVATE_MASK,EMPTY))
        try:self.port.perform('personal-private-exclusive-open',{'selection':self.spec,'mode':'xb'},effect)
        finally:self.port.finish_output(self.spec,self.paths)

    def __enter__(self):return self
    def __exit__(self,*error):self.close()
    def write(self,raw):
        if self.closed:raise ValueError('write to closed file')
        if type(raw) is not bytes or len(raw)>MAX_FILE or self.pending is not None:raise InputAdmissionError('personal_original_single_binary_write_required')
        payload=self.port.store(raw)
        def effect():self.pending=raw;return len(raw)
        return self.port.perform('personal-private-exclusive-write',{'selection':self.spec,'payload':payload},effect)

    def close(self):
        if self.closed:return
        tree=self.port.tree;tree.changed=[]
        def effect():
            value=tree.state(self.path)
            if value['kind']!='file' or value['content']!=EMPTY:raise InputAdmissionError('personal_private_exclusive_file_changed')
            if self.pending is not None:
                if tree.total+len(self.pending)>MAX_TOTAL:raise InputAdmissionError('personal_private_capture_byte_budget')
                payload=self.port.store(self.pending);tree.total+=len(self.pending)
                tree.put(self.path,{**value,'content':payload});self.owner.files[self.path]=payload
                self.owner.writes.append({'path':self.path,'label':self.label,'payload':payload})
            self.closed=True
        try:return self.port.perform('personal-private-exclusive-close',{'selection':self.spec},effect)
        finally:self.port.finish_output(self.spec,self.paths)
