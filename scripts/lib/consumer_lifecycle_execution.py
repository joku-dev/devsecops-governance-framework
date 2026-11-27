"""Whole consumer runner over one ordered file/provider/policy/store cursor."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import io
from lib.lifecycle_preflight_context import PreflightPaths
from lib.personal_channel_context import OrderedStderr
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.synthetic_ledger_store import SyntheticLedgerStore
from lib.consumer_lifecycle_contracts import ConsumerContracts
from lib.consumer_lifecycle_admission import ConsumerAdmission
from lib.consumer_lifecycle_actions import ConsumerActions
from lib.consumer_lifecycle_acceptance import ConsumerAcceptance
from lib.consumer_lifecycle_program import ConsumerLifecycleProgram
from lib.lifecycle_candidate_preparation import CandidateNormalization, ArchitectureCandidateAdapter
from lib.retained_argparse import parser_base, formatter_factory
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError


def execute(source, cwd, argv, owner, *, validator_class, parser_context, description,
            ports_factory, profile_factory, provider_factory, evidence_factory,
            effects_factory, exclusive_factory, temporary_factory, invocation=None):
    if parser_context is None:
        raise InputAdmissionError('consumer_original_parser_context_required')
    paths = PreflightPaths(source, cwd, owner, exclusive_factory); root = paths.path(source)
    out, err = io.StringIO(), OrderedStderr()
    context = RepositoryLifecycle(root, validator_class=validator_class, path_factory=paths.path)
    ports = ports_factory(owner, root, context, err.emit_raw)
    central, evidence, process = ports['central'], ports['evidence'], ports['process']
    temporary = temporary_factory(owner)
    profile = profile_factory(context, central)
    context.provider = provider_factory(context, central)
    options = {'path_factory': paths.path, 'profile': profile, 'process': process,
               'temporary': temporary, 'clock': central.clock, 'validator_class': validator_class}
    context.consumer_contracts = ConsumerContracts(root, context, **options)
    context.consumer_admission = ConsumerAdmission(root, context, **options)
    context.consumer_actions = ConsumerActions(root, context, **options)
    context.consumer_acceptance = ConsumerAcceptance(root, context, **options)
    architecture = ArchitectureCandidateAdapter(context, CandidateNormalization(context))
    context.consumer_evidence = evidence_factory(root, context, profile, architecture, evidence, process, temporary, central.clock, validator_class, paths.path)
    effects = effects_factory(owner, source=source, transaction_name=lambda raw: context.kernel.transaction_name(context.adapter.strict_json(raw)))
    context.store = SyntheticLedgerStore(context, path_factory=paths.path, native=effects, locking=effects, temporary=effects)
    def parser(**kw):
        return parser_base(parser_context)(prog='run_consumer_lifecycle.py', formatter_class=formatter_factory(parser_context), **kw)
    program = ConsumerLifecycleProgram(root, context, **options, argument_parser=parser, argv=argv, description=description)
    code = 0; error = signal = returned = None
    try:
        with redirect_stdout(out), redirect_stderr(err):
            try:
                if invocation is None:
                    returned = program.main()
                elif invocation['method'] in ('run', 'prepare_acceptance'):
                    returned = getattr(program, invocation['method'])(**invocation['arguments'])
                elif invocation['method'] in ('projection', 'validate', 'generate'):
                    returned = getattr(context.consumer_acceptance, invocation['method'])(**invocation['arguments'])
                else:
                    raise InputAdmissionError('consumer_original_API_not_supported')
            except (InputAdmissionError, IntegrityError):
                raise
            except RetainedOutputError as caught:
                code, error = 1, {'type': caught.original_type, 'message': caught.original_message}
            except SystemExit as caught:
                code = 0 if caught.code is None else caught.code if type(caught.code) is int else 1
                if caught.code is not None and type(caught.code) is not int:
                    print(caught.code, file=err)
                signal = {'type': 'SystemExit', 'value': caught.code}
            except Exception as caught:
                code, error = 1, {'type': type(caught).__name__, 'message': str(caught)}
    finally:
        descriptors = deepcopy(effects.descriptors)
        observations = deepcopy({name: part.state.observed for name, part in effects.parts.items()}) if owner.mode == 'selected-files' else {}
        owner.adapter_cleanup = []
        if hasattr(effects, 'release_resources'):
            for cleanup in effects.release_resources():
                owner.adapter_cleanup.append(cleanup)
                if cleanup['observed_descriptors'] or cleanup['remaining_descriptors'] or cleanup['errors']:
                    raise IntegrityError('consumer_unclosed_ledger_resources')
        for session in getattr(owner, 'personal_exclusive_sessions', []):
            session.release()
        for session in getattr(owner, 'pilot_temporary_sessions', []):
            owner.adapter_cleanup.append(session.release())
        if hasattr(process, 'finish'):
            process.finish()
    if len(out.getvalue()) > 131072 or len(err.getvalue()) > 131072 or error and len(error['message']) > 65536:
        raise InputAdmissionError('consumer_original_text_capture_budget')
    return {'exit_code': code, 'kernel_exception': error, 'original_exit_signal': signal,
            'return_value': returned, 'stdout': out.getvalue(), 'stderr': err.getvalue(), 'stderr_parts': err.parts,
            'native_ledger_observations': observations, 'kernel_end_ledger_descriptors': descriptors}
