#!/usr/bin/env python3
"""Intake an explicit synthetic decision/remediation packet; never approve a real decision."""
import argparse
from pathlib import Path

from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import require
from lib.governance_lifecycle.store import append_action
from generate_governance_lifecycle_index import DEFAULT_PROFILE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--resources", type=Path, required=True, help="Directory containing the two flat fixture resources")
    parser.add_argument("--expected-revision", type=int, required=True)
    args = parser.parse_args()
    record = strict_json(args.record.read_bytes())
    body = record["body"]
    if record["record_type"] == "decision":
        refs = [record["approval"]["proof_ref"], body["remediation_plan"]["work_ref"]]
    else:
        require(record["record_type"] == "remediation", "Only decisions and remediations are supported")
        refs = [body["work_ref"], body["progress_evidence_ref"]]
    resources = {}
    for ref in refs:
        uri = ref["uri"]
        require(uri.startswith("fixture://"), "Live resources are not supported")
        name = uri[len("fixture://"):]
        require(name not in ("", ".", "..") and Path(name).name == name and "\\" not in name,
                "Fixture resources must have flat filenames")
        path = args.resources / name
        require(not path.is_symlink(), "Fixture resource cannot be a symlink")
        resources[uri] = path.read_bytes()
    result = append_action(args.ledger, record, resources, strict_json(DEFAULT_PROFILE.read_bytes()),
                           expected_revision=args.expected_revision)
    print(json_bytes(result).decode(), end="")


if __name__ == "__main__":
    main()
