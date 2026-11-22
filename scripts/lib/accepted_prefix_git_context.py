"""Pure frozen Git conversion plans; this module never opens paths or executes Git.

The native adapter must capture effective attributes, builtin settings, index and
object-store bindings before using a plan. A plan is not evidence of that capture.
"""
import json
import posixpath
import re
from lib.requirement_validation_budget import InputAdmissionError

ATTRIBUTES=('crlf','ident','filter','eol','text','working-tree-encoding')
BUILTINS=('core.autocrlf','core.eol','core.safecrlf','core.checkroundtripencoding','core.bigfilethreshold')
MAX_VALUE=8192

def fail(reason):raise InputAdmissionError('accepted_prefix_context_'+reason)

def label(value):
    return (type(value) is str and bool(value) and len(value)<=8192
        and not any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in value))

def setting(value):
    return type(value) is str and len(value)<=MAX_VALUE and not any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in value)

def relative_path(value):
    return (label(value) and not value.startswith('/') and posixpath.normpath(value)==value
        and all(part not in ('','.','..') for part in value.split('/')))

def absolute_path(value):
    return label(value) and value.startswith('/') and posixpath.normpath(value)==value

def attribute_values(raw,path):
    """Decode exactly one check-attr -z response, including the original path."""
    if not relative_path(path) or type(raw) is not bytes or len(raw)>64*1024:fail('attribute_binding')
    try:parts=raw.decode('utf-8').split('\0')
    except UnicodeError:fail('attribute_encoding')
    if parts[-1:]!=[''] or len(parts)!=3*len(ATTRIBUTES)+1:fail('attribute_shape')
    result={}
    for offset,key in zip(range(0,len(parts)-1,3),ATTRIBUTES):
        name,actual,value=parts[offset:offset+3]
        if name!=path or actual!=key or not setting(value):fail('attribute_selection')
        # Git's attribute assignment grammar has no quoted values. Whitespace
        # cannot be serialized into a second token or a second attribute line.
        if any(c.isspace() for c in value):fail('attribute_value')
        result[key]=value
    return result

def selected_driver(attributes):
    value=attributes['filter']
    return None if value in ('set','unset','unspecified') else value

def executable_driver_keys(raw,driver):
    """Only key names are observed: filter command bodies never enter records."""
    if type(raw) is not bytes or len(raw)>64*1024:fail('driver_keys')
    try:names=raw.decode('utf-8').split('\0')
    except UnicodeError:fail('driver_keys_encoding')
    if names==['']:names=[]
    else:
        if names[-1:]!=['']:fail('driver_keys_termination')
        names.pop()
    expected=set() if driver is None else {'filter.'+driver+'.clean','filter.'+driver+'.process'}
    if any(name not in expected for name in names) or len(names)!=len(set(names)):fail('driver_selection')
    if names:fail('external_clean_or_process_not_admitted')
    return []

def config_quote(value):
    if not setting(value):fail('config_value')
    return '"'+value.replace('\\','\\\\').replace('"','\\"')+'"'

def attribute_pattern(path):
    # C-quote the pathname and escape wildcard metacharacters inside the pattern.
    escaped=''.join('\\'+c if c in '*?[]\\' else c for c in path)
    return json.dumps(escaped,ensure_ascii=False)

def frozen_files(path,attributes,configuration,*,filter_required=None):
    """Return deterministic private metadata; no source Git config is included."""
    if not relative_path(path) or type(attributes) is not dict or set(attributes)!=set(ATTRIBUTES):fail('plan_attributes')
    for value in attributes.values():
        if not setting(value) or any(c.isspace() for c in value):fail('plan_attribute_value')
    if type(configuration) is not dict or not set(configuration)<=set(BUILTINS):fail('plan_configuration')
    if any(not setting(value) for value in configuration.values()):fail('plan_config_value')
    if filter_required is not None and type(filter_required) is not bool:fail('filter_required')
    driver=selected_driver(attributes)
    if driver is None and filter_required is not None:fail('unused_filter_required')
    tokens=[]
    for key in ATTRIBUTES:
        value=attributes[key]
        tokens.append('!'+key if value=='unspecified' else key if value=='set' else '-'+key if value=='unset' else key+'='+value)
    config=['[core]','repositoryformatversion = 0','bare = false','attributesFile = /dev/null']
    for key in BUILTINS:
        if key in configuration:config.append(key.split('.',1)[1]+' = '+config_quote(configuration[key]))
    if filter_required is not None:
        config.extend(['[filter '+config_quote(driver)+']','required = '+str(filter_required).lower()])
    return {'HEAD':b'ref: refs/heads/axiom-prefix-snapshot\n',
        'config':('\n'.join(config)+'\n').encode('utf-8'),
        'info/attributes':(attribute_pattern(path)+' '+' '.join(tokens)+'\n').encode('utf-8')}

class FrozenHashArguments:
    """Closed internal label binding; the native owner must prove its file lifecycle."""
    def __init__(self,root,private_gitdir,path):
        if (not absolute_path(root) or not absolute_path(private_gitdir) or not relative_path(path)
                or private_gitdir==root or private_gitdir.startswith(root+'/') or root.startswith(private_gitdir+'/')):
            fail('private_hash_scope')
        self.root,self.private_gitdir,self.path=root,private_gitdir,path
    def arguments(self,command,selected,safety):
        if (type(command) is not list or len(command)!=4 or command[:3]!=['git','hash-object','--']
                or command[3] not in (self.path,self.root+'/'+self.path)):
            fail('hash_path_binding')
        return [selected or 'git',*safety,'--git-dir='+self.private_gitdir,'--work-tree='+self.root,*command[1:]]
