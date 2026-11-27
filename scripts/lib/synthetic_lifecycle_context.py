"""Entire synthetic generator execution over logical paths and explicit IO."""
import argparse,io,posixpath
from contextlib import redirect_stdout,redirect_stderr
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.synthetic_lifecycle_reports import (SyntheticIndex,SyntheticPilot,
    SyntheticExceptions,SyntheticOverview,SyntheticViewer)
from lib.requirement_validation_budget import InputAdmissionError
from lib.retained_argparse import parser_base,formatter_factory
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

GENERATORS={'index':('generate_governance_lifecycle_index.py',SyntheticIndex),
    'pilot':('generate_governance_lifecycle_pilot.py',SyntheticPilot),
    'exceptions':('generate_governance_lifecycle_exceptions.py',SyntheticExceptions),
    'overview':('generate_governance_lifecycle_overview.py',SyntheticOverview),
    'viewer':('generate_governance_lifecycle_viewer.py',SyntheticViewer)}


class LifecyclePaths:
 def __init__(self,source,cwd,io_port):
  self.source,self.cwd=PurePosixPath(source),PurePosixPath(cwd);self.io=io_port
  if any(not p.is_absolute() or '..' in p.parts for p in (self.source,self.cwd)):raise InputAdmissionError('synthetic_lifecycle_absolute_context_required')
 def path(self,value):
  if isinstance(value,LifecyclePath):
   if value.namespace is not self:raise InputAdmissionError('synthetic_lifecycle_foreign_path')
   return value
  return LifecyclePath(self,PurePosixPath(value))
 def absolute(self,value):return posixpath.normpath(str(value if value.is_absolute() else self.cwd/value))


class LifecyclePath:
 def __init__(self,namespace,value):self.namespace,self.value=namespace,value
 def __str__(self):return str(self.value)
 def __repr__(self):return 'PosixPath('+repr(str(self))+')'
 def __hash__(self):return hash((id(self.namespace),self.value))
 def __eq__(self,other):return isinstance(other,LifecyclePath) and self.namespace is other.namespace and self.value==other.value
 def __lt__(self,other):return self.value<self.namespace.path(other).value
 def __truediv__(self,value):
  if isinstance(value,LifecyclePath):value=self.namespace.path(value).value
  try:joined=self.value/value
  except TypeError as error:raise TypeError(str(error).replace("'PurePosixPath' and","'PosixPath' and",1)) from None
  return LifecyclePath(self.namespace,joined)
 @property
 def parent(self):return LifecyclePath(self.namespace,self.value.parent)
 @property
 def parents(self):return tuple(LifecyclePath(self.namespace,p) for p in self.value.parents)
 @property
 def name(self):return self.value.name
 @property
 def suffix(self):return self.value.suffix
 @property
 def parts(self):return self.value.parts
 def as_posix(self):return self.value.as_posix()
 def is_absolute(self):return self.value.is_absolute()
 def relative_to(self,other):return self.value.relative_to(self.namespace.path(other).value)
 def is_relative_to(self,other):return self.value.is_relative_to(self.namespace.path(other).value)
 def resolve(self,strict=False):
  value=LifecyclePath(self.namespace,PurePosixPath(self.namespace.absolute(self.value)))
  if strict and not value.exists():
   import errno
   raise FileNotFoundError(errno.ENOENT,'No such file or directory',str(value))
  return value
 def probe(self,kind):return self.namespace.io.probe(self.namespace.absolute(self.value),kind,str(self))
 def exists(self):return self.probe('exists')
 def is_dir(self):return self.probe('is_dir')
 def is_file(self):return self.probe('is_file')
 def is_symlink(self):return self.probe('is_symlink')
 def read_bytes(self):return self.namespace.io.read(self.namespace.absolute(self.value),str(self))
 def open(self,mode='r',encoding=None,errors=None):
  if mode not in ('r','rt','rb'):raise InputAdmissionError('synthetic_lifecycle_original_read_mode_required')
  if mode!='rb':encoding=self.namespace.io.text_encoding(encoding,errors)
  buffer=io.BytesIO(self.read_bytes());buffer.name=str(self)
  return buffer if mode=='rb' else io.TextIOWrapper(buffer,encoding=encoding,errors=errors)
 def read_text(self,encoding=None,errors=None):
  with self.open(encoding=encoding,errors=errors) as stream:return stream.read()
 def iterdir(self):
  return iter(self/child for child in self.namespace.io.iterdir(self.namespace.absolute(self.value),str(self)))
 def glob(self,pattern):
  if type(pattern) is not str or not pattern or '/' in pattern or pattern in ('.','..'):raise InputAdmissionError('synthetic_lifecycle_original_glob_required')
  if not self.is_dir():return
  for path in self.iterdir():
   if fnmatchcase(path.name,pattern):yield path
 def mkdir(self,mode=0o777,parents=False,exist_ok=False):return self.namespace.io.mkdir(self.namespace.absolute(self.value),mode,parents,exist_ok,str(self))
 def write_bytes(self,raw):return self.namespace.io.write_bytes(self.namespace.absolute(self.value),raw,str(self))
 def write_text(self,value,encoding=None,errors=None):return self.namespace.io.write_text(self.namespace.absolute(self.value),value,encoding,errors,str(self))


def execute(source,cwd,name,argv,io_port,*,validator_class,parser_context=None):
 if name not in GENERATORS:raise InputAdmissionError('synthetic_lifecycle_generator_not_supported')
 paths=LifecyclePaths(source,cwd,io_port);root=paths.path(source)
 context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=paths.path)
 def parser(filename,**options):
  cls=argparse.ArgumentParser if parser_context is None else parser_base(parser_context)
  if parser_context is not None:
   if options.get('fromfile_prefix_chars') is not None:raise InputAdmissionError('retained_argparse_argument_file_expansion_not_admitted')
   options['formatter_class']=formatter_factory(parser_context)
  return cls(prog=filename,**options)
 def make(kind,overview=None):
  filename,cls=GENERATORS[kind]
  return cls(root,context,path_factory=paths.path,
      argument_parser=lambda **kw:parser(filename,**kw),argv=argv,overview=overview)
 overview=make('overview');context.governance_lifecycle_overview=overview
 item=overview if name=='overview' else make(name,overview)
 out,err=io.StringIO(),io.StringIO()
 with redirect_stdout(out),redirect_stderr(err):
  try:code,error,signal=item.main(),None,None
  except (InputAdmissionError,IntegrityError):raise
  except RetainedOutputError as failure:code,error,signal=1,{'type':failure.original_type,'message':failure.original_message},None
  except SystemExit as failure:
   value=failure.code
   if len(str(value))>65536:raise InputAdmissionError('synthetic_lifecycle_exit_message_budget') from failure
   code=0 if value is None else value if isinstance(value,int) else 1
   if value is not None and not isinstance(value,int):print(value,file=err)
   error=None;signal={'type':'SystemExit','value':value}
  except Exception as failure:
   if len(str(failure))>65536:raise InputAdmissionError('synthetic_lifecycle_error_message_budget') from failure
   code,error,signal=1,{'type':type(failure).__name__,'message':str(failure)},None
  if code is None:code=0
  stdout,stderr=out.getvalue(),err.getvalue()
  if len(stdout)>131072 or len(stderr)>131072:raise InputAdmissionError('synthetic_lifecycle_stream_budget')
 return {'exit_code':code,'kernel_exception':error,'original_exit_signal':signal,'stdout':stdout,'stderr':stderr}
