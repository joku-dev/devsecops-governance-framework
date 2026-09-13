#!/usr/bin/env python3
"""Capture an action-bound personal statement into pilot validation; never post or execute it."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
from lib.governance_lifecycle.adapter import strict_json
from lib.governance_lifecycle.contracts import ROOT, require
from lib.governance_lifecycle.pilot_actions import collect_action, append_action_snapshot

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--expected-sequence',type=int,required=True)
    args=parser.parse_args()
    request=strict_json(args.request.read_bytes())
    snapshot=collect_action(request)
    require(snapshot['capture_method']=='github_api_get_via_gh','Fresh GitHub capture required')
    at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
    print(append_action_snapshot(ROOT,snapshot,recorded_at=at,expected_sequence=args.expected_sequence))
