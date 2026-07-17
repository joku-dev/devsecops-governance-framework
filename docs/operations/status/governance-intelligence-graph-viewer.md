# Governance Intelligence Graph Viewer

## Purpose

The Governance Intelligence Graph is a generated, read-only projection of governed repository data. It makes relationships between source documents, derived artifacts, repositories, workflow runs, commits, baselines, evidence records, Trust assessments, scanners, and result snapshots explorable in the existing static viewer.

It improves presentation and investigation without introducing a second source of truth. Git-tracked models, status indexes, result snapshots, and released packages remain authoritative.

## Current Contract

| Concern | Path |
|---|---|
| Graph schema | `schemas/governance-graph.schema.json` |
| Deterministic generator | `scripts/generate_governance_graph.py` |
| Generated graph | `generated/graph/governance-graph.json` |
| Viewer generator | `scripts/generate_status_viewer.py` |
| Generated viewer | `generated/viewer/status-viewer.html` |

The graph currently uses these versioned inputs:

- `model/documents/source-document-register.yaml`
- `generated/reports/source-lineage-report.json`
- `status/repository-results-index.json`
- `status/architecture-results-index.json`
- `status/typed-evidence-results-index.json`

Only the latest result selected by each official status index is projected into the operational graph. Historical snapshots remain available through the indexes and viewer history tables.

## Generate Locally

Run the graph generator before the viewer generator:

```bash
python3 scripts/generate_source_lineage_report.py
python3 scripts/generate_governance_graph.py
python3 scripts/generate_status_viewer.py
```

Then open `generated/viewer/status-viewer.html` or serve the repository through the documented local viewer flow.

## Use During A Demo

1. Open **Governance Graph** in the viewer navigation.
2. Start with **Operational flow** to show repository-to-run-to-baseline, commit, Trust, evidence, and snapshot relationships.
3. Search for `ha-CPsWMS` to focus the current demo repository and its immediate relationships.
4. Select a node to inspect properties plus incoming and outgoing relationships.
5. Switch to **Source lineage** to explain how registered governance sources derive machine-readable and human-readable artifacts.
6. Use **All graph data** or the node-type filter for deeper review.

The visualization is implemented with native SVG and browser JavaScript. It therefore works offline and on GitHub Pages without adding a third-party runtime dependency.

## Trust Boundary And Invariants

- The graph is derived output, not an approval record or policy decision.
- The viewer has no write-back path.
- Graph selection never changes the official latest-result selection.
- Graph generation does not alter control, OPA, baseline, release, or enforcement semantics.
- Missing or `unverified` Trust remains visible as such; the graph never upgrades evidence Trust.
- Intake remains report-only unless an independent governance change explicitly enables blocking behavior.

## Future Evolution

The JSON contract deliberately separates graph generation from rendering. A later phase can import the same nodes and edges into Cytoscape.js, Neo4j, Backstage, or another professional UI without changing the authoritative governance model. Before such a migration, define authentication, authorization, provenance, retention, synchronization, and write-back boundaries explicitly.

## Validation

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```
