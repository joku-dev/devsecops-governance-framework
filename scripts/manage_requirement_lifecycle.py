#!/usr/bin/env python3
"""Guide source-document and native Git requirements through the governed lifecycle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lib.requirement_lifecycle import (
    activate_case, analyze_statement, build_native_case, build_source_case, digest, load_yaml,
    shortlist_candidates,
    record_decision, render_requirement_markdown, write_json, write_yaml,
)

CATALOG_PATH = ROOT / "model/requirements/governance-requirement-catalog.yaml"
LEDGER_PATH = ROOT / "model/requirements/requirement-authority-ledger.yaml"
REGISTER_PATH = ROOT / "model/documents/source-document-register.yaml"
CASE_ROOT = ROOT / "model/requirements/lifecycle-cases"
DOC_ROOT = ROOT / "docs/governance/requirements"


def case_path(case_id: str) -> Path:
    return CASE_ROOT / f"{case_id}.json"


def load_case(case_id: str) -> dict:
    return json.loads(case_path(case_id).read_text(encoding="utf-8"))


def source_entry(source_id: str) -> dict:
    register = load_yaml(REGISTER_PATH)
    source = next((item for item in register["documents"] if item["id"] == source_id), None)
    if source is None:
        raise ValueError(f"unknown registered source: {source_id}")
    if source["status"] != "approved":
        raise ValueError(f"source must be approved before migration: {source_id}")
    return source


def import_source(args) -> None:
    source = source_entry(args.source_id)
    source_path = ROOT / source["source_path"]
    catalog = load_yaml(CATALOG_PATH)
    ledger = load_yaml(LEDGER_PATH)
    if any(item["source_id"] == source["id"] for item in ledger["sources"]):
        raise ValueError(f"authority ledger already contains {source['id']}")
    if case_path(args.case_id).exists():
        raise ValueError(f"lifecycle case already exists: {args.case_id}")
    case = build_source_case(case_id=args.case_id, source=source, source_path=source_path, catalog=catalog)
    write_json(case_path(args.case_id), case)
    total = len(case["proposals"])
    ledger["sources"].append({
        "source_id": source["id"],
        "source_version": source["version"],
        "source_path": source["source_path"],
        "document_sha256": digest(source_path),
        "authority_mode": "migration_in_progress",
        "owner": source["owner"],
        "decision_ref": "docs/governance/change-requests/GCR-2026-143-hybrid-requirement-lifecycle.md",
        "effective_from": "2026-10-09",
        "catalog_release": None,
        "coverage": {"total": total, "analyzed": total, "decided": 0, "effective": 0, "unresolved": total},
    })
    write_yaml(LEDGER_PATH, ledger)
    print(f"Created {case_path(args.case_id).relative_to(ROOT)} with {total} proposals")


def start_native(args) -> None:
    source_path = ROOT / args.source_path
    if not source_path.is_file():
        raise ValueError("native source path must exist before the case is created")
    case = build_native_case(
        case_id=args.case_id, source_id=args.source_id, source_path=Path(args.source_path),
        owner=args.owner, domain=args.domain, title=args.title, statement=args.statement,
        strength=args.strength, decision_ref=args.decision_ref, catalog=load_yaml(CATALOG_PATH),
    )
    write_json(case_path(args.case_id), case)
    print(f"Created {case_path(args.case_id).relative_to(ROOT)}")


def decide(args) -> None:
    case = load_case(args.case_id)
    record_decision(
        case, proposal_id=args.proposal_id, disposition=args.disposition,
        classification=args.classification, target_requirement_id=args.target,
        decided_by=args.decided_by, decision_role=args.decision_role,
        rationale=args.rationale, authorized_derivations=args.authorized_derivation,
        runtime_enforcement=args.runtime_enforcement,
    )
    write_json(case_path(args.case_id), case)
    refresh_ledger(case)
    print(f"Recorded decision for {args.proposal_id}")


def reanalyze_all(_) -> None:
    catalog = load_yaml(CATALOG_PATH)
    paths = sorted(CASE_ROOT.glob("*.json"))
    cases = [(path, json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    corpus = [
        (proposal["proposal_id"], proposal["statement"])
        for _, case in cases for proposal in case["proposals"]
    ]
    for path, case in cases:
        for proposal in case["proposals"]:
            candidates = shortlist_candidates(
                proposal["statement"], [item for item in corpus if item[0] != proposal["proposal_id"]]
            )
            proposal["analysis"] = analyze_statement(proposal["statement"], catalog, candidates)
        write_json(path, case)
    print(f"Reanalyzed {len(corpus)} proposals across {len(cases)} lifecycle cases")


def activate(args) -> None:
    case = load_case(args.case_id)
    catalog = load_yaml(CATALOG_PATH)
    activate_case(case, catalog, effective_from=args.effective_from, commit=args.commit)
    write_json(case_path(args.case_id), case)
    write_yaml(CATALOG_PATH, catalog)
    refresh_ledger(case)
    for requirement in catalog["requirements"]:
        if requirement["active_revision"] is not None:
            target = DOC_ROOT / requirement["id"] / f"v{requirement['active_revision']:04d}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text(render_requirement_markdown(requirement), encoding="utf-8")
    print(f"Activated {args.case_id}")


def refresh_ledger(case: dict) -> None:
    if case["intake_type"] != "source_document":
        return
    ledger = load_yaml(LEDGER_PATH)
    entry = next((item for item in ledger["sources"] if item["source_id"] == case["source"]["source_id"]), None)
    if entry is None:
        raise ValueError(f"authority ledger entry missing for {case['source']['source_id']}")
    decided = sum(item["decision"] is not None for item in case["proposals"])
    effective = sum(
        item["activation"] is not None or (
            item["decision"] is not None and (
                item["decision"]["disposition"] == "reject" or item["decision"]["classification"] == "duplicate"
            )
        ) for item in case["proposals"]
    )
    entry["coverage"].update(decided=decided, effective=effective, unresolved=len(case["proposals"]) - decided)
    write_yaml(LEDGER_PATH, ledger)


def complete_migration(args) -> None:
    case = load_case(args.case_id)
    refresh_ledger(case)
    ledger = load_yaml(LEDGER_PATH)
    entry = next((item for item in ledger["sources"] if item["source_id"] == case["source"]["source_id"]), None)
    if case["status"] != "activated" or entry["coverage"]["unresolved"] != 0:
        raise ValueError("migration can complete only after all decisions and activation")
    if entry["coverage"]["effective"] != entry["coverage"]["total"]:
        raise ValueError("migration coverage is incomplete")
    entry["authority_mode"] = "git_authoritative"
    entry["catalog_release"] = args.catalog_release
    entry["effective_from"] = args.effective_from
    entry["decision_ref"] = args.decision_ref
    write_yaml(LEDGER_PATH, ledger)
    print(f"Completed migration for {entry['source_id']}")


def report(_) -> None:
    catalog = load_yaml(CATALOG_PATH)
    ledger = load_yaml(LEDGER_PATH)
    cases = sorted(CASE_ROOT.glob("*.json")) if CASE_ROOT.exists() else []
    print(f"Authority sources: {len(ledger['sources'])}")
    print(f"Lifecycle cases: {len(cases)}")
    print(f"Canonical requirements: {len(catalog['requirements'])}")
    classification_counts = {}
    open_decisions = 0
    for path in cases:
        case = json.loads(path.read_text(encoding="utf-8"))
        for proposal in case["proposals"]:
            key = proposal["analysis"]["suggested_classification"]
            classification_counts[key] = classification_counts.get(key, 0) + 1
            open_decisions += proposal["decision"] is None
    print(f"Open human decisions: {open_decisions}")
    if classification_counts:
        print("Analysis suggestions: " + ", ".join(f"{key}={classification_counts[key]}" for key in sorted(classification_counts)))
    for item in ledger["sources"]:
        coverage = item["coverage"]
        print(f"- {item['source_id']}: {item['authority_mode']} · {coverage['decided']}/{coverage['total']} decided")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    source = commands.add_parser("import-source")
    source.add_argument("--case-id", required=True)
    source.add_argument("--source-id", required=True)
    source.set_defaults(handler=import_source)
    native = commands.add_parser("start-native")
    for name in ("case-id", "source-id", "source-path", "owner", "domain", "title", "statement", "decision-ref"):
        native.add_argument(f"--{name}", required=True)
    native.add_argument("--strength", choices=["MUST", "SHOULD", "MAY", "REQUIREMENT"], required=True)
    native.set_defaults(handler=start_native)
    decision = commands.add_parser("decide")
    for name in ("case-id", "proposal-id", "decided-by", "decision-role", "rationale"):
        decision.add_argument(f"--{name}", required=True)
    decision.add_argument("--disposition", choices=["approve", "reject"], required=True)
    decision.add_argument("--classification", choices=["duplicate", "new", "extend", "change", "supersede", "conflict"], required=True)
    decision.add_argument("--target")
    decision.add_argument("--authorized-derivation", action="append", default=[])
    decision.add_argument("--runtime-enforcement", choices=["none", "report_only", "blocking"], default="none")
    decision.set_defaults(handler=decide)
    reanalyze = commands.add_parser("reanalyze-all")
    reanalyze.set_defaults(handler=reanalyze_all)
    activation = commands.add_parser("activate")
    activation.add_argument("--case-id", required=True)
    activation.add_argument("--effective-from", required=True)
    activation.add_argument("--commit", required=True)
    activation.set_defaults(handler=activate)
    completion = commands.add_parser("complete-migration")
    for name in ("case-id", "catalog-release", "effective-from", "decision-ref"):
        completion.add_argument(f"--{name}", required=True)
    completion.set_defaults(handler=complete_migration)
    status = commands.add_parser("report")
    status.set_defaults(handler=report)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        args.handler(args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Requirement lifecycle failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
