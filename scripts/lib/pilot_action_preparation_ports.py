"""Explicit original captured-field validation, sampled time and exclusive output."""
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.providers.pilot_action_preparation_clock import NativePreparationClock
from lib.pilot_action_preparation_clock import ReplayPreparationClock
from lib.personal_channel_ports import exclusive_factory
from lib.pilot_action_preparation_context import execute as execute_kernel
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.portable.contracts import ROOT
from lib.v2_source import selected_paths
from lib.providers.retained_argparse import capture_context as capture_parser_context

CAPTURE_PROFILES=('legacy-lifecycle-capture-v1',)
COMPONENTS=('pilot_action_preparation.py','pilot_action_preparation_context.py',
    'pilot_action_preparation_clock.py','providers/pilot_action_preparation_clock.py',
    'pilot_action_preparation_ports.py','pilot_action_preparation_application.py')

def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):
        raise ValueError('pilot_action_preparation_closure_not_registered')
    return lifecycle_source(node,product_tree)

def execute(request,owner,*,validator_class):
    if request['capture_profile'] not in CAPTURE_PROFILES:raise ValueError('pilot_action_preparation_capture_profile_not_supported')
    return execute_kernel(request['source_label'],request['cwd_label'],request['argv'],owner,
        validator_class=validator_class,provider_factory=LegacyRepositoryLifecycleCapture,
        exclusive_factory=exclusive_factory,clock_factory=NativePreparationClock if hasattr(owner,'record') else ReplayPreparationClock,
        parser_context=request['parser_context'])
