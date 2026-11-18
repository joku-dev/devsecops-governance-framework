"""Retained V1 historical consistency over explicit data and capture adapters.

Historical outputs describe their original scope; they confer no operating
acceptance, personal consent or authority on the executing V2 node.
"""
_OMITTED = object()
REQUEST = 'model/governance/lifecycle/personal-channel/00000001.json'
TEMPLATE = 'generated/reports/lifecycle-personal-channel-statement.md'

class LifecycleStatementReport:

    def __init__(self, root, context, *, path_factory):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.REQUEST = REQUEST
        self.TEMPLATE = TEMPLATE

    def render(self, request):
        return '# Persönlicher GitHub-Kanaltest\n\nDiskussion: ' + self.context.provider.discussion_url(request['repository_id'], request['discussion_number']) + '\n\nBitte als `joku-dev` selbst einen neuen Kommentar mit dem folgenden vollständigen Inhalt posten. Die Erklärung prüft ausschließlich den persönlichen Freigabekanal. Sie gibt keine Behebung, keinen Abschluss und keine Live-Aktivierung frei.\n\n```text\n' + self.context.personal.statement_body(request) + '```\n\nNicht durch Codex oder eine andere Automation posten lassen. Einen abgegebenen Kommentar nicht bearbeiten oder löschen; Ablehnung und Widerruf werden als neue, referenzierende Kommentare erfasst.\n'

    def validate(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        request = self.context.adapter.strict_json((repo / REQUEST).read_bytes())
        self.context.personal.validate_request(request, repo, require_current_head=False)
        self.context.contracts.require((repo / TEMPLATE).read_text() == self.render(request), 'Personal statement template differs')
        return request
