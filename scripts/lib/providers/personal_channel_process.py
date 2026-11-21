"""Finite raw-pipe process capture with original timeout and observed group cleanup."""
import os,selectors,subprocess,time
from lib.providers import process_groups
from lib.personal_channel_process import MAX_STDOUT,MAX_STDERR
from lib.requirement_validation_budget import InputAdmissionError

class NativeReadProcess:
    def __init__(self,*,stream_limits=(MAX_STDOUT,MAX_STDERR)):
        if type(stream_limits) is not tuple or len(stream_limits)!=2 or type(stream_limits[0]) is not int or not 0<stream_limits[0]<=16*1024**2 or type(stream_limits[1]) is not int or stream_limits[1]!=MAX_STDERR:raise InputAdmissionError("personal_process_stream_profile")
        self.stream_limits=stream_limits
        self.observation={'started':False,'terminal_observed':False,'returncode':None,'timed_out':False,
            'stream_budget_exceeded':False,'cleanup_signal_permission_denied':False,'cleanup_absence_check':'not_needed',
            'OS_network_or_process_tree_isolation_attested':False}

    def run(self,arguments,cwd,environment,timeout):
        process=None;buffers={'stdout':bytearray(),'stderr':bytearray()};limits=dict(zip(('stdout','stderr'),self.stream_limits))
        drain_deadline=None
        try:
            process=subprocess.Popen(arguments,cwd=cwd,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
            # subprocess.check_output starts its communicate timeout only after
            # Popen construction has returned; creation time is not included.
            started=time.monotonic()
            self.observation['started']=True
            with selectors.DefaultSelector() as selector:
                for name in buffers:
                    stream=getattr(process,name);os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,name)
                while selector.get_map() or process.poll() is None:
                    now=time.monotonic()
                    if drain_deadline is None and now-started>=timeout:
                        self.observation['timed_out']=True;process_groups.stop(process);drain_deadline=time.monotonic()+2
                    if drain_deadline is not None and now>=drain_deadline:raise InputAdmissionError('personal_process_pipe_drain_incomplete')
                    for selected,_ in selector.select(.02):
                        raw=os.read(selected.fd,65536)
                        if not raw:selector.unregister(selected.fileobj);continue
                        channel=selected.data
                        if len(buffers[channel])+len(raw)>limits[channel]:
                            self.observation['stream_budget_exceeded']=True;raise InputAdmissionError('personal_process_stream_budget')
                        buffers[channel].extend(raw)
            code=process.wait(timeout=2)
            self.observation.update(terminal_observed=True,returncode=code)
            return code,bytes(buffers['stdout']),bytes(buffers['stderr'])
        finally:
            try:
                if process is not None:process_groups.stop(process,graceful=process.poll() is None)
            finally:
                if process is not None:process.stdout.close();process.stderr.close()
                self.observation.update(process_groups.observations(process))
