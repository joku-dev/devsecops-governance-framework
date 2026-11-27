"""Explicit fresh GET/clock, temporary-scope and single receipt-ledger composition."""
import posixpath,tempfile
from pathlib import Path,PurePosixPath
from lib.providers.pilot_run_intake_io import NativeRunIO as NativeIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.providers.lifecycle_preflight import LegacyLifecyclePreflight
from lib.providers.lifecycle_preflight_protocol import NativePreflightTransport,ReplayPreflightTransport
from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
from lib.synthetic_ledger_replay_effects import ReplayLedgerEffects
from lib.synthetic_ledger_private import PrivateLedgerPort
from lib.providers.pilot_run_temporary import NativeTemporaryFactory
from lib.pilot_run_temporary import ReplayTemporaryFactory
from lib.pilot_run_private_temporary import PrivateTemporaryFactory
from lib.personal_channel_ports import exclusive_factory
from lib.pilot_run_intake_context import execute as execute_kernel
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.portable.contracts import ROOT
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.v2_source import selected_paths
from lib.providers.retained_argparse import capture_context as capture_parser_context

TRANSPORT_PROFILES=('legacy-preflight-github-get-v1',)
DEFAULT_PROVIDER_EXECUTABLE='gh'
LEDGER='governance/lifecycle/live-validation'
COMPONENTS=('pilot_run_intake.py','pilot_run_intake_context.py','pilot_run_intake_io.py',
 'pilot_run_temporary.py','pilot_run_private_temporary.py','synthetic_ledger_budget.py',
 'providers/pilot_run_intake_io.py','providers/pilot_run_temporary.py',
 'pilot_run_intake_ports.py','pilot_run_intake_application.py')

def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):
        raise ValueError('pilot_run_intake_closure_not_registered')
    return lifecycle_source(node,product_tree)

def transaction_name(raw):
    context=RepositoryLifecycle(ROOT,validator_class=None)
    return context.kernel.transaction_name(context.adapter.strict_json(raw))

def ledger(source):return str(PurePosixPath(source)/LEDGER)

def replay_owner(request,events,blob):
    return ReplayRunIO(events,blob,request['export_mode'],request['cwd_label'],ledger=ledger(request['source_label']),transaction_name=transaction_name)

def temporary_parent(mode,selected=None):
    # The private model needs an owned ordinary anchor, without making native
    # candidate directories. Its default home anchor is an observed environment
    # input, not a claim about the system temp directory. Native mode retains
    # the actual canonical system temp parent. Pure replay uses the saved field.
    if selected is None:
        return str((Path.home() if mode=='private-candidate' else Path(tempfile.gettempdir())).resolve())
    return posixpath.normpath(str(Path(selected).expanduser().absolute()))

def execute(request,owner,*,validator_class):
    if request['transport_profile'] not in TRANSPORT_PROFILES:raise ValueError('pilot_run_intake_transport_profile_not_supported')
    native=hasattr(owner,'record');selected=request['export_mode']=='selected-files';ports={}
    def fresh(context,emit):
        port=NativePreflightTransport(owner,context.root,emit_stderr=emit,provider_executable=request['provider_executable']) if native else ReplayPreflightTransport(owner,context.root,emit_stderr=emit)
        ports['transport']=port
        return LegacyLifecyclePreflight(context,transport=port,clock=port.clock)
    def effects(io):
        if not selected:return PrivateLedgerPort(io,ledger(request['source_label']))
        return (NativeLedgerEffects if native else ReplayLedgerEffects)(io,ledger(request['source_label']),transaction_name=transaction_name)
    def temporary(io):
        kind=PrivateTemporaryFactory if not selected else NativeTemporaryFactory if native else ReplayTemporaryFactory
        return kind(io,request['temporary_parent'])
    return execute_kernel(request['source_label'],request['cwd_label'],request['argv'],owner,
        validator_class=validator_class,historical_provider_factory=lambda context:LegacyRepositoryLifecycleCapture(context),
        fresh_provider_factory=fresh,effects_factory=effects,exclusive_factory=exclusive_factory,
        temporary_factory=temporary,clock_factory=lambda io:ports['transport'].clock,parser_context=request['parser_context'])
