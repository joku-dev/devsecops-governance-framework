"""Explicit legacy captured-field semantics; no provider calls or authority."""
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.providers.sbom_export_storage import owned_directory
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.synthetic_lifecycle_ports import current_source as lifecycle_source
from lib.portable.contracts import ROOT
from lib.v2_source import selected_paths

CAPTURE_PROFILES=('legacy-lifecycle-capture-v1',)
COMPONENTS=('pilot_projection_programs.py','pilot_projection_context.py','pilot_projection_application.py',
            'pilot_projection_ports.py','providers/repository_lifecycle_capture.py')

def captured_provider(profile):
    if profile not in CAPTURE_PROFILES:raise ValueError('pilot_projection_capture_profile_not_supported')
    return LegacyRepositoryLifecycleCapture

def current_source(node,product_tree=None):
    if not {'scripts/lib/'+name for name in COMPONENTS}<=set(selected_paths(ROOT)):
        raise ValueError('pilot_projection_closure_not_registered')
    return lifecycle_source(node,product_tree)
