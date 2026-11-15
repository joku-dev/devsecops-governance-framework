#!/usr/bin/env python3
"""Generate the separate portable candidate read model without accepting any result."""
import argparse
from pathlib import Path
from lib.consumer_intake_store import atomic_json
from lib.portable_intake.candidate_index import build_index

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path)
    a=p.parse_args();root=a.root.resolve();destination=a.output or root/'generated/portable-intake/index.json'
    # Caller-selected output is allowed for tests/artifacts, never an accepted status index.
    resolved=destination.resolve()
    if resolved.is_relative_to(root) and resolved!=root/'generated/portable-intake/index.json':
        raise SystemExit('Only generated/portable-intake/index.json is writable inside the source checkout')
    atomic_json(destination,build_index(root),mode=0o644)
