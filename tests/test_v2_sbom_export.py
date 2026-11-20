"""Complete immutable-V1 streams, export bytes, clock and fail-fast order."""
from copy import deepcopy
from datetime import datetime,timezone
from importlib.machinery import SourceFileLoader
import hashlib,importlib.util,io,json
from pathlib import Path
import sys,unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib import sbom_export as core
from lib.providers import sbom_export_profile as profile

REFERENCE='acbb6441bd8fd74e1974ad40d755466e1882d6a5fb3c5dcef0880046d24adf3b'
AT=datetime(2026,11,20,0,0,0,123456,tzinfo=timezone.utc)
REPO='joku-dev/ha-CPsWMS';SHA='a'*40;ID='12345678-1234-1234-1234-123456789012'
LOCATOR=profile.API_ROOT+f'/repos/{REPO}/dependency-graph/sbom/fetch-report/'+ID
DOWNLOAD='https://github.s3.amazonaws.com/fixture?signature=TEST_ONLY_NOT_A_SECRET'
CASES=[]


def document(repository=REPO):
 return {'SPDXID':'SPDXRef-DOCUMENT','spdxVersion':'SPDX-2.3','documentNamespace':'https://spdx.org/spdxdocs/test',
  'creationInfo':{'created':'2026-11-15T12:00:00Z'},'packages':[{'SPDXID':'root','name':f'com.github.{repository}',
  'externalRefs':[{'referenceType':'purl','referenceLocator':f'pkg:github/{repository}@main'}]},
  {'SPDXID':'dep','name':'jsonschema','versionInfo':'4.26.0'}],
  'relationships':[{'spdxElementId':'SPDXRef-DOCUMENT','relationshipType':'DESCRIBES','relatedSpdxElement':'root'}]}


class Files:
 def __init__(self,events,fail=None):self.events=events;self.files={};self.fail=fail
 def mkdir(self,**kwargs):
  self.events.append(('mkdir',))
  if self.fail=='mkdir':raise OSError('test directory denied')
 def __truediv__(self,name):return File(self,name)
 def write(self,name,raw):
  self.events.append(('write',name))
  if self.fail==name:raise OSError('test file denied')
  self.files[name]=raw;return str(self/name)


class File:
 def __init__(self,parent,name):self.parent=parent;self.name=name
 def write_text(self,text,encoding):return self.parent.write(self.name,text.encode(encoding))
 def __str__(self):return 'fixture-output/'+self.name


class Environment:
 def __init__(self,scenario,events):self.s=scenario;self.events=events;self.metadata_count=0;self.commit_count=0;self.poll_count=0
 def api_json(self,url,token):
  assert token=='TEST_ONLY_TOKEN'
  if url.endswith('/generate-report'):return self.generate_report(REPO)
  if '/commits/' in url:return self.branch_commit(REPO,url.rsplit('/commits/',1)[1])
  return self.repository_metadata(REPO)
 def repository_metadata(self,repository):
  self.metadata_count+=1;self.events.append(('metadata',repository))
  if 'metadata' in self.s:return deepcopy(self.s['metadata'])
  branch=self.s.get('after_branch','main') if self.metadata_count==2 else 'main'
  return 200,{'default_branch':branch}
 def branch_commit(self,repository,branch):
  self.commit_count+=1;self.events.append(('commit',repository,branch))
  if 'commit_response' in self.s:return deepcopy(self.s['commit_response'])
  sha=self.s.get('after_sha',SHA) if self.commit_count==2 else self.s.get('before_sha',SHA)
  return 200,{'sha':sha}
 def generate_report(self,repository):self.events.append(('generate',repository));return deepcopy(self.s.get('generation',(201,{'sbom_url':LOCATOR})))
 def report_locator(self,payload):return profile.report_locator(payload)
 def report_identifier(self,repository,locator):return profile.report_identifier(repository,locator)
 def poll_report(self,repository,identifier):
  self.events.append(('poll',repository,identifier));self.poll_count+=1
  if self.s.get('all_pending') or self.poll_count<=self.s.get('pending',0):raise RuntimeError('GitHub SBOM fetch returned HTTP 202')
  if 'poll_error' in self.s:raise RuntimeError(self.s['poll_error'])
  return None if self.s.get('missing_download') else DOWNLOAD
 def old_poll(self,url,token):
  assert token=='TEST_ONLY_TOKEN';assert url==LOCATOR
  return self.poll_report(REPO,ID)
 def download(self,handle):
  self.events.append(('download',));assert handle==DOWNLOAD
  if self.s.get('download_error'):raise RuntimeError('Could not download the generated SPDX SBOM')
  return self.s.get('raw',json.dumps(document()).encode())
 def spdx_identity(self,repository):return profile.identity(repository)
 def sleep(self,seconds):self.events.append(('sleep',seconds))
 def now(self,*args):
  self.events.append(('clock',))
  if self.s.get('clock_error'):raise RuntimeError('test clock failed')
  return AT
 def request_error(self,name):return profile.ERRORS[name]
 def generation_timeout_error(self):return profile.generation_timeout_error()
 def source_label(self):return profile.SOURCE


class OriginalExportTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  path=ROOT/'tests/fixtures/v2-sbom-export-original/export_repository_sbom.py.txt';assert hashlib.sha256(path.read_bytes()).hexdigest()==REFERENCE
  loader=SourceFileLoader('immutable_V1_SBOM_export',str(path));spec=importlib.util.spec_from_loader(loader.name,loader);cls.old=importlib.util.module_from_spec(spec);loader.exec_module(cls.old)
 def compare(self,scenario=None,*,repository=REPO,sha=SHA,token='TEST_ONLY_TOKEN',event_ref='refs/heads/main'):
  s=deepcopy(scenario or {});old_events=[];new_events=[];old_env=Environment(s,old_events);new_env=Environment(s,new_events)
  old_files=Files(old_events,s.get('fail_output'));new_files=Files(new_events,s.get('fail_output'))
  request={'repository':repository,'expected_sha':sha,'token_available':bool(token),'event_ref':event_ref}
  stdout=io.StringIO();stderr=io.StringIO();old_exception=None
  class Clock:
   @staticmethod
   def now(*args):return old_env.now(*args)
  with patch.object(self.old,'api_json',side_effect=old_env.api_json),patch.object(self.old,'api_redirect',side_effect=old_env.old_poll),patch.object(self.old,'download_sbom',side_effect=old_env.download),patch.object(self.old.time,'sleep',side_effect=old_env.sleep),patch.object(self.old,'datetime',Clock),patch.dict(self.old.os.environ,{} if event_ref is None else {'GITHUB_REF':event_ref},clear=True),redirect_stdout(stdout),redirect_stderr(stderr):
   # Invoke the whole original generate and exactly its main's known exception contract.
   try:
    a,b=self.old.generate(repository,sha,token,old_files)
    old_result={'exit_code':0,'stdout':f'Validated SPDX SBOM: {a} ({b})\n','stderr':''}
   except (OSError,ValueError,RuntimeError) as error:old_result={'exit_code':1,'stdout':'','stderr':f'SBOM generation failed: {error}\n'}
   except Exception as error:old_exception=type(error)
  if old_exception:
   with self.assertRaises(old_exception):core.run(request,new_env,new_files)
   self.assertEqual(new_events,old_events);self.assertEqual(new_files.files,old_files.files)
   CASES.append({'exception':old_exception.__name__,'complete':False});return
  actual=core.run(request,new_env,new_files)
  self.assertEqual(actual,old_result);self.assertEqual(new_events,old_events);self.assertEqual(new_files.files,old_files.files)
  CASES.append({'exit':actual['exit_code'],'whole_streams_equal':True,'whole_files_equal':True,'complete_order_equal':True,'file_count':len(new_files.files)})
  return actual,new_env,new_files
 def test_positive_complete_files_metadata_microseconds_clock_and_unwrapped_forms(self):
  for version in ('SPDX-2.2','SPDX-2.3'):
   for wrapped in (False,True):
    d=document();d['spdxVersion']=version;raw=json.dumps({'sbom':d} if wrapped else d).encode();_,env,files=self.compare({'raw':raw})
    metadata=json.loads(files.files['sbom-metadata.json']);self.assertEqual(metadata['generated_at'],'2026-11-20T00:00:00.123456Z')
    self.assertLess(env.events.index(('write','sbom.spdx.json')),env.events.index(('clock',)))
 def test_optional_empty_and_absent_workflow_ref_are_preserved(self):
  for ref in (None,''):
   _,_,files=self.compare(event_ref=ref);self.assertEqual(json.loads(files.files['sbom-metadata.json'])['workflow_ref'],ref)
 def test_request_guards_stop_before_network_generation(self):
  for kwargs in ({'repository':'bad'},{'sha':'bad'},{'token':''},{'event_ref':'refs/heads/feature'}):
   with self.subTest(kwargs=kwargs):self.compare(**kwargs)
  self.compare({'before_sha':'b'*40})
 def test_metadata_and_commit_failures_preserve_original_complete_errors(self):
  for scenario in ({'metadata':(403,{})},{'metadata':(200,{})},{'metadata':(200,{'default_branch':4})},
   {'commit_response':(403,{})},{'commit_response':(200,{})},{'commit_response':(200,{'sha':'bad'})}):
   with self.subTest(scenario=scenario):self.compare(scenario)
 def test_report_origin_exact_prefix_and_identifier_boundaries(self):
  for value in (None,'http://api.github.com/repos/'+REPO+'/dependency-graph/sbom/fetch-report/'+ID,
     LOCATOR.replace(REPO,'other/repo'),LOCATOR+'?token=BAD',LOCATOR[:-1],LOCATOR[:-1]+'G'):
   with self.subTest(value=value):self.compare({'generation':(201,{'sbom_url':value})})
  self.compare({'generation':(202,{})});self.compare({'generation':(200,{})})
 def test_poll_202_retries_order_and_final_attempt_fail_fast(self):
  for pending in (0,1,17):
   with self.subTest(pending=pending):result,env,_=self.compare({'pending':pending});self.assertEqual(env.poll_count,pending+1);self.assertEqual(sum(e[0]=='sleep' for e in env.events),pending)
  result,env,_=self.compare({'all_pending':True});self.assertEqual(env.poll_count,18);self.assertEqual(sum(e[0]=='sleep' for e in env.events),17);self.assertEqual(result['exit_code'],1)
  self.compare({'poll_error':'GitHub SBOM fetch returned HTTP 403'});self.compare({'missing_download':True})
 def test_download_error_before_any_output(self):self.compare({'download_error':True})
 def test_every_spdx_shape_root_and_identity_failure(self):
  raws=[b'not JSON',b'null',b'[]']
  for key,value in (('spdxVersion','unknown'),('documentNamespace','http://x'),('creationInfo',{}),('packages',[]),('packages',[{}]),('relationships',[])):
   d=document();d[key]=value;raws.append(json.dumps(d).encode())
  raws.append(json.dumps(document('other/repo')).encode());d=document();d['packages'].append(deepcopy(d['packages'][0]));raws.append(json.dumps(d).encode())
  for raw in raws:
   with self.subTest(raw=raw):self.compare({'raw':raw})
 def test_casefolded_identity_purl_alias_unicode_extensions_and_root_uniqueness(self):
  for root in ({'name':'unrelated','externalRefs':[{'referenceType':'purl','referenceLocator':'pkg:GITHUB/JOKU-DEV/HA-CPSWMS@head'}]}, {'name':'GITHUB/JOKU-DEV/HA-CPSWMS','externalRefs':None}):
   d=document();d['packages'][0].update(root);d['Änderung']={'opaque':['ä','ß']};self.compare({'raw':json.dumps(d).encode()})
 def test_branch_move_after_valid_download_never_writes_output(self):
  for scenario in ({'after_sha':'b'*40},{'after_branch':'changed'}):
   _,env,files=self.compare(scenario);self.assertEqual(files.files,{});self.assertNotIn(('mkdir',),env.events)
 def test_every_partial_export_boundary_and_clock_order_preserves_original(self):
  for part in ('mkdir','sbom.spdx.json','sbom-metadata.json'):
   with self.subTest(part=part):self.compare({'fail_output':part})
  _,_,files=self.compare({'clock_error':True});self.assertEqual(set(files.files),{'sbom.spdx.json'})
 def test_unexpected_payload_types_stay_original_exceptions(self):
  for scenario in ({'metadata':(200,[])},{'commit_response':(200,[])},{'generation':(201,[])}):self.compare(scenario)
 def test_missing_legacy_environment_variable_priority_and_original_main_streams(self):
  for values,missing in (({},'GITHUB_REPOSITORY'),({'GITHUB_REPOSITORY':REPO},'GITHUB_SHA'),({'GITHUB_REPOSITORY':REPO,'GITHUB_SHA':SHA},'GH_TOKEN')):
   stdout=io.StringIO();stderr=io.StringIO()
   with patch.dict(self.old.os.environ,values,clear=True),redirect_stdout(stdout),redirect_stderr(stderr):code=self.old.main()
   current=core.run({'missing_environment':missing},None,None)
   self.assertEqual(current,{'exit_code':code,'stdout':stdout.getvalue(),'stderr':stderr.getvalue()})


if __name__=='__main__':unittest.main()
