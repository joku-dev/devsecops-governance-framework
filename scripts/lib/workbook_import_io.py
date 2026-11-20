"""Closed whole-workbook selection and ordered no-native IO reconstruction."""
import json
import builtins
from pathlib import PurePosixPath
import posixpath

from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import snapshot,text_bytes,RetainedOutputError
from lib.validation_files import MAX_FILE,MAX_TOTAL

MODES=('private-candidate','selected-files')
READ_ERRORS={name:getattr(builtins,name) for name in (
    'OSError','PermissionError','FileExistsError','FileNotFoundError','IsADirectoryError','NotADirectoryError',
    'BlockingIOError','InterruptedError','TimeoutError','BrokenPipeError','ChildProcessError',
    'ProcessLookupError','ConnectionError','ConnectionAbortedError','ConnectionRefusedError','ConnectionResetError')}
NATIVE_ERRORS=frozenset(READ_ERRORS)|{'UnicodeEncodeError'}


def path_spec(value):
    if type(value) is not dict or set(value)!={'path','label'}:
        raise IntegrityError('workbook_path_selection_changed')
    for key in ('path','label'):
        name=value[key]
        if (type(name) is not str or not name or len(name)>8192 or '\\' in name
                or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in name)
                or '..' in PurePosixPath(name).parts or str(PurePosixPath(name))!=name):
            raise IntegrityError('workbook_path_label_invalid')
    if not PurePosixPath(value['path']).is_absolute():raise IntegrityError('workbook_absolute_selection_required')
    return value


def selection_value(value,cwd):
    if type(value) is not dict or set(value)!={'inputs','outputs'}:
        raise IntegrityError('workbook_selection_changed')
    for key,count in (('inputs',2),('outputs',3)):
        if type(value[key]) is not list or len(value[key])!=count:
            raise IntegrityError('workbook_selection_count_changed')
        for item in value[key]:
            path_spec(item);label=PurePosixPath(item['label'])
            expected=posixpath.normpath(str(label if label.is_absolute() else PurePosixPath(cwd)/label))
            if item['path']!=expected:raise IntegrityError('workbook_selection_namespace_changed')
    return value


def ancestor_paths(root,name):
    r,p=PurePosixPath(root),PurePosixPath(name)
    try:relative=p.relative_to(r)
    except ValueError:raise IntegrityError('workbook_export_anchor_changed') from None
    if not relative.parts:raise IntegrityError('workbook_export_anchor_must_be_parent')
    return [str(r.joinpath(*relative.parts[:i])) for i in range(1,len(relative.parts)+1)]


def error_wire(value,label):
    if (type(value) is not dict or set(value)!={'type','message','errno','strerror','filename'}
            or value['type'] not in READ_ERRORS or type(value['message']) is not str or len(value['message'])>65536
            or type(value['errno']) is not int or type(value['strerror']) is not str or value['filename']!=label):
        raise IntegrityError('workbook_original_read_error_changed')
    error=READ_ERRORS[value['type']](value['errno'],value['strerror'],value['filename'])
    if str(error)!=value['message']:raise IntegrityError('workbook_original_read_diagnostic_changed')
    return error


class ReplayIO:
    def __init__(self,events,blob,mode,cwd):
        if mode not in MODES:raise IntegrityError('workbook_export_mode_changed')
        self.events,self.mode,self.cwd=events,mode,cwd;self.position=2;self.limit=len(events)-1
        self.selected=None;self.mkdir_position=self.write_position=self.total=0
        self.observed={};self.anchors={};self.reads={};self.files={};self.writes=[];self.touched={}
        def guarded(ref):
            try:return blob(ref)
            except (ValueError,OSError,KeyError,TypeError) as error:raise IntegrityError('workbook_retained_blob_invalid') from error
        self.blob=guarded

    def row(self):
        if self.position>=self.limit:raise IntegrityError('workbook_io_event_missing')
        row=self.events[self.position];self.position+=1
        if type(row) is not dict:raise IntegrityError('workbook_io_event_invalid')
        return row

    def select(self,value):
        selection_value(value,self.cwd)
        if self.selected is not None or self.row()!={'kind':'workbook-selected','selection':value}:
            raise IntegrityError('workbook_selected_intent_changed')
        self.selected=value

    def outcome(self,action,arguments,encoding):
        token=self.position;intent=self.row()
        if intent!={'kind':'intent','operation':token,'action':action,'arguments':arguments}:
            raise IntegrityError('workbook_io_intent_changed')
        value=self.row()
        if value.get('operation')!=token:raise IntegrityError('workbook_io_identity_changed')
        if value.get('kind')=='failed':
            if set(value)!={'kind','operation','exception','message'} or value['exception'] not in NATIVE_ERRORS or type(value['message']) is not str or len(value['message'])>65536:
                raise IntegrityError('workbook_io_failure_changed')
            return False,value
        if value.get('kind')!='returned' or set(value)!={'kind','operation','encoding','value'} or value['encoding']!=encoding:
            raise IntegrityError('workbook_io_outcome_changed')
        raw=self.blob(value['value'])
        if encoding=='bytes':return True,raw
        try:return True,json.loads(raw)
        except (ValueError,UnicodeError,TypeError) as error:raise IntegrityError('workbook_io_return_invalid') from error

    def read(self,path,label):
        spec=path_spec({'path':path,'label':label})
        if self.selected is None or spec not in self.selected['inputs']:
            raise IntegrityError('workbook_unselected_input_read')
        ok,value=self.outcome('workbook-input-read',spec,'bytes');after=self.row()
        if set(after)!={'kind','selection','observation','failure'} or after['kind']!='workbook-input-after' or after['selection']!=spec:
            raise IntegrityError('workbook_input_observation_changed')
        info=after['observation']
        if ok:
            if (after['failure'] is not None or type(info) is not dict or set(info)!={'kind','mode','identity','bytes'}
                    or info['kind']!='file' or type(info['mode']) is not int or not 0<=info['mode']<=0o777 or info['mode']&0o022
                    or type(info['identity']) is not list or len(info['identity'])!=2 or any(type(i) is not int or i<0 for i in info['identity'])
                    or type(info['bytes']) is not int or info['bytes']!=len(value) or len(value)>MAX_FILE):
                raise IntegrityError('workbook_complete_input_metadata_changed')
            self.total+=len(value)
            if self.total>MAX_TOTAL:raise IntegrityError('workbook_input_total_budget')
            if path in self.reads and self.reads[path]!=(value,info):raise IntegrityError('workbook_repeated_input_changed')
            self.reads[path]=(value,info);return value
        if info is not None:raise IntegrityError('workbook_failed_input_metadata_changed')
        if path in self.reads:raise IntegrityError('workbook_repeated_input_became_unavailable')
        failure=error_wire(after['failure'],label)
        if type(failure).__name__!=value['exception'] or str(failure)!=value['message']:
            raise IntegrityError('workbook_input_failure_wire_changed')
        raise failure

    def anchor(self,frame,target):
        if type(frame) is not dict or set(frame)!={'path','snapshot'}:
            raise IntegrityError('workbook_anchor_frame_changed')
        spec=path_spec({'path':frame['path'],'label':frame['path']});value=frame['snapshot'];snapshot(value,self.blob)
        if value['kind']!='directory':raise IntegrityError('workbook_anchor_directory_required')
        if spec['path'] in self.anchors and self.anchors[spec['path']]!=value:
            raise IntegrityError('workbook_anchor_replaced')
        if spec['path'] in self.observed and self.observed[spec['path']]!=value:
            raise IntegrityError('workbook_observed_anchor_changed')
        self.anchors[spec['path']]=value
        return ancestor_paths(spec['path'],target)

    def prior(self,path,value):
        snapshot(value,self.blob)
        if path in self.observed and self.observed[path]!=value:
            raise IntegrityError('workbook_output_changed_between_operations')

    def expected(self,kind,path,label):
        if self.selected is None:raise IntegrityError('workbook_output_without_selection')
        if kind=='mkdir':
            if self.mkdir_position>=3 or self.write_position:raise IntegrityError('workbook_mkdir_order_changed')
            selected=self.selected['outputs'][self.mkdir_position];self.mkdir_position+=1
            expected={'path':str(PurePosixPath(selected['path']).parent),'label':str(PurePosixPath(selected['label']).parent)}
        else:
            if self.mkdir_position!=3 or self.write_position>=3:raise IntegrityError('workbook_write_order_changed')
            expected=self.selected['outputs'][self.write_position];self.write_position+=1
        if {'path':path,'label':label}!=expected:raise IntegrityError('workbook_output_selection_changed')

    def mkdir(self,path,mode,parents,exist_ok,label):
        self.expected('mkdir',path,label)
        if (mode,parents,exist_ok)!=(0o777,True,True):raise IntegrityError('workbook_mkdir_options_changed')
        before=self.row()
        if set(before)!={'kind','path','label','anchor','snapshots'} or before['kind']!='workbook-mkdir-before' or before['path']!=path or before['label']!=label:
            raise IntegrityError('workbook_mkdir_before_changed')
        ok,value=self.outcome('workbook-output-mkdir',{'path':path,'label':label,'mode':mode,'parents':parents,'exist_ok':exist_ok,'export_mode':self.mode},'json')
        after=self.row()
        if set(after)!={'kind','path','label','snapshots','created'} or after['kind']!='workbook-mkdir-after' or after['path']!=path or after['label']!=label or type(after['created']) is not list:
            raise IntegrityError('workbook_mkdir_after_changed')
        if self.mode=='private-candidate':
            if before['anchor'] is not None or before['snapshots'] is not None or after['snapshots'] is not None or after['created'] or not ok:
                raise IntegrityError('workbook_private_mkdir_effect_changed')
        else:
            paths=self.anchor(before['anchor'],path)
            if type(before['snapshots']) is not dict or type(after['snapshots']) is not dict or set(before['snapshots'])!=set(paths) or set(after['snapshots'])!=set(paths):
                raise IntegrityError('workbook_mkdir_snapshot_paths_changed')
            created=[]
            for name in paths:
                a,z=before['snapshots'][name],after['snapshots'][name];self.prior(name,a);snapshot(z,self.blob)
                if name!=path and a['kind']=='directory':raise IntegrityError('workbook_mkdir_anchor_not_nearest')
                if a['kind']=='missing' and z['kind']=='directory':created.append(name);self.touched[name]=z
                elif a!=z:raise IntegrityError('workbook_mkdir_unexpected_change')
                self.observed[name]=z
            if created!=after['created'] or ok and after['snapshots'][path]['kind']!='directory':
                raise IntegrityError('workbook_mkdir_progress_changed')
        if ok:
            if value is not None:raise IntegrityError('workbook_mkdir_result_changed')
            return
        if value['exception']=='UnicodeEncodeError':raise IntegrityError('workbook_mkdir_encoding_claim_changed')
        raise RetainedOutputError(value['exception'],value['message'])

    def write_text(self,path,data,encoding,label):
        self.expected('write',path,label)
        if encoding!='utf-8':raise IntegrityError('workbook_write_encoding_changed')
        before=self.row()
        if set(before)!={'kind','path','label','anchor','snapshot','text','payload'} or before['kind']!='workbook-write-before' or before['path']!=path or before['label']!=label or self.blob(before['text'])!=text_bytes(data):
            raise IntegrityError('workbook_write_before_changed')
        try:raw=data.encode(encoding);encoding_error=None
        except UnicodeEncodeError as error:raw=None;encoding_error=error
        if raw is None:
            if before['payload'] is not None:raise IntegrityError('workbook_encoding_payload_changed')
        elif self.blob(before['payload'])!=raw:raise IntegrityError('workbook_write_payload_changed')
        ok,value=self.outcome('workbook-output-write',{'path':path,'label':label,'text':before['text'],'payload':before['payload'],'encoding':encoding,'export_mode':self.mode},'json')
        after=self.row()
        if set(after)!={'kind','path','label','snapshot','progress'} or after['kind']!='workbook-write-after' or after['path']!=path or after['label']!=label:
            raise IntegrityError('workbook_write_after_changed')
        progress=after['progress']
        if (type(progress) is not dict or set(progress)!={'opened','truncated','written_bytes'} or type(progress['opened']) is not bool
                or type(progress['truncated']) is not bool or type(progress['written_bytes']) is not int or not 0<=progress['written_bytes']<=(len(raw) if raw is not None else 0)
                or progress['truncated'] and not progress['opened'] or progress['written_bytes'] and not progress['truncated']):
            raise IntegrityError('workbook_write_progress_changed')
        if self.mode=='private-candidate':
            if before['anchor'] is not None or before['snapshot'] is not None or after['snapshot'] is not None or progress!={'opened':False,'truncated':False,'written_bytes':0}:
                raise IntegrityError('workbook_private_write_effect_changed')
        else:
            if before['anchor']['path']!=str(PurePosixPath(path).parent):raise IntegrityError('workbook_write_parent_missing_or_changed')
            self.anchor(before['anchor'],path);a,z=before['snapshot'],after['snapshot'];self.prior(path,a);snapshot(z,self.blob)
            if progress['opened']:
                if a['kind'] not in ('missing','file') or z['kind']!='file':raise IntegrityError('workbook_opened_file_changed')
                if a['kind']=='file' and (a['identity']!=z['identity'] or a['mode']!=z['mode']):raise IntegrityError('workbook_overwrite_identity_changed')
                if progress['truncated']:
                    expected=b'' if raw is None else raw[:progress['written_bytes']]
                    if self.blob(z['content'])!=expected:raise IntegrityError('workbook_partial_bytes_changed')
                elif a['kind']=='file' and a!=z or a['kind']=='missing' and self.blob(z['content'])!=b'':raise IntegrityError('workbook_untruncated_file_changed')
                self.touched[path]=z
            elif a!=z:raise IntegrityError('workbook_unopened_file_changed')
            if ok and (not progress['truncated'] or raw is None or progress['written_bytes']!=len(raw)):
                raise IntegrityError('workbook_successful_write_changed')
            self.observed[path]=z
        if ok:
            if raw is None or type(value) is not int or value!=len(data):raise IntegrityError('workbook_write_result_changed')
            self.files[path]=before['payload'];self.writes.append({'path':path,'label':label,'payload':before['payload']});return value
        if self.mode=='private-candidate' and value['exception']!='UnicodeEncodeError':raise IntegrityError('workbook_private_native_failure_changed')
        if value['exception']=='UnicodeEncodeError' and (encoding_error is None or value['message']!=str(encoding_error) or self.mode=='selected-files' and not progress['truncated']):
            raise IntegrityError('workbook_encoding_failure_changed')
        raise RetainedOutputError(value['exception'],value['message'])

    def finish(self):
        if self.position!=self.limit:raise IntegrityError('workbook_io_events_unused')
