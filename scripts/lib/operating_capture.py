"""Complete original operating capture and report generation; no node authority transfer."""
_OMITTED=object()
class OperatingCapture:
    def __init__(self,root,context,*,path_factory,collector):self.root,self.context,self.Path,self.collector=root,context,path_factory,collector;self.verify_provider=collector.verify_provider

    def capture(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.Path(repo)
        history = self.context.operating.captures(root)
        snapshot = self.collector.collect(root)
        self.context.contracts.require(snapshot['result']['status'] != 'waiting_for_personal_statement', 'Personal LD-07 statement is still missing')
        destination = root / self.context.operating.CAPTURES / f'{len(history) + 1:08d}.json'
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(self.context.adapter.json_bytes(snapshot))
        return snapshot

    def generate(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.Path(repo)
        index = self.context.operating.projection(root)
        (root / self.context.operating.INDEX).write_bytes(self.context.adapter.json_bytes(index))
        (root / self.context.operating.REPORT).write_text(self.context.operating.render(index))
        statement_body = self.context.personal.statement_body
        (root / self.context.operating.STATEMENT_PATH).write_text(self.context.operating.statement_template(self.context.operating.request(root), self.context.personal.statement_body))
