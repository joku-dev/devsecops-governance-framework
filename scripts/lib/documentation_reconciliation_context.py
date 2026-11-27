"""Complete original execution over logical file and explicit local-Git ports."""
from contextlib import redirect_stdout,redirect_stderr
import argparse,io,re
from pathlib import PurePosixPath
from lib.synthetic_lifecycle_context import LifecyclePaths,LifecyclePath
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError
from lib.documentation_reconciliation import DocumentationReconciliation
from lib.retained_argparse import formatter_factory,parser_base

class DocumentationPaths(LifecyclePaths):
    def __init__(self,source,cwd,io_port,append_factory):
        super().__init__(source,cwd,io_port);self.append_factory=append_factory
    def path(self,value):
        if isinstance(value,LifecyclePath):
            value=super().path(value).value
        return DocumentationPath(self,PurePosixPath(value))

class DocumentationPath(LifecyclePath):
    def __truediv__(self,value):return self.namespace.path(super().__truediv__(value))
    @property
    def parent(self):return self.namespace.path(super().parent)
    @property
    def parents(self):return tuple(self.namespace.path(value) for value in super().parents)
    def resolve(self,strict=False):return self.namespace.path(super().resolve(strict))
    def open(self,mode='r',encoding=None,errors=None):
        if mode=='a':
            if encoding!='utf-8' or errors is not None:
                raise InputAdmissionError('documentation_original_append_options_required')
            return self.namespace.append_factory(self.namespace.io,self.namespace.absolute(self.value),str(self))
        return super().open(mode,encoding,errors)

def execute(source,cwd,argv,io_port,process_factory,*,append_factory,parser_context=None):
    paths=DocumentationPaths(source,cwd,io_port,append_factory);root=paths.path(source)
    process=process_factory(io_port,root)
    def parser(**options):
        cls=argparse.ArgumentParser if parser_context is None else parser_base(parser_context)
        if parser_context is not None:
            if options.get('fromfile_prefix_chars') is not None:raise InputAdmissionError('retained_argparse_argument_file_expansion_not_admitted')
            options['formatter_class']=formatter_factory(parser_context)
        return cls(prog='reconcile_documentation_after_merge.py',**options)
    kernel=DocumentationReconciliation(root,process=process,path_factory=paths.path,argument_parser=parser,argv=argv)
    out,err=io.StringIO(),io.StringIO();error=signal=None
    try:
      with redirect_stdout(out),redirect_stderr(err):
        try:code=kernel.main()
        except (InputAdmissionError,IntegrityError):raise
        except RetainedOutputError as caught:code,error=1,{'type':caught.original_type,'message':caught.original_message}
        except SystemExit as caught:
            code=0 if caught.code is None else caught.code if type(caught.code) is int else 1
            if caught.code is not None and type(caught.code) is not int:print(caught.code,file=err)
            signal={'type':'SystemExit','value':caught.code}
        except Exception as caught:code,error=1,{'type':process.error_type(caught),'message':str(caught)}
    finally:
        for session in getattr(io_port,'documentation_append_sessions',[]):
            session.release()
    return {'exit_code':0 if code is None else code,'kernel_exception':error,'original_exit_signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue()}
