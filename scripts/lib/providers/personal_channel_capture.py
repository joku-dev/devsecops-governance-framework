"""Explicit legacy captured-field and read-only fetch profile; no consent authority."""
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.requirement_validation_budget import InputAdmissionError

_DEFAULT_FETCH=object()

class LegacyPersonalChannelCapture(LegacyRepositoryLifecycleCapture):
    def __init__(self,context,*,path_factory=None,fetch=None,clock=None):
        super().__init__(context,path_factory=path_factory)
        self.fetch,self.clock=fetch,clock

    def collect_bound(self,request,*,assessor,previous_comments=(),fetch=_DEFAULT_FETCH,captured_at=None):
        default=fetch is _DEFAULT_FETCH
        if default:
            if self.fetch is None:raise InputAdmissionError('personal_channel_explicit_fetch_port_required')
            fetch=self.fetch
        endpoint=f"repos/{request['repository_id']}/issues/{request['discussion_number']}"
        issue_bytes=fetch(endpoint);issue=self.context.adapter.strict_json(issue_bytes)
        self.context.contracts.require(issue['number']==request['discussion_number'] and issue['html_url']==f"https://github.com/{request['repository_id']}/pull/{request['discussion_number']}"
            and bool(issue.get('pull_request')),'Probe discussion is not the expected pull request')
        def read_comments():
            result=[];raw=[]
            for page in range(1,11):
                data=fetch(endpoint+f'/comments?per_page=100&page={page}');batch=self.context.adapter.strict_json(data)
                self.context.contracts.require(type(batch) is list,'Expected comment page')
                result.extend(batch);raw.append(data.decode())
                if len(batch)<100:return result,raw
            raise ValueError('Personal discussion exceeds supported page count')
        before,raw_before=read_comments();after,raw_after=read_comments()
        self.context.contracts.require(before==after,'Personal discussion changed during capture')
        if not captured_at and self.clock is None:raise InputAdmissionError('personal_channel_explicit_clock_port_required')
        at=captured_at or self.clock()
        result=assessor(request,after,captured_at=at,previous_comments=previous_comments)
        return {'request':request,'result':result,'issue_response':issue_bytes.decode(),
            'comment_pages_before':raw_before,'comment_pages_after':raw_after,'previous_comments':list(previous_comments),
            'capture_method':'github_api_get_via_gh' if default else 'injected_test_transport'}
