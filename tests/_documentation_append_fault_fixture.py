"""Same actual buffered native dependency faults for unchanged V1 and prototype."""
import errno,io,os,runpy,sys,signal,subprocess
from contextlib import contextmanager
from unittest.mock import patch

class PartialRaw(io.RawIOBase):
    def __init__(self,raw):super().__init__();self.raw=raw;self.count=0
    def writable(self):return True
    def fileno(self):return self.raw.fileno()
    def write(self,data):
        if self.count:raise OSError(errno.ENOSPC,'injected original append short-write then full disk')
        self.count+=1;return self.raw.write(data[:3])
    def close(self):
        try:self.raw.close()
        finally:super().close()

class FullCloseFailure:
    def __init__(self,stream):self.stream=stream
    @property
    def closed(self):return self.stream.closed
    def fileno(self):return self.stream.fileno()
    def write(self,text):return self.stream.write(text)
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def close(self):
        self.stream.close();raise OSError(errno.EIO,'injected original append close after full bytes')

@contextmanager
def inject(kind):
    if kind.startswith('git-signal-'):
        selected=getattr(signal,kind.removeprefix('git-signal-'));ordinary_process=subprocess.Popen
        def terminated(*args,**kwargs):
            child=ordinary_process(*args,**kwargs)
            if args and isinstance(args[0],list) and os.path.basename(args[0][0])=='git':
                os.kill(child.pid,selected)
            return child
        with patch('subprocess.Popen',side_effect=terminated):yield
        return
    ordinary=io.open
    def selected(file,mode='r',*args,**kwargs):
        stream=ordinary(file,mode,*args,**kwargs)
        if mode!='a':return stream
        if kind=='full-close':return FullCloseFailure(stream)
        if kind!='partial-close':raise ValueError('Unknown isolated append fault')
        buffer=stream.detach();raw=buffer.detach()
        return io.TextIOWrapper(io.BufferedWriter(PartialRaw(raw)),encoding='utf-8')
    with patch('io.open',side_effect=selected):yield

def run_original():
    kind=sys.argv.pop(1);script=sys.argv.pop(1);sys.argv[0]=script
    with inject(kind):runpy.run_path(script,run_name='__main__')
