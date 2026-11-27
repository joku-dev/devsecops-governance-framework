"""Complete original lifecycle validator orchestration over explicit model and observation ports."""

class LifecycleLedgerValidator:

    def __init__(self, context, *, argument_parser, argv, description, messages, prefix, receipts, personal, actions, operating):
        self.context = context
        self.root = context.root
        self.default_ledger = self.root / context.ledger.LEDGER_PATH
        self.argument_parser, self.argv, self.description, self.messages = (argument_parser, list(argv), description, messages)
        self.prefix, self.receipts, self.personal, self.actions, self.operating = (prefix, receipts, personal, actions, operating)

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--base-ref')
        parser.add_argument('--verify-new-provider', action='store_true')
        args = parser.parse_args(self.argv)
        if args.base_ref:
            count = self.prefix.check_accepted_prefix(self.root, args.base_ref)
            print(f'Preserved {count} accepted lifecycle blobs from {args.base_ref}.')
        self.context.contracts.require(all((tx['schema_version'] != '0.4.0' for tx in self.context.store.load_transactions(self.default_ledger))), 'Exceptions require their separate scenario')
        self.context.preparation.validate_preparation()
        validate_live_pilot = self.context.lifecycle_pilot_validation.validate
        validate_live_pilot()
        validate_personal_probe = self.context.personal_channel_probe.validate
        validate_personal_probe()
        validate_channel_evidence = self.context.personal_channel_evidence.validate
        verify_new_captures = self.personal.verify_new_captures
        validate_channel_evidence()
        validate_pilot_actions = self.context.lifecycle_pilot_actions.validate
        validate_pilot_actions()
        validate_operating = self.context.operating.validate
        verify_operating = self.operating.verify_new_captures
        validate_operating()
        if args.verify_new_provider:
            self.context.contracts.require(bool(args.base_ref), 'Provider verification requires an accepted base')
            print(self.messages.receipts(self.receipts.verify_new_receipts(self.root, args.base_ref)))
            print(self.messages.captures(verify_new_captures(self.root, args.base_ref)))
            print(self.messages.actions(self.actions.verify_new_actions(self.root, args.base_ref)))
            print(self.messages.operating(verify_operating(self.root, args.base_ref)))
        index = self.context.ledger.validate_current()
        pilot = self.context.ledger.validate_pilot()
        exceptions = self.context.ledger.validate_exceptions()
        validate_overview = self.context.governance_lifecycle_overview.validate_overview
        overview = validate_overview()
        validate_viewer = self.context.governance_lifecycle_viewer.validate_viewer
        validate_viewer(overview=overview)
        print(f"Lifecycle: exceptions {exceptions['counts']}; original scenario {index['counts']}; synthetic closure pilot {pilot['counts']}; no live activation.")
