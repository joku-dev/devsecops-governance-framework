"""Isolated full-validator input mutations using unmodified frozen V1 producers.

No response is live or independently authenticated. The helper writes only the
caller's temporary fixture and a fake read-only provider outside that source.
"""
from pathlib import Path
import base64,json,os,subprocess,sys

GENERATE='''from pathlib import Path
import runpy
import lib.governance_lifecycle.operating_acceptance as op
from lib.governance_lifecycle.contracts import ROOT
for name in ('generate_lifecycle_pilot_validation.py','generate_personal_channel_evidence.py','generate_lifecycle_pilot_actions.py'):
 runpy.run_path(str(ROOT/'scripts'/name),run_name='__main__')
op.generate()
import generate_governance_lifecycle_overview as overview
import generate_governance_lifecycle_viewer as viewer
from lib.governance_lifecycle.adapter import strict_json
from lib.governance_lifecycle.store import load_transactions
from validate_governance_lifecycle_ledger import LEDGER_PATHS
old=strict_json((ROOT/overview.OUTPUT).read_bytes())['as_of']
as_of=max([old,'2026-09-13T17:00:00Z',*[row['recorded_at'] for name in LEDGER_PATHS for row in load_transactions(ROOT/name)]])
overview.generate(as_of=as_of);viewer.generate()
'''
FAKE='''import base64,json,sys
from pathlib import Path
root=Path(__file__).parent;args=sys.argv[1:]
assert args[:5]==['api','--hostname','github.com','--method','GET'] and len(args) in (6,8)
if len(args)==8:assert args[6:]==['-H','Accept: application/vnd.github.raw+json']
endpoint=args[5];responses=json.loads((root/'responses.json').read_bytes())
with (root/'calls.jsonl').open('a') as stream:stream.write(json.dumps(endpoint)+'\\n')
sys.stderr.buffer.write(b'opaque\\xffwhole-validator-provider\\r\\n');sys.stderr.buffer.flush()
sys.stdout.buffer.write(base64.b64decode(responses[endpoint],validate=True))
'''

def prepare_tools(root,tools):
    responses={}
    for path in sorted((root/'governance/lifecycle/live-validation/transactions').glob('*.json')):
        receipt=json.loads(path.read_bytes());capture={k:base64.b64decode(v,validate=True) for k,v in receipt['capture'].items()};repo=json.loads(capture['repository.json']);run=json.loads(capture['run-before.json']);artifact=json.loads(capture['artifact-before.json']);endpoint='repos/'+repo['full_name'];run_url=endpoint+'/actions/runs/'+str(run['id']);artifact_url=endpoint+'/actions/artifacts/'+str(artifact['id'])
        responses.update({endpoint:capture['repository.json'],run_url:capture['run-before.json'],endpoint+'/actions/workflows/'+str(run['workflow_id']):capture['workflow.json'],artifact_url:capture['artifact-before.json'],artifact_url+'/zip':capture['artifact.zip']})
        for name,raw in capture.items():
            if name.startswith('artifacts-page-'):responses[run_url+'/artifacts?per_page=100&page='+name.removeprefix('artifacts-page-').removesuffix('.json')]=raw
            elif name.startswith('producer/'):responses[endpoint+'/contents/'+name.removeprefix('producer/')+'?ref='+run['head_sha']]=raw
    for folder in ('lifecycle-personal-channel','lifecycle-operating-acceptance'):
        for path in sorted((root/'generated/reports'/folder).glob('*.json')):
            snapshot=json.loads(path.read_bytes());request=snapshot['request'];endpoint=f"repos/{request['repository_id']}/issues/{request['discussion_number']}";responses[endpoint]=snapshot['issue_response'].encode()
            for page,raw in enumerate(snapshot['comment_pages_after'],1):responses[endpoint+f'/comments?per_page=100&page={page}']=raw.encode()
    tools.mkdir(mode=0o700);(tools/'responses.json').write_text(json.dumps({k:base64.b64encode(v).decode() for k,v in responses.items()}));(tools/'gh').write_text('#!'+sys.executable+'\n'+FAKE);(tools/'gh').chmod(0o700)
    return responses

def run(root,tools,code,*arguments):
    env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','LD_','DYLD_'))};env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(root/'scripts'),PATH=str(tools)+os.pathsep+env.get('PATH',''),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1')
    result=subprocess.run([sys.executable,'-B','-c',code,*arguments],cwd=root,env=env,capture_output=True,timeout=300)
    if result.returncode:raise AssertionError(('Unmodified original fixture producer failed',result.returncode,result.stderr[-5000:],result.stdout[-2000:]))
    return result

def refresh(root,tools):return run(root,tools,GENERATE)

def append_personal(root,tools,at):
    run(root,tools,'''from pathlib import Path
import sys
import generate_personal_channel_evidence as channel
from lib.governance_lifecycle.adapter import json_bytes
from lib.governance_lifecycle.personal_probe import collect_probe
from lib.governance_lifecycle.contracts import ROOT
old=channel.load_captures();snapshot=collect_probe(old[-1]['request'],repo=ROOT,previous_comments=channel.prior_comments(old),captured_at=sys.argv[1])
(ROOT/channel.CAPTURES/f'{len(old)+1:08d}.json').write_bytes(json_bytes(snapshot))
''',at)

def append_operating(root,tools,at):
    run(root,tools,'''import sys
from lib.governance_lifecycle import operating_acceptance as op
from lib.governance_lifecycle.adapter import json_bytes
from lib.governance_lifecycle.contracts import ROOT
old=op.captures();snapshot=op.collect(captured_at=sys.argv[1]);(ROOT/op.CAPTURES/f'{len(old)+1:08d}.json').write_bytes(json_bytes(snapshot))
''',at)

def append_role_withdrawal(root,tools,at):
    # Source data is explicitly synthetic; no comment is posted to any service.
    run(root,tools,'''from pathlib import Path
import base64,json,sys
from lib.governance_lifecycle import pilot_actions as actions
from lib.governance_lifecycle.adapter import json_bytes
from lib.governance_lifecycle.kernel import transaction_ref
from lib.governance_lifecycle.live_preparation import revision_ref
from lib.governance_lifecycle.personal_probe import statement_body
profile,binding,receipts,old=actions.load_context();assert not old
at=sys.argv[1];request={'schema_version':'0.1.0','request_type':'lifecycle-pilot-action','environment':'live_pilot_validation','repository_id':profile['scope']['repository_id'],'scope':profile['scope'],'operating_profile_ref':revision_ref(profile),'role_binding_ref':revision_ref(binding),'created_at':at,'discussion_number':900001,'required_role':'role_registry_owner','required_subject_id':binding['assignments']['role_registry_owner'],'expected_receipt_head':transaction_ref(receipts[-1]),'expected_action_head':None,'expected_revision':len(receipts),'body':{'kind':'role_withdrawal','reason':'EXPLICIT SYNTHETIC FIXTURE; no real role withdrawal or authority'}}
endpoint=f"repos/{request['repository_id']}/issues/{request['discussion_number']}";comment={'id':900001,'body':statement_body(request),'user':{'id':81616324,'type':'User'},'performed_via_github_app':None,'issue_url':f"https://api.github.com/repos/{request['repository_id']}/issues/{request['discussion_number']}",'html_url':f"https://github.com/{request['repository_id']}/pull/{request['discussion_number']}#issuecomment-900001",'created_at':at,'updated_at':at}
config=Path(sys.argv[2]);data=json.loads(config.read_bytes());data[endpoint]=base64.b64encode(json_bytes({'number':request['discussion_number'],'html_url':f"https://github.com/{request['repository_id']}/pull/{request['discussion_number']}",'pull_request':{'url':'EXPLICIT SYNTHETIC FIXTURE'}})).decode();data[endpoint+'/comments?per_page=100&page=1']=base64.b64encode(json_bytes([comment])).decode();config.write_text(json.dumps(data))
snapshot=actions.collect_action(request,captured_at=at);record=actions.append_action_snapshot(actions.ROOT,snapshot,recorded_at=at,expected_sequence=0);assert record['outcome']=='eligible_for_pilot'
''',at,str(tools/'responses.json'))
