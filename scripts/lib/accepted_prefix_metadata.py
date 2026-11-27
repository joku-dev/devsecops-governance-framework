"""Pure decoding of captured Git conversion metadata and bounded file observations."""
import hashlib,posixpath,re
from lib.accepted_prefix_git_context import ATTRIBUTES,BUILTINS,attribute_values,executable_driver_keys,selected_driver,absolute_path,relative_path
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError

MAX_INPUT=64*1024**2
MAX_INDEX=32*1024**2

def fail(reason):raise InputAdmissionError('accepted_prefix_metadata_'+reason)
def required(result):
    if type(result.returncode) is not int or result.returncode!=0:fail('query_incomplete')
    return result.stdout

def line(raw,*,empty=False):
    if type(raw) is not bytes or len(raw)>8192:fail('line_budget')
    try:value=raw.decode('utf-8')
    except UnicodeError:fail('line_encoding')
    if empty and not value:return ''
    if not value.endswith('\n') or value.count('\n')!=1 or '\r' in value or '\0' in value:fail('line_shape')
    return value[:-1]

def scalar(result):
    if type(result.returncode) is not int:fail('config_status')
    if result.returncode==1 and result.stdout==b'' and result.stderr==b'':return None
    raw=required(result)
    if type(raw) is not bytes or not raw.endswith(b'\0') or raw.count(b'\0')!=1:fail('config_shape')
    try:value=raw[:-1].decode('utf-8')
    except UnicodeError:fail('config_encoding')
    if len(value)>8192 or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in value):fail('config_value')
    return value

def source_path(root,value):
    if type(value) is not str or not value or '\0' in value:fail('path_value')
    candidate=posixpath.normpath(value if value.startswith('/') else root+'/'+value)
    if not absolute_path(candidate):fail('canonical_path')
    return candidate

def capture_context(root,path,transport_factory):
    """Same finite call order on native and pure ports, including driver admission."""
    port=transport_factory(path,None)
    def query(*arguments):return port.run(['git',*arguments])
    gitdir=source_path(root,line(required(query('rev-parse','--absolute-git-dir'))))
    common=source_path(root,line(required(query('rev-parse','--git-common-dir'))))
    shared=line(required(query('rev-parse','--shared-index-path')),empty=True)
    if line(required(query('rev-parse','--show-object-format')))!='sha1':fail('original_SHA1_context_required')
    index=source_path(root,line(required(query('rev-parse','--git-path','index'))))
    objects=source_path(root,line(required(query('rev-parse','--git-path','objects'))))
    if index!=gitdir+'/index' or objects!=common+'/objects':fail('Git_metadata_path_binding')
    if shared:
        shared=source_path(root,shared)
        if posixpath.dirname(shared) not in (gitdir,common) or re.fullmatch(r'sharedindex\.[a-f0-9]{40}',posixpath.basename(shared)) is None:fail('shared_index_path_binding')
    attributes=attribute_values(required(query('check-attr','-z',*ATTRIBUTES,'--',path)),path)
    configuration={}
    for key in BUILTINS:
        value=scalar(query('config','--null','--get',key))
        if value is not None:configuration[key]=value
    driver=selected_driver(attributes);filter_required=None
    if driver is not None:
        port=transport_factory(path,driver)
        value=scalar(port.run(['git','config','--null','--type=bool','--get','filter.'+driver+'.required']))
        if value is not None:
            if value not in ('true','false'):fail('required_boolean')
            filter_required=value=='true'
        command=port.profile.commands()[-1];result=port.run(command)
        if result.returncode not in (0,1) or result.returncode==1 and (result.stdout or result.stderr):fail('driver_query_incomplete')
        executable_driver_keys(result.stdout,driver)
    return {'gitdir':gitdir,'common':common,'index':index,'shared':shared,'objects':objects,
        'attributes':attributes,'configuration':configuration,'filter_required':filter_required}

def file_selection(root,path,context):
    if not absolute_path(root) or not relative_path(path):fail('input_selection')
    selected={'source':root+'/'+path,'index':context['index']}
    if context['shared']:selected['shared']=context['shared']
    return selected

def file_value(wire,selection,blob):
    def need(value,reason):
        if not value:raise IntegrityError('accepted_prefix_metadata_'+reason)
    need(type(wire) is dict and set(wire)=={'schema_version','selection','before','after','content'} and type(wire['schema_version']) is int and wire['schema_version']==1 and wire['selection']==selection,'file_wire_changed')
    before,after=wire['before'],wire['after'];need(type(before) is dict and before==after,'file_moved')
    if before=={'kind':'missing'}:
        need(wire['content'] is None,'missing_file_has_content');return None,before
    need(set(before)=={'kind','identity','mode','uid','nlink','bytes','mtime_ns','ctime_ns'} and before['kind']=='file','file_shape')
    need(type(before['identity']) is list and len(before['identity'])==2 and all(type(v) is int and v>=0 for v in before['identity']),'file_identity')
    need(all(type(before[k]) is int and before[k]>=0 for k in ('mode','uid','nlink','bytes','mtime_ns','ctime_ns')) and before['nlink']==1 and before['mode']<=0o777 and not before['mode']&0o022,'file_metadata')
    limit=MAX_INPUT if selection['role']=='source' else MAX_INDEX
    ref=wire['content'];need(type(ref) is dict and set(ref)=={'sha256','bytes'} and type(ref['bytes']) is int and ref['bytes']==before['bytes'] and ref['bytes']<=limit,'file_budget')
    raw=blob(ref);need(type(raw) is bytes and len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'file_bytes')
    return raw,before

class ReplayGitInputs:
    def __init__(self,owner,selected):self.owner,self.selected=owner,selected
    def read(self,role):
        selection={'role':role,'path':self.selected[role]}
        ok,wire=self.owner.outcome('accepted-prefix-git-input',selection,'json')
        if not ok:raise IntegrityError('accepted_prefix_metadata_input_incomplete')
        return file_value(wire,selection,self.owner.blob)
