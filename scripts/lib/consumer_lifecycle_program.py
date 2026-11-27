"""Complete original consumer lifecycle functions over explicit data/effect ports.

Retained source history is not this node's operating authority.
"""
from __future__ import annotations
from copy import deepcopy
from referencing import Registry, Resource
import base64, hashlib
_OMITTED = object()
_DEFAULT_FETCH = object()

class ConsumerLifecycleProgram:

    def __init__(self, root, context, *, path_factory, profile, process=None, temporary=None, clock=None, validator_class=None, default_fetch=None, architecture=None, argument_parser=None, argv=(), description=None):
        self.root, self.context, self.Path, self.profile = (root, context, path_factory, profile)
        self.process, self.temporary, self.clock = (process, temporary, clock)
        self.validator_class, self.default_fetch, self.architecture = (validator_class, default_fetch, architecture)
        self.argument_parser, self.argv, self.description = (argument_parser, list(argv), description)
        self.positive_id = profile.positive_id

    def prepare_acceptance(self, discussion_number, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.Path(repo)
        profile, binding = self.context.consumer_contracts.load_model(root)
        value = {'schema_version': '0.1.0', 'repository_id': self.profile.literal('legacy_78f9096520382e56'), 'scope': profile['scope'], 'operating_profile_ref': self.context.preparation.revision_ref(profile), 'role_binding_ref': self.context.preparation.revision_ref(binding), 'created_at': self.clock(), 'discussion_number': discussion_number, 'required_subject_id': binding['assignments']['role_registry_owner'], 'required_role': 'role_registry_owner', 'request_type': 'consumer-lifecycle-operating-acceptance', 'purpose': 'accept_manual_demo_operation_readiness_pilot_with_individual_personal_action_consent', 'permitted_operations': ['manual_observation_intake', 'personal_action_intake', 'pilot_state_publication_via_pr'], 'excluded_operations': ['automatic_remediation', 'blocking_enforcement', 'direct_main_writes', 'waiver_authority', 'baseline_changes', 'other_consumers', 'bitbucket_operation'], 'promotion_scope': 'new_verified_demo_operation_readiness_receipts_and_personal_actions_only', 'implementation_manifest': self.context.consumer_acceptance.manifest(root), 'channel_probe_comment': self.profile.literal('legacy_adf37aa1af6a2392')}
        path = root / self.context.consumer_acceptance.REQUEST_PATH
        self.context.contracts.require(not path.exists(), 'Existing acceptance request cannot be overwritten')
        path.write_bytes(self.context.adapter.json_bytes(value))
        self.context.consumer_acceptance.generate(root)
        return value

    def run(self, operation, *, run_id=None, request_path=None, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.Path(repo)
        if operation == 'acceptance':
            self.context.consumer_acceptance.capture(root)
        else:
            self.context.consumer_acceptance.verify_provider(root)
            if operation == 'observe':
                self.context.contracts.require(run_id is not None and run_id.isdigit() and (int(run_id) > 0), 'Positive source run ID required')
                with self.temporary.TemporaryDirectory() as temporary:
                    directory = self.Path(temporary) / 'capture'
                    self.context.consumer_evidence.collect_preflight(run_id, directory, repo_root=root)
                    at = self.clock()
                    self.context.consumer_admission.append_capture(root / self.context.consumer_admission.VALIDATION_LEDGER, directory, self.context.consumer_contracts.load_model(root)[0], recorded_at=at, expected_sequence=len(self.context.store.load_transactions(root / self.context.consumer_admission.VALIDATION_LEDGER)))
            elif operation == 'action':
                self.context.contracts.require(bool(request_path), 'Committed consumer action request required')
                path = (root / request_path).resolve()
                self.context.contracts.require(path.is_relative_to((root / self.context.consumer_contracts.MODEL / 'action-requests').resolve()) and path.is_file(), 'Request outside consumer action directory')
                self.process.run(['git', 'ls-files', '--error-unmatch', '--', str(path.relative_to(root.resolve()))], cwd=root, check=True, capture_output=True)
                snapshot = self.context.consumer_actions.collect_action(self.context.adapter.strict_json(path.read_bytes()), repo=root)
                self.context.contracts.require(snapshot['capture_method'] == self.profile.capture_method, 'Actual provider capture required')
                at = self.clock()
                self.context.consumer_actions.append_action_snapshot(root, snapshot, recorded_at=at, expected_sequence=len(self.context.store.load_transactions(root / self.context.consumer_actions.ACTION_LEDGER)))
            elif operation != 'refresh':
                raise ValueError('Unknown consumer operation')
        self.context.consumer_acceptance.generate(root)

    def main(self):
        parser = self.argument_parser(description=self.description)
        parser.add_argument('--operation', choices=('acceptance', 'observe', 'action', 'refresh', 'validate', 'prepare-acceptance', 'preflight'), required=True)
        parser.add_argument('--source-run-id')
        parser.add_argument('--request-path')
        parser.add_argument('--base-ref')
        parser.add_argument('--verify-provider', action='store_true')
        parser.add_argument('--discussion-number', type=int)
        parser.add_argument('--output', type=self.Path)
        args = parser.parse_args(self.argv)
        if args.operation == 'prepare-acceptance':
            self.context.contracts.require(type(args.discussion_number) is int and args.discussion_number > 0, 'Positive discussion number required')
            self.prepare_acceptance(args.discussion_number)
        elif args.operation == 'preflight':
            self.context.contracts.require(args.output is not None and args.source_run_id is not None, 'Preflight requires run and output')
            print(self.context.consumer_evidence.collect_preflight(args.source_run_id, args.output)['criterion'])
        elif args.operation == 'validate':
            if args.base_ref:
                self.context.consumer_acceptance.check_prefix(self.root, args.base_ref)
            if args.verify_provider:
                self.context.contracts.require(bool(args.base_ref), 'Independent publication verification requires immutable base')
                self.context.consumer_acceptance.validate_publication(self.root, args.base_ref)
            else:
                self.context.consumer_acceptance.validate(self.root)
            print('Consumer lifecycle validated')
        else:
            self.run(args.operation, run_id=args.source_run_id, request_path=args.request_path)
