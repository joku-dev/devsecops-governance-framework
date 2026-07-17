from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


provenance = load_script("record_evidence_agent_provenance")


class EvidenceAgentProvenanceTests(unittest.TestCase):
    def test_example_validates(self):
        schema = json.loads((ROOT / "schemas" / "evidence-agent-provenance.schema.json").read_text())
        example = json.loads((ROOT / "docs" / "examples" / "evidence-agent-provenance.example.json").read_text())
        Draft202012Validator(schema).validate(example)

    def test_explicit_record_is_idempotent(self):
        args = type("Args", (), {
            "repository_id": "owner/repo", "evidence_type": "vulnerability_scan",
            "subject_id": "report", "subject_digest": "a" * 64, "source_file": "status/result.json",
            "agent_id": "evidence-and-intake", "role_version": "1.0.0", "skill": "evidence-and-intake",
            "provider": "codex", "model": "", "involvement": "reviewed", "dispatch_id": "dispatch-1",
            "run_type": "provider_review", "dispatch_source": "manual", "dispatch_timestamp": "",
            "recorded_at": "2026-07-17T18:00:00Z", "notes": "review"
        })()
        payload = provenance.build_record(args)
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "owner__repo" / "record.json"
            first = provenance.write_record(path, payload)
            second = provenance.write_record(path, payload)
            self.assertEqual(first, second)
            self.assertEqual(json.loads(path.read_text()), payload)


if __name__ == "__main__":
    unittest.main()
