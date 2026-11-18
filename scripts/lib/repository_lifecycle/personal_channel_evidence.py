"""Retained V1 historical consistency over explicit data and capture adapters.

Historical outputs describe their original scope; they confer no operating
acceptance, personal consent or authority on the executing V2 node.
"""
_OMITTED = object()
CAPTURES = 'generated/reports/lifecycle-personal-channel'
REPORT = 'generated/reports/lifecycle-personal-channel-evidence.md'

class LifecycleStatementEvidenceReport:

    def __init__(self, root, context, *, path_factory):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.CAPTURES = CAPTURES
        self.REPORT = REPORT

    def prior_comments(self, snapshots):
        comments = {}
        for snapshot in snapshots:
            for comment in snapshot['result']['relevant_comments']:
                comments.setdefault(comment['id'], comment)
        return list(comments.values())

    def load_captures(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.path_factory(repo)
        directory = root / CAPTURES
        self.context.contracts.require(directory.is_dir() and (not directory.is_symlink()), 'Channel capture directory required')
        request = self.context.adapter.strict_json((root / self.context.personal_channel_probe.REQUEST).read_bytes())
        self.context.personal.validate_request(request, root, require_current_head=False)
        captures = []
        for number, path in enumerate(sorted(directory.iterdir()), 1):
            self.context.contracts.require(path.is_file() and (not path.is_symlink()) and (path.name == f'{number:08d}.json'), 'Unexpected channel capture path or sequence')
            snapshot = self.context.adapter.strict_json(path.read_bytes())
            self.context.contracts.require(snapshot['request'] == request, 'Archived channel request differs')
            self.context.contracts.require(snapshot['capture_method'] == self.context.provider.capture_method, 'A provider capture is required')
            self.context.contracts.require(snapshot['previous_comments'] == self.prior_comments(captures), 'Channel capture omits or changes prior statement history')
            result = self.context.personal.replay_probe_snapshot(snapshot)
            if captures:
                self.context.contracts.require(self.context.contracts.timestamp(result['captured_at']) >= self.context.contracts.timestamp(captures[-1]['result']['captured_at']), 'Channel capture time regressed')
            captures.append(snapshot)
        self.context.contracts.require(bool(captures), 'Channel capture history is empty')
        return captures

    def render(self, captures):
        result = captures[-1]['result']
        lines = ['# Personal GitHub Channel Evidence', '', 'Context: diagnostic personal-channel probe. No remediation, closure, role change or live activation authorized.', '', f"Latest retained status: **{result['status']}** as of `{result['captured_at']}`.", f"Request digest: `{result['request_digest']}`.", 'Human presence: explicit personal self-attestation; GitHub authenticates the account.', '', '| Capture | Captured at | Status | Snapshot digest |', '|---|---|---|---|']
        for i, snapshot in enumerate(captures, 1):
            item = snapshot['result']
            lines.append(f"| {i:08d} | {item['captured_at']} | {item['status']} | `{self.context.contracts.canonical_digest(snapshot)}` |")
        lines += ['', '## Retained personal statements', '']
        for comment in self.prior_comments(captures):
            lines.append(f"- [Comment {comment['id']}]({comment['html_url']}), GitHub user ID `{comment['user']['id']}`, issued `{comment['created_at']}`.")
        lines += ['', 'Original provider response bytes, including CRLF line endings, are retained in each capture.', 'Offline replay verifies consistency. Required PR CI independently rechecks newly published captures against GitHub.', 'This report describes the last retained observation; recheck the provider before relying on a current statement.', '']
        return '\n'.join(lines)

    def validate(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        captures = self.load_captures(repo)
        self.context.contracts.require((self.path_factory(repo) / REPORT).read_text() == self.render(captures), 'Personal channel evidence report differs')
        return captures
