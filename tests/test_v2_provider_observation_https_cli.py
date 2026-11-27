"""Actual original and registered CLI HTTPS requests against a private local CA."""
from pathlib import Path
from types import SimpleNamespace
from contextlib import redirect_stdout,redirect_stderr
from http.server import HTTPServer,BaseHTTPRequestHandler
import copy,hashlib,io,json,os,shutil,ssl,subprocess,sys,tempfile,threading,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_provider_observation as reference
from lib.providers.transports import Reader,BoundedAudit
from lib.provider_observation_application import PROFILE
from lib.provider_observation_ports import read_record
from test_portable_runtime import OPA


class WholeHTTPSObservationCLI(unittest.TestCase):
    completed_comparisons=[];completed_replays=[];foreign_rejections=[];CLI_calls=0
    def test_actual_original_and_public_CLI_all_three_providers_with_TLS_and_source_free_public_replay(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);base=Path(temporary.name).resolve();certificate=base/'certificate.pem';key=base/'tls-key.pem';token='synthetic-local-HTTPS-token-e1b947';state={};requests=[]
        config=base/'test-CA.cnf';config.write_text('[req]\ndistinguished_name=dn\n[dn]\nCN=localhost\n')
        subprocess.run(['openssl','req','-config',str(config),'-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(certificate),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=IP:127.0.0.1','-addext','basicConstraints=critical,CA:TRUE','-addext','keyUsage=critical,digitalSignature,keyEncipherment,keyCertSign'],check=True,capture_output=True,timeout=30)
        class Handler(BaseHTTPRequestHandler):
            def do_GET(this):
                requests.append({'path':this.path,'method':this.command,'authorization':this.headers.get('Authorization')})
                path=this.path.removeprefix(state['prefix']);value=state['rows'].get(path)
                raw=json.dumps(value).encode();this.send_response(200 if path in state['rows'] else 404);this.send_header('Content-Type','application/json');this.send_header('Content-Length',str(len(raw)));this.end_headers();this.wfile.write(raw)
            def log_message(this,*args):pass
        server=HTTPServer(('127.0.0.1',0),Handler);tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(certificate,key);server.socket=tls.wrap_socket(server.socket,server_side=True);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();origin='https://127.0.0.1:'+str(server.server_port)
        cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')];environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','SSL_CERT_FILE':str(certificate),'NO_PROXY':'127.0.0.1,localhost','no_proxy':'127.0.0.1,localhost'};node=base/'node';foreign=base/'foreign';records=[]
        def call(arguments,expected=0):
            result=subprocess.run([*cli,*map(str,arguments)],capture_output=True,env=environment,timeout=120);type(self).CLI_calls+=1;self.assertEqual(result.returncode,expected,(arguments,result.stdout[-2500:],result.stderr[-2500:]));return result
        try:
            call(['--instance',node,'init','--development','--opa',OPA]);call(['--instance',foreign,'init','--development','--opa',OPA])
            for provider,prefix in [('github',''),('gitlab','/api/v4'),('bitbucket-dc','/rest/api/1.0')]:
                work=base/provider;work.mkdir(mode=0o700);profile=reference.data_profile(provider);profile['scm']['instance']=origin;profile['api_url']=origin+prefix;profile_path=work/'profile.json';profile_path.write_text(json.dumps(profile));profile_path.chmod(0o600);credential=work/'credential';credential.write_text(' '+token+'\n');credential.chmod(0o600);output=work/'output';argv=['reviews','--profile',str(profile_path),'--credential-file',str(credential),'--revision',reference.REV,'--change-id','7','--output-root',str(output)];rows,_=reference.routes(provider);state.update(prefix=prefix,rows=copy.deepcopy(rows));requests.clear()
                _,target=reference.routes(provider)
                if provider=='github':state['rows'][target]['html_url']=origin+'/proposal/7'
                elif provider=='gitlab':state['rows'][target]['web_url']=origin+'/proposal/7'
                else:state['rows'][target]['links']['self'][0]['href']=origin+'/proposal/7'
                functions=reference.original_functions('assurance',{'re':reference.re,'yaml':reference.yaml,'urlsplit':reference.urlsplit,'canonical_digest':reference.canonical_digest,'endpoint':reference.endpoint,'repository_key':reference.repository_key,'valid_id':reference.valid_id,'AccessFailure':reference.AccessFailure,'SCM':reference.SCM,'encoded':reference.encoded,'ROOT':ROOT,'PROVIDERS':{'github','gitlab','bitbucket-dc'},'SHA':reference.re.compile(r'(?:[a-f0-9]{40}|[a-f0-9]{64})\Z')})
                runtime=reference.original_functions('runtime',{'Path':Path,'json':json});program=reference.original_functions('entrypoint',{'argparse':reference.parser_port(argv),'Path':Path,'os':os,'__doc__':'Capture candidate provider review/security observations with a GET-only credential.','Reader':Reader,'BoundedAudit':BoundedAudit,'check_private_file':reference.check_private_file,'read_json':runtime['read_json'],'capture_reviews':functions['capture_reviews'],'capture_security':functions['capture_security'],'atomic_json':reference.atomic_json,'datetime':SimpleNamespace(now=lambda zone:reference.datetime.fromisoformat(reference.AT)),'timezone':reference.timezone,'json':json})
                out,err=io.StringIO(),io.StringIO()
                from unittest.mock import patch
                with patch.dict(os.environ,environment,clear=True),redirect_stdout(out),redirect_stderr(err):returned=program['main']()
                original_files={p.name:(p.read_bytes(),p.stat().st_mode&511) for p in output.iterdir()};original_requests=copy.deepcopy(requests);shutil.rmtree(output);requests.clear()
                receipt=json.loads(call(['--instance',node,'provider-observation','capture','--profile',PROFILE,'--working-directory',work,'--',*argv]).stdout);self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],0);record=Path(receipt['record_root']);_,_,retained,*_=read_record(record);kernel=retained['result']['kernel_result']
                self.assertEqual({p.name:(p.read_bytes(),p.stat().st_mode&511) for p in output.iterdir()},original_files);self.assertEqual(requests,original_requests);self.assertTrue(requests);self.assertTrue(all(row['method']=='GET' and row['authorization']=='Bearer '+token for row in requests));self.assertEqual(kernel['return_value'],returned);self.assertEqual(kernel['stdout'],out.getvalue());self.assertEqual(kernel['stderr'],err.getvalue());self.assertIsNone(kernel['kernel_exception']);self.assertIsNone(kernel['original_exit_signal']);self.assertFalse(kernel['native_extra_cleanup_required'])
                checked=json.loads(call(['--instance',node,'provider-observation','inspect','--record',record]).stdout);rejected=call(['--instance',foreign,'provider-observation','inspect','--record',record],2);self.assertEqual(rejected.stdout,b'');self.foreign_rejections.append(provider)
                for path in record.rglob('*'):
                    if path.is_file():self.assertNotIn(token.encode(),path.read_bytes())
                self.completed_comparisons.append(provider);shutil.rmtree(work);records.append((record,checked,provider))
        finally:server.shutdown();server.server_close();thread.join(timeout=5)
        self.assertFalse(thread.is_alive());key.unlink();certificate.unlink()
        for record,checked,provider in records:
            self.assertEqual(json.loads(call(['provider-observation','replay','--record',record]).stdout),checked);self.completed_replays.append(provider)
        self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused');self.assertEqual(len(records),3)
