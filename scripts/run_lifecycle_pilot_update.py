#!/usr/bin/env python3
"""Prepare a bounded pilot update from protected main; publication remains a separate PR step."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import tempfile
from lib.governance_lifecycle.adapter import strict_json
from lib.governance_lifecycle.contracts import ROOT,require
from lib.governance_lifecycle.live_admission import load_operating,VALIDATION_LEDGER,append_capture
from lib.governance_lifecycle.live_evidence import collect_preflight
from lib.governance_lifecycle.store import load_transactions
from lib.governance_lifecycle.pilot_actions import ACTION_LEDGER,collect_action,append_action_snapshot
from lib.governance_lifecycle.operating_acceptance import capture,verify_provider,generate


def run(operation,*,run_id=None,request_path=None):
    if operation=='acceptance':capture()
    else:
        verify_provider()
        if operation=='observe':
            require(run_id is not None and run_id.isdigit() and int(run_id)>0,'A positive source run ID is required')
            with tempfile.TemporaryDirectory() as temporary:
                directory=Path(temporary)/'capture';collect_preflight(run_id,directory)
                at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
                append_capture(ROOT/VALIDATION_LEDGER,directory,load_operating(),recorded_at=at,
                    expected_sequence=len(load_transactions(ROOT/VALIDATION_LEDGER)))
        elif operation=='action':
            require(bool(request_path),'A committed action request path is required')
            path=(ROOT/request_path).resolve()
            require(path.is_relative_to(ROOT/'model/governance/lifecycle/action-requests') and path.is_file(),'Request must be in the dedicated action-request directory')
            # GitHub workflow uses a protected-main checkout. No arbitrary upload,
            # shell command or caller-supplied provider response is accepted.
            import subprocess
            subprocess.run(['git','ls-files','--error-unmatch','--',str(path.relative_to(ROOT))],cwd=ROOT,check=True,capture_output=True)
            snapshot=collect_action(strict_json(path.read_bytes()))
            require(snapshot['capture_method']=='github_api_get_via_gh','Actual provider capture is required')
            at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
            append_action_snapshot(ROOT,snapshot,recorded_at=at,expected_sequence=len(load_transactions(ROOT/ACTION_LEDGER)))
        elif operation!='refresh':raise ValueError('Unknown pilot operation')
    from generate_lifecycle_pilot_validation import main as generate_receipts
    generate_receipts()
    from generate_lifecycle_pilot_actions import project_actions,INDEX,REPORT,render
    from lib.governance_lifecycle.adapter import json_bytes
    index=project_actions();(ROOT/INDEX).write_bytes(json_bytes(index));(ROOT/REPORT).write_text(render(index))
    generate()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operation',choices=('acceptance','observe','action','refresh'),required=True)
    parser.add_argument('--source-run-id')
    parser.add_argument('--request-path')
    args=parser.parse_args();run(args.operation,run_id=args.source_run_id,request_path=args.request_path)
