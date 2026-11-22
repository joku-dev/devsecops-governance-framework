"""Complete selected SQLite file snapshots as unverified boundary observations."""
import hashlib,json,re
from lib.private_intake_sql_protocol import require
FILES=('queue.sqlite3','queue.sqlite3-wal','queue.sqlite3-shm','queue.sqlite3-journal')
MAX_DATABASE=128*1024**2

def checked_ref(value,limit):
    require(type(value) is dict and set(value)=={'sha256','bytes'} and type(value['sha256']) is str and re.fullmatch('[a-f0-9]{64}',value['sha256']) is not None and type(value['bytes']) is int and 0<=value['bytes']<=limit,'file_blob_reference_changed');return value

def snapshot(ref,blob):
    checked_ref(ref,1024**2)
    try:raw=blob(ref);value=json.loads(raw)
    except (ValueError,OSError,TypeError,KeyError):require(False,'file_snapshot_unavailable')
    require(type(raw) is bytes and len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'file_snapshot_hash_changed')
    require(type(value) is dict and set(value)=={'root','files'} and type(value['files']) is dict and set(value['files'])==set(FILES),'file_snapshot_members_changed')
    root=value['root'];require(type(root) is dict and set(root)=={'mode','identity','uid','gid'} and type(root['mode']) is int and root['mode']==0o700 and type(root['identity']) is list and len(root['identity'])==2 and all(type(n) is int and n>=0 for n in root['identity']) and all(type(root[n]) is int and root[n]>=0 for n in ('uid','gid')),'root_snapshot_changed')
    for row in value['files'].values():
        if row is None:continue
        require(type(row) is dict and set(row)=={'mode','identity','uid','gid','links','bytes','mtime_ns','ctime_ns','content'} and type(row['identity']) is list and len(row['identity'])==2 and all(type(n) is int and n>=0 for n in row['identity']) and all(type(row[n]) is int for n in ('mode','uid','gid','links','bytes','mtime_ns','ctime_ns')) and 0<=row['mode']<=0o777 and not row['mode']&0o077 and row['uid']==root['uid'] and row['gid']>=0 and row['links']==1 and 0<=row['bytes']<=MAX_DATABASE,'database_file_metadata_changed')
        checked_ref(row['content'],MAX_DATABASE)
        try:data=blob(row['content'])
        except (ValueError,OSError,TypeError,KeyError):require(False,'database_file_bytes_unavailable')
        require(type(data) is bytes and len(data)==row['bytes']==row['content']['bytes'] and hashlib.sha256(data).hexdigest()==row['content']['sha256'],'database_file_bytes_changed')
    return value
