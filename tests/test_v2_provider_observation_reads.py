"""Actual original urllib GETs and source-free replay with no retained token."""
from pathlib import Path
from unittest.mock import patch
import copy,hashlib,io,json,os,shutil,sys,tempfile,unittest
from urllib.error import HTTPError,URLError
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.provider_observation_context import SecretText
from lib.provider_observation_reads import reader_type,ReplayObservationReads
from lib.providers.provider_observation_reads import NativeObservationReads
from lib.providers.transports import Reader
from lib.providers.consumer_lifecycle_storage import Record,read_record
from lib.provider_errors import AccessFailure
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError

SECRET='synthetic-provider-token-not-for-any-service-8b62b6'
BASE='https://api.example.test/v4'


class Cursor:
    def __init__(self,events):self.events,self.position=events,0
    def row(self):
        if self.position>=len(self.events):raise IntegrityError('test_read_event_missing')
        value=self.events[self.position];self.position+=1;return value


class Response(io.BytesIO):
    def __init__(self,raw):super().__init__(raw);self.headers={}


class ObservationReadPorts(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name).resolve();self.state=self.base/'records';self.state.mkdir(mode=0o700);self.calls=[]
    def capture(self,operation,*,replies=None,open_failure=False,opener_failure=False,budget=150):
        record=Record(self.state,{'profile':'private-read-port-only'},{'no_whole_operator_acceptance':True});requests=[];rows=list(replies or [b'{"ok":true}'])
        class Opener:
            def open(this,request,*,timeout):
                requests.append({'method':request.get_method(),'url':request.full_url,'authorization':request.get_header('Authorization'),'timeout':timeout})
                if open_failure:raise HTTPError(request.full_url,403,'Denied',{},None)
                value=rows.pop(0)
                if isinstance(value,Exception):raise value
                return Response(value)
        def resolve(cap):self.assertEqual(cap.identifier,'credential-1');return '  '+SECRET+'\n'
        port=NativeObservationReads(record,resolve);cls=reader_type(port,Reader)
        def opener(*args):
            if opener_failure:raise OSError('Controlled opener initialization failed')
            return Opener()
        returned=error=None
        with patch('lib.providers.transports.build_opener',side_effect=opener):
            reader=cls(BASE,SecretText('credential-1').strip(),budget=budget)
            try:returned=operation(reader)
            except AccessFailure as caught:error={'code':caught.code,'retryable':caught.retryable,'delay':caught.delay}
            except ValueError as caught:error={'type':'ValueError','message':str(caught)}
        record.finish('incomplete' if record.capture_incomplete else 'complete',{'exit_code':0 if error is None else 1},{});_,_,_,events,blob,closed=read_record(record.root)
        # Retained closure is exercised later by replay, not by this scan.
        for path in record.root.rglob('*'):
            if path.is_file():self.assertNotIn(SECRET.encode(),path.read_bytes())
        self.calls=requests;return record,port,reader,returned,error,events,blob,closed
    def replay(self,captured,operation):
        record,port,reader,returned,error,events,blob,closed=captured;cursor=Cursor(events);cursor.position=1;pure=ReplayObservationReads(cursor,blob,reader_url=Reader.url);cls=reader_type(pure,Reader)
        moved=self.base.with_name(self.base.name+'-unavailable');raw_blobs={p.name:p.read_bytes() for p in record.blobs.iterdir()};self.base.rename(moved)
        def retained(ref):return raw_blobs[ref['sha256']]
        pure.blob=retained
        try:
            with patch('os.open',side_effect=AssertionError('No filesystem replay')),patch('lib.providers.transports.build_opener',side_effect=AssertionError('No HTTP replay')),patch('subprocess.Popen',side_effect=AssertionError('No program replay')):
                replayed=cls(BASE,SecretText('credential-1').strip(),budget=reader.budget);actual=None;failure=None
                try:actual=operation(replayed)
                except AccessFailure as caught:failure={'code':caught.code,'retryable':caught.retryable,'delay':caught.delay}
                except ValueError as caught:failure={'type':'ValueError','message':str(caught)}
                self.assertEqual(cursor.position,len(events)-1)
                self.assertEqual(failure,error);self.assertEqual(actual,returned);self.assertEqual(replayed.calls,reader.calls)
        finally:moved.rename(self.base)
        # Mark every actual response blob consumed; the event closure itself
        # contains no metadata blobs in this deliberately small protocol.
        for name,raw in raw_blobs.items():self.assertEqual(blob({'sha256':name,'bytes':len(raw)}),raw)
        self.assertTrue(closed());return pure
    def test_actual_original_Reader_GET_header_and_all_json_values_replay_without_secret_or_sources(self):
        c=self.capture(lambda r:r.get('/one'),replies=[b'{"items":[true,null,1,-0.0,"Gr\\u00f6\\u00dfe"],"nested":{}}']);self.assertEqual(c[3]['items'][-1],'Größe');self.assertEqual(self.calls,[{'method':'GET','url':BASE+'/one','authorization':'Bearer '+SECRET,'timeout':30}]);self.replay(c,lambda r:r.get('/one'))
    def test_original_Reader_pages_and_exact_budget_exhaustion_replay(self):
        first=json.dumps(list(range(100))).encode();c=self.capture(lambda r:list(r.pages('/items',limit=2)),replies=[first,b'[101]']);self.assertEqual(len(c[3]),101);self.assertEqual([x['url'] for x in self.calls],[BASE+'/items?per_page=100&page=1',BASE+'/items?per_page=100&page=2']);self.replay(c,lambda r:list(r.pages('/items',limit=2)))
        c=self.capture(lambda r:[r.get('/one'),r.get('/two')],budget=1);self.assertEqual(c[4]['code'],'request_budget_exhausted');self.assertEqual(len(self.calls),1);self.replay(c,lambda r:[r.get('/one'),r.get('/two')])
    def test_native_HTTP_failure_and_pre_URL_opener_failure_keep_exact_original_calls(self):
        c=self.capture(lambda r:r.get('/one'),open_failure=True);self.assertEqual(c[4],{'code':'http_403','retryable':False,'delay':60});self.replay(c,lambda r:r.get('/one'))
        c=self.capture(lambda r:r.get('/one'),opener_failure=True);self.assertEqual(c[2].calls,0);self.assertEqual(c[4]['code'],'provider_read_failed');self.replay(c,lambda r:r.get('/one'))
    def test_invalid_path_and_invalid_page_use_original_reader_decisions(self):
        c=self.capture(lambda r:r.get('//cross-origin'));self.assertEqual(self.calls,[]);self.assertEqual(c[4]['code'],'provider_read_failed');self.replay(c,lambda r:r.get('//cross-origin'))
        c=self.capture(lambda r:list(r.pages('/items')),replies=[b'{}']);self.assertEqual(c[4],{'type':'ValueError','message':'invalid_provider_page'});self.replay(c,lambda r:list(r.pages('/items')))
    def test_token_reflection_never_enters_record_and_stops_further_GETs(self):
        record=Record(self.state,{'prototype':True},{'private':True});port=NativeObservationReads(record,lambda cap:SECRET);reader=reader_type(port,Reader)(BASE,SecretText('credential-1'));opened=[]
        class Opener:
            def open(this,*args,**kw):opened.append(True);return Response(json.dumps({'reflection':SECRET}).encode())
        with patch('lib.providers.transports.build_opener',return_value=Opener()):
            with self.assertRaises(InputAdmissionError):reader.get('/one')
            with self.assertRaises(InputAdmissionError):reader.get('/again')
        self.assertEqual(len(opened),1);self.assertTrue(record.capture_incomplete)
        for path in record.root.rglob('*'):
            if path.is_file():self.assertNotIn(SECRET.encode(),path.read_bytes())
    def test_completion_loss_after_real_GET_has_no_retry_or_original_completion(self):
        record=Record(self.state,{'prototype':True},{'private':True});port=NativeObservationReads(record,lambda cap:SECRET);reader=reader_type(port,Reader)(BASE,SecretText('credential-1'));append=record.append;called=[]
        def lose(row):
            if row.get('kind')=='provider-observation-read-returned':raise OSError('Controlled completion loss')
            append(row)
        record.append=lose
        class Opener:
            def open(this,*args,**kw):called.append(True);return Response(b'{"ok":true}')
        with patch('lib.providers.transports.build_opener',return_value=Opener()):
            with self.assertRaises(InputAdmissionError):reader.get('/one')
            with self.assertRaises(InputAdmissionError):reader.get('/again')
        self.assertEqual(len(called),1);self.assertTrue(record.capture_incomplete)
        with self.assertRaises(ValueError):record.finish('complete',{'exit_code':0},{})
    def test_intent_loss_prevents_the_first_GET_and_all_later_attempts(self):
        record=Record(self.state,{'prototype':True},{'private':True});port=NativeObservationReads(record,lambda cap:SECRET);reader=reader_type(port,Reader)(BASE,SecretText('credential-1'))
        def unavailable(row):raise OSError('Controlled intent persistence failure')
        record.append=unavailable
        with patch('lib.providers.transports.build_opener',side_effect=AssertionError('No HTTP without durable intent')):
            with self.assertRaises(InputAdmissionError):reader.get('/one')
            with self.assertRaises(InputAdmissionError):reader.get('/two')
        self.assertTrue(record.capture_incomplete)
    def test_original_rate_limit_JSON_failure_and_null_response_are_retained(self):
        failure=HTTPError(BASE+'/one',429,'Rate limit',{'Retry-After':'7'},None)
        c=self.capture(lambda r:r.get('/one'),replies=[failure]);self.assertEqual(c[4],{'code':'rate_limited','retryable':True,'delay':7.0});self.replay(c,lambda r:r.get('/one'))
        c=self.capture(lambda r:r.get('/one'),replies=[b'{invalid']);self.assertEqual(c[4]['code'],'provider_read_failed');self.replay(c,lambda r:r.get('/one'))
        c=self.capture(lambda r:r.get('/one'),replies=[b'null']);self.assertIsNone(c[3]);self.assertIsNone(c[4]);self.replay(c,lambda r:r.get('/one'))
        operation=lambda r:json.dumps(r.get('/one'),sort_keys=True)
        c=self.capture(operation,replies=[b'{"nonfinite":NaN,"limit":Infinity}']);self.assertIn('NaN',c[3]);self.replay(c,operation)
    def test_release_revokes_native_credential_without_another_request(self):
        c=self.capture(lambda r:r.get('/one'));record,port,reader,*_=c;port.release_credentials();self.assertTrue(all(x['native'].token=='' for x in port.sessions.values()))
        with patch('lib.providers.transports.build_opener',side_effect=AssertionError('No GET after release')),self.assertRaisesRegex(InputAdmissionError,'session_closed'):reader.get('/again')
        with patch('lib.providers.transports.build_opener',side_effect=AssertionError('No unrecorded download')),self.assertRaisesRegex(InputAdmissionError,'GET_only'):
            reader.download('/unrecorded',self.base/'never-created')
        self.assertFalse((self.base/'never-created').exists())
    def test_forged_counters_types_credential_and_missing_response_fail_closed(self):
        c=self.capture(lambda r:r.get('/one'));events=c[5];cache={p.name:p.read_bytes() for p in c[0].blobs.iterdir()}
        for kind in ('boolean-operation','boolean-calls','credential','counter','missing-response'):
            with self.subTest(kind=kind):
                changed=copy.deepcopy(events);get=next(i for i,x in enumerate(changed) if x.get('action')=='get')
                if kind=='boolean-operation':changed[1]['operation']=True
                elif kind=='boolean-calls':changed[2]['result']['calls']=False
                elif kind=='credential':changed[1]['arguments']['credential']['identifier']='credential-2'
                elif kind=='counter':changed[get+1]['result']['calls_after']=99
                else:changed[get+1]['result']['response']={'sha256':'0'*64,'bytes':1}
                cursor=Cursor(changed);cursor.position=1;pure=ReplayObservationReads(cursor,lambda ref:cache[ref['sha256']],reader_url=Reader.url);cls=reader_type(pure,Reader)
                with self.assertRaises((IntegrityError,InputAdmissionError)):
                    reader=cls(BASE,SecretText('credential-1').strip(),budget=150);reader.get('/one')
                previous=cursor.position
                with self.assertRaises((IntegrityError,InputAdmissionError)):pure.get(None,'/again')
                self.assertEqual(cursor.position,previous)
