from pathlib import Path
import importlib.util
import json
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def load_script():
    path = ROOT / "scripts" / "generate_governance_graph.py"
    spec = importlib.util.spec_from_file_location("generate_governance_graph", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


graph_generator = load_script()


def load_viewer_script():
    path = ROOT / "scripts" / "generate_status_viewer.py"
    spec = importlib.util.spec_from_file_location("generate_status_viewer", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


viewer_generator = load_viewer_script()


class GovernanceGraphTests(unittest.TestCase):
    def test_graph_is_deterministic_schema_valid_and_has_no_dangling_edges(self):
        first = graph_generator.build_graph(ROOT)
        second = graph_generator.build_graph(ROOT)
        self.assertEqual(first, second)

        schema = json.loads((ROOT / "schemas" / "governance-graph.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema).validate(first)
        node_ids = {node["id"] for node in first["nodes"]}
        self.assertEqual(len(node_ids), len(first["nodes"]))
        self.assertTrue(all(edge["source"] in node_ids and edge["target"] in node_ids for edge in first["edges"]))

    def test_graph_projects_current_mainline_results_and_trust(self):
        graph = graph_generator.build_graph(ROOT)
        repositories = [
            node for node in graph["nodes"]
            if node["type"] == "Repository" and node["properties"].get("repository_id") == "joku-dev/ha-CPsWMS"
        ]
        self.assertEqual(len(repositories), 1)
        trust_nodes = [
            node for node in graph["nodes"]
            if node["type"] == "TrustAssessment"
            and node["properties"].get("effective_level") == "integrity_verified"
        ]
        self.assertGreaterEqual(len(trust_nodes), 3)
        self.assertIn("DERIVES", graph["summary"]["edge_types"])
        self.assertIn("HAS_RESULT", graph["summary"]["edge_types"])

    def test_viewer_section_embeds_read_only_graph_controls(self):
        graph = graph_generator.build_graph(ROOT)
        section = viewer_generator.build_governance_graph_section(graph)
        self.assertIn('id="governance-graph"', section)
        self.assertIn('id="graph-scope-filter"', section)
        self.assertIn('id="governance-graph-data"', section)
        self.assertIn("Git and versioned JSON remain authoritative", section)
        self.assertIn('"graph_id":"governance-intelligence-graph"', section)


if __name__ == "__main__":
    unittest.main()
