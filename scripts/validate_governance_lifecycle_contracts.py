#!/usr/bin/env python3
"""Validate checked-in CLG-01 synthetic contracts only; never perform live intake."""
import json

from lib.governance_lifecycle.contracts import (
    ROOT, KINDS, require, check_closure_prerequisites, check_event_references, validate_test_profile, validate_test_record,
)


def load_examples():
    profile = json.loads((ROOT / "model/governance/lifecycle/synthetic-grs002-profile.json").read_text())
    directory = ROOT / "docs/examples/governance-lifecycle"
    records = {}
    for path in sorted(directory.glob("*.json")):
        record = json.loads(path.read_text())
        require(record["record_id"] not in records, "Duplicate example record ID")
        records[record["record_id"]] = record
    require({r["record_type"] for r in records.values()} == set(KINDS), "Missing example record kind")
    fixtures = ROOT / "tests/fixtures/governance-lifecycle/resources"
    resources = {"fixture://" + p.name: p.read_bytes() for p in fixtures.glob("*.json")}
    return profile, records, resources


def main():
    profile, records, resources = load_examples()
    validate_test_profile(profile)
    for record in records.values():
        validate_test_record(record, profile, resources)
        if record["record_type"] == "event":
            check_event_references(record, records)
    closure = records["closure:synthetic-001"]
    check_closure_prerequisites(closure, records, profile, resources, as_of=closure["body"]["as_of"])
    print(f"CLG-01: {len(records)} synthetic records and closure prerequisites valid; no live acceptance or state transition.")


if __name__ == "__main__":
    main()
