"""Real loopback TLS and urllib redirects; this is no vendor-live attestation."""
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json,os,shutil,ssl,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import HTTPSHandler,ProxyHandler,build_opener

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib import sbom_export_application as app
from lib.providers import sbom_export_native as native,sbom_export_profile as profile
import test_v2_sbom_export as oracle


class NativeTLSExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve();self.calls=[];self.pending=1;self.api_redirect=False
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        executable=shutil.which('openssl')
        self.assertIsNotNone(executable,'Pinned validation requires the native OpenSSL tool')
        config=self.base/'openssl.cnf'
        config.write_text('[req]\nprompt=no\ndistinguished_name=dn\nx509_extensions=ext\n[dn]\nCN=127.0.0.1\n[ext]\nsubjectAltName=IP:127.0.0.1\n')
        key=self.base/'temporary-key.pem';cert=self.base/'temporary-cert.pem'
        result=subprocess.run([executable,'req','-x509','-newkey','rsa:2048','-nodes','-days','1','-config',str(config),'-keyout',str(key),'-out',str(cert)],capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'));key.chmod(0o600)
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                owner.calls.append((self.path,{k.lower():v for k,v in self.headers.items()}))
                def respond(code,body=b'',**headers):
                    self.send_response(code)
                    for name,value in headers.items():self.send_header(name,value)
                    self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
                prefix='/repos/'+oracle.REPO
                if self.path==prefix:
                    if owner.api_redirect:return respond(302,Location=owner.origin+'/must-not-receive-api-bearer')
                    return respond(200,json.dumps({'default_branch':'main','visibility':'public'}).encode())
                if self.path==prefix+'/commits/main':return respond(200,json.dumps({'sha':oracle.SHA}).encode())
                if self.path==prefix+'/dependency-graph/sbom/generate-report':
                    return respond(201,json.dumps({'sbom_url':owner.origin+prefix+'/dependency-graph/sbom/fetch-report/'+oracle.ID}).encode())
                if self.path==prefix+'/dependency-graph/sbom/fetch-report/'+oracle.ID:
                    if owner.pending:owner.pending-=1;return respond(202)
                    return respond(302,Location=owner.origin+'/private-download?signature=TLS_TEST_QUERY_ONLY')
                if self.path.startswith('/private-download?'):return respond(302,Location=owner.origin+'/payload?signature=TLS_TEST_QUERY_ONLY')
                if self.path.startswith('/payload?'):return respond(200,json.dumps(oracle.document()).encode())
                return respond(500)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert,key)
        server.socket=context.wrap_socket(server.socket,server_side=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def close():server.shutdown();server.server_close();thread.join(timeout=5)
        self.addCleanup(close)
        self.origin='https://127.0.0.1:'+str(server.server_port)
        client=ssl.create_default_context(cafile=str(cert))
        def real_opener(handler):return build_opener(ProxyHandler({}),HTTPSHandler(context=client),handler)
        self.stack.enter_context(patch.object(profile,'API_ROOT',self.origin))
        self.stack.enter_context(patch.object(native,'DOWNLOAD_HOSTS',native.DOWNLOAD_HOSTS|{'127.0.0.1'}))
        self.stack.enter_context(patch.object(native,'build_opener',side_effect=real_opener))
        self.token=self.base/'token';self.token.write_text('TLS_TEST_BEARER_ONLY');self.token.chmod(0o600)
        self.options={'repository':oracle.REPO,'commit':oracle.SHA,'token_file':self.token,
                      'output_directory':self.base/'exports','state_directory':self.base/'records'}

    def test_real_tls_202_then_302_download_redirect_never_receives_api_bearer(self):
        with patch.object(native.time,'sleep',return_value=None) as sleep:
            report,result,code=app.execute(self.options)
        self.assertEqual(code,0,report);sleep.assert_called_once_with(5)
        self.assertEqual(json.loads((self.base/'exports/sbom.spdx.json').read_bytes()),oracle.document())
        downloads=[headers for path,headers in self.calls if path.startswith(('/private-download?','/payload?'))]
        self.assertEqual(len(downloads),2)
        for headers in downloads:self.assertNotIn('authorization',headers)
        for path,headers in self.calls:
            if path.startswith('/repos/'):
                self.assertEqual(headers.get('authorization'),'Bearer TLS_TEST_BEARER_ONLY')
                self.assertEqual(headers.get('x-github-api-version'),'2026-03-10')
        for path in Path(report['record_root']).rglob('*'):
            if path.is_file():
                self.assertNotIn(b'TLS_TEST_BEARER_ONLY',path.read_bytes())
                self.assertNotIn(b'TLS_TEST_QUERY_ONLY',path.read_bytes())
        with patch.object(native,'build_opener',side_effect=AssertionError('No repeated transport')):
            self.assertTrue(app.inspect(report['record_root'])['retained_declared_replay_consistent'])

    def test_real_api_redirect_is_rejected_before_any_followup_request_or_export(self):
        self.api_redirect=True
        report,result,code=app.execute(self.options)
        self.assertEqual(code,1);self.assertIn('HTTP 302',result['stderr'])
        self.assertEqual(len(self.calls),1);self.assertFalse((self.base/'exports').exists())
        self.assertTrue(app.inspect(report['record_root'])['retained_declared_replay_consistent'])


if __name__=='__main__':unittest.main()
