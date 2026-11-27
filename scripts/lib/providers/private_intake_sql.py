"""Explicit owned-root SQLite primitives; journal before effects and separate cleanup.

The original Python SQLite connection and transaction semantics are retained.
Guards bind ordinary private paths before/after calls; they do not claim a VFS
sandbox or Python support for the C-only SQLITE_OPEN_NOFOLLOW flag.
"""
from pathlib import Path
import json,math,os,sqlite3,stat,time
from lib.private_intake_sql_protocol import PROFILE,MAX_ROWS,MAX_VALUE,atom,scalar,statement
from lib.private_intake_sql_files import FILES,MAX_DATABASE
from lib.providers.validation_worktree import signature
from lib.providers.operations_files import held_root
from lib.providers.workbook_import_io import ordinary_ancestors
from lib.requirement_validation_budget import InputAdmissionError


class NativeSQLite:
    def __init__(self,owner,*,root,cwd,forbidden_roots):
        self.owner,self.record=owner,owner.record;self.root=Path(root);self.cwd=cwd;self.connections={};self.cursors={};self.failure=None;self.closed=False;self.anchor=None;self.fd=None;self.identity=None;self.root_gid=None;self.facade=None;self.started=False;self.initial_snapshot=None;self.final_snapshot=None
        if not self.root.is_absolute() or '..' in self.root.parts or str(self.root)!=root or not forbidden_roots:raise InputAdmissionError('private_intake_sql_explicit_absolute_scope_required')
        for value in (*forbidden_roots,self.record.root):
            other=Path(value)
            if self.root.is_relative_to(other) or other.is_relative_to(self.root):raise InputAdmissionError('private_intake_sql_protected_root_overlap')
        self.context={'kind':'private-intake-sql-context','profile':PROFILE,'root':root,'cwd':cwd,'sqlite_version':sqlite3.sqlite_version};self.append(self.context)
    def stop(self,reason='capture_incomplete'):
        if self.failure is None:self.failure=InputAdmissionError('private_intake_sql_'+reason)
        self.record.capture_incomplete=True;raise self.failure from None
    def invalidate(self,error):return self.stop('interface_admission_failed')
    def append(self,value):
        try:self.record.append(value)
        except Exception:self.stop('journal_failed')
    def store(self,raw):
        if self.failure is not None or self.record.capture_incomplete:self.stop()
        try:return self.record.blob(raw)
        except Exception:self.stop('blob_failed')
    def blob(self,ref):
        from lib.providers.sbom_export_storage import read_private
        import hashlib
        raw=read_private(self.record.blobs/ref['sha256'],MAX_VALUE)
        if len(raw)!=ref['bytes'] or hashlib.sha256(raw).hexdigest()!=ref['sha256']:self.stop('retained_blob_changed')
        return raw
    def guard(self):
        if self.fd is None:
            self.anchor=held_root(self.root);self.fd=self.anchor.__enter__();info=os.fstat(self.fd);self.identity=(info.st_dev,info.st_ino);self.root_gid=info.st_gid
        info=os.fstat(self.fd);entry=self.root.stat(follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.geteuid() or stat.S_IMODE(info.st_mode)!=0o700 or self.identity!=(info.st_dev,info.st_ino) or self.identity!=(entry.st_dev,entry.st_ino) or stat.S_IMODE(entry.st_mode)!=0o700 or info.st_gid!=self.root_gid:self.stop('private_root_binding_changed')
        for name in FILES:
            try:value=os.stat(name,dir_fd=self.fd,follow_symlinks=False)
            except FileNotFoundError:continue
            if not stat.S_ISREG(value.st_mode) or value.st_uid!=os.geteuid() or value.st_nlink!=1 or value.st_mode&0o7077 or value.st_size>MAX_DATABASE:self.stop('ordinary_private_database_files_required')
    def root_probe(self,path,label):
        if self.closed or self.failure is not None or self.record.capture_incomplete:self.stop()
        if Path(path)!=self.root:self.stop('root_path_scope_required')
        self.owner.check(path,label)
        return self.owner.perform('private-intake-root-is-symlink',{'path':path,'label':label},lambda:Path(path).is_symlink())
    def root_mkdir(self,path,mode,parents,exist_ok,label):
        if self.closed or self.failure is not None or self.record.capture_incomplete:self.stop()
        if Path(path)!=self.root or (mode,parents,exist_ok)!=(0o700,True,True):self.stop('original_root_mkdir_required')
        self.owner.check(path,label,write=True)
        try:value=Path(path).lstat()
        except (FileNotFoundError,NotADirectoryError):value=None
        direct=value is not None
        self.owner.append({'kind':'private-intake-root-mkdir-strategy','direct_existing':direct})
        if not direct:return self.owner.mkdir(path,mode,parents,exist_ok,label)
        ordinary_ancestors(Path(path).parent)
        if stat.S_ISDIR(value.st_mode):
            with held_root(path) as fd:
                current=os.fstat(fd)
                if current.st_uid!=os.geteuid() or current.st_mode&0o022:self.stop('owned_unshared_root_required')
                return self.owner.perform('private-intake-root-mkdir-existing',{'path':path,'label':label,'mode':mode,'parents':parents,'exist_ok':exist_ok},lambda:Path(path).mkdir(mode=mode,parents=parents,exist_ok=exist_ok))
        return self.owner.perform('private-intake-root-mkdir-existing',{'path':path,'label':label,'mode':mode,'parents':parents,'exist_ok':exist_ok},lambda:Path(path).mkdir(mode=mode,parents=parents,exist_ok=exist_ok))
    def snapshot(self):
        self.guard();info=os.fstat(self.fd);value={'root':{'mode':stat.S_IMODE(info.st_mode),'identity':[info.st_dev,info.st_ino],'uid':info.st_uid,'gid':info.st_gid},'files':{}}
        for name in FILES:
            try:before=os.stat(name,dir_fd=self.fd,follow_symlinks=False)
            except FileNotFoundError:value['files'][name]=None;continue
            fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=self.fd)
            try:
                if signature(before)!=signature(os.fstat(fd)):self.stop('database_file_replaced_during_snapshot')
                parts=[];size=0
                while True:
                    raw=os.read(fd,min(65536,MAX_DATABASE+1-size))
                    if not raw:break
                    parts.append(raw);size+=len(raw)
                    if size>MAX_DATABASE:self.stop('database_file_snapshot_budget')
                if signature(before)!=signature(os.fstat(fd)) or signature(before)!=signature(os.stat(name,dir_fd=self.fd,follow_symlinks=False)):self.stop('database_file_changed_during_snapshot')
                content=self.store(b''.join(parts));value['files'][name]={'mode':stat.S_IMODE(before.st_mode),'identity':[before.st_dev,before.st_ino],'uid':before.st_uid,'gid':before.st_gid,'links':before.st_nlink,'bytes':size,'mtime_ns':before.st_mtime_ns,'ctime_ns':before.st_ctime_ns,'content':content}
            finally:os.close(fd)
        self.guard();return self.store(json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode())
    def error(self,value):
        if type(value).__module__ not in ('sqlite3','builtins') or len(str(value))>65536:self.stop('original_error_not_retained')
        return {'module':type(value).__module__,'type':type(value).__name__,'message':str(value),'sqlite_errorcode':getattr(value,'sqlite_errorcode',None),'sqlite_errorname':getattr(value,'sqlite_errorname',None)}
    def connection(self,args):
        name=args['connection']
        if name not in self.connections:self.stop('connection_capability_required')
        return self.connections[name]
    def cursor(self,args):
        name=args['cursor']
        if name not in self.cursors:self.stop('cursor_capability_required')
        return self.cursors[name]
    def row(self,value):return None if value is None else [atom(v,self.store) for v in value]
    def cursor_result(self,value,connection):
        name='cursor-'+str(len(self.cursors)+1)
        if len(self.cursors)>=32768:self.stop('cursor_budget')
        self.cursors[name]=value;return {'cursor':name,'names':None if value.description is None else [v[0] for v in value.description],'row_mode':'mapping' if connection.row_factory is sqlite3.Row else 'tuple'}
    def native(self,action,args,exception):
        if action=='clock':
            value=time.time()
            if type(value) is not float or not math.isfinite(value):self.stop('clock_required')
            return atom(value,self.store)
        if action=='connect':
            label=args['database'];selected=Path(label) if Path(label).is_absolute() else Path(self.cwd)/label
            if selected!=self.root/'queue.sqlite3' or type(args['timeout']) not in (float,int) or args['timeout']!=30:self.stop('original_connection_scope_required')
            value=sqlite3.connect(selected,timeout=args['timeout']);name='connection-'+str(len(self.connections)+1);self.connections[name]={'native':value,'closed':False}
            return {'connection':name,'sqlite_version':sqlite3.sqlite_version}
        if action in ('iter','next','fetchone','fetchall'):
            value=self.cursor(args)
            if action=='iter':return {'same_cursor':iter(value) is value}
            if action=='next':
                try:row=next(value)
                except StopIteration:return {'stopped':True,'row':None}
                return {'stopped':False,'row':self.row(row)}
            if action=='fetchone':return {'row':self.row(value.fetchone())}
            rows=value.fetchall()
            if len(rows)>MAX_ROWS:self.stop('row_budget')
            return {'rows':[self.row(row) for row in rows]}
        connection=self.connection(args);native=connection['native']
        if action=='row-factory':
            if args['factory']!='sqlite-row':self.stop('original_row_factory_required')
            native.row_factory=sqlite3.Row;return None
        if action=='execute':
            statement(args['sql']);parameters=tuple(scalar(v,self.blob) for v in args['parameters']);return self.cursor_result(native.execute(args['sql'],parameters),native)
        if action=='executescript':statement(args['sql'],True);return self.cursor_result(native.executescript(args['sql']),native)
        if action=='enter':return {'same_connection':native.__enter__() is native}
        if action=='exit':
            if exception is None:self.stop('original_context_exception_required')
            return native.__exit__(*exception)
        if action=='close':
            result=native.close();connection['closed']=True;return result
        self.stop('original_primitive_required')
    def call(self,action,args,*,exception=None):
        if self.closed or self.failure is not None or self.record.capture_incomplete:self.stop()
        if action not in ('connect','clock','execute','executescript','row-factory','enter','exit','close','iter','next','fetchone','fetchall'):self.stop('primitive_profile_required')
        try:
            if action!='clock':self.guard()
            if action=='connect' and not self.started:
                self.initial_snapshot=self.snapshot();self.append({'kind':'private-intake-sql-database-start','snapshot':self.initial_snapshot});self.started=True
            token=self.record.sequence;self.append({'kind':'private-intake-sql-intent','operation':token,'action':action,'arguments':args});value=error=None
            try:value=self.native(action,args,exception)
            except InputAdmissionError:raise
            except Exception as caught:error=caught
            if action!='clock':self.guard()
            self.append({'kind':'private-intake-sql-outcome','operation':token,'result':value,'error':None if error is None else self.error(error)})
        except InputAdmissionError:self.stop()
        except Exception:self.stop('primitive_capture_failed')
        if error is not None:raise error
        return value
    def release_resources(self):
        if self.closed:self.stop('release_repeated')
        extras=[];failure=None;opened=self.fd is not None
        try:
            for name,row in self.connections.items():
                if row['closed']:continue
                try:row['native'].close();row['closed']=True;extras.append(name)
                except Exception as caught:failure=caught
        finally:
            try:
                try:
                    if self.started and not self.record.capture_incomplete:self.final_snapshot=self.snapshot()
                finally:
                    if self.anchor is not None:self.anchor.__exit__(None,None,None)
            except Exception as caught:failure=caught
            finally:self.fd=None;self.closed=True
        if failure is not None:self.stop('resource_cleanup_failed')
        value={'kind':'private-intake-sql-released','original_unclosed_connections':extras,'outside_original_connection_cleanup':extras,'directory_lease_released':opened,'database_snapshot':self.final_snapshot}
        if not self.record.capture_incomplete:self.append(value)
        return {k:v for k,v in value.items() if k!='kind'}
