"""Whole original collect/verify-provider/verify-new-operating-captures helpers."""
_OMITTED=object()
class OperatingVerification:
    def __init__(self,root,context,*,path_factory,git):
        self.root,self.context,self.Path,self.git=root,context,path_factory,git

    def collect(self,repo=_OMITTED,*,fetch=None,captured_at=None):
        if repo is _OMITTED:repo=self.root
        root=self.Path(repo);value=self.context.operating.request(root);history=self.context.operating.captures(root)
        options={'fetch':fetch} if fetch is not None else {}
        return self.context.provider.collect_bound(value,assessor=self.context.operating.assess,previous_comments=self.context.operating.prior_comments(history),captured_at=captured_at,**options)

    def verify_provider(self,repo=_OMITTED,*,fetch=None):
        if repo is _OMITTED:repo=self.root
        history=self.context.operating.captures(repo)
        self.context.contracts.require(bool(history),'No retained operating acceptance exists')
        latest=self.collect(repo,fetch=fetch)
        self.context.contracts.require(self.context.operating.proof(latest)==self.context.operating.proof(history[-1]),'Operating acceptance changed or was withdrawn at GitHub; capture the correction first')
        self.context.contracts.require(self.context.operating.effective(repo)['effective'],'Personal operating acceptance is not effective')
        return latest

    def verify_new_captures(self,repo,base_ref,*,fetch=None,checked_at=None):
        root=self.Path(repo);history=self.context.operating.captures(root)
        old=set(self.git.check_output(['git','ls-tree','-r','--name-only',base_ref,'--',self.context.operating.CAPTURES],cwd=root,text=True).splitlines())
        count=0
        for n,snapshot in enumerate(history,1):
            if f'{self.context.operating.CAPTURES}/{n:08d}.json' in old:continue
            latest=self.collect(root,fetch=fetch,captured_at=checked_at)
            self.context.contracts.require(self.context.operating.proof(latest)==self.context.operating.proof(snapshot),'New operating acceptance differs from GitHub')
            self.context.contracts.require(self.context.contracts.timestamp(snapshot['result']['captured_at'])<=self.context.contracts.timestamp(latest['result']['captured_at']),'Operating acceptance capture is future-dated')
            if snapshot['result']['status']=='confirmed':
                self.context.contracts.require(self.context.operating.request(root)['implementation_manifest']==self.context.operating.manifest(root),'Implementation changed after acceptance request')
            count+=1
        # A new official projection must not rely on an old operating snapshot after
        # the person withdraws it. Recheck even when no new acceptance capture is added.
        index=self.context.operating.projection(root)
        if index['live_activation_approved']:
            previous=self.git.run(['git','show',f'{base_ref}:{self.context.operating.INDEX}'],cwd=root,capture_output=True)
            if previous.returncode or previous.stdout!=(root/self.context.operating.INDEX).read_bytes():
                self.verify_provider(root,fetch=fetch)
        return count
