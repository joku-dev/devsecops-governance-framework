"""Whole original personal-channel programs over explicit context, paths and ports."""
from lib.repository_lifecycle.personal_channel_probe import LifecycleStatementReport
from lib.repository_lifecycle.personal_channel_evidence import LifecycleStatementEvidenceReport

_OMITTED=object()

class PersonalStatementProgram(LifecycleStatementReport):
    def main(self):
        request=self.context.adapter.strict_json((self.root/self.REQUEST).read_bytes())
        self.context.personal.validate_request(request,self.root)
        (self.root/self.TEMPLATE).write_text(self.render(request))
        print('Rendered personal-channel statement; nothing posted to GitHub.')

class PersonalChannelCheckProgram:
    def __init__(self,root,context,*,path_factory,argument_parser,argv,collector):
        self.root,self.context,self.Path=root,context,path_factory
        self.argument_parser,self.argv,self.collector=argument_parser,argv,collector
        self.description='Check or replay a personal-channel probe; this command never posts a statement.'
        self.REQUEST=context.personal_channel_probe.REQUEST

    def main(self):
        parser=self.argument_parser(description=self.description)
        parser.add_argument('--replay',type=self.Path)
        parser.add_argument('--previous-capture',type=self.Path)
        parser.add_argument('--output',type=self.Path)
        args=parser.parse_args(self.argv)
        if args.replay:
            self.context.contracts.require(args.previous_capture is None and args.output is None,'Replay does not fetch or write')
            result=self.context.personal.replay_probe_snapshot(self.context.adapter.strict_json(args.replay.read_bytes()))
        else:
            self.context.contracts.require(args.output is not None,'A new output capture path is required')
            output=args.output.resolve()
            self.context.contracts.require(not output.exists(),'Existing probe capture cannot be replaced')
            if output.is_relative_to(self.root):
                self.context.contracts.require(output.is_relative_to(self.root/'generated/reports/lifecycle-personal-channel'),'Dedicated diagnostic output path required')
            request=self.context.adapter.strict_json((self.root/self.REQUEST).read_bytes())
            previous=[]
            if args.previous_capture:
                snapshot=self.context.adapter.strict_json(args.previous_capture.read_bytes())
                self.context.contracts.require(snapshot['request']==request,'Previous capture belongs to a different request')
                previous=self.context.personal.replay_probe_snapshot(snapshot)['relevant_comments']
                # Retain the first captured identity, including later deletions.
                previous=list({c['id']:c for c in previous+snapshot.get('previous_comments',[])}.values())
            snapshot=self.collector.collect_probe(request,repo=self.root,previous_comments=previous)
            output.parent.mkdir(parents=True,exist_ok=True)
            with output.open('xb') as stream:stream.write(self.context.adapter.json_bytes(snapshot))
            result=snapshot['result']
        print(f"Personal channel probe: {result['status']}; no remediation, closure or live activation authorized.")

class PersonalChannelEvidenceProgram(LifecycleStatementEvidenceReport):
    def __init__(self,root,context,*,path_factory,process,collector):
        super().__init__(root,context,path_factory=path_factory)
        self.process,self.collector=process,collector

    def provider_projection(self,result):
        return {key:result[key] for key in ('request_digest','status','last_statement_id','issues')} | {
            'comments':[self.context.provider.comment_identity(c) for c in result['relevant_comments']]}

    def verify_new_captures(self,repo,base_ref,*,collector=_OMITTED):
        if collector is _OMITTED:collector=self.collector.collect_probe
        repo=self.path_factory(repo);captures=self.load_captures(repo)
        accepted=set(self.process.check_output(['git','ls-tree','-r','--name-only',base_ref,'--',self.CAPTURES],cwd=repo,text=True).splitlines())
        count=0
        for number,snapshot in enumerate(captures,1):
            if f'{self.CAPTURES}/{number:08d}.json' in accepted:continue
            fresh=collector(snapshot['request'],repo=repo,previous_comments=snapshot['previous_comments'])
            self.context.contracts.require(self.context.contracts.timestamp(snapshot['result']['captured_at'])<=self.context.contracts.timestamp(fresh['result']['captured_at']),'Channel capture claims a future observation')
            self.context.contracts.require(self.provider_projection(snapshot['result'])==self.provider_projection(fresh['result']),'Personal channel provider state differs')
            count+=1
        return count

    def main(self):
        captures=self.load_captures()
        (self.root/self.REPORT).write_text(self.render(captures))
        print(f"Rendered {len(captures)} retained personal-channel captures; no lifecycle authorization.")
