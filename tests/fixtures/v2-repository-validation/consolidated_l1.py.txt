"""Combine an exact measured L1 run with its exact staging supplement."""

from collections import Counter
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from lib.measured_l1 import ROOT, STATES, validate_snapshot as validate_measured
from lib.staging_deployment import validate_snapshot as validate_staging

PROFILE = "ha-cpswms-l1-consolidated-v1"
SCHEMA = ROOT / "schemas/consolidated-l1-assessment.schema.json"
RESULT_ROOT = ROOT / "status/consolidated-l1-results"
STAGING_CONTROLS = {"DSCB-L1-REQ-013", "DSCB-L1-REQ-014", "DSCB-L1-REQ-016"}


def binding(item: dict) -> str:
    payload = {key: value for key, value in item.items() if key != "evidence_binding"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _same_subject(measured: dict, staging: dict) -> bool:
    subject = staging["deployed_subject"]
    return (
        measured["repository_id"] == staging["repository_id"]
        and measured["reference_baseline"] == staging["reference_baseline"]
        and measured["run"]["commit"] == subject["commit"]
        and measured["run"]["id"] == subject["source_run_id"]
        and measured["run"]["attempt"] == subject["source_attempt"]
    )


def build_consolidated(
    measured: dict,
    staging: dict,
    *,
    measured_source_file: str,
    staging_source_file: str,
) -> dict:
    validate_measured(measured)
    validate_staging(staging)
    if not _same_subject(measured, staging):
        raise ValueError("Staging deployment does not match the measured run exactly")
    staging_rows = {row["control_id"]: row for row in staging["controls"]}
    if set(staging_rows) != STAGING_CONTROLS:
        raise ValueError("Staging supplement has an unexpected control scope")
    controls = []
    for source in measured["controls"]:
        row = deepcopy(source)
        supplement = staging_rows.get(row["control_id"])
        if supplement:
            row["assessment"] = supplement["assessment"]
            row["observation"] = supplement["observation"]
            row["remaining"] = supplement["remaining"]
            row["tools"] = sorted(set([*row["tools"], "Staging deployment evidence"]))
            row["evidence_refs"] = [
                *("measured:" + ref for ref in source["evidence_refs"]),
                *("staging:" + ref for ref in supplement["evidence_refs"]),
            ]
        else:
            row["evidence_refs"] = ["measured:" + ref for ref in row["evidence_refs"]]
        controls.append(row)
    result = {
        "schema_version": "1.0.0",
        "result_type": "consolidated-l1-assessment",
        "profile": PROFILE,
        "repository_id": measured["repository_id"],
        "reference_baseline": measured["reference_baseline"],
        "run": deepcopy(measured["run"]),
        "verified_at": staging["verified_at"],
        "enforcement": "report-only",
        "official_compliance_result": False,
        "production_approval": False,
        "risk_acceptance": False,
        "source_assessments": {
            "measured": {
                "source_file": measured_source_file,
                "profile": measured["profile"],
                "evidence_binding": measured["evidence_binding"],
            },
            "staging": {
                "source_file": staging_source_file,
                "evidence_binding": staging["evidence_binding"],
                "effective_level": staging["trust"]["effective_level"],
                "freshness": staging["trust"]["freshness"],
                "replay": staging["trust"]["replay"],
            },
        },
        "controls": controls,
        "summary": {state: Counter(row["assessment"] for row in controls)[state] for state in STATES},
    }
    result["evidence_binding"] = binding(result)
    validate_snapshot(result)
    return result


def validate_snapshot(item: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(item)
    if item["evidence_binding"] != binding(item):
        raise ValueError("Consolidated L1 evidence binding changed")
    controls = item["controls"]
    if {row["control_id"] for row in controls} != {
            f"DSCB-L1-REQ-{number:03}" for number in range(1, 17)} or len(controls) != 16:
        raise ValueError("Consolidated L1 assessment must contain all controls exactly once")
    expected = {state: Counter(row["assessment"] for row in controls)[state] for state in STATES}
    if item["summary"] != expected:
        raise ValueError("Consolidated L1 summary differs from controls")


def validate_sources(item: dict, repository_root: Path = ROOT) -> None:
    sources = item["source_assessments"]
    loaded = {}
    for name in ("measured", "staging"):
        path = repository_root / sources[name]["source_file"]
        try:
            path.resolve().relative_to(repository_root.resolve())
        except ValueError as exc:
            raise ValueError("Consolidated L1 source escapes repository root") from exc
        if not path.is_file() or path.is_symlink():
            raise ValueError("Consolidated L1 source is missing or unsafe")
        loaded[name] = json.loads(path.read_text(encoding="utf-8"))
    expected = build_consolidated(
        loaded["measured"], loaded["staging"],
        measured_source_file=sources["measured"]["source_file"],
        staging_source_file=sources["staging"]["source_file"],
    )
    if expected != item:
        raise ValueError("Consolidated L1 assessment differs from its exact sources")


def store_snapshot(root: Path, item: dict) -> Path:
    validate_snapshot(item)
    path = root / item["repository_id"].replace("/", "__") / f"run-{item['run']['id']}-attempt-{item['run']['attempt']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(item, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(encoded)
    except FileExistsError:
        if json.loads(path.read_text(encoding="utf-8")) != item:
            raise ValueError("Conflicting consolidated L1 assessment; historical snapshot preserved")
    return path


def load_snapshots(root: Path) -> list[dict]:
    items = []
    for path in sorted(root.rglob("*.json")) if root.exists() else []:
        item = json.loads(path.read_text(encoding="utf-8"))
        validate_snapshot(item)
        expected = item["repository_id"].replace("/", "__") + f"/run-{item['run']['id']}-attempt-{item['run']['attempt']}.json"
        if path.is_symlink() or path.relative_to(root).as_posix() != expected:
            raise ValueError("Consolidated L1 snapshot path/identity mismatch")
        items.append(item)
    return sorted(items, key=lambda row: (
        datetime.fromisoformat(row["run"]["created_at"].replace("Z", "+00:00")),
        int(row["run"]["id"]), row["run"]["attempt"]))


def reconcile(measured_items: list[dict], staging_items: list[dict], root: Path = RESULT_ROOT) -> list[Path]:
    paths = []
    for measured in measured_items:
        matches = [staging for staging in staging_items if _same_subject(measured, staging)]
        if len(matches) > 1:
            raise ValueError("Multiple staging deployments match one measured L1 run")
        if not matches:
            continue
        staging = matches[0]
        measured_file = (
            f"status/measured-l1-results/{measured['repository_id'].replace('/', '__')}/"
            f"run-{measured['run']['id']}-attempt-{measured['run']['attempt']}.json"
        )
        item = build_consolidated(
            measured, staging,
            measured_source_file=measured_file,
            staging_source_file=staging["source_file"],
        )
        paths.append(store_snapshot(root, item))
    return paths
