"""Hash-bound decision coverage from frozen V1; no identity or approval assertion."""
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker
from lib.portable.contracts import ROOT

def supplied_json(path):
    from lib.dcr_application import supplied_json as load
    return load(path)

def validate_decisions(report: dict, manifest: dict, manifest_path: Path, paths: list[Path], *, schema_root: Path = ROOT) -> None:
    schema = supplied_json(schema_root / "schemas/document-consistency-human-decision.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if not paths:
        raise ValueError("no human decision artifacts supplied")
    found = set()
    for path in paths:
        decision = supplied_json(path)
        validator.validate(decision)
        finding = next((item for item in report["findings"] if item["finding_id"] == decision["finding_id"]), None)
        if finding is None:
            raise ValueError(f"decision references unknown finding: {decision['finding_id']}")
        finding_hash = hashlib.sha256(
            json.dumps(finding, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if decision["review_id"] != report["review_id"]:
            raise ValueError("decision review ID does not match report")
        if decision["source_manifest_sha256"] != manifest_hash:
            raise ValueError("decision source manifest hash does not match supplied manifest")
        if decision["finding_sha256"] != finding_hash:
            raise ValueError(f"decision finding hash does not match: {decision['finding_id']}")
        if decision["finding_id"] in found:
            raise ValueError(f"duplicate decision for finding: {decision['finding_id']}")
        found.add(decision["finding_id"])
    if found != {item["finding_id"] for item in report["findings"]}:
        raise ValueError("human decisions do not cover every report finding")

