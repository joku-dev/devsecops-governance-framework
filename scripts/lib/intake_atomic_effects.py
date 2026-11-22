"""Closed atomic text-output protocol and pure native-effect reconstruction."""
from collections import OrderedDict
import hashlib
import json
import posixpath
from pathlib import PurePosixPath
import re

from lib.requirement_validation_replay import IntegrityError
from lib.requirement_validation_budget import InputAdmissionError

MAX_FILE=32*1024**2
MAX_LIVE=128*1024**2
MAX_DESCRIPTORS=64
ERRORS={'OSError','PermissionError','FileNotFoundError','FileExistsError','NotADirectoryError',
        'IsADirectoryError','BlockingIOError','InterruptedError','TimeoutError'}


def require(condition,reason):
    if not condition:raise IntegrityError('intake_atomic_'+reason)


class AtomicScope:
    def __init__(self,root,targets,*,cwd):
        for value in (root,cwd):
            if (type(value) is not str or not value.startswith('/') or str(PurePosixPath(value))!=value
                    or '..' in PurePosixPath(value).parts or len(value)>8192
                    or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in value)):
                raise InputAdmissionError('intake_atomic_absolute_context_required')
        if (type(targets) not in (list,tuple) or not 1<=len(targets)<=64
                or any(type(n) is not str or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',n) is None or n in ('.','..') for n in targets) or len(targets)!=len(set(targets))):
            raise InputAdmissionError('intake_atomic_closed_target_names_required')
        self.root,self.cwd,self.targets=root,cwd,tuple(sorted(targets))
    def name(self,path,*,directory=False):
        label=str(path);p=PurePosixPath(label)
        if ('..' in p.parts or len(label)>8192 or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in label)):
            raise InputAdmissionError('intake_atomic_normalized_path_required')
        absolute=posixpath.normpath(label if p.is_absolute() else self.cwd+'/'+label)
        if directory and absolute==self.root:return ''
        if str(PurePosixPath(absolute).parent)!=self.root:raise InputAdmissionError('intake_atomic_path_outside_scope')
        return PurePosixPath(absolute).name


class AtomicPath:
    def __init__(self,effects,value):self.effects,self.value=effects,PurePosixPath(value)
    def __str__(self):return str(self.value)
    @property
    def parent(self):return AtomicPath(self.effects,self.value.parent)
    def mkdir(self,mode=0o777,parents=False,exist_ok=False):
        return self.effects.call('mkdir',{'path':str(self),'mode':mode,'parents':parents,'exist_ok':exist_ok})
    def unlink(self,missing_ok=False):return self.effects.call('unlink',{'path':str(self),'missing_ok':missing_ok})


class AtomicPorts:
    def path(self,value):
        if isinstance(value,AtomicPath):
            if value.effects is not self:raise InputAdmissionError('intake_atomic_foreign_path')
            return value
        return AtomicPath(self,value)
    def mkstemp(self,*,dir):
        value=self.call('mkstemp',{'directory':str(dir)})
        return value['descriptor'],value['temporary']
    def fdopen(self,descriptor,mode):
        self.call('fdopen',{'descriptor':descriptor,'mode':mode})
        return AtomicStream(self,descriptor)
    def fsync(self,descriptor):return self.call('fsync',{'descriptor':descriptor})
    def chmod(self,path,mode):return self.call('chmod',{'path':str(path),'mode':mode})
    def replace(self,source,target):return self.call('replace',{'source':str(source),'target':str(target)})


class AtomicStream:
    def __init__(self,effects,descriptor):self.effects,self.descriptor=effects,descriptor
    def __enter__(self):self.effects.call('enter',{'descriptor':self.descriptor});return self
    def __exit__(self,kind,error,tb):
        return self.effects.call('close',{'descriptor':self.descriptor,'exception_type':None if kind is None else kind.__name__})
    def write(self,text):return self.effects.call('write',{'descriptor':self.descriptor,'text':text})
    def flush(self):return self.effects.call('flush',{'descriptor':self.descriptor})
    def fileno(self):return self.effects.call('fileno',{'descriptor':self.descriptor})


def error_value(error):
    return {'type':type(error).__name__,'message':str(error),'errno':error.errno,
            'strerror':error.strerror,'filename':error.filename,'filename2':error.filename2}


def original_error(value):
    import builtins
    require(type(value) is dict and set(value)=={'type','message','errno','strerror','filename','filename2'}
            and value['type'] in ERRORS and type(value['errno']) is int
            and type(value['strerror']) is str and type(value['message']) is str
            and len(value['message'])<=65536
            and all(value[k] is None or type(value[k]) is str for k in ('filename','filename2')),'error_wire_changed')
    cls=getattr(builtins,value['type'])
    result=cls(value['errno'],value['strerror'],value['filename'],None,value['filename2']) if value['filename2'] is not None else cls(value['errno'],value['strerror'],value['filename'])
    require(type(result).__name__==value['type'] and str(result)==value['message'],'error_diagnostic_changed')
    return result


class AtomicState:
    def __init__(self,scope,blob):
        self.scope,self.blob=scope,blob;self.current=None;self.temps=set();self.descriptors={}
        self.phase='idle';self.active=None;self.buffers={};self.failed=set();self.serial=0
        self.cache=OrderedDict()
    def raw(self,ref):
        require(type(ref) is dict and set(ref)=={'sha256','bytes'} and type(ref['sha256']) is str
                and re.fullmatch('[a-f0-9]{64}',ref['sha256']) is not None and type(ref['bytes']) is int
                and 0<=ref['bytes']<=MAX_FILE,'blob_reference_changed')
        key=(ref['sha256'],ref['bytes'])
        if key in self.cache:self.cache.move_to_end(key);return self.cache[key]
        try:raw=self.blob(ref)
        except (ValueError,OSError,KeyError,TypeError) as error:raise IntegrityError('intake_atomic_retained_blob_unavailable') from error
        require(type(raw) is bytes and len(raw)==ref['bytes']
            and hashlib.sha256(raw).hexdigest()==ref['sha256'],'blob_content_changed')
        self.cache[key]=raw
        while len(self.cache)>4:self.cache.popitem(last=False)
        return raw
    def snapshot(self,value,temps=None,descriptors=None):
        temps=self.temps if temps is None else temps;descriptors=self.descriptors if descriptors is None else descriptors
        require(type(value) is dict and set(value)=={'root','files','descriptors'},'snapshot_fields_changed')
        require(type(value['files']) is dict and set(value['files'])==set(self.scope.targets)|set(temps),'snapshot_paths_changed')
        total=0
        for name,row in {'':value['root'],**value['files']}.items():
            require(type(row) is dict and row.get('kind') in ('missing','file','directory'),'snapshot_kind_changed')
            if row['kind']=='missing':require(row=={'kind':'missing'} and name!='','missing_root_or_fields_changed');continue
            keys={'kind','mode','identity','stat'}|({'content'} if row['kind']=='file' else {'members'})
            require(set(row)==keys and type(row['mode']) is int and 0<=row['mode']<=0o777 and not row['mode']&0o077
                and type(row['identity']) is list and len(row['identity'])==2 and all(type(n) is int and n>=0 for n in row['identity']),'snapshot_identity_or_mode_changed')
            info=row['stat'];require(type(info) is dict and set(info)=={'uid','gid','links','bytes','mtime_ns','ctime_ns'}
                and all(type(n) is int and n>=0 for n in info.values()),'snapshot_stat_changed')
            if row['kind']=='file':
                raw=self.raw(row['content']);total+=len(raw);require(info['bytes']==len(raw) and info['links']==1,'snapshot_file_size_or_links_changed')
            else:require(type(row['members']) is list and row['members']==sorted(set(row['members']))
                and all(type(n) is str and n not in ('.','..') and '/' not in n and '\0' not in n for n in row['members']),'directory_members_changed')
        require(total<=MAX_LIVE,'live_byte_budget')
        require(value['root']['kind']=='directory' and set(value['root']['members'])=={n for n,r in value['files'].items() if r['kind']!='missing'},'root_members_changed')
        require(type(value['descriptors']) is dict and set(value['descriptors'])==set(descriptors),'descriptor_set_changed')
        for token,row in value['descriptors'].items():
            require(type(row) is dict and set(row)=={'name','open','stream'} and row['name']==descriptors[token]
                and type(row['open']) is bool,'descriptor_binding_changed')
            stream=row['stream']
            if stream is not None:
                require(type(stream) is dict and set(stream)=={'encoding','errors','closed'} and stream['encoding'].lower().replace('_','-') in ('utf-8','ascii','us-ascii','ansi-x3.4-1968','iso8859-1','iso-8859-1','cp1252','mac-roman')
                    and stream['errors']=='strict' and type(stream['closed']) is bool and (row['open']!=stream['closed']),'text_stream_context_changed')
    def admit(self,operation,args):
        fields={'mkdir':{'path','mode','parents','exist_ok'},'mkstemp':{'directory'},'fdopen':{'descriptor','mode'},
            'enter':{'descriptor'},'write':{'descriptor','text'},'flush':{'descriptor'},'fileno':{'descriptor'},
            'fsync':{'descriptor'},'close':{'descriptor','exception_type'},'chmod':{'path','mode'},
            'replace':{'source','target'},'unlink':{'path','missing_ok'}}
        require(operation in fields and type(args) is dict and set(args)==fields[operation],'operation_fields_changed')
        if operation=='mkdir':require(self.phase=='idle' and self.scope.name(args['path'],directory=True)==''
            and args['mode']==0o777 and args['parents'] is True and args['exist_ok'] is True,'mkdir_contract_changed')
        elif operation=='mkstemp':require(self.phase=='parent-ready' and self.scope.name(args['directory'],directory=True)=='','temporary_contract_changed')
        elif operation in ('fdopen','enter','write','flush','fileno','fsync','close'):
            token=args['descriptor'];require(type(token) is int and str(token) in self.descriptors and token==self.active,'descriptor_selection_changed')
            if operation=='fdopen':require(self.phase=='allocated' and args['mode']=='w','stream_open_changed')
            if operation=='enter':require(self.phase=='opened','stream_enter_changed')
            if operation=='write':require(self.phase=='writing' and type(args['text']) is str and args['text'].isascii()
                and len(args['text'])<=MAX_FILE,'write_contract_changed')
            if operation=='flush':require(self.phase=='writing','flush_order_changed')
            if operation=='fileno':require(self.phase=='flushed','fileno_order_changed')
            if operation=='fsync':require(self.phase=='flushed','fsync_order_changed')
            if operation=='close':require(self.phase in ('writing','flushed','synced','failed-open')
                and (args['exception_type'] is None or type(args['exception_type']) is str and re.fullmatch('[A-Za-z_][A-Za-z_0-9]{0,127}',args['exception_type'])),'close_contract_changed')
        elif operation=='chmod':require(self.phase=='closed' and self.scope.name(args['path'])==self.descriptors[str(self.active)]
            and type(args['mode']) is int and 0<=args['mode']<=0o777 and not args['mode']&0o077,'chmod_contract_changed')
        elif operation=='replace':require(self.phase=='mode-set' and self.scope.name(args['source'])==self.descriptors[str(self.active)]
            and self.scope.name(args['target']) in self.scope.targets,'replace_contract_changed')
        elif operation=='unlink':require(self.phase in ('replaced','cleanup') and self.scope.name(args['path'])==self.descriptors[str(self.active)]
            and args['missing_ok'] is True,'cleanup_contract_changed')
    def begin(self,operation,args,before):
        self.snapshot(before)
        if self.current is not None:require(self.current==before,'state_changed_between_operations')
        self.admit(operation,args)
    def finish(self,operation,args,before,after,result,error):
        if error is not None:original_error(error)
        success=error is None;temps=set(self.temps);desc=dict(self.descriptors);changed=set()
        if operation=='mkstemp' and success:
            require(type(result) is dict and set(result)=={'descriptor','temporary'} and type(result['descriptor']) is int
                and result['descriptor']==self.serial+1<=MAX_DESCRIPTORS,'temporary_descriptor_changed')
            name=self.scope.name(result['temporary']);require(name not in set(self.scope.targets)|temps
                and re.fullmatch('tmp[a-z0-9_]{8}',name) is not None and result['temporary']==self.scope.root+'/'+name,'temporary_name_changed')
            temps.add(name);desc[str(result['descriptor'])]=name;changed.add(name)
        elif operation in ('write','flush','close'):changed.add(self.descriptors[str(args['descriptor'])])
        elif operation in ('chmod','unlink'):changed.add(self.scope.name(args['path']))
        elif operation=='replace':changed.update((self.scope.name(args['source']),self.scope.name(args['target'])))
        self.snapshot(after,temps,desc)
        root_a,root_b=before['root'],after['root']
        require(all(root_a[k]==root_b[k] for k in ('kind','mode','identity'))
            and all(root_a['stat'][k]==root_b['stat'][k] for k in ('uid','gid')),'root_identity_changed')
        if operation not in ('mkstemp','replace','unlink'):require(root_a==root_b,'unexpected_root_change')
        for name,row in before['files'].items():
            if name not in changed:require(row==after['files'][name],'unrelated_file_changed')
        for token,row in before['descriptors'].items():
            if operation not in ('fdopen','close') or token!=str(args['descriptor']):
                require(row==after['descriptors'][token],'unrelated_descriptor_changed')
        if operation in ('write','flush','close'):
            name=self.descriptors[str(args['descriptor'])];a,b=before['files'][name],after['files'][name]
            require(a['kind']==b['kind']=='file' and all(a[k]==b[k] for k in ('mode','identity'))
                and all(a['stat'][k]==b['stat'][k] for k in ('uid','gid','links')),'stream_file_identity_changed')
        if operation=='mkdir':
            require(after==before and (not success or result is None),'mkdir_outcome_changed');self.phase='parent-ready' if success else 'idle'
        elif operation=='mkstemp':
            if success:
                token=result['descriptor'];name=desc[str(token)];row=after['files'][name]
                require(row['kind']=='file' and self.raw(row['content'])==b'' and after['descriptors'][str(token)]=={'name':name,'open':True,'stream':None},'temporary_creation_changed')
                self.serial=token;self.active=token;self.buffers[token]=bytearray();self.phase='allocated'
            else:require(after==before,'failed_temporary_changed_state');self.phase='idle'
        elif operation=='fdopen':
            row=after['descriptors'][str(self.active)]
            if success:require(result=={'encoding':row['stream']['encoding'],'errors':row['stream']['errors']} and row['open'] and not row['stream']['closed'],'fdopen_outcome_changed')
            self.phase='opened' if success else 'cleanup'
        elif operation=='enter':require(not success or result is None,'enter_return_changed');self.phase='writing' if success else 'cleanup'
        elif operation=='write':
            token=self.active;chunk=args['text'].encode('ascii')
            require(sum(map(len,self.buffers.values()))+len(chunk)<=MAX_LIVE,'buffer_byte_budget')
            if success:require(type(result) is int and result==len(args['text']),'write_count_changed')
            self.buffers[token].extend(chunk)
            if not success:self.failed.add(token);self.phase='failed-open'
            self.prefix(after,token)
        elif operation=='flush':
            if success:require(result is None,'flush_return_changed');self.exact(after,self.active);self.phase='flushed'
            else:self.failed.add(self.active);self.prefix(after,self.active);self.phase='failed-open'
        elif operation=='fileno':
            require(after==before and (not success or result==self.active and type(result) is int),'fileno_outcome_changed')
            if not success:self.phase='failed-open';self.failed.add(self.active)
        elif operation=='fsync':
            require(after==before and (not success or result is None),'fsync_outcome_changed');self.phase='synced' if success else 'failed-open'
            if not success:self.failed.add(self.active)
        elif operation=='close':
            if success:require(result is None and not after['descriptors'][str(self.active)]['open'],'close_outcome_changed')
            if self.active not in self.failed and success:self.exact(after,self.active)
            else:self.prefix(after,self.active)
            self.phase='closed' if success and args['exception_type'] is None and self.active not in self.failed and self.phase=='synced' else 'cleanup'
            if self.phase=='closed':self.buffers[self.active]=bytearray()
        elif operation=='chmod':
            name=self.scope.name(args['path']);a,b=before['files'][name],after['files'][name]
            require(a['kind']==b['kind']=='file' and a['identity']==b['identity'] and a['content']==b['content'],'chmod_file_changed')
            require(not success or result is None and b['mode']==args['mode'],'chmod_outcome_changed');self.phase='mode-set' if success else 'cleanup'
        elif operation=='replace':
            source,target=self.scope.name(args['source']),self.scope.name(args['target']);a,b=before['files'][source],after['files'][target]
            moved=after['files'][source]=={'kind':'missing'} and b['kind']=='file' and all(a[k]==b[k] for k in ('mode','identity','content'))
            require((moved and result is None) if success else moved or all(before['files'][n]==after['files'][n] for n in (source,target)),'replace_progress_changed');self.phase='replaced' if success else 'cleanup'
        else:
            name=self.scope.name(args['path']);require(not success or result is None and after['files'][name]=={'kind':'missing'},'cleanup_outcome_changed')
            if not success:require(before['files'][name]==after['files'][name] or after['files'][name]=={'kind':'missing'},'failed_cleanup_changed_file')
            self.buffers.pop(self.active,None);self.active=None;self.phase='idle'
        self.temps,self.descriptors,self.current=temps,desc,after
    def prefix(self,state,token):
        row=state['files'][self.descriptors[str(token)]]
        require(row['kind']=='file' and self.buffers[token].startswith(self.raw(row['content'])),'physical_bytes_not_emitted_prefix')
    def exact(self,state,token):
        row=state['files'][self.descriptors[str(token)]]
        require(row['kind']=='file' and self.raw(row['content'])==bytes(self.buffers[token]),'flushed_bytes_changed')


class ReplayAtomicEffects(AtomicPorts):
    def __init__(self,scope,events,blob,*,position=0):
        self.scope,self.events,self.position=scope,events,position;self.state=AtomicState(scope,blob);self.sequence=0;self.failure=None
    def row(self):
        require(self.position<len(self.events),'event_missing');value=self.events[self.position];self.position+=1;return value
    def call(self,operation,args):
        if self.failure is not None:raise self.failure
        try:return self.consume(operation,args)
        except (IntegrityError,InputAdmissionError) as error:self.failure=error;raise
    def consume(self,operation,args):
        intent=self.row();require(type(intent) is dict and set(intent)=={'kind','sequence','operation','arguments','before'}
            and intent['kind']=='intake-atomic-intent' and intent['sequence']==self.sequence and type(intent['sequence']) is int
            and intent['operation']==operation and json.dumps(intent['arguments'],sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(args,sort_keys=True,separators=(',',':'),allow_nan=False),'intent_changed')
        self.state.begin(operation,args,intent['before']);outcome=self.row()
        require(type(outcome) is dict and set(outcome)=={'kind','sequence','result','error','after'}
            and outcome['kind']=='intake-atomic-outcome' and outcome['sequence']==self.sequence and type(outcome['sequence']) is int,'outcome_changed')
        self.state.finish(operation,args,intent['before'],outcome['after'],outcome['result'],outcome['error']);self.sequence+=1
        if outcome['error'] is not None:raise original_error(outcome['error'])
        return outcome['result']
    def finish(self):
        if self.failure is not None:raise self.failure
        require(self.position==len(self.events) and self.state.phase=='idle','trailing_or_incomplete_execution')
