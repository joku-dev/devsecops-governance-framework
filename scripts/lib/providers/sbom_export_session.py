"""Stdlib-only operator context, owned source snapshot and fresh private session."""
from pathlib import Path
import hashlib,json,os,tempfile,re
from lib.private_credentials import check_private_file
from lib.providers.sbom_export_storage import Record,normalized,owned_directory
from lib.providers.sbom_export_native import Environment,Output
from lib.providers import sbom_export_profile as profile
from lib.v2_source import active_fingerprints,selected_paths

ROOT=Path(__file__).resolve().parents[3]
REQUIRED=frozenset(('scripts/export_axiom_v2_sbom.py','scripts/lib/sbom_export.py',
 'scripts/lib/sbom_export_application.py','scripts/lib/sbom_export_replay.py','scripts/lib/sbom_export_ports.py',
 'scripts/lib/providers/sbom_export_native.py','scripts/lib/providers/sbom_export_storage.py',
 'scripts/lib/providers/sbom_export_profile.py','scripts/lib/providers/sbom_export_session.py'))
CONTEXT_FIELDS={'repository','expected_sha','token_available','event_ref','missing_environment','anonymous_public'}


def selected_context(options):
 legacy=bool(options.get('legacy_environment'));anonymous=bool(options.get('anonymous'));token='';missing=None
 if anonymous and (legacy or options.get('token_file') is not None):raise ValueError('sbom_context_modes_conflict')
 if legacy:
  if any(options.get(key) is not None for key in ('repository','commit','token_file','workflow_ref')):
   raise ValueError('sbom_context_modes_conflict')
  values={}
  for key in ('GITHUB_REPOSITORY','GITHUB_SHA','GH_TOKEN'):
   if key not in os.environ:missing=key;break
   values[key]=os.environ[key]
  repository=values.get('GITHUB_REPOSITORY');commit=values.get('GITHUB_SHA');token=values.get('GH_TOKEN','')
  event_ref=os.environ.get('GITHUB_REF');output=options.get('output_directory') or os.environ.get('SBOM_OUTPUT_DIR','sbom-output')
  credential_kind='explicit_legacy_environment'
 else:
  repository=options.get('repository');commit=options.get('commit');event_ref=options.get('workflow_ref')
  output=options.get('output_directory') or 'sbom-output';credential_kind='explicit_anonymous_public' if anonymous else 'none'
  if options.get('token_file') is not None:
   path=normalized(options['token_file']);check_private_file(path)
   fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
   try:
    raw=os.read(fd,16385)
    if len(raw)>16384:raise ValueError('sbom_read_credential_budget')
    token=raw.decode('utf-8').strip()
   finally:os.close(fd)
   credential_kind='explicit_private_file'
 if token and any(ord(c)<33 or ord(c)>126 for c in token):raise ValueError('sbom_invalid_read_credential')
 return {'repository':repository,'expected_sha':commit,'token_available':bool(token),'event_ref':event_ref,
  'missing_environment':missing,'anonymous_public':anonymous},token,output,credential_kind


def capture_source(node=None):
 if node is not None:
  if (not isinstance(node,dict) or set(node)!={'node_id','source_revision','runtime_source_digest'}
   or not all(isinstance(value,str) for value in node.values())
   or not re.fullmatch('[a-f0-9]{32}',node['node_id'])
   or not re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}',node['source_revision'])
   or not re.fullmatch('[a-f0-9]{64}',node['runtime_source_digest'])):
   raise ValueError('sbom_node_context_invalid')
 if not REQUIRED<=set(selected_paths(ROOT)):raise ValueError('sbom_execution_closure_not_registered')
 fingerprints=active_fingerprints(ROOT)
 return {'schema_version':1,'kind':'own_registered_stdlib_source','source_root':str(ROOT),
  'active_fingerprints':fingerprints,'source_digest':hashlib.sha256(json.dumps(fingerprints,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
  'node_context':node,'source_authentication_independent':False,'local_git_program_required':False}


class Session:
 def __init__(self,options,context,token,output,credential_kind,*,node=None,instance_root=None):
  if set(context)!=CONTEXT_FIELDS:raise ValueError('sbom_context_contract_invalid')
  if any(part in ('.','..') for part in context['repository'].split('/')):raise ValueError('sbom_repository_path_component_forbidden')
  self.options=options;self.source=capture_source(node);self.token=token
  if options.get('state_directory') is not None:state=normalized(options['state_directory'])
  elif instance_root is not None:state=normalized(instance_root)/'state/sbom-export'
  else:
   # Resolve only the system-selected temporary base (macOS /var -> /private/var).
   # Explicit paths and the actual private state leaf still reject symlinks.
   temporary_base=Path(tempfile.gettempdir()).resolve(strict=True)
   state=normalized(temporary_base/('axiom-sbom-records-'+str(os.geteuid())))
  if state==ROOT or state.is_relative_to(ROOT) or ROOT.is_relative_to(state):raise ValueError('sbom_state_outside_product_required')
  owned_directory(state,True)
  if os.statvfs(state).f_bavail*os.statvfs(state).f_frsize<512*1024**2:raise ValueError('sbom_free_space_reserve')
  request={'schema_version':1,'profile':profile.PROFILE,'context':context,'output_label':str(Path(output)),
   'credential_kind':credential_kind,'token_value_retained':False,'temporary_download_URL_retained':False}
  self.record=Record(state,request,self.source)
  self.environment=Environment(self.record,token,anonymous_public=context['anonymous_public'])
  self.output=Output(self.record,output,source=ROOT,credential=options.get('token_file'),allow_workspace_output=True)
 def __enter__(self):return self
 def checkpoint(self):
  if capture_source(self.source['node_context'])!=self.source:raise ValueError('sbom_own_source_changed_during_operation')
 def __exit__(self,*args):
  self.environment.token='';self.environment.locations.clear();self.token=''
