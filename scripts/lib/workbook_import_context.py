"""Complete original main over logical paths and explicit lazy IO ports."""
import argparse
from contextlib import redirect_stdout,redirect_stderr
import io
from pathlib import PurePosixPath
import posixpath

from lib.harmonized_workbook_import import HarmonizedWorkbookImport
from lib.workbook_import_limits import InputAdmissionError,yaml_text,workbook_archive
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError


class WorkbookPaths:
    def __init__(self,cwd_label,data_port,output_port):
        self.cwd=PurePosixPath(cwd_label);self.data,self.output=data_port,output_port
        if not self.cwd.is_absolute() or '..' in self.cwd.parts:
            raise ValueError('workbook_import_working_directory_invalid')
    def path(self,value):
        if isinstance(value,WorkbookPath):
            if value.namespace is not self:raise ValueError('workbook_import_foreign_path')
            return value
        return WorkbookPath(self,PurePosixPath(value))
    def absolute(self,value):
        return posixpath.normpath(str(value if value.is_absolute() else self.cwd/value))


class WorkbookPath:
    def __init__(self,namespace,value):self.namespace,self.value=namespace,value
    def __str__(self):return str(self.value)
    def __truediv__(self,value):return WorkbookPath(self.namespace,self.value/str(value))
    @property
    def parent(self):return WorkbookPath(self.namespace,self.value.parent)
    def relative_to(self,other):return self.value.relative_to(PurePosixPath(str(other)))
    def read_bytes(self):return self.namespace.data.read(self.namespace.absolute(self.value),str(self))
    def read_text(self,encoding=None):
        with io.TextIOWrapper(io.BytesIO(self.read_bytes()),encoding=encoding or 'utf-8',newline=None) as stream:
            return stream.read()
    def mkdir(self,mode=0o777,parents=False,exist_ok=False):
        return self.namespace.output.mkdir(self.namespace.absolute(self.value),mode,parents,exist_ok,str(self))
    def write_text(self,data,encoding=None):
        if encoding!='utf-8' or not isinstance(data,str):raise InputAdmissionError('workbook_import_original_utf8_required')
        if len(data)>32*1024**2:raise InputAdmissionError('workbook_import_output_budget')
        return self.namespace.output.write_text(self.namespace.absolute(self.value),data,encoding,str(self))


def execute(source_label,cwd_label,argv,data_port,output_port,*,program='import_harmonized_requirements_workbook.py',selection=None):
    namespace=WorkbookPaths(cwd_label,data_port,output_port);root=namespace.path(source_label)
    if not root.value.is_absolute() or '..' in root.value.parts:
        raise ValueError('workbook_import_source_label_invalid')
    stdout,stderr=io.StringIO(),io.StringIO()
    class SelectedParser(argparse.ArgumentParser):
        def parse_args(self,*args,**kwargs):
            value=super().parse_args(*args,**kwargs)
            if selection is not None:
                def selected(path):return {'path':namespace.absolute(path.value),'label':str(path)}
                selection({'inputs':[selected(value.requirements_model),selected(value.input_xlsx)],
                    'outputs':[selected(value.mapping_output),selected(value.report_json),selected(value.report_md)]})
            return value
    with redirect_stdout(stdout),redirect_stderr(stderr):
        engine=HarmonizedWorkbookImport(root,path_factory=namespace.path,zip_file=workbook_archive,
            yaml_load=yaml_text,argument_parser=lambda:SelectedParser(prog=program),argv=argv)
        try:
            code,error,signal=engine.main(),None,None
        except (InputAdmissionError,IntegrityError):raise
        except RetainedOutputError as failure:
            code,error,signal=1,{'type':failure.original_type,'message':failure.original_message},None
        except SystemExit as failure:
            value=failure.code
            if len(str(value))>65536:raise InputAdmissionError('workbook_original_exit_message_budget') from failure
            if value is None:code=0
            elif isinstance(value,int):code=value
            else:code=1;print(value,file=stderr)
            error=None;signal={'type':'SystemExit','value':value}
        except Exception as failure:
            if len(str(failure))>65536:raise InputAdmissionError('workbook_original_error_message_budget') from failure
            code,error,signal=1,{'type':type(failure).__name__,'message':str(failure)},None
    if len(stdout.getvalue())>131072 or len(stderr.getvalue())>131072:
        raise InputAdmissionError('workbook_original_stream_budget')
    return {'exit_code':code,'stdout':stdout.getvalue(),'stderr':stderr.getvalue(),
            'kernel_exception':error,'original_exit_signal':signal}
