"""Complete stdlib SBOM export orchestration and declared retained inspection."""
import json
from pathlib import Path
from lib import sbom_export as decisions
from lib.sbom_export_ports import Session,selected_context,capture_source,read_record,AUTHORITY,profile,encode
from lib.sbom_export_replay import Replay


def execute(options,*,instance_root=None,node=None):
 if options.get('profile',profile.PROFILE)!=profile.PROFILE:raise ValueError('sbom_profile_unsupported')
 request,token,output,credential_kind=selected_context(options)
 if request['missing_environment'] is not None:
  result=decisions.run(request,None,None)
  return {'state':'rejected','record_root':None,'exit_code':2,**AUTHORITY},result,2
 try:decisions.validate_request(request,profile.ERRORS)
 except ValueError as error:
  result={'exit_code':1,'stdout':'','stderr':f'SBOM generation failed: {error}\n'}
  return {'state':'rejected','record_root':None,'exit_code':1,**AUTHORITY},result,1
 with Session(options,request,token,output,credential_kind,node=node,instance_root=instance_root) as session:
  error=None;result=None
  try:
   result=decisions.run(request,session.environment,session.output)
   session.checkpoint()
  except Exception as exception:error=exception
  state='incomplete' if error is not None or session.record.capture_incomplete else 'complete'
  retained=session.record.finish(state,result,session.output.files,error)
  report={'state':state,'record_root':str(session.record.root),'exit_code':2 if state=='incomplete' else result['exit_code'],
   'source_digest':session.source['source_digest'],'node_context':node,**AUTHORITY}
 if state=='complete':inspect(session.record.root,node=node)
 return report,result,report['exit_code']


def inspect(root,*,node=None):
 request,source,result,events,blob,all_blobs=read_record(root)
 if (not isinstance(request,dict) or set(request)!={'schema_version','profile','context','output_label','credential_kind','token_value_retained','temporary_download_URL_retained'}
  or type(request['schema_version']) is not int or request['schema_version']!=1 or request['profile']!=profile.PROFILE
  or request['token_value_retained'] is not False or request['temporary_download_URL_retained'] is not False
  or request['credential_kind'] not in ('none','explicit_legacy_environment','explicit_private_file','explicit_anonymous_public')
  or not isinstance(request['output_label'],str)):
  raise ValueError('sbom_retained_request_changed')
 if (set(result)!={'schema_version','state','result','touched_files','exception_type','event_count','event_tip',*AUTHORITY}
  or type(result['schema_version']) is not int or result['schema_version']!=1 or any(result.get(k)!=v for k,v in AUTHORITY.items())
  or not events or events[0]!={'kind':'opened',**AUTHORITY}):raise ValueError('sbom_retained_authority_or_result_changed')
 if node is not None and source.get('node_context')!=node:raise ValueError('sbom_retained_node_context_changed')
 current=capture_source(source.get('node_context'))
 label=source.get('source_root')
 if (not isinstance(label,str) or len(label)>8192 or not Path(label).is_absolute() or '..' in Path(label).parts
  or any(ord(c)<32 for c in label)):
  raise ValueError('sbom_retained_source_label_changed')
 # This is a descriptive recorded path; replay always uses the current own code.
 current['source_root']=label
 if source!=current:raise ValueError('sbom_retained_source_changed')
 if result['state']!='complete' or result['exception_type'] is not None:
  return {'state':'incomplete','record_root':str(root),'retained_declared_replay_consistent':False,'diagnostics':['sbom_incomplete_requires_review'],**AUTHORITY}
 context=request['context']
 if (not isinstance(context,dict) or set(context)!={'repository','expected_sha','token_available','event_ref','missing_environment','anonymous_public'}
  or type(context['token_available']) is not bool or type(context['anonymous_public']) is not bool or context['missing_environment'] is not None
  or not isinstance(context['repository'],str) or not isinstance(context['expected_sha'],str)
  or context['event_ref'] is not None and not isinstance(context['event_ref'],str)):
  raise ValueError('sbom_retained_context_changed')
 if context['anonymous_public']:
  if context['token_available'] or request['credential_kind']!='explicit_anonymous_public':raise ValueError('sbom_retained_credential_mode_changed')
 elif not context['token_available'] or request['credential_kind'] not in ('explicit_private_file','explicit_legacy_environment'):
  raise ValueError('sbom_retained_credential_mode_changed')
 replay=Replay(events,blob,profile,request['output_label']);actual=decisions.run(request['context'],replay,replay);replay.finish(actual)
 for value in result['touched_files'].values():replay.snapshot(value)
 if encode(actual)!=encode(result['result']) or encode(replay.files)!=encode(result['touched_files']) or not all_blobs():
  raise ValueError('sbom_complete_retained_replay_changed')
 return {'state':'complete','record_root':str(root),'original_exit_code':actual['exit_code'],
  'retained_declared_replay_consistent':True,'current_exports_rechecked':False,'native_HTTP_or_wait_or_clock_repeated':False,
  'temporary_download_URL_revalidated':False,'source_digest':source['source_digest'],**AUTHORITY}
