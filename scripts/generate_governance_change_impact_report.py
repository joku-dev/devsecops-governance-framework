#!/usr/bin/env python3
"""Generate a lightweight governance change impact report.

The v0.1 report is intentionally based on the source document register and the
source-lineage report. It does not try to infer semantic document changes yet;
it tells maintainers what a source document update is likely to affect.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = ROOT / "model" / "documents" / "source-document-register.yaml"
LINEAGE_JSON = ROOT / "generated" / "reports" / "source-lineage-report.json"
OUT_JSON = ROOT / "generated" / "reports" / "governance-change-impact.json"
OUT_MD = ROOT / "generated" / "reports" / "governance-change-impact.md"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def ensure_lineage_report() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_source_lineage_report.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise RuntimeError(f"source lineage generation failed: {details}")


def review_lanes(document: dict, artifacts: list[dict]) -> list[str]:
    lanes = set()
    domains = set(document.get("governance_domains", []))
    if {"policy", "directive"} & domains:
        lanes.add("governance-review")
    if "devsecops" in domains:
        lanes.add("devsecops-review")
    if "platform" in domains:
        lanes.add("platform-review")
    if "architecture" in domains:
        lanes.add("architecture-review")

    artifact_paths = {item.get("artifact_path", "") for item in artifacts}
    artifact_types = {item.get("artifact_type", "") for item in artifacts}
    if "policy_as_code" in artifact_types or any(path.startswith("policies/opa/") for path in artifact_paths):
        lanes.add("policy-as-code-review")
    if any(path.startswith("schemas/") for path in artifact_paths):
        lanes.add("schema-review")
    if any(path.startswith("releases/") or path.startswith("docs/releases/") for path in artifact_paths):
        lanes.add("release-review")
    if any(path.startswith("generated/viewer/") or path.startswith("status/") for path in artifact_paths):
        lanes.add("viewer-status-review")
    return sorted(lanes)


def release_consideration(artifacts: list[dict]) -> str:
    paths = [item.get("artifact_path", "") for item in artifacts]
    types = {item.get("artifact_type", "") for item in artifacts}
    if any(path.startswith("releases/") or path.startswith("docs/releases/") for path in paths):
        return "baseline_release_review"
    if "policy_as_code" in types or any(path.startswith("schemas/") for path in paths):
        return "release_candidate_recommended"
    return "no_release_by_default"


def source_state(document: dict, artifacts: list[dict]) -> str:
    status = document.get("status")
    if status == "candidate":
        return "candidate_pending_similarity_review"
    if status == "draft" and not artifacts:
        return "draft_registered_no_lineage_required"
    if status == "draft":
        return "draft_with_lineage"
    if status == "superseded":
        return "superseded_source"
    if status == "retired":
        return "retired_source"
    return "active_source"


def suggested_validation(document: dict, artifacts: list[dict]) -> list[str]:
    validations = {
        "python3 scripts/validate_governance_repo.py",
        "python3 -m unittest discover -s tests",
    }
    domains = set(document.get("governance_domains", []))
    paths = [item.get("artifact_path", "") for item in artifacts]
    if "architecture" in domains or any(path.startswith("architecture/") for path in paths):
        validations.add("python3 scripts/validate_runtime_governance.py")
    if any(path.startswith("generated/viewer/") or path.startswith("status/") for path in paths):
        validations.add("python3 scripts/generate_status_viewer.py")
    if any(path.startswith("releases/") for path in paths):
        validations.add("verify release package metadata and checksums")
    return sorted(validations)


def build_report() -> dict:
    ensure_lineage_report()
    register = load_yaml(REGISTER_PATH)
    lineage = load_json(LINEAGE_JSON)
    lineage_by_source = {
        item["source_document"]: item.get("derived_artifacts", [])
        for item in lineage.get("lineage", [])
    }

    source_impacts = []
    domain_counter = Counter()
    status_counter = Counter()
    release_counter = Counter()
    artifact_type_counter = Counter()
    review_lane_counter = Counter()

    for document in register.get("documents", []):
        source_path = document["source_path"]
        artifacts = lineage_by_source.get(source_path, [])
        artifact_counts = Counter(item.get("artifact_type", "unknown") for item in artifacts)
        lanes = review_lanes(document, artifacts)
        release = release_consideration(artifacts)
        validations = suggested_validation(document, artifacts)

        for domain in document.get("governance_domains", []):
            domain_counter[domain] += 1
        status_counter[document.get("status", "unknown")] += 1
        release_counter[release] += 1
        artifact_type_counter.update(artifact_counts)
        review_lane_counter.update(lanes)

        source_impacts.append(
            {
                "id": document["id"],
                "title": document["title"],
                "status": document["status"],
                "source_path": source_path,
                "owner": document["owner"],
                "version": document["version"],
                "governance_domains": document.get("governance_domains", []),
                "derived_artifact_areas": document.get("derived_artifact_areas", []),
                "lineage_artifact_count": len(artifacts),
                "lineage_artifact_types": dict(sorted(artifact_counts.items())),
                "review_lanes": lanes,
                "release_consideration": release,
                "source_state": source_state(document, artifacts),
                "candidate_replacement_for": document.get("candidate_replacement_for", []),
                "supersedes": document.get("supersedes"),
                "superseded_by": document.get("superseded_by"),
                "similarity_assessment": document.get("similarity_assessment", {}),
                "suggested_validation": validations,
                "change_request_required_for_source_update": True,
                "representative_artifacts": [
                    item["artifact_path"]
                    for item in sorted(artifacts, key=lambda entry: entry.get("artifact_path", ""))[:10]
                ],
            }
        )

    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "inputs": {
            "source_document_register": rel(REGISTER_PATH),
            "source_lineage_report": rel(LINEAGE_JSON),
        },
        "summary": {
            "registered_source_documents": len(register.get("documents", [])),
            "source_documents_with_lineage": len(lineage_by_source),
            "derived_artifact_links": sum(item["lineage_artifact_count"] for item in source_impacts),
            "domains": dict(sorted(domain_counter.items())),
            "statuses": dict(sorted(status_counter.items())),
            "release_considerations": dict(sorted(release_counter.items())),
            "artifact_types": dict(sorted(artifact_type_counter.items())),
            "review_lanes": dict(sorted(review_lane_counter.items())),
        },
        "source_impacts": source_impacts,
        "open_questions": [
            "Is the new source document a new source, possible duplicate, or replacement candidate?",
            "Does the source document update change governance behavior or only explanatory text?",
            "Is the intended rollout report-only or blocking?",
            "Does the change require a release candidate or a new baseline release?",
            "Which downstream repositories need migration or communication?",
        ],
    }


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    lines = [
        "# Governance Change Impact Report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Inputs",
        "",
        f"- Source document register: `{report['inputs']['source_document_register']}`",
        f"- Source lineage report: `{report['inputs']['source_lineage_report']}`",
        "",
        "## Summary",
        "",
        f"- Registered source documents: `{summary['registered_source_documents']}`",
        f"- Source documents with lineage: `{summary['source_documents_with_lineage']}`",
        f"- Derived artifact links: `{summary['derived_artifact_links']}`",
        "",
        "## Domain Coverage",
        "",
        "| Domain | Source documents |",
        "|---|---:|",
    ]
    for domain, count in summary["domains"].items():
        lines.append(f"| `{domain}` | `{count}` |")

    lines.extend(["", "## Release Considerations", "", "| Consideration | Source documents |", "|---|---:|"])
    for consideration, count in summary["release_considerations"].items():
        lines.append(f"| `{consideration}` | `{count}` |")

    lines.extend(["", "## Review Lanes", "", "| Review lane | Source documents |", "|---|---:|"])
    for lane, count in summary["review_lanes"].items():
        lines.append(f"| `{lane}` | `{count}` |")

    lines.extend(["", "## Source Impact Details", ""])
    for item in report["source_impacts"]:
        lines.extend(
            [
                f"### `{item['id']}`",
                "",
                f"- Title: {item['title']}",
                f"- Source: `{item['source_path']}`",
                f"- Status: `{item['status']}`",
                f"- Owner: `{item['owner']}`",
                f"- Version: `{item['version']}`",
                f"- Domains: `{', '.join(item['governance_domains'])}`",
                f"- Lineage artifacts: `{item['lineage_artifact_count']}`",
                f"- Source state: `{item['source_state']}`",
                f"- Release consideration: `{item['release_consideration']}`",
                f"- Review lanes: `{', '.join(item['review_lanes'])}`",
                "",
                "Derived artifact areas:",
                "",
            ]
        )
        for area in item["derived_artifact_areas"]:
            lines.append(f"- `{area}`")
        if item["candidate_replacement_for"] or item["supersedes"] or item["superseded_by"] or item["similarity_assessment"]:
            lines.extend(["", "Replacement and similarity:", ""])
            if item["candidate_replacement_for"]:
                lines.append(f"- Candidate replacement for: `{', '.join(item['candidate_replacement_for'])}`")
            if item["supersedes"]:
                lines.append(f"- Supersedes: `{item['supersedes']}`")
            if item["superseded_by"]:
                lines.append(f"- Superseded by: `{item['superseded_by']}`")
            assessment = item["similarity_assessment"].get("assessment")
            if assessment:
                lines.append(f"- Similarity assessment: `{assessment}`")
        lines.extend(["", "Suggested validation:", ""])
        for validation in item["suggested_validation"]:
            lines.append(f"- `{validation}`")
        lines.extend(["", "Representative artifacts:", ""])
        for artifact in item["representative_artifacts"]:
            lines.append(f"- `{artifact}`")
        lines.append("")

    lines.extend(["## Open Questions For Change Requests", ""])
    for question in report["open_questions"]:
        lines.append(f"- {question}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    try:
        report = build_report()
    except RuntimeError as issue:
        print(f"Error: {issue}", file=sys.stderr)
        return 1
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(report), encoding="utf-8")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
