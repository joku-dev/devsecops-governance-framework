"""Closed read-session protocol; retained GETs never confer provider authority."""
import json,math,re
from functools import wraps
from lib.provider_observation_context import SecretText
from lib.provider_errors import AccessFailure
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError

MAX_RESPONSE=16*1024**2
ACCESS_CODE=re.compile(r'(?:http_[0-9]{3}|rate_limited|provider_read_failed|request_budget_exhausted|provider_pagination_limit)\Z')


def require(value,reason):
    if not value:raise IntegrityError('provider_observation_'+reason)


def capability(value):
    if (not isinstance(value,SecretText) or type(value.identifier) is not str
            or re.fullmatch(r'credential-[1-9][0-9]{0,3}',value.identifier) is None or type(value.stripped) is not bool):
        raise InputAdmissionError('provider_observation_secret_capability_required')
    return {'identifier':value.identifier,'stripped':value.stripped}


def access_wire(error):
    if (type(error) is not AccessFailure or type(error.code) is not str or not ACCESS_CODE.fullmatch(error.code)
            or type(error.retryable) is not bool or type(error.delay) not in (int,float)
            or not math.isfinite(error.delay) or error.delay<0):
        raise InputAdmissionError('provider_observation_redacted_access_failure_required')
    return {'code':error.code,'retryable':error.retryable,'delay':error.delay}


def access_error(value):
    require(type(value) is dict and set(value)=={'code','retryable','delay'},'access_failure_changed')
    try:error=AccessFailure(**value);expected=access_wire(error)
    except (TypeError,ValueError,InputAdmissionError):raise IntegrityError('provider_observation_access_failure_changed') from None
    require(json.dumps(expected,sort_keys=True)==json.dumps(value,sort_keys=True),'access_failure_types_changed')
    return error


def reader_type(port,reader_base):
    """Retain the original Reader pagination and pure endpoint initialization."""
    class ObservedReader(reader_base):
        def __init__(self,base,secret,*,budget=100):
            super().__init__(base,'',budget=budget)
            port.open(self,base,secret,budget)
        def get(self,path):return port.get(self,path)
        def download(self,*args,**kwargs):
            raise InputAdmissionError('provider_observation_GET_only_reader_required')
    return ObservedReader


def replay_guard(method):
    @wraps(method)
    def guarded(self,*args,**kwargs):
        if self.failure is not None:raise self.failure
        try:return method(self,*args,**kwargs)
        except (IntegrityError,InputAdmissionError) as error:self.failure=error;raise
    return guarded


class ReplayObservationReads:
    """Shared parent cursor and raw response blobs only; no credentials or HTTP."""
    def __init__(self,cursor,blob,*,reader_url):self.cursor,self.blob,self.reader_url=cursor,blob,reader_url;self.sessions={};self.failure=None
    def outcome(self,action,args):
        if self.failure is not None:raise self.failure
        try:
            token=self.cursor.position;intent=self.cursor.row()
            expected={'kind':'provider-observation-read-intent','operation':token,'action':action,'arguments':args}
            try:equal=json.dumps(intent,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False)
            except (ValueError,TypeError):equal=False
            require(equal,'read_intent_changed')
            row=self.cursor.row()
            require(type(row) is dict and set(row)=={'kind','operation','result'} and row['kind']=='provider-observation-read-returned'
                and type(row['operation']) is int and row['operation']==token,'read_completion_changed')
            return row['result']
        except (IntegrityError,InputAdmissionError) as error:self.failure=error;raise
    @replay_guard
    def open(self,reader,base,secret,budget):
        cap=capability(secret);require(type(budget) is int and 1<=budget<=150,'reader_budget_changed')
        args={'base':base,'credential':cap,'budget':budget};value=self.outcome('open',args);name='reader-'+str(len(self.sessions)+1)
        require(type(value) is dict and value=={'session':name,'calls':0} and type(value['calls']) is int,'reader_session_changed');self.sessions[id(reader)]={'session':name,'base':reader.base,'budget':budget,'calls':0,'managed':reader}
    @replay_guard
    def get(self,reader,path):
        require(id(reader) in self.sessions and type(path) is str,'reader_session_or_path_changed');state=self.sessions[id(reader)]
        require(reader.base==state['base'] and reader.budget==state['budget'] and reader.calls==state['calls'] and reader.token=='' and reader.cache is None,'reader_state_changed')
        args={'session':state['session'],'path':path,'calls_before':state['calls']};value=self.outcome('get',args)
        require(type(value) is dict and set(value)=={'calls_after','url_entered','response','failure'}
            and type(value['calls_after']) is int and type(value['url_entered']) is bool,'GET_result_changed')
        local_error=None
        if value['url_entered']:
            try:self.reader_url(reader,path)
            except ValueError:local_error=AccessFailure('provider_read_failed',True)
            except AccessFailure as error:local_error=error
        require(reader.calls==value['calls_after'],'GET_call_counter_changed');state['calls']=reader.calls
        if value['failure'] is not None:
            require(value['response'] is None,'failed_GET_has_response');error=access_error(value['failure'])
            if local_error is not None:require(access_wire(error)==access_wire(local_error),'local_GET_failure_changed')
            elif not value['url_entered']:require(access_wire(error)==access_wire(AccessFailure('provider_read_failed',True)),'pre_URL_failure_changed')
            raise error
        require(value['url_entered'] and local_error is None and value['response'] is not None,'GET_success_without_request')
        try:raw=self.blob(value['response'])
        except (KeyError,ValueError,OSError,TypeError):raise IntegrityError('provider_observation_GET_response_missing_or_changed') from None
        require(type(raw) is bytes and len(raw)<=MAX_RESPONSE,'GET_response_budget')
        try:
            value=json.loads(raw)
            require(json.dumps(value,ensure_ascii=True,allow_nan=True,separators=(',',':')).encode()==raw,'GET_response_encoding_changed')
            return value
        except (ValueError,UnicodeError):raise IntegrityError('provider_observation_GET_response_json_changed') from None
