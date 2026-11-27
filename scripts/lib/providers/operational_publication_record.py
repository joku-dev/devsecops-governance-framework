"""Intent-before-effect capture of each whole original native publisher operation."""
import platform,subprocess,sys
from pathlib import Path
from lib.operational_publication_process import value,EFFECT,observation
from lib.requirement_review_output import RetainedOutputError
from lib.requirement_validation_budget import InputAdmissionError

def identity(row):return {'identity':row[:2],'uid':row[2],'mode':row[3]}

class RecordingPublisherProcess:
    def __init__(self,owner,profile,native):
        self.owner,self.profile,self.calls=owner,profile,0;self.observations=[]
        self.native,self.native_factory=(None,native) if callable(native) else (native,None)
    def run(self,command,**options):
        self.calls+=1
        if self.calls>1024:raise InputAdmissionError('publisher_process_capture_budget')
        spec=self.profile.request(list(command),options);cache={}
        def store(raw):
            ref=self.owner.blob(raw);cache[ref['sha256']]=raw;return ref
        def effect():
            if self.native is None:self.native=self.native_factory()
            before=identity(list(self.native.context()));git_before=identity(list(self.native.git_context()));error=None
            try:self.native.run(command,**({**options,'cwd':Path(str(options['cwd']))} if 'cwd' in options else options))
            except InputAdmissionError:raise
            except (subprocess.CalledProcessError,OSError,UnicodeError) as caught:error={'type':type(caught).__name__,'message':str(caught)}
            captured=self.native.last_native
            if captured is None:raise InputAdmissionError('publisher_native_result_not_observed')
            row=captured['row'];code=captured['returncode'];observe=row['observation']
            if observe['timed_out'] or observe['stream_budget_exceeded']:raise InputAdmissionError('publisher_native_process_incomplete')
            transport={'schema_version':1,'specification':{**spec,'kind':'git-run','text':False},'actual_arguments':row['actual_arguments'],'program':row['program'],
                'source_before':before,'source_after':identity(list(self.native.context())),
                'returncode':code,'stdout':store(captured['raw_stdout']),'stderr':store(captured['raw_stderr']),
                'start_error':captured['start_error'],'original_error':None,'signal_context':None,'effective_encoding':None,'observation':observe}
            signal={'implementation':sys.implementation.name,'version':list(sys.version_info[:3]),'system':platform.system()} if code is not None and code<0 and spec['check'] else None
            return {'schema_version':1,'specification':spec,'transport':transport,'stdin':None if captured['raw_stdin'] is None else store(captured['raw_stdin']),
                'effective_encoding':captured['effective_encoding'],'original_error':error,'signal_context':signal,
                'Git_before':git_before,'Git_after':identity(list(self.native.git_context())),'effect_claim':dict(EFFECT),'remote_binding':row['remote'],'native_working_directory':row['cwd']}
        try:wire=self.owner.perform('operational-publisher-process',spec,effect)
        except Exception:
            self.owner.record.capture_incomplete=True;raise
        try:result=value(wire,spec,self.profile,lambda ref:cache[ref['sha256']])
        except (RetainedOutputError,UnicodeError):self.observations.append(observation(wire));raise
        self.observations.append(observation(wire));return result
