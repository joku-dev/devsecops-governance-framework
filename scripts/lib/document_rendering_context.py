"""Complete original renderer over logical paths, bounded named YAML and ports."""
import argparse
from contextlib import redirect_stdout,redirect_stderr
import io
from pathlib import PurePosixPath
import posixpath

import yaml

from lib.document_rendering import GovernanceDocumentRenderer
from lib.retained_argparse import parser_base,formatter_factory
from lib.operations_sources import SourceLoader
from lib.requirement_validation_budget import InputAdmissionError,YAML_ADMISSION_LIMITS
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError


def named_yaml(stream):
    # Keep SafeLoader's original stream name/decoding/error marks; only composition
    # and expanded alias limits are additional admission conditions.
    try:return yaml.load(stream,Loader=SourceLoader)
    except ValueError as error:
        if str(error) in YAML_ADMISSION_LIMITS:raise InputAdmissionError(str(error)) from error
        raise


class DocumentPaths:
    def __init__(self,cwd,data,output):
        self.cwd=PurePosixPath(cwd);self.data,self.output=data,output
        if not self.cwd.is_absolute() or '..' in self.cwd.parts:raise ValueError('document_rendering_root_invalid')
    def path(self,value):
        if isinstance(value,DocumentPath):
            if value.namespace is not self:raise ValueError('document_rendering_foreign_path')
            return value
        return DocumentPath(self,PurePosixPath(value))
    def absolute(self,value):return posixpath.normpath(str(value if value.is_absolute() else self.cwd/value))


class DocumentPath:
    def __init__(self,namespace,value):self.namespace,self.value=namespace,value
    def __str__(self):return str(self.value)
    def __truediv__(self,value):
        if isinstance(value,DocumentPath):
            if value.namespace is not self.namespace:raise InputAdmissionError('document_rendering_foreign_path')
            value=value.value
        try:joined=self.value/value
        except TypeError as error:
            message=str(error)
            prefix="unsupported operand type(s) for /: 'PurePosixPath' and "
            if message.startswith(prefix):raise TypeError(message.replace(prefix,"unsupported operand type(s) for /: 'PosixPath' and ",1)) from None
            raise
        return DocumentPath(self.namespace,joined)
    @property
    def parent(self):return DocumentPath(self.namespace,self.value.parent)
    def relative_to(self,value):return self.value.relative_to(PurePosixPath(str(value)))
    def open(self,mode='r',encoding=None):
        if mode!='r' or encoding!='utf-8':raise InputAdmissionError('document_rendering_original_text_read_required')
        raw=self.namespace.data.read(self.namespace.absolute(self.value),str(self))
        buffer=io.BytesIO(raw);buffer.name=str(self)
        return io.TextIOWrapper(buffer,encoding=encoding,newline=None)
    def read_text(self,encoding=None):
        with self.open('r',encoding=encoding) as stream:return stream.read()
    def mkdir(self,mode=0o777,parents=False,exist_ok=False):
        return self.namespace.output.mkdir(self.namespace.absolute(self.value),mode,parents,exist_ok,str(self))
    def write_text(self,value,encoding=None):
        if encoding!='utf-8' or not isinstance(value,str):raise InputAdmissionError('document_rendering_original_utf8_required')
        if len(value)>32*1024**2:raise InputAdmissionError('document_rendering_output_budget')
        return self.namespace.output.write_text(self.namespace.absolute(self.value),value,encoding,str(self))


def execute(source_label,argv,data,output,tools,*,program='render_governance_documents.py',parser_context=None):
    paths=DocumentPaths(source_label,data,output);stdout,stderr=io.StringIO(),io.StringIO()
    def parser():
        cls=argparse.ArgumentParser if parser_context is None else parser_base(parser_context)
        options={} if parser_context is None else {'formatter_class':formatter_factory(parser_context)}
        return cls(prog=program,**options)
    renderer=GovernanceDocumentRenderer(paths.path(source_label),path_factory=paths.path,
        yaml_load=named_yaml,which=tools.which,run_process=tools.run,
        argument_parser=parser,argv=argv)
    with redirect_stdout(stdout),redirect_stderr(stderr):
        try:code,error,signal=renderer.main(),None,None
        except (InputAdmissionError,IntegrityError):raise
        except RetainedOutputError as failure:
            code,error,signal=1,{'type':failure.original_type,'message':failure.original_message},None
        except SystemExit as failure:
            value=failure.code
            if len(str(value))>65536:raise InputAdmissionError('document_rendering_exit_message_budget') from failure
            if value is None:code=0
            elif isinstance(value,int):code=value
            else:code=1;print(value,file=stderr)
            error=None;signal={'type':'SystemExit','value':value}
        except Exception as failure:
            if len(str(failure))>65536:raise InputAdmissionError('document_rendering_error_message_budget') from failure
            code,error,signal=1,{'type':type(failure).__name__,'message':str(failure)},None
    if len(stdout.getvalue())>131072 or len(stderr.getvalue())>131072:raise InputAdmissionError('document_rendering_stream_budget')
    return {'exit_code':code,'stdout':stdout.getvalue(),'stderr':stderr.getvalue(),'kernel_exception':error,'original_exit_signal':signal}
