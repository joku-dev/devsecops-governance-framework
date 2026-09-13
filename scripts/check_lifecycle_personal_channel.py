#!/usr/bin/env python3
"""Check or replay a personal-channel probe; this command never posts a statement."""
import argparse
from pathlib import Path
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ROOT, require
from lib.governance_lifecycle.personal_probe import collect_probe, replay_probe_snapshot
from generate_personal_channel_probe import REQUEST


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replay',type=Path)
    parser.add_argument('--previous-capture',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.replay:
        require(args.previous_capture is None and args.output is None,'Replay does not fetch or write')
        result=replay_probe_snapshot(strict_json(args.replay.read_bytes()))
    else:
        require(args.output is not None,'A new output capture path is required')
        output=args.output.resolve()
        require(not output.exists(),'Existing probe capture cannot be replaced')
        if output.is_relative_to(ROOT):
            require(output.is_relative_to(ROOT/'generated/reports/lifecycle-personal-channel'),'Dedicated diagnostic output path required')
        request=strict_json((ROOT/REQUEST).read_bytes())
        previous=[]
        if args.previous_capture:
            snapshot=strict_json(args.previous_capture.read_bytes())
            require(snapshot['request']==request,'Previous capture belongs to a different request')
            previous=replay_probe_snapshot(snapshot)['relevant_comments']
            # Keep the first captured identity for every previous statement, including deletions.
            previous=list({c['id']:c for c in previous+snapshot.get('previous_comments',[])}.values())
        snapshot=collect_probe(request,repo=ROOT,previous_comments=previous)
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('xb') as stream:stream.write(json_bytes(snapshot))
        result=snapshot['result']
    print(f"Personal channel probe: {result['status']}; no remediation, closure or live activation authorized.")


if __name__=='__main__':main()
