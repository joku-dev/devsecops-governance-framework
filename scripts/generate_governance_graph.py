#!/usr/bin/env python3
"""Generate a deterministic read-only graph from governed repository artifacts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import json

import yaml


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "generated" / "graph" / "governance-graph.json"
SOURCE_INPUTS = [
    "model/documents/source-document-register.yaml",
    "generated/reports/source-lineage-report.json",
    "status/repository-results-index.json",
    "status/architecture-results-index.json",
    "status/typed-evidence-results-index.json",
]


def load_json(root: Path, relative_path: str) -> dict:
    path = root / relative_path
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(root: Path, relative_path: str) -> dict:
    path = root / relative_path
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


class GraphBuilder:
    def __init__(self) -> None:
        self.nodes: dict[str, dict] = {}
        self.edges: dict[str, dict] = {}

    def add_node(self, node_id: str, node_type: str, label: str, **properties) -> str:
        node = {
            "id": node_id,
            "type": node_type,
            "label": label,
            "properties": {key: value for key, value in properties.items() if value is not None and value != ""},
        }
        existing = self.nodes.get(node_id)
        if existing is not None and existing != node:
            merged = dict(existing["properties"])
            merged.update(node["properties"])
            existing["properties"] = merged
            if existing["label"] == node_id:
                existing["label"] = label
        else:
            self.nodes[node_id] = node
        return node_id

    def add_edge(self, edge_type: str, source: str, target: str, **properties) -> str:
        edge_id = f"{edge_type}:{source}->{target}"
        edge = {
            "id": edge_id,
            "type": edge_type,
            "source": source,
            "target": target,
            "properties": {key: value for key, value in properties.items() if value is not None and value != ""},
        }
        self.edges[edge_id] = edge
        return edge_id


def graph_timestamp(*documents: dict) -> str:
    timestamps = sorted(
        value
        for document in documents
        if document
        for value in [document.get("generated_at")]
        if isinstance(value, str) and value
    )
    return timestamps[-1] if timestamps else "1970-01-01T00:00:00Z"


def add_lineage(builder: GraphBuilder, register: dict, lineage: dict) -> None:
    register_by_path = {
        document.get("source_path"): document
        for document in register.get("documents", [])
        if document.get("source_path")
    }
    for entry in lineage.get("lineage", []):
        path = entry.get("source_document", "unknown")
        metadata = register_by_path.get(path, {})
        source_id = builder.add_node(
            f"source:{path}",
            "SourceDocument",
            metadata.get("title") or Path(path).stem,
            path=path,
            document_id=metadata.get("id"),
            status=metadata.get("status", "unregistered"),
            owner=metadata.get("owner"),
            governance_domains=metadata.get("governance_domains", []),
        )
        for artifact in entry.get("derived_artifacts", []):
            artifact_path = artifact.get("artifact_path", "unknown")
            artifact_id = builder.add_node(
                f"artifact:{artifact_path}",
                "Artifact",
                artifact_path,
                path=artifact_path,
                artifact_type=artifact.get("artifact_type", "unknown"),
                exists=artifact.get("exists", False),
            )
            builder.add_edge(
                "DERIVES",
                source_id,
                artifact_id,
                role=artifact.get("role", "unknown"),
            )


def load_snapshot(root: Path, result: dict) -> dict:
    source_file = result.get("source_file")
    if not source_file:
        return {}
    return load_json(root, source_file)


def add_result_index(builder: GraphBuilder, root: Path, index: dict, domain: str, baseline_field: str) -> None:
    for repository in index.get("repositories", []):
        repository_id = repository.get("repository_id", "unknown")
        repo_node = builder.add_node(
            f"repository:{repository_id}",
            "Repository",
            repository_id,
            repository_id=repository_id,
        )
        result = repository.get("latest_result", {})
        if not result:
            continue
        snapshot = load_snapshot(root, result)
        pipeline = snapshot.get("pipeline", {})
        repository_context = snapshot.get("repository", {})
        run_id = str(result.get("pipeline_run_id", "unknown"))
        generated_at = result.get("generated_at", "unknown")
        run_node = builder.add_node(
            f"run:{domain}:{repository_id}:{run_id}:{generated_at}",
            "WorkflowRun",
            f"{domain}: {run_id}",
            domain=domain,
            run_id=run_id,
            status=result.get("status", "unknown"),
            generated_at=generated_at,
            event=result.get("pipeline_event") or pipeline.get("event", "unknown"),
            branch=result.get("branch") or repository_context.get("branch", "unknown"),
            url=result.get("pipeline_url") or pipeline.get("pipeline_url", ""),
        )
        builder.add_edge("HAS_RESULT", repo_node, run_node, domain=domain, latest=True)

        commit_id = result.get("commit_id", "unknown")
        commit_node = builder.add_node(
            f"commit:{repository_id}:{commit_id}",
            "Commit",
            commit_id[:12],
            repository_id=repository_id,
            commit_id=commit_id,
        )
        builder.add_edge("EVALUATES_COMMIT", run_node, commit_node)

        baseline = result.get(baseline_field)
        if baseline:
            baseline_node = builder.add_node(
                f"baseline:{domain}:{baseline}",
                "Baseline",
                baseline,
                domain=domain,
                baseline_ref=baseline,
            )
            builder.add_edge("USES_BASELINE", run_node, baseline_node)

        trust = result.get("trust", {})
        trust_node = builder.add_node(
            f"trust:{domain}:{repository_id}:{run_id}:{generated_at}",
            "TrustAssessment",
            trust.get("effective_level", "unverified"),
            domain=domain,
            effective_level=trust.get("effective_level", "unverified"),
            assessment_status=trust.get("assessment_status", "not_available"),
            verified_at=trust.get("verified_at"),
            check_summary=trust.get("check_summary", {}),
        )
        builder.add_edge("HAS_TRUST_ASSESSMENT", run_node, trust_node)

        source_file = result.get("source_file")
        if source_file:
            snapshot_node = builder.add_node(
                f"snapshot:{source_file}",
                "ResultSnapshot",
                Path(source_file).name,
                path=source_file,
                domain=domain,
            )
            builder.add_edge("RECORDED_IN", run_node, snapshot_node)


def add_typed_evidence(builder: GraphBuilder, index: dict) -> None:
    for repository in index.get("repositories", []):
        repository_id = repository.get("repository_id", "unknown")
        repo_node = builder.add_node(
            f"repository:{repository_id}",
            "Repository",
            repository_id,
            repository_id=repository_id,
        )
        result = repository.get("latest_result", {})
        if not result:
            continue
        run_id = str(result.get("pipeline_run_id", "unknown"))
        generated_at = result.get("generated_at", "unknown")
        run_node = builder.add_node(
            f"run:typed-evidence:{repository_id}:{run_id}:{generated_at}",
            "WorkflowRun",
            f"typed evidence: {run_id}",
            domain="typed_evidence",
            run_id=run_id,
            event=result.get("pipeline_event", "unknown"),
            branch=result.get("branch", "unknown"),
            generated_at=generated_at,
            url=result.get("pipeline_url", ""),
        )
        builder.add_edge("HAS_RESULT", repo_node, run_node, domain="typed_evidence", latest=True)

        evidence_type = result.get("evidence_type", "unknown")
        evidence_node = builder.add_node(
            f"evidence:{repository_id}:{run_id}:{evidence_type}:{generated_at}",
            "EvidenceRecord",
            evidence_type,
            evidence_type=evidence_type,
            collector_status=result.get("collector_status", "unknown"),
            enforcement=result.get("enforcement", "report_only"),
            finding_count=result.get("finding_count", 0),
            max_severity=result.get("max_severity", "unknown"),
            freshness=result.get("freshness", "not_evaluated"),
            content_integrity=result.get("content_integrity", "not_evaluated"),
            subject_binding=result.get("subject_binding", {}),
        )
        builder.add_edge("HAS_EVIDENCE", run_node, evidence_node)

        trust = result.get("trust", {})
        trust_node = builder.add_node(
            f"trust:typed-evidence:{repository_id}:{run_id}:{generated_at}",
            "TrustAssessment",
            trust.get("effective_level", "unverified"),
            domain="typed_evidence",
            effective_level=trust.get("effective_level", "unverified"),
            assessment_status=trust.get("assessment_status", "not_available"),
            verified_at=trust.get("verified_at"),
            check_summary=trust.get("check_summary", {}),
        )
        builder.add_edge("HAS_TRUST_ASSESSMENT", evidence_node, trust_node)

        scanner = result.get("scanner", {})
        if scanner.get("name"):
            scanner_key = f"{scanner['name']}:{scanner.get('version', 'unknown')}"
            scanner_node = builder.add_node(
                f"scanner:{scanner_key}",
                "Scanner",
                scanner_key,
                name=scanner.get("name"),
                version=scanner.get("version"),
            )
            builder.add_edge("PRODUCED_BY", evidence_node, scanner_node)

        source_file = result.get("source_file")
        if source_file:
            snapshot_node = builder.add_node(
                f"snapshot:{source_file}",
                "ResultSnapshot",
                Path(source_file).name,
                path=source_file,
                domain="typed_evidence",
            )
            builder.add_edge("RECORDED_IN", evidence_node, snapshot_node)


def build_graph(root: Path = ROOT) -> dict:
    register = load_yaml(root, SOURCE_INPUTS[0])
    lineage = load_json(root, SOURCE_INPUTS[1])
    repository_index = load_json(root, SOURCE_INPUTS[2])
    architecture_index = load_json(root, SOURCE_INPUTS[3])
    typed_index = load_json(root, SOURCE_INPUTS[4])

    builder = GraphBuilder()
    add_lineage(builder, register, lineage)
    add_result_index(builder, root, repository_index, "devsecops", "governance_baseline_ref")
    add_result_index(builder, root, architecture_index, "architecture", "architecture_baseline_ref")
    add_typed_evidence(builder, typed_index)

    nodes = sorted(builder.nodes.values(), key=lambda item: item["id"])
    edges = sorted(builder.edges.values(), key=lambda item: item["id"])
    node_ids = {node["id"] for node in nodes}
    dangling = [edge["id"] for edge in edges if edge["source"] not in node_ids or edge["target"] not in node_ids]
    if dangling:
        raise ValueError(f"Graph contains dangling edges: {dangling}")

    return {
        "schema_version": "1.0.0",
        "graph_id": "governance-intelligence-graph",
        "generated_at": graph_timestamp(lineage, repository_index, architecture_index, typed_index),
        "source_inputs": SOURCE_INPUTS,
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "node_types": dict(sorted(Counter(node["type"] for node in nodes).items())),
            "edge_types": dict(sorted(Counter(edge["type"] for edge in edges).items())),
        },
        "nodes": nodes,
        "edges": edges,
    }


def main() -> int:
    payload = build_graph()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(payload['nodes'])} nodes, {len(payload['edges'])} edges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
