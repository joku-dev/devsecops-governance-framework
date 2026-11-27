"""Closed original SQLite statements and typed retained DB-API observations.

SQLite is an explicit effect port. Pure reconstruction consumes declared native
rows and outcomes; it does not independently authenticate a database producer.
"""
import hashlib,json,re
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

PROFILE='whole-private-intake-sqlite-v1'
MAX_VALUE=32*1024**2
MAX_ROWS=32768
SQL=('INSERT INTO batches(id,base,state,manifest) VALUES (?,?,?,?)', "INSERT INTO jobs(repository,domain,run_id,attempt,payload,state)\n              VALUES (?,?,?,?,?,?) ON CONFLICT(repository,domain,run_id,attempt)\n              DO UPDATE SET payload=excluded.payload,\n                state=CASE WHEN jobs.state='waiting' THEN excluded.state ELSE jobs.state END", 'INSERT OR REPLACE INTO meta VALUES (?,?)', 'PRAGMA integrity_check', 'PRAGMA user_version', "SELECT * FROM batches WHERE state IN ('prepared','open')", "SELECT * FROM jobs WHERE state='queued' AND next_at<=? ORDER BY run_id,attempt LIMIT 1", 'SELECT state,count(*) FROM jobs GROUP BY state', 'SELECT value FROM meta WHERE key=?', "UPDATE batches SET state='abandoned' WHERE id=?", "UPDATE jobs SET state='batched',batch=? WHERE repository=? AND domain=? AND run_id=? AND attempt=?", "UPDATE jobs SET state='held',error='superseded_attempt' WHERE repository=? AND domain='devsecops' AND run_id=? AND attempt<? AND state IN ('waiting','queued')", "UPDATE jobs SET state='queued' WHERE state='working'", "UPDATE jobs SET state='verified',batch=NULL WHERE batch=?", 'UPDATE jobs SET state=? WHERE batch=?')
SCRIPTS=("\n          PRAGMA journal_mode=WAL;\n          PRAGMA foreign_keys=ON;\n          CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);\n          CREATE TABLE IF NOT EXISTS jobs (\n            repository TEXT NOT NULL, domain TEXT NOT NULL, run_id INTEGER NOT NULL,\n            attempt INTEGER NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL,\n            retries INTEGER NOT NULL DEFAULT 0, next_at REAL NOT NULL DEFAULT 0,\n            error TEXT, snapshot TEXT, snapshot_path TEXT, batch TEXT,\n            PRIMARY KEY(repository,domain,run_id,attempt));\n          CREATE INDEX IF NOT EXISTS runnable ON jobs(state,next_at);\n          CREATE TABLE IF NOT EXISTS batches (\n            id TEXT PRIMARY KEY, base TEXT NOT NULL, state TEXT NOT NULL,\n            manifest TEXT NOT NULL, commit_sha TEXT, pr INTEGER, url TEXT);\n          CREATE UNIQUE INDEX IF NOT EXISTS one_active_batch ON batches((1))\n            WHERE state IN ('prepared','open');\n          PRAGMA user_version=1;\n        ",)


def require(value,reason):
    if not value:raise IntegrityError('private_intake_sql_'+reason)


def statement(sql,script=False):
    if type(sql) is not str or len(sql)>1024**2:raise InputAdmissionError('private_intake_sql_statement_budget')
    if sql in (SCRIPTS if script else SQL):return
    if not script and sql in ('SELECT * FROM jobs ORDER BY run_id,attempt','SELECT * FROM jobs WHERE state=? ORDER BY run_id,attempt'):return
    if not script:
        for prefix,suffix,allowed,empty in [('UPDATE jobs SET ',' WHERE repository=? AND domain=? AND run_id=? AND attempt=?',{'state','retries','next_at','error','snapshot','snapshot_path','batch'},False),('UPDATE batches SET ',' WHERE id=?',{'state','commit_sha','pr','url'},True)]:
            if sql.startswith(prefix) and sql.endswith(suffix):
                middle=sql[len(prefix):-len(suffix)];items=[] if middle=='' else middle.split(',');names=[s[:-2] for s in items]
                if (items or empty) and len(names)==len(set(names)) and set(names)<=allowed and all(s==n+'=?' for s,n in zip(items,names)):return
    raise InputAdmissionError('private_intake_sql_original_statement_required')


def atom(value,store):
    if value is None:return {'kind':'null'}
    if type(value) is bool:return {'kind':'bool','value':value}
    if type(value) is int:
        if value.bit_length()>4096:raise InputAdmissionError('private_intake_sql_integer_budget')
        return {'kind':'int','value':str(value)}
    if type(value) is float:return {'kind':'float','value':value.hex()}
    if type(value) in (str,bytes):
        raw=(json.dumps(value,ensure_ascii=True,separators=(',',':')).encode() if type(value) is str else value)
        if len(raw)>MAX_VALUE:raise InputAdmissionError('private_intake_sql_value_byte_budget')
        return {'kind':'text' if type(value) is str else 'bytes','content':store(raw)}
    raise InputAdmissionError('private_intake_sql_explicit_scalar_required')


def scalar(value,blob):
    require(type(value) is dict and type(value.get('kind')) is str,'scalar_changed');kind=value['kind']
    if kind=='null':require(value=={'kind':'null'},'null_changed');return None
    if kind=='bool':require(set(value)=={'kind','value'} and type(value['value']) is bool,'boolean_changed');return value['value']
    if kind in ('int','float'):
        require(set(value)=={'kind','value'} and type(value['value']) is str and len(value['value'])<=1300,'number_changed')
        try:result=int(value['value']) if kind=='int' else float.fromhex(value['value'])
        except ValueError:raise IntegrityError('private_intake_sql_number_changed') from None
        require((result.bit_length()<=4096 and str(result)==value['value']) if kind=='int' else result.hex()==value['value'],'number_encoding_changed');return result
    require(kind in ('text','bytes') and set(value)=={'kind','content'},'scalar_kind_changed')
    from lib.private_intake_sql_files import checked_ref
    checked_ref(value['content'],MAX_VALUE)
    try:raw=blob(value['content'])
    except (ValueError,KeyError,OSError,TypeError):raise IntegrityError('private_intake_sql_blob_missing_or_changed') from None
    require(type(raw) is bytes and len(raw)<=MAX_VALUE,'scalar_byte_budget')
    if kind=='bytes':return raw
    try:result=json.loads(raw)
    except (ValueError,UnicodeError):raise IntegrityError('private_intake_sql_text_changed') from None
    require(type(result) is str and json.dumps(result,ensure_ascii=True,separators=(',',':')).encode()==raw,'text_encoding_changed');return result


class Row:
    def __init__(self,names,values):self.names,self.values=tuple(names),tuple(values)
    def keys(self):return list(self.names)
    def __iter__(self):return iter(self.values)
    def __len__(self):return len(self.values)
    def __getitem__(self,key):
        if isinstance(key,(int,slice)):return self.values[key]
        if isinstance(key,str):
            for n,name in enumerate(self.names):
                if name==key or name.isascii() and key.isascii() and name.lower()==key.lower():return self.values[n]
        raise IndexError('No item with that key')


class RetainedSQLError(RetainedOutputError):
    def __init__(self,value):
        super().__init__(value['type'],value['message']);self.original_module=value['module'];self.sqlite_errorcode=value['sqlite_errorcode'];self.sqlite_errorname=value['sqlite_errorname']


def error(value):
    require(type(value) is dict and set(value)=={'module','type','message','sqlite_errorcode','sqlite_errorname'} and value['module'] in ('sqlite3','builtins') and type(value['type']) is str and re.fullmatch('[A-Za-z_][A-Za-z_0-9]{0,127}',value['type']) and type(value['message']) is str and len(value['message'])<=65536,'error_changed')
    require(value['sqlite_errorcode'] is None or type(value['sqlite_errorcode']) is int,'error_code_changed');require(value['sqlite_errorname'] is None or type(value['sqlite_errorname']) is str,'error_name_changed');return RetainedSQLError(value)


def exception_value(kind,value):
    if kind is None:return None
    return {'type':value.original_type if isinstance(value,RetainedSQLError) else kind.__name__,'module':value.original_module if isinstance(value,RetainedSQLError) else kind.__module__,'message':value.original_message if isinstance(value,RetainedSQLError) else str(value)}
