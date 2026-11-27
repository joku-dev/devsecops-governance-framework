"""Explicit Git/path adapter composition for the original accepted-prefix helper."""
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.providers.accepted_prefix_transport import AcceptedPrefixTransport
from lib.providers.accepted_prefix_paths import NativePrefixPaths
from lib.accepted_prefix_paths import ReplayPrefixPaths
from lib.accepted_prefix_context import execute as execute_kernel
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.portable.contracts import ROOT
from lib.v2_source import selected_paths

TRANSPORT_PROFILES=('legacy-accepted-prefix-git-v1',)
COMPONENTS=('accepted_prefix.py','accepted_prefix_context.py','accepted_prefix_ports.py','accepted_prefix_application.py',
 'accepted_prefix_protocol.py','accepted_prefix_git_context.py','accepted_prefix_hash_scope.py','accepted_prefix_metadata.py','accepted_prefix_paths.py',
 'providers/accepted_prefix_protocol.py','providers/accepted_prefix_hash_scope.py','providers/accepted_prefix_metadata.py',
 'providers/accepted_prefix_metadata_protocol.py','providers/accepted_prefix_paths.py','providers/accepted_prefix_transport.py')

def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):raise ValueError('accepted_prefix_closure_not_registered')
    return lifecycle_source(node,product_tree)
def replay_owner(request,events,blob):return ReplayIO(events,blob,request['export_mode'],request['cwd_label'])
def execute(request,owner,*,validator_class):
    if request['transport_profile'] not in TRANSPORT_PROFILES:raise ValueError('accepted_prefix_transport_profile_not_supported')
    native=hasattr(owner,'record')
    return execute_kernel(request['source_label'],request['cwd_label'],request['base_ref'],owner,validator_class=validator_class,
        transport_factory=lambda io,root,context,emit:AcceptedPrefixTransport(io,root,context,emit_stderr=emit),
        paths_factory=NativePrefixPaths if native else ReplayPrefixPaths)
