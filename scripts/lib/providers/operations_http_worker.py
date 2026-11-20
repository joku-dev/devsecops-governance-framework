#!/usr/bin/env python3
"""One finite read request; credentials arrive only over the private stdin pipe."""
import base64,json,sys
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,build_opener,HTTPRedirectHandler
if __package__:
    from . import operations_report_profile as profile
else:
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import operations_report_profile as profile

MAX_RESPONSE=4*1024**2


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args):return None


def limited(response):
    blocks=[];total=0
    while True:
        part=response.read(min(65536,MAX_RESPONSE+1-total))
        if not part:break
        blocks.append(part);total+=len(part)
        if total>MAX_RESPONSE:raise ValueError('operations_http_response_budget')
    return b''.join(blocks)


def request(value):
    profile.valid_request(value)
    headers={'Accept':'application/vnd.github+json','User-Agent':'axiom-operations-read/2',
             'X-GitHub-Api-Version':profile.API_VERSION}
    if value['token']:headers['Authorization']='Bearer '+value['token']
    data=None if value['body'] is None else json.dumps(value['body'],separators=(',',':')).encode()
    if data is not None:headers['Content-Type']='application/json'
    req=Request(profile.API_ROOT+value['path'],data=data,headers=headers,method=value['method'])
    try:
        with build_opener(NoRedirect).open(req,timeout=60) as response:
            return {'native_code':None,'status':response.status,'body_b64':base64.b64encode(limited(response)).decode()}
    except HTTPError as error:
        try:raw=limited(error)
        finally:error.close()
        return {'native_code':'http_'+str(error.code),'status':error.code,'body_b64':base64.b64encode(raw).decode()}
    except TimeoutError:return {'native_code':'request_timeout','status':None,'body_b64':None}
    except URLError as error:
        return {'native_code':'request_timeout' if isinstance(error.reason,TimeoutError) else 'provider_read_failed','status':None,'body_b64':None}
    except OSError:return {'native_code':'provider_read_failed','status':None,'body_b64':None}


def main():
    try:
        raw=sys.stdin.buffer.read(128*1024+1)
        if len(raw)>128*1024:raise ValueError('operations_http_request_budget')
        result=request(json.loads(raw))
    except ValueError as error:
        if str(error)=='operations_http_response_budget':result={'native_code':'response_byte_budget','status':None,'body_b64':None}
        else:result={'native_code':'invalid_native_response_or_request','status':None,'body_b64':None,'exception_type':type(error).__name__}
    except Exception as error:
        result={'native_code':'invalid_native_response_or_request','status':None,'body_b64':None,'exception_type':type(error).__name__}
    sys.stdout.write(json.dumps(result,allow_nan=False,separators=(',',':'))+'\n')
    return 0


if __name__=='__main__':raise SystemExit(main())
