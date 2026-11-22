"""Actual original HTTPS Reader with opaque credentials and durable read intents."""
import json
from lib.providers.transports import Reader
from lib.provider_observation_reads import capability,access_wire,MAX_RESPONSE
from lib.provider_errors import AccessFailure
from lib.requirement_validation_budget import InputAdmissionError


def contains_secret(value,secret):
    if not secret:return False
    if isinstance(value,str):return secret in value
    if isinstance(value,list):return any(contains_secret(x,secret) for x in value)
    if isinstance(value,dict):return any(contains_secret(k,secret) or contains_secret(v,secret) for k,v in value.items())
    return False


class NativeObservationReads:
    """Trusted composition supplies a checked in-memory credential resolver only.

    This port does not itself claim private-file/ACL validation or whole operator
    completion. Those remain the surrounding observation context's responsibility.
    """
    def __init__(self,record,resolve_secret):self.record,self.resolve_secret=record,resolve_secret;self.sessions={};self.failed=False;self.closed=False
    def stop(self):
        self.record.capture_incomplete=True;self.failed=True
        raise InputAdmissionError('provider_observation_read_capture_incomplete') from None
    def append(self,row):
        try:self.record.append(row)
        except Exception:self.stop()
    def begin(self,action,args):
        if self.closed:raise InputAdmissionError('provider_observation_read_session_closed')
        if self.failed or self.record.capture_incomplete:self.stop()
        token=self.record.sequence;self.append({'kind':'provider-observation-read-intent','operation':token,'action':action,'arguments':args});return token
    def end(self,token,value):self.append({'kind':'provider-observation-read-returned','operation':token,'result':value})
    def open(self,reader,base,secret,budget):
        cap=capability(secret)
        if type(budget) is not int or not 1<=budget<=150:raise InputAdmissionError('provider_observation_reader_budget_required')
        token=self.begin('open',{'base':base,'credential':cap,'budget':budget})
        try:
            private=self.resolve_secret(secret)
            if type(private) is not str or len(private)>65536:self.stop()
            if secret.stripped:private=private.strip()
            phases=[]
            class ObservedNativeReader(Reader):
                def url(this,path):phases.append('url');return super().url(path)
            native=ObservedNativeReader(base,private,budget=budget);name='reader-'+str(len(self.sessions)+1)
            self.sessions[id(reader)]={'session':name,'native':native,'url_phases':phases,'managed':reader}
            self.end(token,{'session':name,'calls':0})
        except Exception:self.stop()
    def get(self,reader,path):
        if id(reader) not in self.sessions or type(path) is not str:raise InputAdmissionError('provider_observation_reader_session_required')
        state=self.sessions[id(reader)];native=state['native'];phases=state['url_phases']
        if (reader.base!=native.base or reader.budget!=native.budget or reader.calls!=native.calls
                or reader.token!='' or reader.cache is not None):self.stop()
        token=self.begin('get',{'session':state['session'],'path':path,'calls_before':native.calls});phases.clear();response=None;failure=None;error=None
        try:
            try:value=native.get(path)
            except AccessFailure as caught:error=caught;failure=access_wire(caught)
            else:
                if contains_secret(value,native.token):self.stop()
                raw=json.dumps(value,ensure_ascii=True,allow_nan=True,separators=(',',':')).encode()
                if len(raw)>MAX_RESPONSE:self.stop()
                response=self.record.blob(raw)
            if phases not in ([],['url']):self.stop()
            reader.calls=native.calls
            self.end(token,{'calls_after':native.calls,'url_entered':bool(phases),'response':response,'failure':failure})
        except Exception:self.stop()
        if error is not None:raise error
        return value
    def release_credentials(self):
        for state in self.sessions.values():state['native'].token=''
        self.resolve_secret=None;self.closed=True
