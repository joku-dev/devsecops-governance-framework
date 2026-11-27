"""Whole original independent receipt verification over explicit fresh/Git/temp/clock ports."""
class PilotReceiptVerification:
    def __init__(self,context,fresh,*,path_factory,temporary,clock,git):
        self.context,self.fresh=context,fresh
        self.Path,self.temporary,self.clock,self.git=path_factory,temporary,clock,git

    def verify_new_receipts(self, repo, base_ref):
        """Required PR check: obtain fresh provider bytes instead of trusting persisted claims."""
        root = self.Path(repo)
        profile = self.context.admission.load_operating(root)
        old = set(self.git.check_output(['git', 'ls-tree', '-r', '--name-only', base_ref, '--', self.context.admission.VALIDATION_LEDGER], cwd=root, text=True).splitlines())
        checked = 0
        for path in sorted((root / self.context.admission.VALIDATION_LEDGER / 'transactions').glob('*.json')):
            if str(path.relative_to(root)) in old:
                continue
            receipt = self.context.adapter.strict_json(path.read_bytes())
            with self.temporary.TemporaryDirectory() as temporary:
                observed = self.fresh.collect_preflight(str(receipt['source']['run_id']), self.Path(temporary) / 'capture', repo_root=root)
            now = self.clock()
            self.context.contracts.require(self.context.admission.origin_key(observed) == receipt['origin_key'] and self.context.admission.producer_fingerprint(observed) == receipt['producer_fingerprint'], 'New receipt differs from independently retrieved GitHub evidence')
            age = (self.context.contracts.timestamp(now) - self.context.contracts.timestamp(observed['source']['observed_at'])).total_seconds()
            self.context.contracts.require(0 <= age <= profile['operating_policy']['maximum_age_seconds'], 'New receipt is stale at PR acceptance')
            self.context.contracts.require(self.context.contracts.timestamp(receipt['recorded_at']) <= self.context.contracts.timestamp(now), 'Receipt claims a future acceptance time')
            checked += 1
        return checked
