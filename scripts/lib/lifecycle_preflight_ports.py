"""Explicit diagnostic GET, larger binary budget, path/output and clock composition."""
from lib.providers.lifecycle_preflight_io import NativePreflightIO as NativeIO
from lib.lifecycle_preflight_io import ReplayPreflightIO as ReplayIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.providers.lifecycle_preflight import LegacyLifecyclePreflight
from lib.providers.lifecycle_preflight_protocol import NativePreflightTransport,ReplayPreflightTransport
from lib.personal_channel_ports import exclusive_factory
from lib.lifecycle_preflight_context import execute as execute_kernel
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.portable.contracts import ROOT
from lib.v2_source import selected_paths
from lib.providers.retained_argparse import capture_context as capture_parser_context

TRANSPORT_PROFILES=('legacy-preflight-github-get-v1',)
DEFAULT_PROVIDER_EXECUTABLE='gh'
COMPONENTS=('lifecycle_preflight_program.py','lifecycle_preflight_context.py','lifecycle_preflight_io.py',
 'lifecycle_preflight_ports.py','lifecycle_preflight_application.py','providers/lifecycle_preflight.py',
 'providers/lifecycle_preflight_protocol.py','providers/lifecycle_preflight_io.py')
def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):
        raise ValueError('lifecycle_preflight_closure_not_registered')
    return lifecycle_source(node,product_tree)
def execute(request,owner,*,validator_class):
    if request['transport_profile'] not in TRANSPORT_PROFILES:
        raise ValueError('lifecycle_preflight_transport_profile_not_supported')
    native=hasattr(owner,'record')
    def transport(io,root,emit):
        if native:return NativePreflightTransport(io,root,emit_stderr=emit,provider_executable=request['provider_executable'])
        return ReplayPreflightTransport(io,root,emit_stderr=emit)
    return execute_kernel(request['source_label'],request['cwd_label'],request['argv'],owner,
        validator_class=validator_class,provider_factory=lambda context,port:LegacyLifecyclePreflight(context,transport=port,clock=port.clock),
        transport_factory=transport,exclusive_factory=exclusive_factory,parser_context=request['parser_context'])
