"""Complete native adapter/storage/application with controlled HTTP, never vendor claims."""
from contextlib import redirect_stdout,redirect_stderr
from copy import deepcopy
from email.message import Message
import io,json,os
from pathlib import Path
import subprocess,sys,tempfile,unittest
from unittest.mock import patch
from urllib.error import HTTPError,URLError
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tests'))
from lib import sbom_export_application as app
from lib.providers import sbom_export_native as native,sbom_export_profile as profile,sbom_export_session as session
from lib.providers.sbom_export_storage import read_private,document
import test_v2_sbom_export as oracle

QUERY='PRIVATE_TEST_LOCATION_QUERY_MUST_NOT_BE_RETAINED'
TOKEN='PRIVATE_TEST_BEARER_MUST_NOT_BE_RETAINED'
LOCATION='https://dgptest.blob.core.windows.net/document?signature='+QUERY


class Response:
 def __init__(self,status,payload=b''):self.status=status;self.body=payload
 def __enter__(self):return self
 def __exit__(self,*args):return None
 def read(self,size):value=self.body[:size];self.body=self.body[size:];return value


class Opener:
 def __init__(self,owner,handler):self.owner=owner;self.handler=handler
 def open(self,request,timeout):
  o=self.owner;url=request.full_url;headers={k.lower():v for k,v in request.header_items()};o.calls.append((url,headers,timeout))
  self.owner.case.assertEqual(request.get_method(),'GET')
  if url==LOCATION:
   o.case.assertNotIn('authorization',headers)
   if o.download_error:raise URLError('untrusted download failure containing '+LOCATION)
   if o.redirect:
    handler=self.handler();headers2=Message();headers2['Location']=o.redirect
    redirected=handler.redirect_request(request,None,302,'redirect',headers2,o.redirect)
    o.case.assertNotIn('Authorization',redirected.headers)
   return Response(200,o.raw)
  o.case.assertEqual(headers.get('authorization'),None if o.anonymous else 'Bearer '+TOKEN)
  o.case.assertEqual(headers.get('x-github-api-version'),'2026-03-10')
  prefix=profile.API_ROOT+'/repos/'+oracle.REPO
  if url==prefix:
   o.metadata+=1;branch='changed' if o.branch_moves and o.metadata==2 else 'main'
   return Response(200,json.dumps({'default_branch':branch,'visibility':'private' if o.private else 'public'}).encode())
  if url.startswith(prefix+'/commits/'):
   return Response(200,json.dumps({'sha':oracle.SHA}).encode())
  if url.endswith('/generate-report'):
   if o.generation_error:
    return Response(201,json.dumps({'sbom_url':oracle.LOCATOR+'?signature='+QUERY}).encode())
   return Response(201,json.dumps({'sbom_url':oracle.LOCATOR}).encode())
  if url==oracle.LOCATOR:
   o.polls+=1
   if o.polls<=o.pending:return Response(202)
   headers=Message();headers['Location']=LOCATION
   raise HTTPError(url,302,'redirect',headers,io.BytesIO())
  raise AssertionError('Unexpected controlled API path')


class HTTP:
 def __init__(self,case,**options):
  self.case=case;self.calls=[];self.metadata=0;self.polls=0;self.pending=options.get('pending',0);self.anonymous=options.get('anonymous',False);self.private=options.get('private',False)
  self.raw=options.get('raw',json.dumps(oracle.document()).encode());self.branch_moves=options.get('branch_moves',False)
  self.redirect=options.get('redirect');self.generation_error=options.get('generation_error',False);self.download_error=options.get('download_error',False)
 def build(self,handler):return Opener(self,handler)


class NativeExportTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name).resolve()
  self.token=self.base/'read-token';self.token.write_text(TOKEN);self.token.chmod(0o600)
  self.out=self.base/'exports';self.state=self.base/'records'
  self.options={'profile':profile.PROFILE,'repository':oracle.REPO,'commit':oracle.SHA,'token_file':self.token,
   'output_directory':self.out,'state_directory':self.state,'legacy_environment':False,'workflow_ref':'refs/heads/main'}
 def execute(self,**scenario):
  http=HTTP(self,**scenario)
  with patch.object(native,'build_opener',side_effect=http.build),patch.object(native.time,'sleep',return_value=None) as sleeps:
   result=app.execute(self.options)
  return (*result,http,sleeps)
 def no_secret(self,root):
  for path in Path(root).rglob('*'):
   if path.is_file():
    self.assertNotIn(TOKEN.encode(),path.read_bytes(),str(path));self.assertNotIn(QUERY.encode(),path.read_bytes(),str(path))
 def test_complete_native_export_poll_and_retained_replay_never_store_credentials_or_query(self):
  report,result,code,http,sleeps=self.execute(pending=2)
  self.assertEqual(code,0,report);self.assertEqual(report['state'],'complete');self.assertEqual(sleeps.call_count,2)
  self.assertEqual(json.loads((self.out/'sbom.spdx.json').read_bytes()),oracle.document())
  metadata=json.loads((self.out/'sbom-metadata.json').read_bytes());self.assertEqual(metadata['commit_sha'],oracle.SHA)
  self.assertEqual(result['stdout'],f'Validated SPDX SBOM: {self.out}/sbom.spdx.json ({self.out}/sbom-metadata.json)\n')
  with patch.object(native,'build_opener',side_effect=AssertionError('HTTP forbidden')),patch.object(native.time,'sleep',side_effect=AssertionError('sleep forbidden')):
   replay=app.inspect(report['record_root'])
  self.assertTrue(replay['retained_declared_replay_consistent']);self.assertFalse(replay['native_HTTP_or_wait_or_clock_repeated'])
  self.no_secret(report['record_root'])
 def test_changed_branch_after_download_preserves_whole_original_failure_and_no_exports(self):
  report,result,code,_,_=self.execute(branch_moves=True)
  self.assertEqual(code,1);self.assertEqual(report['state'],'complete');self.assertFalse(self.out.exists())
  self.assertIn('Default branch moved',result['stderr']);self.assertTrue(app.inspect(report['record_root'])['retained_declared_replay_consistent'])
 def test_malformed_download_and_non_secret_known_transport_failure(self):
  for scenario in ({'raw':b'bad JSON'},{'download_error':True},{'generation_error':True}):
   with self.subTest(scenario=scenario):
    report,result,code,_,_=self.execute(**scenario);self.assertEqual(code,1,report)
    self.assertTrue(app.inspect(report['record_root'])['retained_declared_replay_consistent']);self.no_secret(report['record_root'])
 def test_allowed_and_rejected_download_redirects_remain_credential_free(self):
  for redirect,expected in (('https://github.s3.amazonaws.com/next?signature='+QUERY,0),('https://attacker.example/next?signature='+QUERY,1)):
   with self.subTest(redirect=redirect):
    report,result,code,_,_=self.execute(redirect=redirect);self.assertEqual(code,expected,report)
    self.assertTrue(app.inspect(report['record_root'])['retained_declared_replay_consistent']);self.no_secret(report['record_root'])
 def test_original_narrow_spdx_validation_is_not_silently_replaced_with_a_different_schema(self):
  data=oracle.document();data['opaque_extension']=float('nan')
  report,_,code,_,_=self.execute(raw=json.dumps(data).encode());self.assertEqual(code,0,report)
  self.assertIn(b'NaN',(self.out/'sbom.spdx.json').read_bytes());self.assertTrue(app.inspect(report['record_root'])['retained_declared_replay_consistent'])
 def test_retained_exports_survive_later_external_overwrite_and_reject_blob_or_event_tampering(self):
  report,_,code,_,_=self.execute();self.assertEqual(code,0);root=Path(report['record_root'])
  (self.out/'sbom.spdx.json').write_text('later explicit overwrite')
  self.assertTrue(app.inspect(root)['retained_declared_replay_consistent'])
  for path in (next((root/'blobs').iterdir()),root/'events/0001.json',root/'request.json',root/'result.json'):
   before=path.read_bytes();path.write_bytes(before+b'changed')
   with self.subTest(path=path.name),self.assertRaises((ValueError,json.JSONDecodeError)):app.inspect(root)
   path.write_bytes(before)
  self.assertTrue(app.inspect(root)['retained_declared_replay_consistent'])
 def test_partial_second_file_failure_retains_first_full_export(self):
  original=native.Output.write
  def failed(output,name,raw):
   if name=='sbom-metadata.json':
    # Exercise a real native open failure after the complete first export.
    (output.root/name).mkdir()
   return original(output,name,raw)
  with patch.object(native.Output,'write',failed):report,result,code,_,_=self.execute()
  self.assertEqual(code,1,report);self.assertTrue((self.out/'sbom.spdx.json').is_file())
  self.assertTrue(app.inspect(report['record_root'])['retained_declared_replay_consistent'])
 def test_explicit_scope_token_and_path_guards_do_not_invoke_http(self):
  self.token.chmod(0o644)
  with patch.object(native,'build_opener',side_effect=AssertionError('HTTP forbidden')):
   with self.assertRaises(ValueError):app.execute(self.options)
  self.token.chmod(0o600);self.options['repository']='owner/..'
  with self.assertRaises(ValueError):app.execute(self.options)
 def test_explicit_anonymous_mode_uses_no_fictitious_token_and_requires_public_subject(self):
  self.options['anonymous']=True;self.options['token_file']=None
  for private,expected in ((False,0),(True,1)):
   with self.subTest(private=private):
    report,result,code,http,_=self.execute(anonymous=True,private=private);self.assertEqual(code,expected,report)
    header=document(read_private(Path(report['record_root'])/'request.json'))
    self.assertFalse(header['context']['token_available']);self.assertTrue(header['context']['anonymous_public'])
    self.assertEqual(header['credential_kind'],'explicit_anonymous_public')
    self.assertTrue(app.inspect(report['record_root'])['retained_declared_replay_consistent'])
    if private:self.assertFalse(any(url.endswith('/generate-report') for url,_,_ in http.calls))
 def test_default_system_temporary_base_alias_is_canonicalized_but_explicit_state_symlink_is_rejected(self):
  target=self.base/'system-temp';target.mkdir(mode=0o700)
  alias=self.base/'system-temp-alias';alias.symlink_to(target,target_is_directory=True)
  self.options.pop('state_directory')
  with patch.object(session.tempfile,'gettempdir',return_value=str(alias)):
   report,_,code,_,_=self.execute()
  self.assertEqual(code,0,report)
  self.assertTrue(Path(report['record_root']).is_relative_to(target/('axiom-sbom-records-'+str(os.geteuid()))))
  self.assertTrue(app.inspect(report['record_root'])['retained_declared_replay_consistent'])
  self.options['state_directory']=alias/'explicit'
  with patch.object(native,'build_opener',side_effect=AssertionError('No HTTP before state admission')):
   with self.assertRaisesRegex(ValueError,'sbom_path_symlink_forbidden'):app.execute(self.options)
 def test_stdlib_frontend_missing_legacy_environment_preserves_original_main_stderr(self):
  env={k:v for k,v in os.environ.items() if k not in ('GITHUB_REPOSITORY','GITHUB_SHA','GH_TOKEN')}
  result=subprocess.run([sys.executable,'-I','-S','-B',str(ROOT/'scripts/export_axiom_v2_sbom.py'),'--legacy-environment','--output','legacy'],env=env,capture_output=True,timeout=30)
  self.assertEqual(result.returncode,2);self.assertEqual(result.stdout,b'');self.assertEqual(result.stderr,b'Missing required environment variable: GITHUB_REPOSITORY\n')


if __name__=='__main__':unittest.main()
