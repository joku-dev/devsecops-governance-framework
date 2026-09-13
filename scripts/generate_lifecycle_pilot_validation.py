#!/usr/bin/env python3
"""Generate the separate durable pilot validation projection from complete receipts."""
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ROOT, require
from lib.governance_lifecycle.live_admission import VALIDATION_LEDGER, load_operating, project_receipts
from lib.governance_lifecycle.store import load_transactions

INDEX="status/governance-lifecycle-live-validation.json"
REPORT="generated/reports/governance-lifecycle-live-validation.md"


def render(index):
    return ("# Durable CLG Pilot Validation\n\n"
        "Diagnostic pilot eligibility only; live activation and personal decisions remain separate.\n\n"
        f"Recorded through: `{index['as_of']}`. Official state: `false`.\n\n"
        f"Receipts: {index['counts']['receipts']}; eligible: {index['counts']['eligible']}; "
        f"quarantined: {index['counts']['quarantined']}.\n\n"
        f"Latest captured GRS-002: `{index['latest_criterion_result']}`. "
        f"Pilot finding: `{index['pilot_finding']}`. PASS never creates or closes a Finding.\n")


def validate(repo=ROOT):
    index=project_receipts(load_transactions(repo / VALIDATION_LEDGER),load_operating(repo))
    require(strict_json((repo / INDEX).read_bytes()) == index, "Pilot validation index differs")
    require((repo / REPORT).read_text() == render(index), "Pilot validation report differs")
    return index


def main():
    index=project_receipts(load_transactions(ROOT / VALIDATION_LEDGER),load_operating())
    (ROOT / INDEX).write_bytes(json_bytes(index))
    (ROOT / REPORT).write_text(render(index))
    print(index['counts'])


if __name__ == "__main__":
    main()
