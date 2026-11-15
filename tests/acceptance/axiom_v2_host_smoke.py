"""Private synthetic V2 installed-host acceptance; no native API calls or authority."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time,http.client
prefix=Path(sys.argv[1]).resolve();output=Path(sys.argv[2]);source=prefix/'package/source'
sys.path.insert(0,str(source/'scripts'))
from lib.portable.runtime import baseline,source_digest,prepare_evidence,evaluate,gate
from lib.v2_distribution import verify_source
from lib.portable.contracts import canonical_digest
verify_source(source)
settings=json.loads((prefix/'instance/instance.json').read_text());port=settings['port']
private_key=json.loads((prefix/'instance/workbench-key.json').read_text())['key']
assert (prefix.stat().st_mode&0o077)==0
assert subprocess.check_output([str(prefix/'axiom-v2'),'--version'],text=True).strip()=='2.0.0-candidate'
check=json.loads(subprocess.check_output([str(prefix/'axiom-v2'),'check'],text=True));assert check['passed']
status=json.loads(subprocess.check_output([str(prefix/'axiom-v2'),'collector','status'],text=True))
assert status['paused'] and not status['publisher_active'] and status['counts']=={}
# Deny all non-loopback sockets in this test process, in addition to no provider credentials.
def audit(event,args):
    if event=='socket.connect' and args[1][0] not in ('127.0.0.1','::1'):
        raise AssertionError('native networking forbidden in synthetic host test')
sys.addaudithook(audit)
fixture=prefix/'smoke-fixture';fixture.mkdir(mode=0o700)
artifact=b'explicitly synthetic installed-host parity fixture\n';(fixture/'artifact.bin').write_bytes(artifact)
sha=hashlib.sha256(artifact).hexdigest()
(fixture/'sbom.json').write_text(json.dumps({'bomFormat':'CycloneDX','specVersion':'1.5','components':[],
    'metadata':{'component':{'type':'application','name':'synthetic-host-smoke','hashes':[{'alg':'SHA-256','content':sha}]}}}))
results={}
for ci,scm in [('github-actions','github'),('gitlab-ci','gitlab'),('bamboo','bitbucket-dc')]:
    context={'schema_version':'1.0.0','scm':{'provider':scm,'instance':'https://scm.example','native_id':'42',
      'path':'group/repo','url':'https://scm.example/group/repo'},
      'ci':{'provider':ci,'instance':'https://ci.example','run_id':'PROJ-PLAN-42' if ci=='bamboo' else '42',
        'job_id':'PLAN-JOB' if ci=='bamboo' else 'job-42','attempt':1,'event':'push','native_reference':'synthetic-installed-host'},
      'revision':{'tested':'a'*40,'source':'a'*40,'target':None,'branch':'trunk','mode':'branch'},'change_request':None,
      'capabilities':{name:{'status':'available','source':'synthetic_installed_host_fixture','value':value} for name,value in
        [('direct_push_allowed',False),('protected_branch',True),('review_required',True)]},'synthetic':True,
      'governance':{'baseline_id':baseline()[1]['id'],'baseline_digest':baseline()[1]['digest'],'domain':'devsecops',
        'scope':'pipeline-l1','runtime_version':'1.0.0','adapter_version':'1.0.0','runtime_source_digest':source_digest()}}
    for case in ('pass','critical-finding','missing-fact'):
        ctx=json.loads(json.dumps(context));scan={'scanner':'installed-host-fixture-scanner','max_severity':'none','findings':[],'artifact_sha256':sha}
        if case=='critical-finding':scan.update(max_severity='critical',findings=[{'id':'synthetic-critical','severity':'critical'}])
        if case=='missing-fact':ctx['capabilities']['direct_push_allowed']={'status':'missing','source':'synthetic_missing','value':None}
        (fixture/'scan.json').write_text(json.dumps(scan))
        payload,subjects=prepare_evidence(ctx,fixture,'artifact.bin','sbom.json','scan.json')
        result=evaluate(ctx,payload,subjects,opa=prefix/'venv/bin/opa',at='2026-11-15T12:00:00Z')
        expected={'pass':('complete','pass',0),'critical-finding':('complete','fail',0),'missing-fact':('incomplete','not_evaluated',2)}[case]
        assert (result['execution'],result['decision'],gate(result))==expected
        assert not result['full_baseline_assessment'] and result['evidence_trust']=='unverified'
        results[ci+'/'+case]={k:result[k] for k in ('execution','decision','checks','controls','evidence_trust','full_baseline_assessment')}
for case in ('pass','critical-finding','missing-fact'):
    assert results['github-actions/'+case]==results['gitlab-ci/'+case]==results['bamboo/'+case]
log=(prefix/'workbench-smoke.log').open('wb')
server=subprocess.Popen([str(prefix/'axiom-v2'),'workbench'],stdout=log,stderr=subprocess.STDOUT)
try:
    def request(method,path,payload=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',port,timeout=10)
        h={'Origin':'http://127.0.0.1:'+str(port),'Content-Type':'application/json',**(headers or {})}
        c.request(method,path,json.dumps(payload).encode() if payload is not None else None,h)
        r=c.getresponse();data=r.read();status=r.status;headers=dict(r.getheaders());c.close()
        return status,headers,json.loads(data) if data.startswith(b'{') else data
    for attempt in range(80):
        if server.poll() is not None:raise AssertionError('installed Workbench startup failed')
        try:
            if request('GET','/')[0]==200:break
        except OSError:time.sleep(.1)
    else:raise AssertionError('installed Workbench did not listen')
    assert request('GET','/api/state')[0]==401
    code,headers,body=request('POST','/api/login',{'key':private_key});assert code==200 and body['signed_in']
    cookie=headers['Set-Cookie'].split(';',1)[0]
    code,_,state=request('GET','/api/state',headers={'Cookie':cookie});assert code==200
    assert request('POST','/api/logout',{},headers={'Cookie':cookie})[0]==403
    assert request('POST','/api/logout',{},headers={'Cookie':cookie,'X-CSRF-Token':state['csrf']})[0]==200
    assert request('GET','/api/state',headers={'Cookie':cookie})[0]==401
finally:
    server.terminate();server.wait(timeout=15);log.close()
assert private_key not in (prefix/'workbench-smoke.log').read_text()
# Restart the same immutable instance after a real HTTP session has ended.
assert json.loads(subprocess.check_output([str(prefix/'axiom-v2'),'collector','status'],text=True))['paused']
# A restored retired script must fail before application startup.
rogue=source/'scripts/v1-restored.py';rogue.write_text('print("retired fixture")\n')
try:
    denied=subprocess.run([str(prefix/'axiom-v2'),'collector','status'],capture_output=True,text=True)
    assert denied.returncode==2 and 'undeclared_v2_runtime_file' in denied.stderr
finally:rogue.unlink()
receipt={'schema_version':2,'synthetic':True,'native_provider_acceptance':False,
    'source_revision':settings['source_revision'],'runtime_source_digest':source_digest(),
    'node_id':settings['node_id'],'opa_sha256':settings['opa_sha256'],'http_auth_smoke':True,
    'paused_empty_collector':True,'restart_smoke':True,'retired_script_rejected':True,
    'business_digest':canonical_digest(results),'results':results}
output.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n');output.chmod(0o600)
print(json.dumps({k:v for k,v in receipt.items() if k!='results'},sort_keys=True))
