"""Original request validation before an explicitly selected collection adapter."""
_OMITTED=object()

class PersonalProbeCollection:
    def __init__(self,context):self.context=context

    def collect_probe(self,request,*,repo,previous_comments=(),fetch=_OMITTED,captured_at=None):
        self.context.personal.validate_request(request,repo)
        options={} if fetch is _OMITTED else {'fetch':fetch}
        return self.context.provider.collect_bound(request,assessor=self.context.personal.assess_comments,
            previous_comments=previous_comments,captured_at=captured_at,**options)

    def collect_bound(self,request,*,assessor,previous_comments=(),fetch=_OMITTED,captured_at=None):
        options={} if fetch is _OMITTED else {'fetch':fetch}
        return self.context.provider.collect_bound(request,assessor=assessor,
            previous_comments=previous_comments,captured_at=captured_at,**options)
