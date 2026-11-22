"""Whole original main with real private IO, HTTPS Reader, atomic audit and replay."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr,contextmanager
import ast,copy,errno,hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_provider_observation as reference
from lib.providers.consumer_lifecycle_storage import Record,read_record
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO
from lib.provider_observation_context import execute
from lib.providers.provider_observation_backend import NativeObservationBackend
from lib.provider_observation_backend import ReplayObservationBackend
from lib.provider_observation_reads import reader_type
from lib.providers.provider_observation_assurance import LegacyProviderAssurance
from lib.providers.provider_observation_git import NativeObservationGit
from lib.provider_observation_git import ReplayObservationGit
from lib.providers.transports import Reader,BoundedAudit
from lib.providers.retained_argparse import capture_context
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from test_v2_provider_observation_reads import Response

TOKEN='synthetic-whole-observation-credential-fd4827'


class WholeRecordedObservation(unittest.TestCase):
    completed_comparisons=[]
    completed_replays=[]
    def setUp(self):
        self.world=reference.WholeProviderObservation();self.world.setUp();self.addCleanup(self.world.doCleanups);self.work=self.world.base/'work';self.work.mkdir(mode=0o700);self.records=self.world.base/'records';self.records.mkdir(mode=0o700)
    def arguments(self,provider,action='reviews',case='normal'):
        if self.work.exists():shutil.rmtree(self.work)
        self.work.mkdir(mode=0o700);config=reference.data_profile(provider)
        if case=='bad-endpoint':config['api_url']='http://insecure.example.test'
        if case=='extra-profile':config['extra']=True
        if case=='trailing-api':config['api_url']+='/'
        profile=self.work/'profile.json';profile.write_text(json.dumps(config));profile.chmod(0o644 if case=='public-profile' else 0o600);credential=self.work/'credential';credential.write_text('  '+TOKEN+'\n');credential.chmod(0o600)
        args=[action,'--profile',str(profile),'--credential-file',str(credential),'--revision',reference.REV,'--output-root',str(self.work/'output')]
        if action=='reviews' and case!='missing-change':args+=['--change-id','7']
        if case=='existing-output':(self.work/'output').mkdir(mode=0o700)
        if case=='help':args=['--help']
        if case=='missing-arguments':args=['reviews']
        return config,args
    def factory(self,root,backend,emit_stderr):
        kind=NativeObservationGit if isinstance(backend,NativeObservationBackend) else ReplayObservationGit
        return LegacyProviderAssurance(root,process=kind(backend.owner,root,emit_stderr=emit_stderr),loader=None)
    def capture(self,provider='github',action='reviews',case='normal'):
        results=[];native_capture=None
        for side in ('original','recorded'):
            config,args=self.arguments(provider,action,case);rows,target=reference.routes(provider);calls=[]
            class Opener:
                def open(this,request,*,timeout):
                    self.assertEqual(request.get_method(),'GET');self.assertEqual(request.get_header('Authorization'),'Bearer '+TOKEN);url=request.full_url;prefix=config['api_url'].rstrip('/');self.assertTrue(url.startswith(prefix));path=url[len(prefix):];calls.append(path)
                    if case=='get-error' and 'reviews?' in path:raise HTTPError(url,403,'Controlled fixture denial',{},None)
                    if case=='security-api-error' and path.endswith('/branches/main/protection'):raise HTTPError(url,403,'Controlled fixture denial',{},None)
                    value=copy.deepcopy(rows[path])
                    if case=='review-moved' and path==target and calls.count(path)>1:
                        if provider=='github':value['head']['sha']='b'*40
                        elif provider=='gitlab':value['sha']='b'*40
                        else:value['fromRef']['latestCommit']='b'*40
                    return Response(json.dumps(value).encode())
            def opener(*a):return Opener()
            @contextmanager
            def native_ports():
                with patch('lib.providers.transports.build_opener',side_effect=opener):
                    if case not in ('candidate-replace-error','audit-replace-error','both-replace-error'):
                        yield;return
                    replace=os.replace
                    def failure(source,target,*args,**options):
                        selected=Path(target).name
                        if (selected=='candidate.json' and case in ('candidate-replace-error','both-replace-error')
                                or selected=='native-capture.json' and case in ('audit-replace-error','both-replace-error')):
                            raise OSError(errno.EIO,'Controlled atomic replace failure',str(source),None,str(target))
                        return replace(source,target,*args,**options)
                    with patch('tempfile._get_candidate_names',return_value=iter(['first001','second02'])),patch('os.replace',side_effect=failure):yield
            if side=='original':
                model=reference.original_functions('assurance',{'re':reference.re,'yaml':reference.yaml,'urlsplit':reference.urlsplit,'canonical_digest':reference.canonical_digest,'endpoint':reference.endpoint,'repository_key':reference.repository_key,'valid_id':reference.valid_id,'AccessFailure':reference.AccessFailure,'SCM':reference.SCM,'encoded':reference.encoded,'ROOT':self.world.source,'subprocess':subprocess,'importlib':getattr(self,'original_loader',None),'PROVIDERS':{'github','gitlab','bitbucket-dc'},'SHA':reference.re.compile(r'(?:[a-f0-9]{40}|[a-f0-9]{64})\Z')})
                runtime=reference.original_functions('runtime',{'json':json,'Path':Path})
                clock=SimpleNamespace(now=lambda zone:reference.datetime.fromisoformat(reference.AT))
                namespace=reference.original_functions('entrypoint',{'argparse':reference.parser_port(args),'Path':Path,'os':os,'__doc__':'Capture candidate provider review/security observations with a GET-only credential.','Reader':Reader,'BoundedAudit':BoundedAudit,'check_private_file':reference.check_private_file,'read_json':runtime['read_json'],'capture_reviews':model['capture_reviews'],'capture_security':model['capture_security'],'atomic_json':reference.atomic_json,'datetime':clock,'timezone':reference.timezone,'json':json})
                out,err=io.StringIO(),io.StringIO();value=error=signal=None;code=0
                with native_ports(),redirect_stdout(out),redirect_stderr(err):
                    try:value=namespace['main']()
                    except SystemExit as caught:code=caught.code;signal={'type':'SystemExit','value':caught.code}
                    except Exception as caught:code=1;error={'type':type(caught).__name__,'message':str(caught)}
                result={'exit_code':code,'return_value':value,'kernel_exception':error,'original_exit_signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue()}
            else:
                record=Record(self.records,{'provider':provider,'argv':args},{'development_complete_context_only':True});record.append({'kind':'execution-intent'});owner=NativeIO(record,mode='selected-files',cwd=str(self.work),private_state=self.records,product_root=ROOT);protected=(str(self.records),str(ROOT),str(self.world.source));backend=NativeObservationBackend(owner,protected_roots=protected,clock=lambda:reference.AT);parser=capture_context()
                with native_ports():result=execute(str(self.world.source),str(self.work),args,owner,backend=backend,reader_type=reader_type(backend.reads,Reader),audit_type=BoundedAudit,assurance_factory=self.factory,parser_context=parser)
                resources=backend.release_resources();self.assertFalse(record.capture_incomplete,resources);record.finish('complete',result,{})
                native_capture=(record,result,args,parser,protected,backend)
                result={k:v for k,v in result.items() if k!='stderr_parts'}
                for p in record.root.rglob('*'):
                    if p.is_file():self.assertNotIn(TOKEN.encode(),p.read_bytes())
            files={str(p.relative_to(self.work)):(p.read_bytes(),p.stat().st_mode&511) for p in self.work.rglob('*') if p.is_file() and p.name!='credential'}
            results.append({'result':result,'files':files,'GETs':calls})
        self.assertEqual(results[0],results[1],(provider,action,case));self.completed_comparisons.append((provider,action,case));return native_capture
    def replay(self,captured):
        record,result,args,parser,protected,backend=captured;_,_,_,events,blob,closed=read_record(record.root);owner=ReplayIO(events,blob,'selected-files',str(self.work));pure=ReplayObservationBackend(owner,protected_roots=protected,reader_url=Reader.url);moved=self.world.base.with_name(self.world.base.name+'-absent');cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};self.world.base.rename(moved)
        # Replay still reads retained blobs; the source/credential/output roots
        # and every selected native port are absent or unavailable.
        consumed=set()
        def retained(ref):
            raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);consumed.add(ref['sha256']);return raw
        owner.blob=retained;pure.reads.blob=owner.blob
        try:
            with patch('os.open',side_effect=AssertionError('No replay native file')),patch('os.stat',side_effect=AssertionError('No replay stat')),patch('subprocess.Popen',side_effect=AssertionError('No replay program')),patch('lib.providers.transports.build_opener',side_effect=AssertionError('No replay HTTP')):
                actual=execute(str(self.world.source),str(self.work),args,owner,backend=pure,reader_type=reader_type(pure.reads,Reader),audit_type=BoundedAudit,assurance_factory=self.factory,parser_context=parser);pure.finish();self.assertEqual(actual,result)
        finally:moved.rename(self.world.base)
        self.assertEqual(consumed,set(cache),'Replay must consume every actual retained blob')
        for name in consumed:blob({'sha256':name,'bytes':len(cache[name])})
        self.assertTrue(closed());self.completed_replays.append(True)
    def test_whole_original_main_all_three_review_providers_native_effects_and_source_free_replay(self):
        for provider in ('github','gitlab','bitbucket-dc'):
            with self.subTest(provider=provider):self.replay(self.capture(provider))
        self.replay(self.capture(case='trailing-api'))
    def test_whole_original_non_GitHub_security_models_native_clock_and_replay(self):
        for provider in ('gitlab','bitbucket-dc'):
            with self.subTest(provider=provider):self.replay(self.capture(provider,'security'))
    def test_full_original_pre_output_errors_and_existing_output_are_replayed(self):
        for case in ('extra-profile','public-profile','existing-output','bad-endpoint','help','missing-arguments'):
            with self.subTest(case=case):self.replay(self.capture(case=case))
    def test_original_failed_GET_changed_review_and_missing_change_keep_the_whole_finally_audit(self):
        for case in ('get-error','review-moved','missing-change'):
            with self.subTest(case=case):self.replay(self.capture(case=case))
    def test_candidate_audit_and_both_atomic_failures_keep_original_partial_files_and_error(self):
        for case in ('candidate-replace-error','audit-replace-error','both-replace-error'):
            with self.subTest(case=case):self.replay(self.capture(case=case))
    def test_whole_original_GitHub_security_mismatched_and_dirty_own_source_with_actual_Git_and_inert_replay(self):
        root=self.world.source
        subprocess.check_call(['git','init','--quiet'],cwd=root)
        subprocess.check_call(['git','add','.'],cwd=root)
        subprocess.check_call(['git','-c','user.name=Fixture','-c','user.email=fixture@example.test','-c','commit.gpgsign=false','commit','--quiet','-m','Own-source fixture'],cwd=root)
        self.replay(self.capture('github','security','installed-revision-mismatch'))
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        (root/'scripts').mkdir();(root/'scripts/dirty.txt').write_text('Explicit dirty own source\n')
        with patch.object(reference,'REV',revision):self.replay(self.capture('github','security','dirty-own-source'))
