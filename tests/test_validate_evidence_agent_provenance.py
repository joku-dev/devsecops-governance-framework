from pathlib import Path
import json
import tempfile
import unittest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from validate_evidence_agent_provenance import validate_record, SCHEMA_PATH


class ValidateEvidenceAgentProvenanceTests(unittest.TestCase):
    def test_matching_subject_digest_passes(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            source = root / "source.json"
            source.write_text(json.dumps({"trust": {"capture": {"subjects": [{"id": "report", "digest": "a" * 64}]}}}))
            record = {
                "schema_version": "1.0.0", "record_type": "evidence-agent-provenance", "provenance_id": "p1",
                "enforcement": "report_only", "recorded_at": "2026-07-17T18:00:00Z",
                "evidence": {"repository_id": "owner/repo", "evidence_type": "vulnerability_scan", "subject_id": "report", "subject_digest": "a" * 64, "source_file": "source.json"},
                "agent": {"id": "evidence-and-intake", "role_version": "1.0.0"}, "involvement": "reviewed",
                "dispatch": {"id": "d1", "run_type": "manual", "source": "test"},
            }
            record_path = root / "record.json"
            record_path.write_text(json.dumps(record))
            old_root = __import__("validate_evidence_agent_provenance").ROOT
            try:
                __import__("validate_evidence_agent_provenance").ROOT = root
                self.assertEqual(validate_record(record_path, schema), [])
            finally:
                __import__("validate_evidence_agent_provenance").ROOT = old_root


if __name__ == "__main__":
    unittest.main()
