#!/usr/bin/env python3
"""Validate synthetic lifecycle history and optionally enforce an accepted Git prefix."""
import argparse
from pathlib import Path
import re
import subprocess

from lib.governance_lifecycle.adapter import strict_json
from lib.governance_lifecycle.contracts import ROOT, require, timestamp
from lib.governance_lifecycle.kernel import project, replay
from lib.governance_lifecycle.store import load_transactions
from generate_governance_lifecycle_index import DEFAULT_LEDGER, DEFAULT_INDEX, DEFAULT_PROFILE

LEDGER_PATH = "governance/lifecycle/synthetic"
PILOT_LEDGER_PATH = "governance/lifecycle/synthetic-closure"
LEDGER_PATHS = (LEDGER_PATH, PILOT_LEDGER_PATH)
PROFILE_PATH = "model/governance/lifecycle/synthetic-grs002-profile.json"


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, text=True)


def check_accepted_prefix(repo, base_ref):
    """Preserve every accepted blob; merged union is separately replayed for forks."""
    require(re.fullmatch(r"[a-f0-9]{40}", base_ref) is not None, "Base must be an immutable Git SHA")
    require(base_ref != "0" * 40, "An existing accepted base is required")
    git(repo, "cat-file", "-e", base_ref + "^{commit}")
    tracked = git(repo, "ls-files", "--", *LEDGER_PATHS).splitlines()
    for name in tracked:
        require(re.fullmatch("(?:" + "|".join(re.escape(p) for p in LEDGER_PATHS) + r")/transactions/[0-9]{8,}-[a-f0-9]{64}\.json", name)
                is not None, "Only published transactions may be tracked in the ledger")
    entries = git(repo, "ls-tree", "-r", base_ref, "--", *LEDGER_PATHS).splitlines()
    for entry in entries:
        metadata, name = entry.split("\t", 1)
        mode, kind, digest = metadata.split()
        require(mode == "100644" and kind == "blob", "Unexpected accepted ledger file type")
        path = Path(repo) / name
        require(path.is_file() and not path.is_symlink(), "Accepted transaction deleted or replaced")
        require(git(repo, "hash-object", "--", str(path)).strip() == digest, "Accepted transaction modified")
    if entries:
        before = git(repo, "rev-parse", base_ref + ":" + PROFILE_PATH).strip()
        after = git(repo, "hash-object", "--", PROFILE_PATH).strip()
        require(before == after, "Accepted profile requires an explicit versioned migration")
    return len(entries)


def validate_current(ledger=DEFAULT_LEDGER, index_path=DEFAULT_INDEX, profile_path=DEFAULT_PROFILE):
    profile = strict_json(Path(profile_path).read_bytes())
    transactions = load_transactions(ledger)
    replay(transactions, profile)
    index = strict_json(Path(index_path).read_bytes())
    require(not transactions or timestamp(index["as_of"]) >= timestamp(transactions[-1]["recorded_at"]),
            "Current index cannot hide a later accepted ledger transaction")
    expected = project(transactions, profile, as_of=index["as_of"])
    require(index == expected, "Lifecycle index differs from the immutable ledger projection")
    return expected


def validate_pilot(repo=ROOT):
    from generate_governance_lifecycle_pilot import render_report
    root = Path(repo)
    index = validate_current(root / PILOT_LEDGER_PATH, root / "status/governance-lifecycle-closure-index.json",
                             root / PROFILE_PATH)
    report = root / "generated/reports/governance-lifecycle-pilot.md"
    require(report.read_text() == render_report(index), "Lifecycle pilot report differs from projection")
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref")
    args = parser.parse_args()
    if args.base_ref:
        count = check_accepted_prefix(ROOT, args.base_ref)
        print(f"Preserved {count} accepted lifecycle blobs from {args.base_ref}.")
    index = validate_current()
    pilot = validate_pilot()
    print(f"Lifecycle: original scenario {index['counts']}; synthetic closure pilot {pilot['counts']}; no live activation.")


if __name__ == "__main__":
    main()
