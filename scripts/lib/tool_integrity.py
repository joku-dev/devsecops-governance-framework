"""Pinned local OPA execution shared by full product assessments."""
from pathlib import Path
import json
import re
import subprocess


def require_opa(opa):
    from lib.portable.runtime import approved_opa_hashes, file_digest
    opa=Path(opa).resolve()
    if not opa.is_file() or file_digest(opa) not in approved_opa_hashes('1.18.2'):
        raise ValueError('opa_checksum_mismatch')
    result=subprocess.run([str(opa),'version'],capture_output=True,text=True,timeout=15,check=False)
    if result.returncode or not re.search(r'^Version:\s*1\.18\.2\s*$',result.stdout,re.M):
        raise ValueError('opa_version_mismatch')
    return opa


def evaluate_query(opa,policy,input_path,query):
    result=subprocess.run([str(opa),'eval','--format=json','--data',str(policy),
                           '--input',str(input_path),query],capture_output=True,text=True,timeout=60,check=False)
    if result.returncode:raise ValueError('opa_evaluation_failed')
    try:findings=json.loads(result.stdout)['result'][0]['expressions'][0]['value']
    except (ValueError,KeyError,IndexError,TypeError):raise ValueError('invalid_opa_result') from None
    if not isinstance(findings,list) or any(not isinstance(f,str) for f in findings):
        raise ValueError('invalid_opa_result')
    return findings
