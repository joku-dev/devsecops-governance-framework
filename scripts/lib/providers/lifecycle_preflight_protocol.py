"""Only original diagnostic repository/run/workflow/artifact/raw-producer GETs."""
import re
from lib.requirement_validation_budget import InputAdmissionError
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.personal_channel_process import ReplayPersonalTransport

STREAM_LIMITS=(16*1024**2,256*1024)
REPOSITORY=r'repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+'
GET=re.compile(REPOSITORY+r'(?:/actions/runs/[1-9][0-9]*(?:/artifacts\?per_page=100&page=(?:[1-9]|10))?|/actions/workflows/[1-9][0-9]*|/actions/artifacts/[1-9][0-9]*(?:/zip)?)?\Z')
RAW=re.compile(REPOSITORY+r'/contents/(?P<name>[A-Za-z0-9_./-]+)\?ref=[a-f0-9]{40}\Z')
class LegacyPreflightProtocol:
    def request(self,kind,arguments,root,cwd):
        if kind!='get' or type(arguments) is not dict or set(arguments)!={'endpoint','raw'}:
            raise InputAdmissionError('preflight_fixed_get_required')
        endpoint,raw=arguments['endpoint'],arguments['raw']
        if type(endpoint) is not str or len(endpoint)>8192 or type(raw) is not bool:
            raise InputAdmissionError('preflight_fixed_get_required')
        if raw:
            match=RAW.fullmatch(endpoint)
            if match is None or any(p in ('','..','.') for p in match['name'].split('/')):
                raise InputAdmissionError('preflight_pinned_raw_get_required')
        elif GET.fullmatch(endpoint) is None:
            raise InputAdmissionError('preflight_fixed_get_endpoint_required')
        original=['gh','api','--hostname','github.com','--method','GET',endpoint]
        if raw:original.extend(['-H','Accept: application/vnd.github.raw+json'])
        return {'kind':kind,'original_arguments':original,'source_root':root,'cwd':cwd,'timeout':90,'text':False}
    def actual_arguments(self,spec,selected):
        original=spec['original_arguments']
        return [original[0] if selected is None else selected,*original[1:]]
class NativePreflightTransport(NativePersonalTransport):
    def __init__(self,owner,root,*,emit_stderr,environment=None,provider_executable='gh'):
        super().__init__(owner,root,LegacyPreflightProtocol(),emit_stderr=emit_stderr,environment=environment,provider_executable=provider_executable,stream_limits=STREAM_LIMITS)
    def fetch(self,endpoint,*,raw=False):return self.request('get',{'endpoint':endpoint,'raw':raw})
class ReplayPreflightTransport(ReplayPersonalTransport):
    def __init__(self,owner,root,*,emit_stderr):
        super().__init__(owner,root,LegacyPreflightProtocol(),emit_stderr=emit_stderr,stream_limits=STREAM_LIMITS)
    def fetch(self,endpoint,*,raw=False):return self.request('get',{'endpoint':endpoint,'raw':raw})
