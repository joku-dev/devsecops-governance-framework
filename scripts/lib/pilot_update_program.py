"""Whole original pilot update run and executable parser over explicit ports."""
class PilotUpdateProgram:
    def __init__(self,root,context,*,path_factory,operating,receipts,actions,fresh,temporary,git,clock,receipt_reports,action_reports,capture_method,argument_parser,argv,description):
        self.root,self.context,self.Path=root,context,path_factory
        self.operating,self.receipts,self.actions,self.fresh=operating,receipts,actions,fresh
        self.temporary,self.git,self.clock=temporary,git,clock
        self.receipt_reports,self.action_reports=receipt_reports,action_reports
        self.capture_method,self.argument_parser,self.argv,self.description=capture_method,argument_parser,argv,description

    def run(self, operation, *, run_id=None, request_path=None):
        if operation == 'acceptance':
            self.operating.capture()
        else:
            self.operating.verify_provider()
            if operation == 'observe':
                self.context.contracts.require(run_id is not None and run_id.isdigit() and (int(run_id) > 0), 'A positive source run ID is required')
                with self.temporary.TemporaryDirectory() as temporary:
                    directory = self.Path(temporary) / 'capture'
                    self.fresh.collect_preflight(run_id, directory)
                    at = self.clock()
                    self.receipts.append_capture(self.root / self.context.admission.VALIDATION_LEDGER, directory, self.context.admission.load_operating(), recorded_at=at, expected_sequence=len(self.context.store.load_transactions(self.root / self.context.admission.VALIDATION_LEDGER)))
            elif operation == 'action':
                self.context.contracts.require(bool(request_path), 'A committed action request path is required')
                path = (self.root / request_path).resolve()
                self.context.contracts.require(path.is_relative_to(self.root / 'model/governance/lifecycle/action-requests') and path.is_file(), 'Request must be in the dedicated action-request directory')
                self.git.run(['git', 'ls-files', '--error-unmatch', '--', str(path.relative_to(self.root))], cwd=self.root, check=True, capture_output=True)
                snapshot = self.actions.collect_action(self.context.adapter.strict_json(path.read_bytes()))
                self.context.contracts.require(snapshot['capture_method'] == self.capture_method, 'Actual provider capture is required')
                at = self.clock()
                self.actions.append_action_snapshot(self.root, snapshot, recorded_at=at, expected_sequence=len(self.context.store.load_transactions(self.root / self.context.actions.ACTION_LEDGER)))
            elif operation != 'refresh':
                raise ValueError('Unknown pilot operation')
        generate_receipts = self.receipt_reports.main
        generate_receipts()
        project_actions, INDEX, REPORT, render = (self.context.actions.project_actions, self.action_reports.INDEX, self.action_reports.REPORT, self.action_reports.render)
        json_bytes = self.context.adapter.json_bytes
        index = project_actions()
        (self.root / INDEX).write_bytes(json_bytes(index))
        (self.root / REPORT).write_text(render(index))
        self.operating.generate()

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--operation', choices=('acceptance', 'observe', 'action', 'refresh'), required=True)
        parser.add_argument('--source-run-id')
        parser.add_argument('--request-path')
        args = parser.parse_args(self.argv)
        self.run(args.operation, run_id=args.source_run_id, request_path=args.request_path)
