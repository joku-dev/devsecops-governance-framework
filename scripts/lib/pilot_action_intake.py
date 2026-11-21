"""Entire original action intake, collection and atomic two-ledger append."""
_OMITTED=object()
class PilotActionIntake:
    def __init__(self,root,context,*,path_factory,argument_parser,argv,clock):
        self.root,self.context,self.Path=root,context,path_factory
        self.argument_parser,self.argv,self.clock=argument_parser,argv,clock
        self.description='Capture an action-bound personal statement into pilot validation; never post or execute it.'

    def collect_action(self, request, repo=_OMITTED, *, fetch=None, captured_at=None):
        if repo is _OMITTED:
            repo = self.root
        (profile, binding, receipts, actions) = self.context.actions.load_context(repo)
        self.context.contracts.schema_validator('pilot-action-request').validate(request)
        options = {'fetch': fetch} if fetch is not None else {}
        snapshot = self.context.provider.collect_bound(request, assessor=self.context.actions.assess_action_comments, previous_comments=self.context.actions.prior_statements(actions, request), captured_at=captured_at, **options)
        self.context.actions.prepare_action(snapshot, profile, binding, receipts, actions, recorded_at=snapshot['result']['captured_at'], expected_sequence=len(actions))
        return snapshot

    def append_action_snapshot(self, repo, snapshot, *, recorded_at, expected_sequence):
        root = self.Path(repo)
        with self.context.store.writer_lock(root / self.context.admission.VALIDATION_LEDGER), self.context.store.writer_lock(root / self.context.actions.ACTION_LEDGER):
            (profile, binding, receipts, actions) = self.context.actions.load_context(root)
            action = self.context.actions.prepare_action(snapshot, profile, binding, receipts, actions, recorded_at=recorded_at, expected_sequence=expected_sequence)
            if action is None:
                return {'outcome': 'duplicate', 'transaction_ref': None}
            self.context.store.publish_transaction(root / self.context.actions.ACTION_LEDGER / 'transactions', action)
            return {'outcome': action['outcome'], 'transaction_ref': self.context.kernel.transaction_ref(action)}

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--request', type=self.Path, required=True)
        parser.add_argument('--expected-sequence', type=int, required=True)
        args = parser.parse_args(self.argv)
        request = self.context.adapter.strict_json(args.request.read_bytes())
        snapshot = self.collect_action(request)
        self.context.contracts.require(snapshot['capture_method'] == 'github_api_get_via_gh', 'Fresh GitHub capture required')
        at = self.clock()
        print(self.append_action_snapshot(self.root, snapshot, recorded_at=at, expected_sequence=args.expected_sequence))
