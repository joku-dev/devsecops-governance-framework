"""Explicit original workflow names, index names, URL and error presentation."""
from datetime import datetime
import json,re
PROFILE='legacy-daily-operations-v1'
PRODUCT_INPUTS={'schema':'schemas/governance-operations-report.schema.json','config':'.github/operations-report.json'}
API_ROOT='https://api.github.com'
API_VERSION='2026-03-10'
MAIN_WORKFLOW='governance-ci.yml'
DOCS_WORKFLOW='publish-docs.yml'
SECURITY_WORKFLOW='governance-repository-security.yml'
CI_ACCESS_ACTION='Restore Actions read access.'
INTAKES=('intake-governance-result.yml','intake-architecture-result.yml','intake-evidence-trust.yml')
INDEXES={'devsecops':'repository-results-index.json',
         'architecture':'architecture-results-index.json',
         'typed_evidence':'typed-evidence-results-index.json'}


def repository_url(repository):return f'https://github.com/{repository}'


def workflow_url(repository,name):return repository_url(repository)+'/actions/workflows/'+name


def repository_actions_url(repository):return repository_url(repository)+'/actions'


def expected_optional_protection_error(error):
    # Exact provided-observation semantics. Native bounded codes require an
    # explicit acquisition mapping; accepting arbitrary new strings would change V1.
    return 'HTTP 404' in error


def workflow_queries(config):
    return {MAIN_WORKFLOW:'push',DOCS_WORKFLOW:None,
            **{name:'schedule' for name in config['scheduled_workflows']},
            **{name:None for name in INTAKES}}


PR_QUERY='''query AxiomOperationsPullRequests($owner:String!,$repo:String!,$limit:Int!,$cursor:String){
 repository(owner:$owner,name:$repo){pullRequests(states:[OPEN],baseRefName:"main",first:$limit,after:$cursor,orderBy:{field:CREATED_AT,direction:DESC}){
 nodes{number url title createdAt isDraft reviewDecision mergeStateStatus author{login ... on User{id name}} headRefName}
 pageInfo{hasNextPage endCursor}}}}
'''
PR_FIELDS=('number','url','title','createdAt','isDraft','reviewDecision','mergeStateStatus','author','headRefName')


def repository_parts(repository):
    if not isinstance(repository,str) or len(repository)>400 or not re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):
        raise ValueError('operations_repository_invalid')
    parts=repository.split('/')
    if any(p in ('.','..') for p in parts):raise ValueError('operations_repository_invalid')
    return parts


def valid_request(value):
    if not isinstance(value,dict) or set(value)!={'method','path','body','token'}:raise ValueError('operations_http_request_invalid')
    token=value['token']
    if not isinstance(token,str) or len(token)>16384 or any(ord(c)<33 or ord(c)>126 for c in token):raise ValueError('operations_read_credential_invalid')
    path=value['path'];method=value['method'];body=value['body']
    if not isinstance(path,str) or len(path)>8192:raise ValueError('operations_http_path_invalid')
    if method=='GET' and body is None:
        match=re.fullmatch(r'/repos/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/(?:git/ref/heads/main|actions/workflows/([A-Za-z0-9_.%~-]+)/runs\?branch=main&per_page=100(?:&event=(push|schedule))?)',path)
        if not match:raise ValueError('operations_http_path_invalid')
        repository_parts(match[1]);return
    if method!='POST' or path!='/graphql' or not isinstance(body,dict) or set(body)!={'query','variables'} or body['query']!=PR_QUERY:
        raise ValueError('operations_readonly_query_required')
    variables=body['variables']
    if not isinstance(variables,dict) or set(variables)!={'owner','repo','limit','cursor'}:raise ValueError('operations_query_variables_invalid')
    if not all(isinstance(variables[k],str) for k in ('owner','repo')):raise ValueError('operations_query_variables_invalid')
    repository_parts(variables['owner']+'/'+variables['repo'])
    if type(variables['limit']) is not int or not 1<=variables['limit']<=100:raise ValueError('operations_query_limit_invalid')
    cursor=variables['cursor']
    if cursor is not None and (not isinstance(cursor,str) or not cursor or len(cursor)>4096 or any(ord(c)<32 for c in cursor)):
        raise ValueError('operations_query_cursor_invalid')


def legacy_created_at(value):
    # Validate with datetime; preserve up to nine fractional digits rather than
    # truncating them to Python microseconds. Go's RFC3339Nano omits trailing0s.
    if not isinstance(value,str):raise ValueError('operations_PR_time_invalid')
    match=re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(Z|[+-]\d{2}:\d{2})',value)
    if not match:raise ValueError('operations_PR_time_invalid')
    datetime.fromisoformat(value.replace('Z','+00:00'))
    fraction=(match[2] or '').rstrip('0');zone='Z' if match[3] in ('Z','+00:00','-00:00') else match[3]
    return match[1]+('.'+fraction if fraction else '')+zone


def legacy_pull_request(value):
    if not isinstance(value,dict) or not set(PR_FIELDS)<=value.keys():raise ValueError('operations_PR_fields_missing')
    result={k:value[k] for k in PR_FIELDS}
    if type(result['number']) is not int or result['number']<1 or type(result['isDraft']) is not bool:
        raise ValueError('operations_PR_identity_invalid')
    for key in ('url','title','headRefName'):
        if not isinstance(result[key],str):raise ValueError('operations_PR_text_invalid')
    for key in ('reviewDecision','mergeStateStatus'):
        if result[key] is None:result[key]=''
        if not isinstance(result[key],str):raise ValueError('operations_PR_status_invalid')
    author=result['author']
    if author is None:author={}
    if not isinstance(author,dict) or any(not isinstance(author.get(k,''),str) and author.get(k) is not None for k in ('id','login','name')):
        raise ValueError('operations_PR_author_invalid')
    identity=author.get('id') or '';login=author.get('login') or '';name=author.get('name') or ''
    result['author']=({'id':identity,'is_bot':False,'login':login,'name':name} if identity
                      else {'is_bot':True,'login':'app/'+login})
    result['createdAt']=legacy_created_at(result['createdAt'])
    # gh exports a map with encoding/json's recursively sorted map keys.
    return json.loads(json.dumps(result,sort_keys=True))


def native_security_error_projection(report):
    """Explicit native-to-legacy error spelling; retain the child raw report."""
    from copy import deepcopy
    value=deepcopy(report)
    observation=value.get('observation',{})
    errors=observation.get('api_errors',[])
    if not isinstance(errors,list):raise ValueError('operations_security_errors_invalid')
    mapped=[]
    for error in errors:
        if not isinstance(error,str):raise ValueError('operations_security_error_invalid')
        match=re.fullmatch(r'(repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/[^\s:]+): http_([0-9]{3})',error)
        mapped.append(match[1]+': HTTP '+match[2] if match else error)
    if 'api_errors' in observation:observation['api_errors']=mapped
    return value
