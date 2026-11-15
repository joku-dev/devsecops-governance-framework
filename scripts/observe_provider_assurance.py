#!/usr/bin/env python3
"""Capture candidate provider review/security observations with a GET-only credential."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
from lib.consumer_intake_store import atomic_json
from lib.portable_intake.bundle import read_json
from lib.private_credentials import check_private_file
from lib.portable_intake.assurance import capture_reviews,capture_security
from lib.portable_intake.transport import BoundedAudit,Reader


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['reviews','security'])
    parser.add_argument('--profile',type=Path,required=True)
    parser.add_argument('--credential-file',type=Path,required=True)
    parser.add_argument('--revision',required=True)
    parser.add_argument('--change-id')
    parser.add_argument('--output-root',type=Path,required=True)
    args=parser.parse_args();os.umask(0o077)
    check_private_file(args.profile);check_private_file(args.credential_file)
    profile=read_json(args.profile)
    if set(profile)!={'scm','api_url','platform_version','edition'}:parser.error('exact candidate profile fields required')
    if any(value is not None and (not isinstance(value,str) or len(value)>200) for value in (profile['platform_version'],profile['edition'])):
        parser.error('versions/edition must be explicit strings or null (unknown)')
    args.output_root.mkdir(parents=True,mode=0o700,exist_ok=False)
    audit=BoundedAudit()
    class AuditedReader(Reader):
        def get(self,path):
            value=super().get(path);audit.append({'path':path,'response':value});return value
    reader=AuditedReader(profile['api_url'],args.credential_file.read_text().strip(),budget=150)
    try:
        if args.action=='reviews':
            if not args.change_id:parser.error('--change-id required for reviews')
            result=capture_reviews(profile['scm'],reader,args.change_id,args.revision)
        else:result=capture_security(profile['scm'],reader,args.revision,datetime.now(timezone.utc).isoformat())
        result.update(platform_version=profile['platform_version'],edition=profile['edition'])
        atomic_json(args.output_root/'candidate.json',result)
    finally:
        # Private immutable capture, including preceding reads on a failed observation.
        atomic_json(args.output_root/'native-capture.json',list(audit))
    print(json.dumps({'candidate_written':True,'live_authority':False}))


if __name__=='__main__':main()
