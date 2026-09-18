"""Validate and preserve report-only evidence from an authorized staging deployment."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator, FormatChecker

from lib.measured_security import ROOT


REPOSITORY = "joku-dev/ha-CPsWMS"
BASELINE = "l1-baseline-v1.1.3"
SCHEMA = ROOT / "schemas/staging-deployment-result.schema.json"
RESULT_ROOT = ROOT / "status/staging-deployment-results"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def binding(item: dict) -> str:
    payload = {key: value for key, value in item.items() if key != "evidence_binding"}
    return digest(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())


def _parse_checksums(path: Path) -> dict[str, str]:
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([a-f0-9]{64})  ([A-Za-z0-9._-]+)", line)
        if not match or match.group(2) in rows:
            raise ValueError("Invalid or duplicate SHA256SUMS entry")
        rows[match.group(2)] = match.group(1)
    return rows


def _measured_subject(receipt: dict) -> dict:
    context = receipt["context"]
    path = (RESULT_ROOT.parent / "measured-l1-results" / REPOSITORY.replace("/", "__")
            / f"run-{context['source_run_id']}-attempt-{context['source_attempt']}.json")
    measured = json.loads(path.read_text(encoding="utf-8"))
    if (measured["run"]["commit"] != context["commit"]
            or measured["run"]["event"] != "push" or measured["run"]["branch"] != "main"):
        raise ValueError("Deployment subject is not bound to the admitted mainline measured run")
    return measured


def validate_approval(receipt: dict, approval: dict) -> None:
    context = receipt["context"]
    target = receipt["target"]
    risk = approval.get("risk_context", {})
    subject = approval.get("subject", {})
    approved_target = approval.get("target", {})
    if (approval.get("schema_version") != "1.0"
            or approval.get("decision") != "approved_for_staging"
            or receipt.get("approval", {}).get("decision") != approval["decision"]
            or receipt.get("approval", {}).get("record") != "deployment-approval.json"
            or risk.get("scope") != "staging_only"
            or risk.get("enforcement") != "report_only"
            or risk.get("critical_findings") != receipt["approval"].get("critical_findings_acknowledged")
            or risk.get("high_findings") != receipt["approval"].get("high_findings_acknowledged")
            or subject.get("repository") != context["repository"]
            or subject.get("commit") != context["commit"]
            or str(subject.get("evidence_run_id")) != str(context["source_run_id"])
            or approved_target.get("hostname") != target["hostname"]
            or approved_target.get("address") != target["address"]
            or approved_target.get("environment") != context["environment"]
            or approval.get("components") != {
                name: {"runtime_image_id": component["runtime_image_id"]}
                for name, component in receipt["components"].items()
            }):
        raise ValueError("Deployment approval does not match the deployed subject")


def normalize_bundle(bundle: Path, *, evidence_repository_commit: str,
                     verified_at: str | None = None) -> dict:
    if not re.fullmatch(r"[a-f0-9]{40}", evidence_repository_commit):
        raise ValueError("Evidence repository commit must be a full Git commit")
    files = {path.name: path for path in bundle.iterdir() if path.is_file()}
    required = {"SHA256SUMS", "deployment-receipt.json", "deployment-approval.json", "checks.txt"}
    if not required <= set(files):
        raise ValueError("Incomplete staging evidence bundle")
    checksums = _parse_checksums(files["SHA256SUMS"])
    if set(checksums) != set(files) - {"SHA256SUMS"}:
        raise ValueError("SHA256SUMS must cover every evidence file exactly once")
    for name, expected in checksums.items():
        if digest(files[name].read_bytes()) != expected:
            raise ValueError(f"Staging evidence digest mismatch: {name}")
    receipt = json.loads(files["deployment-receipt.json"].read_text(encoding="utf-8"))
    approval = json.loads(files["deployment-approval.json"].read_text(encoding="utf-8"))
    if (receipt.get("schema_version") != "1.0.0" or receipt.get("evidence_type") != "staging_deployment"
            or receipt.get("status") != "pass" or receipt.get("enforcement") != "report_only"
            or receipt.get("context", {}).get("repository") != REPOSITORY
            or receipt.get("context", {}).get("environment") != "staging"
            or receipt.get("tests", {}).get("fail") != 0
            or receipt.get("tests", {}).get("pass", 0) < 1):
        raise ValueError("Incompatible staging deployment receipt")
    validate_approval(receipt, approval)
    for name, record in receipt.get("artifacts", {}).items():
        if name not in files or record != {"sha256": digest(files[name].read_bytes()), "bytes": files[name].stat().st_size}:
            raise ValueError(f"Receipt artifact record mismatch: {name}")
    measured = _measured_subject(receipt)
    started = datetime.fromisoformat(receipt["deployment"]["started_at"].replace("Z", "+00:00"))
    finished = datetime.fromisoformat(receipt["deployment"]["finished_at"].replace("Z", "+00:00"))
    approved = datetime.fromisoformat(approval["approved_at"].replace("Z", "+00:00"))
    if approved > started or started > finished:
        raise ValueError("Deployment approval and runtime timestamps are out of order")
    verified = datetime.fromisoformat(verified_at.replace("Z", "+00:00")) if verified_at else datetime.now(timezone.utc)
    if verified < finished or (verified - finished).total_seconds() > 7 * 86400:
        raise ValueError("Staging deployment evidence is outside the seven-day intake window")
    verified_at = verified.isoformat().replace("+00:00", "Z")
    source_dir = bundle.name
    filename = f"{receipt['deployment']['finished_at'].replace(':', '-')}-run-{receipt['context']['source_run_id']}.json"
    source_file = f"status/staging-deployment-results/{REPOSITORY.replace('/', '__')}/{filename}"
    result = {
        "schema_version": "1.0.0",
        "result_type": "staging-deployment-result",
        "repository_id": REPOSITORY,
        "reference_baseline": BASELINE,
        "deployed_subject": {
            "commit": receipt["context"]["commit"],
            "source_run_id": str(receipt["context"]["source_run_id"]),
            "source_attempt": int(receipt["context"]["source_attempt"]),
        },
        "evidence_repository": {
            "commit": evidence_repository_commit,
            "path": f"deployment/staging/evidence/{source_dir}/",
        },
        "environment": {
            "name": "staging", "hostname": receipt["target"]["hostname"],
            "address": receipt["target"]["address"],
        },
        "deployment": {
            "started_at": receipt["deployment"]["started_at"],
            "finished_at": receipt["deployment"]["finished_at"],
            "project": receipt["deployment"]["project"], "status": "pass",
            "enforcement": "report-only", "production_approval": False,
            "risk_acceptance": False, "compose_sha256": receipt["deployment"]["compose_sha256"],
            "api_binding": receipt["deployment"]["api_binding"],
        },
        "approval": {
            "decision": approval["decision"], "approved_at": approval["approved_at"],
            "scope": approval["risk_context"]["scope"],
            "critical_findings_acknowledged": receipt["approval"]["critical_findings_acknowledged"],
            "high_findings_acknowledged": receipt["approval"]["high_findings_acknowledged"],
        },
        "components": receipt["components"],
        "tests": receipt["tests"],
        "security_boundaries": receipt["security_boundaries"],
        "observations": receipt.get("observations", []),
        "controls": [
            {"control_id": "DSCB-L1-REQ-013", "assessment": "measured",
             "observation": "A maintainer explicitly approved the exact commit, source run, target and acknowledged staging risk before deployment.",
             "remaining": "Staging-only decision; no production approval or general vulnerability risk acceptance.",
             "evidence_refs": ["deployment-approval.json", "deployment-receipt.json"]},
            {"control_id": "DSCB-L1-REQ-014", "assessment": "measured",
             "observation": "The target ran only the two approved local image IDs with pull_policy never; both identities and health were rechecked after start.",
             "remaining": "Runtime IDs are locally observed transport identities; no independent signed deployment attestation.",
             "evidence_refs": ["deployment-receipt.json", "checks.txt"]},
            {"control_id": "DSCB-L1-REQ-016", "assessment": "partial",
             "observation": "Deployed versions, container logs, outage detection, recovery, restart and security boundaries are retained for the staging run.",
             "remaining": "Define durable operational/security-event retention, backup-restore, monitoring and incident ownership before production use.",
             "evidence_refs": ["deployment-receipt.json", "query-api.log", "neo4j.log", "checks.txt"]},
        ],
        "trust": {
            "effective_level": "integrity_verified", "assessment_status": "evaluated",
            "content_integrity": "pass", "freshness": "pass", "replay": "pass",
            "verified_at": verified_at, "check_summary": {"pass": 8, "fail": 0, "not_evaluated": 4},
        },
        "verified_sources": {
            name: {"sha256": digest(path.read_bytes()), "bytes": path.stat().st_size}
            for name, path in sorted(files.items())
        },
        "verified_at": verified_at,
        "source_file": source_file,
    }
    if measured["reference_baseline"] != result["reference_baseline"]:
        raise ValueError("Measured run uses a different baseline")
    result["evidence_binding"] = binding(result)
    validate_snapshot(result)
    return result


def validate_snapshot(item: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(item)
    if item["evidence_binding"] != binding(item):
        raise ValueError("Staging evidence binding changed")
    expected = {
        "DSCB-L1-REQ-013": "measured", "DSCB-L1-REQ-014": "measured",
        "DSCB-L1-REQ-016": "partial",
    }
    actual = {row["control_id"]: row["assessment"] for row in item["controls"]}
    if actual != expected or len(item["controls"]) != len(actual):
        raise ValueError("Staging control projection changed")
    if not all(item["security_boundaries"].values()):
        raise ValueError("Required staging security boundary failed")


def store_snapshot(root: Path, item: dict) -> Path:
    validate_snapshot(item)
    path = ROOT / item["source_file"] if root == RESULT_ROOT else root / item["repository_id"].replace("/", "__") / Path(item["source_file"]).name
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(item, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(encoded)
    except FileExistsError:
        if json.loads(path.read_text(encoding="utf-8")) != item:
            raise ValueError("Conflicting staging snapshot; existing evidence preserved")
    return path


def load_snapshots(root: Path) -> list[dict]:
    items = []
    for path in sorted(root.rglob("*.json")) if root.exists() else []:
        item = json.loads(path.read_text(encoding="utf-8"))
        validate_snapshot(item)
        if path.is_symlink() or path.relative_to(ROOT).as_posix() != item["source_file"]:
            raise ValueError("Staging snapshot path/identity mismatch")
        items.append(item)
    return sorted(items, key=lambda row: datetime.fromisoformat(row["deployment"]["finished_at"].replace("Z", "+00:00")))
