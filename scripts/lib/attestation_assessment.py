"""Original report-only attestation decisions over explicit local observations.

Lineage: V1 6b557fe, lib/evidence_attestation.py. Native tool invocation is
injected; a retained legacy effective-level label never authorizes a V2 node.
"""
import base64
import json
import yaml
from lib.review_planning import ContractLoader, MAX_CONTRACT_BYTES

CHECK_IDS = ['trust_root_known','attestation_signature_valid','attestation_subject_matches','attestation_context_matches']
CONTEXT_FIELDS = ('repository_id','commit_id','run_id','run_attempt','artifact_name')
MAX_INPUT = 1024**2


class RegistryLoader(ContractLoader):
    """Keep bounded composition but preserve the pilot's ordinary SafeLoader grammar."""


# Pilot registries originally accept merge keys and ordinary SafeLoader keys.
# Do not accidentally replace that grammar with the review-contract grammar.
RegistryLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    yaml.SafeLoader.yaml_constructors[yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG])


def registry(raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_CONTRACT_BYTES:raise ValueError('attestation_registry_byte_budget')
    try:value=yaml.load(raw.decode('utf-8'),Loader=RegistryLoader)
    except (yaml.YAMLError,UnicodeError,RecursionError,OverflowError,TypeError):raise ValueError('invalid_attestation_registry') from None
    if not isinstance(value,dict) or value.get('status')!='pilot_report_only' or value.get('enforcement')!='report_only':
        raise ValueError('report_only_attestation_registry_required')
    return value


def input_object(raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_INPUT:raise ValueError('attestation_input_byte_budget')
    try:value=json.loads(raw.decode('utf-8'))
    except (UnicodeError,RecursionError):raise ValueError('invalid_attestation_json') from None
    if not isinstance(value,dict):raise ValueError('attestation_object_required')
    stack=[(value,0)];nodes=0
    while stack:
        item,depth=stack.pop();nodes+=1
        if nodes>100000 or depth>64:raise ValueError('attestation_input_graph_budget')
        if isinstance(item,dict):stack.extend((child,depth+1) for child in item.values())
        elif isinstance(item,list):stack.extend((child,depth+1) for child in item)
    return value


def canonical_statement(statement):
    return json.dumps(statement,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')


def assess(*,attestation,registry,expected_context,expected_subject,evaluated_at,
           attestation_ref,verify,current_effective_level='integrity_verified'):
    roots=registry.get('roots',[])
    root=next((item for item in roots if item.get('key_id')==attestation.get('key_id')
        and item.get('issuer')==attestation.get('issuer') and item.get('status')=='pilot'),None)
    checks={key:{'id':key,'result':'not_evaluated','reason':'Prerequisite check did not pass.'} for key in CHECK_IDS}
    permitted=root is not None and attestation.get('statement',{}).get('repository_id') in root.get('permitted_repositories',[])
    checks['trust_root_known']={'id':'trust_root_known','result':'pass' if permitted else 'fail',
        'reason':'Pilot issuer, key, and repository scope are registered.' if permitted else 'Issuer, key, or repository scope is not registered.'}
    if permitted:
        key=root['public_key_pem'];statement_bytes=canonical_statement(attestation['statement']);encoded=attestation['signature']
        try:signature=base64.b64decode(encoded,validate=True)
        except (ValueError,TypeError) as exc:valid,reason=False,f'Signature is not valid base64: {exc}'
        else:valid,reason=verify(key,statement_bytes,signature)
        checks['attestation_signature_valid']={'id':'attestation_signature_valid','result':'pass' if valid else 'fail','reason':reason}
    statement=attestation.get('statement',{});matches=statement.get('subject')==expected_subject
    checks['attestation_subject_matches']={'id':'attestation_subject_matches','result':'pass' if matches else 'fail',
        'reason':'Attested subject identifier and digest match the collected subject.' if matches else 'Attested subject does not match the collected subject.'}
    matches={key:statement.get(key) for key in CONTEXT_FIELDS}==expected_context
    checks['attestation_context_matches']={'id':'attestation_context_matches','result':'pass' if matches else 'fail',
        'reason':'Repository, commit, run attempt, and artifact are bound to the attestation.' if matches else 'Attestation context differs from the authoritative collection context.'}
    ordered=[checks[key] for key in CHECK_IDS];passed=all(check['result']=='pass' for check in ordered)
    return {'schema_version':'0.1.0','assessment_type':'evidence-attestation-pilot','enforcement':'report_only',
        'evaluated_at':evaluated_at,'attestation_ref':attestation_ref,'effective_level':current_effective_level,
        'candidate_level':'attested' if passed else 'none','status':'pass' if passed else 'fail','checks':ordered}


def wire(value):return (json.dumps(value,indent=2)+'\n').encode('utf-8')


def summary(value):return f"Attestation pilot assessment: {value['status']} ({value['candidate_level']})\n"
