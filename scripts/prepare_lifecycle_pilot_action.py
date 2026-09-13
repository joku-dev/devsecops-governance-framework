#!/usr/bin/env python3
"""Prepare a complete action request and printable statement; never issue personal consent."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
from lib.governance_lifecycle.adapter import json_bytes,strict_json
from lib.governance_lifecycle.contracts import ROOT,require
from lib.governance_lifecycle.kernel import transaction_ref
from lib.governance_lifecycle.live_preparation import revision_ref
from lib.governance_lifecycle.personal_probe import statement_body
from lib.governance_lifecycle.pilot_actions import load_context,required_role,validate_context


def prepare(body,discussion_number,*,repo=ROOT,created_at=None):
    profile,binding,receipts,actions=load_context(repo)
    require(bool(receipts),'A retained pilot receipt is required')
    at=created_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    role=required_role({'body':body},actions)
    request={'schema_version':'0.1.0','request_type':'lifecycle-pilot-action','environment':'live_pilot_validation',
        'repository_id':profile['scope']['repository_id'],'scope':profile['scope'],
        'operating_profile_ref':revision_ref(profile),'role_binding_ref':revision_ref(binding),'created_at':at,
        'discussion_number':discussion_number,'required_role':role,'required_subject_id':binding['assignments'][role],
        'expected_receipt_head':transaction_ref(receipts[-1]),'expected_action_head':transaction_ref(actions[-1]) if actions else None,
        'expected_revision':len(receipts)+len(actions),'body':body}
    validate_context(request,profile,binding,receipts,actions,at=at)
    return request


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--body',type=Path,required=True)
    parser.add_argument('--discussion-number',type=int,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    request=prepare(strict_json(args.body.read_bytes()),args.discussion_number)
    require(not args.output.exists(),'Request cannot replace an existing file')
    with args.output.open('xb') as stream:stream.write(json_bytes(request))
    print('Review the complete request before personally issuing this statement. No live activation is authorized.')
    print(statement_body(request))
