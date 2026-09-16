"""GitHub GET capture and offline verification for operation_readiness only."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import io
import re
import subprocess
import tempfile
import zipfile
from jsonschema import Draft202012Validator
from .adapter import strict_json, json_bytes
from .contracts import ROOT, FORMAT_CHECKER, require, timestamp
from .consumer_contracts import load_operating, schema_validator
from .live_preparation import revision_ref
from .live_evidence import github_get, positive_id
from .architecture_candidates import adapt_architecture

MAX_BYTES = 10 * 1024 * 1024
sha = lambda b: hashlib.sha256(b).hexdigest()


def verify_capture(profile, snapshots, *, captured_at):
    """Replay exact bytes; authenticity additionally requires the independent PR guard."""
    schema_validator('profile').validate(profile)
    source, scope = profile['source'], profile['scope']
    expected = {'repository.json','run-before.json','run-after.json','workflow.json',
                'artifact-before.json','artifact-after.json','artifact.zip','consumer-workflow.yml',
                'baseline-ref.json','baseline-tag.json'} | {'producer/'+p for p in source['reference_files']}
    require(set(snapshots) == expected, 'Consumer capture inventory differs')
    require(sum(map(len,snapshots.values())) <= 3*MAX_BYTES, 'Capture exceeds supported size')
    read = lambda name: strict_json(snapshots[name])
    repository, run, workflow, artifact = map(read, ('repository.json','run-before.json','workflow.json','artifact-before.json'))
    require(run == read('run-after.json') and artifact == read('artifact-after.json'), 'Provider metadata changed during capture')
    rid = scope['github_repository_id']
    require(type(repository['id']) is int and repository['id'] == rid and repository['full_name'] == scope['repository_id']
            and repository['default_branch'] == 'main', 'Consumer repository identity differs')
    positive_id(run['id']);positive_id(run['workflow_id']);positive_id(artifact['id'])
    require(run['repository']['id'] == rid and run['head_repository']['id'] == rid, 'Consumer run repository or fork differs')
    require(run['head_branch'] == 'main' and run['event'] == 'push', 'Only mainline push evidence is eligible')
    require(run['status'] == 'completed' and run['conclusion'] == 'success', 'Completed successful producer required')
    require(type(run['run_attempt']) is int and run['run_attempt'] == 1, 'Only first-attempt artifacts are supported')
    commit = run['head_sha'];require(re.fullmatch(r'[a-f0-9]{40}',commit) is not None, 'Full producer commit required')
    require(run['path'] == source['workflow_path'] and workflow['path'] == source['workflow_path']
            and workflow['id'] == run['workflow_id'], 'Consumer workflow differs')
    require(sha(snapshots['consumer-workflow.yml']) == source['workflow_sha256'], 'Consumer producer implementation changed')
    expected_reference = f"{source['baseline_repository']}/.github/workflows/architecture-baseline-l1-v0.1.0.yml@{source['baseline_ref']}"
    refs = run.get('referenced_workflows', [])
    require(len(refs) == 1 and refs[0]['path'] == expected_reference
            and refs[0]['sha'] in (source['baseline_tag_object'], source['reference_commit']), 'Referenced baseline differs')
    tagref, tag = read('baseline-ref.json'), read('baseline-tag.json')
    require(tagref['ref'] == 'refs/tags/'+source['baseline_ref'] and tagref['object'] == {
        'sha':source['baseline_tag_object'],'type':'tag',
        'url':f"https://api.github.com/repos/{source['baseline_repository']}/git/tags/{source['baseline_tag_object']}"}, 'Baseline tag reference changed')
    require(tag['sha'] == source['baseline_tag_object'] and tag['object']['type'] == 'commit'
            and tag['object']['sha'] == source['reference_commit'], 'Annotated baseline tag resolution differs')
    for path, digest in source['reference_files'].items():
        require(sha(snapshots['producer/'+path]) == digest, 'Pinned baseline file differs: '+path)
    require(artifact['name'] == source['artifact_name'] and artifact['expired'] is False, 'Artifact name or availability differs')
    archive = snapshots['artifact.zip']
    require(type(artifact['size_in_bytes']) is int and 0 < artifact['size_in_bytes'] <= MAX_BYTES
            and 0 < len(archive) <= MAX_BYTES, 'Unsupported artifact size')
    require(artifact['digest'] == 'sha256:'+sha(archive), 'Archive digest does not match GitHub')
    association = artifact['workflow_run']
    require(association['id'] == run['id'] and association['repository_id'] == rid and association['head_repository_id'] == rid
            and association['head_sha'] == commit and association['head_branch'] == 'main', 'Artifact run association differs')
    start, produced, completed, captured = map(timestamp, (run['run_started_at'],artifact['created_at'],run['updated_at'],captured_at))
    require(start <= produced <= completed <= captured < timestamp(artifact['expires_at']), 'Artifact timeline or expiry differs')
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        members = bundle.infolist()
        names = {source['report_path'], source['input_path'], 'architecture-governance-report.md'}
        require(len(members) == 3 and {m.filename for m in members} == names, 'Unexpected or duplicate archive members')
        require(all(not m.is_dir() and m.file_size <= MAX_BYTES and not m.flag_bits & 1
                    and (m.external_attr >> 16) & 0o170000 != 0o120000 for m in members), 'Unsafe archive member')
        report_bytes, input_bytes = bundle.read(source['report_path']), bundle.read(source['input_path'])
    report, data = strict_json(report_bytes), strict_json(input_bytes)
    Draft202012Validator(strict_json(snapshots['producer/schemas/architecture-release-candidate.schema.json']),
                         format_checker=FORMAT_CHECKER).validate(data)
    require(data['release_candidate'] is True and not data['architecture'].get('exceptions'), 'Release gate required; live architecture waivers excluded')
    require(data['target_repository'] == report['target'] and report['target']['release_id'] == commit
            and len(report['target']['commit']) >= 7 and commit.startswith(report['target']['commit']), 'Architecture input/report target differs')
    context = {'repository_id':scope['repository_id'],'branch':'main','commit_id':commit,'producer_id':run['name'],
               'run_id':str(run['id']),'run_attempt':1,'baseline_ref':source['baseline_ref'],'policy_revision':source['reference_commit'],
               'event':'push','purpose':'release','release_context':True,'synthetic':False,'observed_at':artifact['created_at'],
               'report_sha256':sha(report_bytes)}
    adapted = adapt_architecture(report_bytes, context, evaluated_at=captured_at)
    gate = next(g for g in adapted['candidates'] if g['subject']['rule_id'] == 'operation_readiness')
    # Independently evaluate the selected gate with the retained immutable policy.
    with tempfile.TemporaryDirectory() as temp:
        p = Path(temp);(p/'input.json').write_bytes(input_bytes)
        (p/'policy.rego').write_bytes(snapshots['producer/policies/opa/architecture_operation_readiness.rego'])
        result = subprocess.run(['opa','eval','--format=json','--data',str(p/'policy.rego'),'--input',str(p/'input.json'),
                                 'data.architecture.operation_readiness.deny'],capture_output=True,check=True,timeout=30)
        denies = strict_json(result.stdout)['result'][0]['expressions'][0]['value']
    require(sorted(denies) == sorted(gate['source_messages']), 'Gate report differs from independent pinned OPA evaluation')
    return {'profile_ref':revision_ref(profile),'repository_id':scope['repository_id'],'captured_at':captured_at,
            'source':{'run_id':run['id'],'run_attempt':1,'commit_id':commit,'workflow_id':run['workflow_id'],
                      'workflow_path':source['workflow_path'],'artifact_id':artifact['id'],'artifact_sha256':sha(archive),
                      'report_sha256':sha(report_bytes),'input_sha256':sha(input_bytes),'observed_at':artifact['created_at'],
                      'policy_revision':source['reference_commit'],'verified_file_digests':source['reference_files']},
            'criterion':{'id':'operation_readiness','resource':'repository','granularity':'gate',
                         'status':'fail' if denies else 'pass','source_status':gate['result'],'source_messages':gate['source_messages']}}


def collect_preflight(run_id, output_dir, *, repo_root=ROOT, fetch=github_get, captured_at=None):
    profile = load_operating(repo_root); source = profile['source']
    require(re.fullmatch(r'[1-9][0-9]*',str(run_id)) is not None, 'Positive run identity required')
    destination = Path(output_dir).resolve(); root = Path(repo_root).resolve()
    require(not destination.exists(), 'Capture destination already exists')
    if destination.is_relative_to(root):
        require(destination.is_relative_to(root/'generated/reports/consumer-lifecycle-preflight'), 'Dedicated consumer preflight directory required')
    endpoint = 'repos/'+profile['scope']['repository_id']; baseline = 'repos/'+source['baseline_repository']; snapshots = {}
    def get(name, path):
        snapshots[name] = fetch(path);return strict_json(snapshots[name])
    get('repository.json',endpoint)
    run_endpoint = endpoint+'/actions/runs/'+str(run_id)
    run = get('run-before.json',run_endpoint)
    require(str(run['id']) == str(run_id) and type(run['run_attempt']) is int and run['run_attempt'] == 1, 'Run identity or attempt differs')
    require(re.fullmatch(r'[a-f0-9]{40}',run['head_sha']) is not None, 'Full commit required')
    get('workflow.json',endpoint+'/actions/workflows/'+positive_id(run['workflow_id']))
    artifacts = []
    for page in range(1,11):
        listing = strict_json(fetch(run_endpoint+f'/artifacts?per_page=100&page={page}'))
        artifacts.extend(listing['artifacts'])
        if len(artifacts) >= listing['total_count']:break
    else:raise ValueError('Artifact inventory limit exceeded')
    matching = [a for a in artifacts if a['name'] == source['artifact_name']]
    require(len(matching) == 1, 'Exactly one architecture artifact required')
    artifact_endpoint = endpoint+'/actions/artifacts/'+positive_id(matching[0]['id'])
    artifact = get('artifact-before.json',artifact_endpoint);require(artifact == matching[0], 'Artifact inventory race')
    require(0 < artifact['size_in_bytes'] <= MAX_BYTES, 'Artifact too large')
    snapshots['artifact.zip'] = fetch(artifact_endpoint+'/zip')
    snapshots['consumer-workflow.yml'] = fetch(endpoint+'/contents/'+source['workflow_path']+'?ref='+run['head_sha'],raw=True)
    get('baseline-ref.json',baseline+'/git/ref/tags/'+source['baseline_ref'])
    get('baseline-tag.json',baseline+'/git/tags/'+source['baseline_tag_object'])
    for path in source['reference_files']:
        snapshots['producer/'+path] = fetch(baseline+'/contents/'+path+'?ref='+source['reference_commit'],raw=True)
    get('run-after.json',run_endpoint);get('artifact-after.json',artifact_endpoint)
    at = captured_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    result = verify_capture(profile,snapshots,captured_at=at)
    result['capture'] = {'method':'github_api_get_via_gh' if fetch is github_get else 'injected_test_transport',
                         'snapshot_sha256':{p:sha(b) for p,b in snapshots.items()}}
    snapshots['profile.json'] = json_bytes(profile)
    destination.mkdir(parents=True)
    for name,data in snapshots.items():
        path=destination/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:stream.write(data)
    with (destination/'preflight.json').open('xb') as stream:stream.write(json_bytes(result))
    return result


def replay_capture(directory):
    root=Path(directory);require(root.is_dir() and not any(p.is_symlink() for p in (root,*root.rglob('*'))),'Capture contains symlink')
    recorded=strict_json((root/'preflight.json').read_bytes());profile=strict_json((root/'profile.json').read_bytes())
    manifest=recorded['capture']['snapshot_sha256']
    require({str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} == set(manifest)|{'profile.json','preflight.json'},'Capture inventory differs')
    snapshots={}
    for name,digest in manifest.items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Unsafe capture path')
        data=(root/name).read_bytes();require(sha(data)==digest,'Capture bytes differ');snapshots[name]=data
    expected=verify_capture(profile,snapshots,captured_at=recorded['captured_at'])
    require({k:v for k,v in recorded.items() if k!='capture'}==expected,'Capture projection differs')
    return expected
