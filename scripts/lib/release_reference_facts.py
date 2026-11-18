"""Closed inert local release references; no Git, network or signature authority."""
import base64
from fnmatch import fnmatchcase
import hashlib
import re

MAX_REFS=2048
MAX_OBJECTS=4096
MAX_OBJECT=1024**2
MAX_TOTAL=32*1024**2
MAX_CHAIN=64
KINDS=('tag','commit','tree','blob')


def release_name(name):
    if (not isinstance(name,str) or not name or len(name.encode('utf-8'))>4096
            or name=='@' or name.endswith('.') or '..' in name or '@{' in name
            or any(ord(c)<=32 or ord(c)==127 or c in '~^:?*[\\' for c in name)
            or any(not part or part.startswith('.') or part.endswith('.lock') for part in name.split('/'))
            or not any(fnmatchcase(name,pattern) for pattern in ('*baseline*','v*-public-adoption'))):
        raise ValueError('invalid_release_reference_name')
    return name


def object_id(value,algorithm):
    size=40 if algorithm=='sha1' else 64 if algorithm=='sha256' else None
    if size is None or not isinstance(value,str) or not re.fullmatch('[a-f0-9]{'+str(size)+'}',value):
        raise ValueError('invalid_release_object_identity')
    return value


def digest(kind,raw,algorithm):
    if kind not in KINDS or not isinstance(raw,bytes) or len(raw)>MAX_OBJECT:
        raise ValueError('invalid_release_object_bytes')
    return hashlib.new(algorithm,kind.encode()+b' '+str(len(raw)).encode()+b'\0'+raw,usedforsecurity=False).hexdigest()


def tag_target(raw,algorithm):
    lines=raw.split(b'\n',2)
    if len(lines)!=3 or not lines[0].startswith(b'object ') or not lines[1].startswith(b'type '):
        raise ValueError('invalid_release_tag_header')
    try:target=object_id(lines[0][7:].decode('ascii'),algorithm);kind=lines[1][5:].decode('ascii')
    except UnicodeError:raise ValueError('invalid_release_tag_header') from None
    if kind not in KINDS:raise ValueError('invalid_release_tag_target_type')
    return target,kind


def validate(value):
    if (not isinstance(value,dict) or set(value)!={'schema_version','source_head','source_tree','object_format','refs','objects'}
            or type(value['schema_version']) is not int or value['schema_version']!=1):
        raise ValueError('invalid_release_reference_facts')
    algorithm=value['object_format']
    object_id(value['source_head'],algorithm);object_id(value['source_tree'],algorithm)
    refs=value['refs'];objects=value['objects']
    if (not isinstance(refs,dict) or len(refs)>MAX_REFS or not isinstance(objects,dict) or len(objects)>MAX_OBJECTS):
        raise ValueError('release_reference_count_budget')
    raw_objects={};total=0
    for oid,row in objects.items():
        object_id(oid,algorithm)
        if (not isinstance(row,dict) or set(row)!={'kind','base64','sha256'}
                or row['kind'] not in KINDS or not isinstance(row['base64'],str)
                or len(row['base64'])>4*((MAX_OBJECT+2)//3)
                or not isinstance(row['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',row['sha256'])):
            raise ValueError('invalid_release_object_record')
        try:raw=base64.b64decode(row['base64'],validate=True)
        except (ValueError,TypeError):raise ValueError('invalid_release_object_encoding') from None
        if base64.b64encode(raw).decode('ascii')!=row['base64']:
            raise ValueError('noncanonical_release_object_encoding')
        total+=len(raw)
        if total>MAX_TOTAL:raise ValueError('release_object_total_budget')
        if digest(row['kind'],raw,algorithm)!=oid or hashlib.sha256(raw).hexdigest()!=row['sha256']:
            raise ValueError('release_object_bytes_changed')
        raw_objects[oid]=(row['kind'],raw)
    reachable=set()
    for name,oid in refs.items():
        release_name(name);object_id(oid,algorithm)
        seen=set()
        while True:
            if oid not in raw_objects:raise ValueError('release_reference_object_missing')
            if oid in seen or len(seen)>=MAX_CHAIN:raise ValueError('release_tag_chain_budget')
            seen.add(oid);reachable.add(oid);kind,raw=raw_objects[oid]
            if kind!='tag':break
            oid,expected=tag_target(raw,algorithm)
            if oid not in raw_objects or raw_objects[oid][0]!=expected:
                raise ValueError('release_tag_target_missing_or_changed')
    if reachable!=set(raw_objects):raise ValueError('unexpected_release_reference_object')
    return raw_objects
