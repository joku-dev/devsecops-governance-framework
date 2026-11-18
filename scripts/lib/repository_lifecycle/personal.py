"""Retained V1 historical consistency over explicit data and capture adapters.

Historical outputs describe their original scope; they confer no operating
acceptance, personal consent or authority on the executing V2 node.
"""
import json
_OMITTED = object()
MARKER = 'CLG-PERSONAL-CONSENT/1\n'
STATEMENT = 'Ich habe diese Anfrage persönlich geprüft und gebe diese Erklärung selbst ab; keine Automation handelt dabei für mich.'

class LifecyclePersonalStatements:

    def __init__(self, root, context, *, path_factory):
        self.root = root
        self.context = context
        self.path_factory = path_factory
        self.MARKER = MARKER
        self.STATEMENT = STATEMENT

    def statement_body(self, request, *, disposition='approve', supersedes_comment_id=None):
        self.context.contracts.require(disposition in ('approve', 'reject', 'revoke'), 'Unknown personal disposition')
        return MARKER + json.dumps({'request_digest': self.context.contracts.canonical_digest(request), 'disposition': disposition, 'supersedes_comment_id': supersedes_comment_id, 'statement': STATEMENT}, ensure_ascii=False, indent=2, sort_keys=True) + '\n'

    def validate_request(self, request, repo, *, require_current_head=True):
        self.context.contracts.schema_validator('personal-channel-probe').validate(request)
        profile = self.context.admission.load_operating(repo)
        prepared = self.context.preparation.validate_preparation(repo)
        self.context.contracts.require(request['operating_profile_ref'] == self.context.preparation.revision_ref(profile), 'Probe operating profile differs')
        self.context.contracts.require(request['role_binding_ref'] == self.context.preparation.revision_ref(prepared['binding']), 'Probe role binding differs')
        self.context.contracts.require(prepared['assignments'][request['required_role']] == request['required_subject_id'], 'Probe appointed subject differs')
        history = self.context.admission.replay_receipts(self.context.store.load_transactions(self.path_factory(repo) / self.context.admission.VALIDATION_LEDGER), profile)
        self.context.contracts.require(any((request['receipt_head_ref'] == self.context.kernel.transaction_ref(t) for t in history)), 'Probe receipt reference is missing')
        if require_current_head:
            self.context.contracts.require(request['receipt_head_ref'] == self.context.kernel.transaction_ref(history[-1]), 'Probe receipt head is no longer current')
        return prepared

    def assess_comments(self, request, comments, *, captured_at, previous_comments=()):
        self.context.contracts.schema_validator('personal-channel-probe').validate(request)
        return self.context.provider.assess_bound_comments(request, comments, captured_at=captured_at, previous_comments=previous_comments)

    def replay_probe_snapshot(self, snapshot):
        return self.context.provider.replay_bound_snapshot(snapshot, assessor=self.assess_comments)
