"""Explicit personal-channel GET/Git/clock/output composition; no posting port."""
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.providers.personal_channel_protocol import LegacyPersonalProtocol
from lib.providers.personal_channel_exclusive import NativeExclusive
from lib.personal_channel_process import ReplayPersonalTransport
from lib.personal_channel_exclusive import ReplayExclusive
from lib.personal_channel_private import PrivateExclusive
from lib.personal_channel_context import execute as execute_kernel
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.portable.contracts import ROOT
from lib.v2_source import selected_paths
from lib.providers.retained_argparse import capture_context as capture_parser_context

TRANSPORT_PROFILES=('legacy-personal-github-get-v1',)
DEFAULT_PROVIDER_EXECUTABLE='gh'
COMPONENTS=('personal_channel_programs.py','personal_channel_collection.py','personal_channel_context.py',
    'personal_channel_exclusive.py','personal_channel_private.py','personal_channel_process.py',
    'personal_channel_ports.py','personal_channel_application.py','providers/personal_channel_capture.py',
    'providers/personal_channel_exclusive.py','providers/personal_channel_process.py',
    'providers/personal_channel_protocol.py','providers/personal_channel_transport.py')

def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):
        raise ValueError('personal_channel_closure_not_registered')
    return lifecycle_source(node,product_tree)

def exclusive_factory(owner,path,label):
    cls=PrivateExclusive if owner.mode=='private-candidate' else NativeExclusive if hasattr(owner,'record') else ReplayExclusive
    return cls(owner,path,label)

def execute(request,owner,*,validator_class):
    if request['transport_profile'] not in TRANSPORT_PROFILES:raise ValueError('personal_channel_transport_profile_not_supported')
    def transport(io,root,emit):
        if hasattr(io,'record'):
            return NativePersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit,provider_executable=request['provider_executable'])
        return ReplayPersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit)
    return execute_kernel(request['source_label'],request['cwd_label'],request['program'],request['argv'],owner,
        validator_class=validator_class,transport_factory=transport,exclusive_factory=exclusive_factory,
        provider_factory=lambda context,port:LegacyPersonalChannelCapture(context,fetch=port.fetch,clock=port.clock),
        parser_context=request.get('parser_context'),verify_base_ref=request['verify_base_ref'])
