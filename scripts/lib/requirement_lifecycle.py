"""Hybrid document and Git-native governance requirement lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from difflib import SequenceMatcher
from hashlib import sha256
import json
import re
from pathlib import Path

import yaml


CLASSIFICATIONS = {"duplicate", "new", "extend", "change", "supersede", "conflict"}
RELATIONSHIP_BY_CLASSIFICATION = {
    "duplicate": "duplicates",
    "extend": "extends",
    "change": "revises",
    "supersede": "supersedes",
    "conflict": "conflicts_with",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def normalize(statement: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", statement.lower()).split())


def load_yaml(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected mapping in {path}")
    return value


def write_yaml(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_requirement_table(path: Path) -> list[dict]:
    requirements = []
    pattern = re.compile(r"^\| `([^`]+)` \| ([^|]+) \| ([^|]+) \| (.*) \|$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        source_id, strength, context, statement = (part.strip() for part in match.groups())
        strength = strength.upper()
        if strength not in {"MUST", "SHOULD", "MAY", "REQUIREMENT"}:
            strength = "REQUIREMENT"
        requirements.append({
            "source_requirement_id": source_id,
            "normative_strength": strength,
            "context": context,
            "statement": statement.replace("\\|", "|").strip(),
        })
    if not requirements:
        raise ValueError(f"no requirement rows found in {path}")
    return requirements


def parse_native_requirement(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)(.*)\Z", content, re.DOTALL)
    if not match:
        raise ValueError(f"native requirement must start with YAML frontmatter: {path}")
    metadata = yaml.safe_load(match.group(1))
    statement = match.group(2).strip()
    if not isinstance(metadata, dict) or not statement:
        raise ValueError(f"native requirement metadata and statement are required: {path}")
    required = {"id", "title", "normative_strength", "domain", "owner", "decision_ref"}
    missing = sorted(required - metadata.keys())
    extra = sorted(metadata.keys() - required)
    if missing or extra:
        raise ValueError(f"native requirement metadata mismatch; missing={missing}, extra={extra}")
    if metadata["normative_strength"] not in {"MUST", "SHOULD", "MAY", "REQUIREMENT"}:
        raise ValueError("invalid native requirement normative_strength")
    return {**metadata, "statement": statement}


def active_revisions(catalog: dict) -> list[tuple[str, dict]]:
    active = []
    for requirement in catalog.get("requirements", []):
        revision_number = requirement.get("active_revision")
        revision = next((item for item in requirement["revisions"] if item["revision"] == revision_number), None)
        if revision and revision["status"] == "effective":
            active.append((requirement["id"], revision))
    return active


def analyze_statement(statement: str, catalog: dict, proposal_candidates: list[tuple[str, str]] | None = None) -> dict:
    normalized = normalize(statement)
    matches = []
    for requirement_id, revision in active_revisions(catalog):
        similarity = SequenceMatcher(None, normalized, normalize(revision["statement"])).ratio()
        matches.append({"requirement_id": requirement_id, "similarity": round(similarity, 4)})
    for proposal_id, candidate_statement in proposal_candidates or []:
        similarity = SequenceMatcher(None, normalized, normalize(candidate_statement)).ratio()
        matches.append({"requirement_id": proposal_id, "similarity": round(similarity, 4)})
    matches.sort(key=lambda item: (-item["similarity"], item["requirement_id"]))
    candidates = matches[:5]
    best = candidates[0]["similarity"] if candidates else 0.0
    if best == 1.0:
        classification, method, confidence = "duplicate", "deterministic_exact", 1.0
    elif best >= 0.86:
        classification, method, confidence = "change", "deterministic_similarity", best
    else:
        classification, method, confidence = "new", "no_catalog_match", round(1.0 - best, 4)
    return {
        "suggested_classification": classification,
        "confidence": confidence,
        "candidate_matches": candidates,
        "method": method,
    }


def shortlist_candidates(statement: str, candidates: list[tuple[str, str]], limit: int = 20) -> list[tuple[str, str]]:
    """Select likely matches cheaply before the more expensive sequence comparison."""
    normalized = normalize(statement)
    tokens = set(normalized.split())
    exact = []
    ranked = []
    for candidate_id, candidate_statement in candidates:
        candidate_normalized = normalize(candidate_statement)
        if candidate_normalized == normalized:
            exact.append((candidate_id, candidate_statement))
            continue
        candidate_tokens = set(candidate_normalized.split())
        union = tokens | candidate_tokens
        overlap = len(tokens & candidate_tokens) / len(union) if union else 0.0
        if overlap >= 0.25:
            ranked.append((overlap, candidate_id, candidate_statement))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return exact + [(item[1], item[2]) for item in ranked[:limit]]


def build_source_case(*, case_id: str, source: dict, source_path: Path, catalog: dict) -> dict:
    proposals = []
    for position, row in enumerate(parse_requirement_table(source_path), start=1):
        proposals.append({
            "proposal_id": f"{case_id}-P{position:04d}",
            "source_requirement_id": row["source_requirement_id"],
            "title": row["context"],
            "statement": row["statement"],
            "normative_strength": row["normative_strength"],
            "domain": source["governance_domains"][0],
            "analysis": analyze_statement(row["statement"], catalog),
            "decision": None,
            "activation": None,
        })
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "intake_type": "source_document",
        "status": "decision_required",
        "created_at": utc_now(),
        "source": {
            "source_id": source["id"],
            "source_path": source["source_path"],
            "source_sha256": digest(source_path),
            "owner": source["owner"],
            "decision_ref": "docs/governance/change-requests/GCR-2026-143-hybrid-requirement-lifecycle.md",
        },
        "proposals": proposals,
    }


def build_native_case(*, case_id: str, source_id: str, source_path: Path, owner: str, domain: str,
                      title: str, statement: str, strength: str, decision_ref: str, catalog: dict,
                      source_file: Path | None = None) -> dict:
    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "intake_type": "native_git",
        "status": "decision_required",
        "created_at": utc_now(),
        "source": {
            "source_id": source_id,
            "source_path": source_path.as_posix(),
            "source_sha256": digest(source_file or source_path),
            "owner": owner,
            "decision_ref": decision_ref,
        },
        "proposals": [{
            "proposal_id": f"{case_id}-P0001",
            "source_requirement_id": source_id,
            "title": title,
            "statement": statement,
            "normative_strength": strength,
            "domain": domain,
            "analysis": analyze_statement(statement, catalog),
            "decision": None,
            "activation": None,
        }],
    }


def record_decision(case: dict, *, proposal_id: str, disposition: str, classification: str,
                    target_requirement_id: str | None, decided_by: str, decision_role: str,
                    rationale: str, authorized_derivations: list[str], runtime_enforcement: str) -> None:
    if classification not in CLASSIFICATIONS:
        raise ValueError(f"unsupported classification: {classification}")
    if disposition not in {"approve", "reject"}:
        raise ValueError("disposition must be approve or reject")
    if classification != "new" and disposition == "approve" and not target_requirement_id:
        raise ValueError(f"{classification} approval requires a target requirement")
    if classification == "new" and target_requirement_id:
        raise ValueError("new classification must not have a target requirement")
    if runtime_enforcement == "blocking":
        raise ValueError("blocking enforcement requires a separate enforcement authorization")
    proposal = next((item for item in case["proposals"] if item["proposal_id"] == proposal_id), None)
    if proposal is None:
        raise ValueError(f"unknown proposal: {proposal_id}")
    if proposal["decision"] is not None:
        raise ValueError(f"decision already recorded for {proposal_id}")
    proposal["decision"] = {
        "disposition": disposition,
        "classification": classification,
        "target_requirement_id": target_requirement_id,
        "decided_by": decided_by,
        "decision_role": decision_role,
        "decided_at": utc_now(),
        "rationale": rationale,
        "authorized_derivations": authorized_derivations,
        "runtime_enforcement": runtime_enforcement,
    }
    case["status"] = "approved" if all(item["decision"] is not None for item in case["proposals"]) else "decision_required"


def _update_case_status(case: dict) -> None:
    open_items = [item for item in case["proposals"] if item["decision"] is None]
    incomplete = [
        item for item in case["proposals"]
        if item["decision"] is not None
        and item["decision"]["disposition"] == "approve"
        and item["decision"]["classification"] != "duplicate"
        and item["activation"] is None
    ]
    progressed = any(item["decision"] is not None or item["activation"] is not None for item in case["proposals"])
    if not open_items and not incomplete:
        case["status"] = "activated"
    elif progressed:
        case["status"] = "partially_activated"
    else:
        case["status"] = "decision_required"


def activate_case(case: dict, catalog: dict, *, effective_from: str, commit: str,
                  proposal_ids: list[str] | None = None) -> None:
    """Activate approved proposals, optionally as an explicit partial batch."""
    selected = set(proposal_ids or [item["proposal_id"] for item in case["proposals"]])
    known_proposals = {item["proposal_id"] for item in case["proposals"]}
    unknown = selected - known_proposals
    if unknown:
        raise ValueError(f"unknown proposals: {', '.join(sorted(unknown))}")
    if not proposal_ids and any(item["decision"] is None for item in case["proposals"]):
        raise ValueError("all proposals require an explicit decision before full-case activation")
    known = {item["id"]: item for item in catalog["requirements"]}
    for proposal in case["proposals"]:
        if proposal["proposal_id"] not in selected:
            continue
        if proposal["activation"] is not None:
            raise ValueError(f"proposal already activated: {proposal['proposal_id']}")
        decision = proposal["decision"]
        if decision is None:
            raise ValueError(f"proposal requires an explicit decision: {proposal['proposal_id']}")
        if decision["disposition"] == "reject" or decision["classification"] == "duplicate":
            continue
        if decision["classification"] == "conflict":
            raise ValueError("an approved conflict must be resolved by a later change or supersede decision before activation")
        target_id = decision["target_requirement_id"]
        if decision["classification"] == "new" or decision["classification"] == "extend":
            requirement_id = f"GRQ-{catalog['next_sequence']:06d}"
            catalog["next_sequence"] += 1
            requirement = {"id": requirement_id, "active_revision": None, "revisions": []}
            catalog["requirements"].append(requirement)
            known[requirement_id] = requirement
        else:
            if target_id not in known:
                raise ValueError(f"unknown target requirement: {target_id}")
            requirement_id = target_id
            requirement = known[target_id]
        revision_number = len(requirement["revisions"]) + 1
        relationships = [{"type": "derived_from", "target": proposal["source_requirement_id"]}]
        relationship = RELATIONSHIP_BY_CLASSIFICATION.get(decision["classification"])
        if relationship and target_id:
            relation_target = target_id
            if decision["classification"] in {"change", "supersede"}:
                relation_target = f"{target_id}@rev{revision_number - 1}"
            relationships.append({"type": relationship, "target": relation_target})
        requirement["revisions"].append({
            "revision": revision_number,
            "status": "effective",
            "title": proposal["title"],
            "statement": proposal["statement"],
            "normative_strength": proposal["normative_strength"],
            "domain": proposal["domain"],
            "owner": case["source"]["owner"],
            "approved_at": decision["decided_at"],
            "effective_from": effective_from,
            "effective_until": None,
            "source_refs": [proposal["source_requirement_id"]],
            "relationships": relationships,
            "decision_ref": case["source"]["decision_ref"],
            "authorized_derivations": decision["authorized_derivations"],
            "runtime_enforcement": decision["runtime_enforcement"],
        })
        requirement["active_revision"] = revision_number
        proposal["activation"] = {
            "requirement_id": requirement_id,
            "revision": revision_number,
            "effective_from": effective_from,
            "commit": commit,
        }
    _update_case_status(case)


def render_requirement_markdown(requirement: dict) -> str:
    revision = next(item for item in requirement["revisions"] if item["revision"] == requirement["active_revision"])
    metadata = {
        "id": requirement["id"],
        "revision": revision["revision"],
        "status": revision["status"],
        "normative_strength": revision["normative_strength"],
        "domain": revision["domain"],
        "owner": revision["owner"],
        "effective_from": revision["effective_from"],
        "source_refs": revision["source_refs"],
        "decision_ref": revision["decision_ref"],
    }
    return "---\n" + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).strip() + "\n---\n\n" + f"# {requirement['id']}: {revision['title']}\n\n{revision['statement']}\n"
