"""Pure reconstruction of exact original ordered report output observations."""
import json
from lib.requirement_validation_replay import IntegrityError
from lib.validation_files import MAX_FILE

OUTPUTS = {
    'implemented-migration': ('generated/reports/implemented-requirement-migration.json',
                             'generated/reports/implemented-requirement-migration.md'),
    'pra-platform': ('docs/governance/review-packets/PRA-2026-001/review.json',
                     'docs/governance/review-packets/PRA-2026-001/review.md'),
}
MODES = ('private-candidate', 'source-worktree')
EMPTY_MIN_ERRORS = ('min() arg is an empty sequence', 'min() iterable argument is empty')
NATIVE_ERRORS = frozenset(('OSError','PermissionError','FileExistsError','FileNotFoundError',
                          'IsADirectoryError','NotADirectoryError','UnicodeEncodeError'))


class RetainedOutputError(Exception):
    """An expressly retained native failure, not a newly executed effect."""
    def __init__(self, original_type, original_message):
        self.original_type, self.original_message = original_type, original_message


def text_bytes(value):
    return (json.dumps({'text':value},sort_keys=True,ensure_ascii=True,allow_nan=False,
                       separators=(',',':'))+'\n').encode()


def prefixes(name):
    parts=name.split('/')
    return ['/'.join(parts[:n]) for n in range(1,len(parts)+1)]


def snapshot(value, blob):
    if type(value) is not dict or value.get('kind') not in ('missing','unreachable','file','directory'):
        raise IntegrityError('requirement_review_snapshot_kind_changed')
    kind=value['kind']
    if kind=='missing':
        if set(value)!={'kind'}:raise IntegrityError('requirement_review_missing_snapshot_changed')
        return
    if kind=='unreachable':
        if value!={'kind':'unreachable','cause':'NotADirectoryError'}:
            raise IntegrityError('requirement_review_unreachable_snapshot_changed')
        return
    keys={'kind','mode','identity'}|({'content'} if kind=='file' else set())
    if (set(value)!=keys or type(value['mode']) is not int or not 0<=value['mode']<=0o777 or value['mode']&0o022
            or type(value['identity']) is not list or len(value['identity'])!=2
            or any(type(x) is not int or x<0 for x in value['identity'])):
        raise IntegrityError('requirement_review_snapshot_metadata_changed')
    if kind=='file' and len(blob(value['content']))>MAX_FILE:
        raise IntegrityError('requirement_review_snapshot_byte_budget')


class ReplayOutput:
    def __init__(self, events, blob, kind, mode):
        def guarded(ref):
            try:return blob(ref)
            except (ValueError,OSError,KeyError,TypeError) as error:
                raise IntegrityError('requirement_review_retained_blob_invalid') from error
        self.events,self.blob,self.kind,self.mode=events,guarded,kind,mode
        self.position=2;self.limit=len(events)-2
        self.files={};self.touched={}

    def row(self):
        if self.position>=self.limit:raise IntegrityError('requirement_review_output_event_missing')
        value=self.events[self.position];self.position+=1
        if type(value) is not dict:raise IntegrityError('requirement_review_output_event_invalid')
        return value

    def outcome(self, action, arguments):
        position=self.position;intent=self.row()
        if intent!={'kind':'intent','operation':position,'action':action,'arguments':arguments}:
            raise IntegrityError('requirement_review_output_intent_changed')
        result=self.row()
        if result.get('operation')!=position:raise IntegrityError('requirement_review_output_identity_changed')
        if result.get('kind')=='failed':
            if (set(result)!={'kind','operation','exception','message'} or result['exception'] not in NATIVE_ERRORS
                    or type(result['message']) is not str or len(result['message'])>65536):
                raise IntegrityError('requirement_review_output_failure_changed')
            return False,result
        if (set(result)!={'kind','operation','encoding','value'} or result.get('kind')!='returned'
                or result['encoding']!='json'):
            raise IntegrityError('requirement_review_output_return_changed')
        try:value=json.loads(self.blob(result['value']))
        except (ValueError,UnicodeError,TypeError) as error:
            raise IntegrityError('requirement_review_output_return_invalid') from error
        return True,value

    def mkdir(self,name,mode,parents,exist_ok):
        if (self.kind!='pra-platform' or name!='docs/governance/review-packets/PRA-2026-001'
                or (mode,parents,exist_ok)!=(0o777,True,True)):
            raise IntegrityError('requirement_review_mkdir_selection_changed')
        before=self.row()
        if set(before)!={'kind','name','snapshots'} or before['kind']!='review-mkdir-before' or before['name']!=name:
            raise IntegrityError('requirement_review_mkdir_before_changed')
        ok,value=self.outcome('review-output-mkdir',{'name':name,'mode':mode,'parents':parents,'exist_ok':exist_ok,'export_mode':self.mode})
        after=self.row()
        if (set(after)!={'kind','name','snapshots','created'} or after['kind']!='review-mkdir-after'
                or after['name']!=name or type(after['created']) is not list):
            raise IntegrityError('requirement_review_mkdir_after_changed')
        if self.mode=='private-candidate':
            if before['snapshots'] is not None or after['snapshots'] is not None or after['created'] or not ok:
                raise IntegrityError('requirement_review_private_mkdir_claim_changed')
        else:
            expected=prefixes(name)
            if type(before['snapshots']) is not dict or type(after['snapshots']) is not dict or set(before['snapshots'])!=set(expected) or set(after['snapshots'])!=set(expected):
                raise IntegrityError('requirement_review_mkdir_paths_changed')
            created=[]
            for path in expected:
                a,b=before['snapshots'][path],after['snapshots'][path]
                snapshot(a,self.blob);snapshot(b,self.blob)
                if a['kind']=='missing' and b['kind']=='directory':created.append(path);self.touched[path]=b
                elif a!=b:raise IntegrityError('requirement_review_mkdir_unexpected_change')
            if after['created']!=created or ok and after['snapshots'][name]['kind']!='directory':
                raise IntegrityError('requirement_review_mkdir_progress_changed')
        if ok:
            if value is not None:raise IntegrityError('requirement_review_mkdir_result_changed')
            return
        if value['exception']=='UnicodeEncodeError':
            raise IntegrityError('requirement_review_mkdir_encoding_claim_changed')
        raise RetainedOutputError(value['exception'],value['message'])

    def write_text(self,name,data,encoding):
        if name not in OUTPUTS[self.kind] or encoding!='utf-8':
            raise IntegrityError('requirement_review_write_selection_changed')
        before=self.row()
        if (set(before)!={'kind','name','text','payload','snapshot'} or before['kind']!='review-output-before'
                or before['name']!=name or self.blob(before['text'])!=text_bytes(data)):
            raise IntegrityError('requirement_review_write_text_changed')
        try:raw=data.encode(encoding);encoding_error=None
        except UnicodeEncodeError as error:raw=None;encoding_error=error
        if raw is None:
            if before['payload'] is not None:raise IntegrityError('requirement_review_encoding_payload_changed')
        elif self.blob(before['payload'])!=raw:raise IntegrityError('requirement_review_payload_changed')
        ok,value=self.outcome('review-output-write',{'name':name,'text':before['text'],'payload':before['payload'],'encoding':encoding,'export_mode':self.mode})
        after=self.row()
        if (set(after)!={'kind','name','snapshot','progress'} or after['kind']!='review-output-after' or after['name']!=name):
            raise IntegrityError('requirement_review_write_after_changed')
        progress=after['progress']
        if (type(progress) is not dict or set(progress)!={'opened','truncated','written_bytes'}
                or type(progress['opened']) is not bool or type(progress['truncated']) is not bool
                or type(progress['written_bytes']) is not int or not 0<=progress['written_bytes']<=(len(raw) if raw is not None else 0)
                or progress['truncated'] and not progress['opened'] or progress['written_bytes'] and not progress['truncated']):
            raise IntegrityError('requirement_review_write_progress_changed')
        if self.mode=='private-candidate':
            if before['snapshot'] is not None or after['snapshot'] is not None or progress!={'opened':False,'truncated':False,'written_bytes':0}:
                raise IntegrityError('requirement_review_private_source_effect_claim_changed')
        else:
            a,b=before['snapshot'],after['snapshot'];snapshot(a,self.blob);snapshot(b,self.blob)
            if progress['opened']:
                if b['kind']!='file' or a['kind'] not in ('missing','file'):
                    raise IntegrityError('requirement_review_opened_file_changed')
                if a['kind']=='file' and (a['identity']!=b['identity'] or a['mode']!=b['mode']):
                    raise IntegrityError('requirement_review_overwrite_identity_changed')
                if progress['truncated']:
                    expected=b'' if raw is None else raw[:progress['written_bytes']]
                    if self.blob(b['content'])!=expected:raise IntegrityError('requirement_review_partial_bytes_changed')
                elif a['kind']=='file' and a!=b or a['kind']=='missing' and self.blob(b['content'])!=b'':
                    raise IntegrityError('requirement_review_untruncated_file_changed')
                self.touched[name]=b
            elif a!=b:raise IntegrityError('requirement_review_unopened_file_changed')
            if ok and (not progress['truncated'] or raw is None or progress['written_bytes']!=len(raw)):
                raise IntegrityError('requirement_review_success_write_changed')
        if ok:
            if raw is None or type(value) is not int or value!=len(data):raise IntegrityError('requirement_review_write_result_changed')
            self.files[name]=before['payload'];return value
        if self.mode=='private-candidate' and value['exception']!='UnicodeEncodeError':
            raise IntegrityError('requirement_review_private_native_failure_claim_changed')
        if value['exception']=='UnicodeEncodeError' and (encoding_error is None or self.mode=='source-worktree' and not progress['truncated']):
            raise IntegrityError('requirement_review_encoding_failure_changed')
        if value['exception']=='UnicodeEncodeError' and value['message']!=str(encoding_error):
            raise IntegrityError('requirement_review_encoding_diagnostic_changed')
        raise RetainedOutputError(value['exception'],value['message'])

    def finish(self):
        if self.position!=self.limit:raise IntegrityError('requirement_review_output_events_unused')
