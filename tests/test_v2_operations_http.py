"""Controlled native-worker pipe, raw API capture and complete PR pagination."""
from copy import deepcopy
import base64,hashlib,io,json,os,subprocess,sys,tempfile,time,unittest
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from email.message import Message

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.operations_collection import AcquisitionFailure
from lib.operations_replay import ReplayCalls
from lib.providers import operations_http as transport,operations_http_worker as worker,operations_report_profile as profile
from lib.providers.sbom_export_storage import Record,read_record,AUTHORITY

TOKEN='EXPLICIT_TEST_READ_TOKEN_NOT_FOR_STORAGE'


def node(number,**values):
    return {'number':number,'url':'https://example.invalid/pr/'+str(number),'title':'Fixture',
            'createdAt':'2026-11-20T00:00:00Z','isDraft':False,'reviewDecision':'REVIEW_REQUIRED',
            'mergeStateStatus':'BLOCKED','author':{'id':'U1','login':'person','name':'Person'},'headRefName':'branch',**values}


def page(rows,more=False,cursor=None):
    return {'data':{'repository':{'pullRequests':{'nodes':rows,'pageInfo':{'hasNextPage':more,'endCursor':cursor}}}}}


def packet(value,status=200,code=None):
    raw=value if isinstance(value,bytes) else json.dumps(value).encode()
    return {'status':status,'native_code':code,'body_b64':base64.b64encode(raw).decode()}


class ControlledProcess:
    def __init__(self,owner,args,options):self.owner=owner;self.args=args;self.options=options;self.returncode=None
    def communicate(self,input=None,timeout=None):
        self.owner.assertNotIn(TOKEN,' '.join(self.args));self.owner.assertNotIn('GH_TOKEN',self.options['env'])
        self.owner.assertGreater(timeout,0);self.owner.assertLessEqual(timeout,60)
        request=json.loads(input);self.owner.inputs.append(deepcopy(request));value=self.owner.answer(request)
        self.returncode=0;return json.dumps(value).encode(),b''
    def poll(self):return self.returncode
    def kill(self):self.returncode=-9


class NativeOperationsHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name).resolve()
        self.record=Record(self.base/'records',{'kind':'controlled-technical-test'},{'kind':'controlled-technical-test'})
        self.assertIs(worker.profile,profile,'Package import and worker must share the selected profile')
        self.backend=transport.NativeBackend(self.record,TOKEN);self.inputs=[];self.answer=lambda request:packet({'object':{'sha':'a'*40}})
    def process(self,*args,**kwargs):return ControlledProcess(self,args[0],kwargs)
    def reads(self,queries=None):return transport.ProviderReads(self.backend,'fixture/repository',queries or {profile.MAIN_WORKFLOW:'push'})
    def no_token(self):
        for path in self.record.root.rglob('*'):
            if path.is_file():self.assertNotIn(TOKEN.encode(),path.read_bytes(),str(path))

    def test_explicit_bearer_only_in_private_stdin_and_complete_raw_response_retained(self):
        with patch.object(transport.subprocess,'Popen',side_effect=self.process),patch.dict(os.environ,{'GH_TOKEN':'UNSELECTED_AMBIENT_TOKEN'}):
            value=self.reads().main_reference('fixture/repository')
        self.assertEqual(value,{'object':{'sha':'a'*40}});self.assertEqual(self.inputs[0]['token'],TOKEN)
        self.assertEqual(self.inputs[0]['method'],'GET');self.no_token()
        self.assertTrue(any(p.read_bytes()==json.dumps(value).encode() for p in self.record.blobs.iterdir()))

    def test_workflow_name_is_encoded_and_only_the_admitted_event_is_used(self):
        self.answer=lambda request:packet({'workflow_runs':[]})
        with patch.object(transport.subprocess,'Popen',side_effect=self.process):
            self.assertEqual(self.reads({'folder/name?event=bad.yml':'schedule'}).workflow_runs('fixture/repository','folder/name?event=bad.yml','schedule'),{'workflow_runs':[]})
        self.assertIn('folder%2Fname%3Fevent%3Dbad.yml',self.inputs[0]['path'])
        self.assertTrue(self.inputs[0]['path'].endswith('&event=schedule'))
        with self.assertRaisesRegex(ValueError,'operations_workflow_scope_changed'):self.reads().workflow_runs('fixture/repository','other.yml',None)

    def test_malformed_successful_JSON_stays_JSONDecodeError_and_HTTP_failure_is_separate(self):
        self.answer=lambda request:packet(b'bad JSON')
        with patch.object(transport.subprocess,'Popen',side_effect=self.process):
            with self.assertRaises(json.JSONDecodeError):self.reads().main_reference('fixture/repository')
        self.answer=lambda request:packet(b'HTTP body can be non-JSON',status=403,code='http_403')
        with patch.object(transport.subprocess,'Popen',side_effect=self.process):
            with self.assertRaises(AcquisitionFailure) as error:self.reads().main_reference('fixture/repository')
        self.assertEqual(error.exception.family,'CalledProcessError');self.no_token()

    def test_missing_explicit_GraphQL_credential_is_unknown_without_starting_a_worker(self):
        self.backend.token=''
        with patch.object(transport.subprocess,'Popen',side_effect=AssertionError('No unauthenticated GraphQL invocation')):
            with self.assertRaises(AcquisitionFailure):self.reads().pull_requests('fixture/repository')
        self.assertEqual(self.backend.calls,0)

    def test_PR_pages_keep_all_requested_fields_deduplicate_and_follow_the_original_limit(self):
        responses=[page([node(1),node(2)],True,'cursor1'),page([node(2),node(3,author={'login':'robot'},reviewDecision=None)],False)]
        self.answer=lambda request:packet(responses.pop(0))
        with patch.object(transport.subprocess,'Popen',side_effect=self.process):value=self.reads().pull_requests('fixture/repository')
        self.assertEqual([r['number'] for r in value],[1,2,3]);self.assertEqual(value[2]['reviewDecision'],'')
        self.assertEqual(value[2]['author'],{'is_bot':True,'login':'app/robot'})
        self.assertEqual(list(value[0]),sorted(profile.PR_FIELDS))
        self.assertEqual(self.inputs[1]['body']['variables']['cursor'],'cursor1')
        self.assertTrue(all(r['method']=='POST' and r['path']=='/graphql' and r['body']['query']==profile.PR_QUERY for r in self.inputs))
        self.no_token()

    def test_whole_captured_PR_paging_replays_without_any_worker_or_clock_and_consumes_all_raw_blobs(self):
        responses=[page([node(1)],True,'cursor1'),page([node(2)],False)]
        self.answer=lambda request:packet(responses.pop(0))
        with patch.object(transport.subprocess,'Popen',side_effect=self.process):expected=self.reads().pull_requests('fixture/repository')
        self.record.finish('complete',{'exit_code':0},{})
        _,_,result,events,blob,complete=read_record(self.record.root)
        calls=ReplayCalls(events,blob,expected_opened={'kind':'opened',**AUTHORITY})
        backend=transport.ReplayBackend(calls);reader=transport.ProviderReads(backend,'fixture/repository',{profile.MAIN_WORKFLOW:'push'})
        with patch.object(transport.subprocess,'Popen',side_effect=AssertionError('No native worker in replay')),patch.object(transport.time,'monotonic',side_effect=AssertionError('No fresh clock in replay')):
            actual=reader.pull_requests('fixture/repository')
        calls.finish(result['result']);self.assertEqual(actual,expected);self.assertTrue(complete())

    def test_changed_retained_query_or_unused_blob_and_error_response_cannot_gain_success(self):
        self.answer=lambda request:packet(b'permission error',status=403,code='http_403')
        with patch.object(transport.subprocess,'Popen',side_effect=self.process):
            with self.assertRaises(AcquisitionFailure):self.reads().main_reference('fixture/repository')
        self.record.finish('complete',{'exit_code':1},{})
        _,_,result,events,blob,complete=read_record(self.record.root)
        calls=ReplayCalls(events,blob,expected_opened={'kind':'opened',**AUTHORITY})
        reader=transport.ProviderReads(transport.ReplayBackend(calls),'fixture/repository',{profile.MAIN_WORKFLOW:'push'})
        with self.assertRaises(AcquisitionFailure):reader.main_reference('fixture/repository')
        calls.finish(result['result']);self.assertTrue(complete())
        calls=ReplayCalls(events,blob,expected_opened={'kind':'opened',**AUTHORITY})
        with self.assertRaisesRegex(ValueError,'operations_replay_call_changed'):
            calls.call('operations_http',{'method':'GET','path':'/repos/other/repository/git/ref/heads/main','body':None,'wall_budget_seconds':60})
        self.record.blob(b'unreferenced forged addition')
        _,_,_,_,_,complete2=read_record(self.record.root)
        self.assertFalse(complete2())

    def test_impossible_worker_success_is_an_incomplete_capture(self):
        self.answer=lambda request:{'status':200,'native_code':None,'body_b64':None}
        with patch.object(transport.subprocess,'Popen',side_effect=self.process):
            with self.assertRaisesRegex(RuntimeError,'operations_http_worker_success_invalid'):self.reads().main_reference('fixture/repository')
        self.assertTrue(self.record.capture_incomplete)

    def test_PR_cap_returns_exactly_1000_and_graph_errors_or_repeated_cursors_never_become_empty_success(self):
        def response(request):
            number=len(self.inputs)-1
            return packet(page([node(i+1) for i in range(number*100,number*100+100)],True,'c'+str(number)))
        self.answer=response
        with patch.object(transport.subprocess,'Popen',side_effect=self.process):value=self.reads().pull_requests('fixture/repository')
        self.assertEqual(len(value),1000);self.assertEqual(len(self.inputs),10)
        self.answer=lambda request:packet({'errors':[{'message':'access unavailable'}],'data':None})
        with patch.object(transport.subprocess,'Popen',side_effect=self.process):
            with self.assertRaises(AcquisitionFailure):self.reads().pull_requests('fixture/repository')
        self.answer=lambda request:packet(page([],True,'same'))
        with patch.object(transport.subprocess,'Popen',side_effect=self.process):
            with self.assertRaises(AcquisitionFailure) as error:self.reads().pull_requests('fixture/repository')
        self.assertEqual(error.exception.family,'CalledProcessError')

    def test_original_author_map_and_nanosecond_timestamp_serialization(self):
        self.assertEqual(profile.legacy_pull_request(node(1,author=None))['author'],{'is_bot':True,'login':'app/'})
        self.assertEqual(profile.legacy_pull_request(node(1,author={'id':'U','login':'a','name':None}))['author'],{'id':'U','is_bot':False,'login':'a','name':''})
        self.assertEqual(profile.legacy_created_at('2026-11-20T00:00:00.123456789+00:00'),'2026-11-20T00:00:00.123456789Z')
        self.assertEqual(profile.legacy_created_at('2026-11-20T00:00:00.120000000-00:00'),'2026-11-20T00:00:00.12Z')
        for bad in (node(True),node(1,createdAt='bad'),node(1,isDraft=None),{}):
            with self.subTest(bad=bad),self.assertRaises(ValueError):profile.legacy_pull_request(bad)

    def test_worker_contract_error_is_incomplete_instead_of_a_missing_provider_fact(self):
        self.answer=lambda request:{'status':None,'native_code':'invalid_native_response_or_request','body_b64':None,'exception_type':'RuntimeError'}
        with patch.object(transport.subprocess,'Popen',side_effect=self.process):
            with self.assertRaisesRegex(RuntimeError,'operations_http_worker_internal_error'):self.reads().main_reference('fixture/repository')
        self.assertTrue(self.record.capture_incomplete)

    def test_real_owned_process_is_killed_at_the_operation_deadline(self):
        backend=transport.NativeBackend(self.record,TOKEN,wall_budget_seconds=0.05)
        real=subprocess.Popen;children=[]
        def sleepy(*args,**kwargs):
            process=real([sys.executable,'-I','-S','-c','import time; time.sleep(10)'],**kwargs);children.append(process);return process
        start=time.monotonic()
        with patch.object(transport.subprocess,'Popen',side_effect=sleepy):
            value=backend.request('GET','/repos/fixture/repository/git/ref/heads/main')
        self.assertLess(time.monotonic()-start,2);self.assertEqual(value['native_code'],'operation_deadline_exceeded')
        self.assertTrue(all(p.poll() is not None for p in children));self.no_token()

    def test_worker_rejects_writes_foreign_paths_and_modified_queries_before_http(self):
        values=[{'method':'DELETE','path':'/repos/fixture/repository','body':None,'token':TOKEN},
                {'method':'GET','path':'//attacker.invalid/data','body':None,'token':TOKEN},
                {'method':'POST','path':'/graphql','body':{'query':'mutation { dangerous }','variables':{}},'token':TOKEN}]
        with patch.object(worker,'build_opener',side_effect=AssertionError('No unadmitted transport')):
            for value in values:
                with self.subTest(value=value),self.assertRaises(ValueError):worker.request(value)

    def test_worker_http_redirect_is_returned_as_a_failure_without_reissuing_credentials(self):
        calls=[]
        class Opener:
            def open(self,request,timeout):
                calls.append(request)
                headers=Message();headers['Location']='https://attacker.invalid/credential-recipient'
                raise HTTPError(request.full_url,302,'redirect',headers,io.BytesIO(b'body'))
        with patch.object(worker,'build_opener',return_value=Opener()):
            value=worker.request({'method':'GET','path':'/repos/fixture/repository/git/ref/heads/main','body':None,'token':TOKEN})
        self.assertEqual(value['status'],302);self.assertEqual(value['native_code'],'http_302');self.assertEqual(len(calls),1)
        self.assertEqual(dict(calls[0].header_items())['Authorization'],'Bearer '+TOKEN)

    def test_actual_loopback_redirect_never_delivers_the_bearer_to_another_origin(self):
        received=[];initial=[]
        class Sink(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                received.append(dict(self.headers));self.send_response(200);self.send_header('Content-Length','0');self.end_headers()
        sink=ThreadingHTTPServer(('127.0.0.1',0),Sink)
        class Redirect(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                initial.append(dict(self.headers));self.send_response(302)
                self.send_header('Location','http://127.0.0.1:'+str(sink.server_port)+'/should-not-be-requested')
                self.send_header('Content-Length','0');self.end_headers()
        origin=ThreadingHTTPServer(('127.0.0.1',0),Redirect)
        threads=[threading.Thread(target=s.serve_forever,daemon=True) for s in (origin,sink)]
        for t in threads:t.start()
        try:
            with patch.object(profile,'API_ROOT','http://127.0.0.1:'+str(origin.server_port)):
                value=worker.request({'method':'GET','path':'/repos/fixture/repository/git/ref/heads/main','body':None,'token':TOKEN})
            self.assertEqual(value['native_code'],'http_302');self.assertEqual(len(initial),1)
            self.assertEqual(initial[0]['Authorization'],'Bearer '+TOKEN);self.assertEqual(received,[])
        finally:
            for server in (origin,sink):server.shutdown();server.server_close()
            for t in threads:t.join(timeout=5)

    def test_native_security_HTTP_mapping_retains_original_report_and_only_translates_exact_codes(self):
        report={'observation':{'api_errors':['repos/owner/repo/branches/main/protection: http_404',
                    'repos/owner/repo/actions/permissions: http_403','unrecognized http_404x']}}
        before=deepcopy(report);mapped=profile.native_security_error_projection(report)
        self.assertEqual(report,before);self.assertEqual(mapped['observation']['api_errors'][0],'repos/owner/repo/branches/main/protection: HTTP 404')
        self.assertTrue(profile.expected_optional_protection_error(mapped['observation']['api_errors'][0]))
        self.assertFalse(profile.expected_optional_protection_error(mapped['observation']['api_errors'][1]))
        self.assertEqual(mapped['observation']['api_errors'][2],'unrecognized http_404x')


if __name__=='__main__':unittest.main()
