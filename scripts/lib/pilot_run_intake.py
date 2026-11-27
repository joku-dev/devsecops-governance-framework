"""Entire original fresh pilot-run intake and complete saved-capture append APIs."""
import base64
class PilotRunIntake:
    def __init__(self,root,context,fresh,*,path_factory,temporary,argument_parser,argv,clock):
        self.root,self.context,self.fresh=root,context,fresh
        self.Path,self.temporary,self.argument_parser=path_factory,temporary,argument_parser
        self.argv,self.clock=argv,clock
        self.description='Collect fresh provider evidence into durable pilot validation; no live activation.'

    def capture_files(self, directory):
        result = self.context.provider.replay_capture(directory)
        root = self.Path(directory)
        files = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        self.context.contracts.require(sum(map(len, files.values())) <= self.context.admission.MAX_CAPTURE_BYTES, 'Capture exceeds supported size')
        return (result, files)

    def append_capture(self, root, directory, profile, *, recorded_at, expected_sequence):
        capture, files = self.capture_files(directory)
        encoded = {p: base64.b64encode(b).decode('ascii') for p, b in sorted(files.items())}
        with self.context.store.writer_lock(root):
            history = self.context.admission.replay_receipts(self.context.store.load_transactions(root), profile)
            receipt = self.context.admission.prepare_receipt(capture, encoded, profile, history, recorded_at=recorded_at, expected_sequence=expected_sequence)
            if receipt is None:
                return {'outcome': 'duplicate', 'transaction_ref': None}
            self.context.store.publish_transaction(self.Path(root) / 'transactions', receipt)
            return {'outcome': receipt['outcome'], 'transaction_ref': self.context.kernel.transaction_ref(receipt)}

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--run-id', required=True)
        parser.add_argument('--expected-sequence', type=int, required=True)
        args = parser.parse_args(self.argv)
        profile = self.context.admission.load_operating()
        with self.temporary.TemporaryDirectory() as temporary:
            capture = self.Path(temporary) / 'capture'
            self.fresh.collect_preflight(args.run_id, capture)
            at = self.clock()
            result = self.append_capture(self.root / self.context.admission.VALIDATION_LEDGER, capture, profile, recorded_at=at, expected_sequence=args.expected_sequence)
        print(result)
