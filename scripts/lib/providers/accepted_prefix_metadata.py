"""Stable bounded reads of explicitly bound source/index/shared-index data."""
import os,stat
from pathlib import Path
from lib.accepted_prefix_metadata import file_value,MAX_INPUT,MAX_INDEX
from lib.providers.operations_files import held_root
from lib.providers.workbook_import_io import ordinary_ancestors
from lib.requirement_validation_budget import InputAdmissionError

def fail(reason):raise InputAdmissionError('accepted_prefix_metadata_'+reason)
def metadata(value):return {'kind':'file','identity':[value.st_dev,value.st_ino],'mode':stat.S_IMODE(value.st_mode),
    'uid':value.st_uid,'nlink':value.st_nlink,'bytes':value.st_size,'mtime_ns':value.st_mtime_ns,'ctime_ns':value.st_ctime_ns}
def checked(value,limit):
    if not stat.S_ISREG(value.st_mode) or value.st_uid!=os.geteuid() or value.st_nlink!=1 or value.st_mode&0o7022 or value.st_size>limit:fail('owned_regular_input_required')
    return metadata(value)

class NativeGitInputs:
    def __init__(self,owner,selected):self.owner,self.selected=owner,selected
    def read(self,role):
        if role not in self.selected:fail('input_role')
        selection={'role':role,'path':self.selected[role]};path=Path(selection['path']);limit=MAX_INPUT if role=='source' else MAX_INDEX
        if not path.is_absolute() or str(path)!=os.path.normpath(str(path)) or path.is_relative_to(self.owner.private_state):fail('input_binding')
        cache={}
        def effect():
            try:ordinary_ancestors(path.parent)
            except (FileNotFoundError,NotADirectoryError):
                return {'schema_version':1,'selection':selection,'before':{'kind':'missing'},'after':{'kind':'missing'},'content':None}
            with held_root(path.parent) as parent:
                try:entry=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
                except FileNotFoundError:
                    return {'schema_version':1,'selection':selection,'before':{'kind':'missing'},'after':{'kind':'missing'},'content':None}
                before=checked(entry,limit);fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
                try:
                    if checked(os.fstat(fd),limit)!=before:fail('input_replaced')
                    blocks=[];total=0
                    while block:=os.read(fd,min(65536,limit+1-total)):
                        blocks.append(block);total+=len(block)
                        if total>limit:fail('input_byte_budget')
                    after=checked(os.fstat(fd),limit);current=checked(os.stat(path.name,dir_fd=parent,follow_symlinks=False),limit)
                    if before!=after or before!=current:fail('input_changed_during_read')
                finally:os.close(fd)
            raw=b''.join(blocks);ref=self.owner.blob(raw);cache[ref['sha256']]=raw
            return {'schema_version':1,'selection':selection,'before':before,'after':after,'content':ref}
        try:
            wire=self.owner.perform('accepted-prefix-git-input',selection,effect)
            return file_value(wire,selection,lambda ref:cache[ref['sha256']])
        except Exception:
            self.owner.record.capture_incomplete=True;raise
