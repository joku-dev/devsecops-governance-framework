"""Complete original request preparation and main guard over explicit ports."""
_OMITTED=object()

class PilotActionPreparation:
    def __init__(self,root,context,*,path_factory,argument_parser,argv,clock):
        self.root,self.context,self.Path=root,context,path_factory
        self.argument_parser,self.argv,self.clock=argument_parser,argv,clock
        self.description='Prepare a complete action request and printable statement; never issue personal consent.'

    def prepare(self,body,discussion_number,*,repo=_OMITTED,created_at=None):
        if repo is _OMITTED:repo=self.root
        profile,binding,receipts,actions=self.context.actions.load_context(repo)
        self.context.contracts.require(bool(receipts),'A retained pilot receipt is required')
        at=created_at or self.clock()
        role=self.context.actions.required_role({'body':body},actions)
        request={'schema_version':'0.1.0','request_type':'lifecycle-pilot-action','environment':'live_pilot_validation',
            'repository_id':profile['scope']['repository_id'],'scope':profile['scope'],
            'operating_profile_ref':self.context.preparation.revision_ref(profile),'role_binding_ref':self.context.preparation.revision_ref(binding),'created_at':at,
            'discussion_number':discussion_number,'required_role':role,'required_subject_id':binding['assignments'][role],
            'expected_receipt_head':self.context.kernel.transaction_ref(receipts[-1]),'expected_action_head':self.context.kernel.transaction_ref(actions[-1]) if actions else None,
            'expected_revision':len(receipts)+len(actions),'body':body}
        self.context.actions.validate_context(request,profile,binding,receipts,actions,at=at)
        return request

    def main(self):
        parser=self.argument_parser(description=self.description)
        parser.add_argument('--body',type=self.Path,required=True)
        parser.add_argument('--discussion-number',type=int,required=True)
        parser.add_argument('--output',type=self.Path,required=True)
        args=parser.parse_args(self.argv)
        request=self.prepare(self.context.adapter.strict_json(args.body.read_bytes()),args.discussion_number)
        self.context.contracts.require(not args.output.exists(),'Request cannot replace an existing file')
        with args.output.open('xb') as stream:stream.write(self.context.adapter.json_bytes(request))
        print('Review the complete request before personally issuing this statement. No live activation is authorized.')
        print(self.context.personal.statement_body(request))
