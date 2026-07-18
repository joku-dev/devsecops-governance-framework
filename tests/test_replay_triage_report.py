from pathlib import Path
import json
import sys
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_replay_triage_report import build_report, relationship


def trust_record(*, repository="owner/repo", commit="commit-a", run="1", artifact="evidence",
                 subject_id="control_evaluation_report", digest="a" * 64, artifact_digest=None,
                 replay_result="pass"):
    source = {
        "repository_id": repository, "commit_id": commit, "workflow_name": "Governance",
        "run_id": run, "run_attempt": 1, "artifact_name": artifact,
    }
    if artifact_digest:
        source["artifact_digest"] = artifact_digest
    return {
        "model_id": "evidence-trust-model-v1", "effective_level": "integrity_verified",
        "checks": [{"id": "replay_key_unique", "result": replay_result, "reason": "stored"}],
        "capture": {"source": source, "subjects": [{"id": subject_id, "digest": digest}]},
    }


def row(*, generated_at, source_file, trust, domain="devsecops"):
    source = trust["capture"]["source"]
    payload = {
        "repository_id": source["repository_id"], "generated_at": generated_at,
        "pipeline": {"pipeline_run_id": source["run_id"], "event": "push"},
        "repository": {"commit_id": source["commit_id"], "branch": "main"}, "trust": trust,
    }
    return {"domain": domain, "source_file": source_file, "payload": payload, "trust": trust, "generated_at": generated_at}


class ReplayTriageReportTests(unittest.TestCase):
    def test_current_report_is_schema_valid_and_preserves_decision_boundaries(self):
        report = json.loads((ROOT / "generated/reports/replay-triage.json").read_text())
        schema = json.loads((ROOT / "schemas/replay-triage.schema.json").read_text())
        Draft202012Validator(schema).validate(report)
        self.assertEqual(report["enforcement"], "report_only")
        self.assertEqual(report["summary"]["recorded_failures"], 3)
        self.assertEqual(report["summary"]["recalculated_failures"], 1)
        self.assertEqual(report["summary"]["legacy_assessments_superseded"], 2)
        self.assertEqual(report["summary"]["official_latest_findings"], 1)
        self.assertFalse(any(report["decision_boundary"].values()))

    def test_cross_commit_without_artifact_digest_remains_actionable(self):
        prior = row(generated_at="2026-07-17T10:00:00Z", source_file="status/results/prior.json",
                    trust=trust_record(commit="commit-a", run="1"))
        current = row(generated_at="2026-07-17T11:00:00Z", source_file="status/results/current.json",
                      trust=trust_record(commit="commit-b", run="2", replay_result="fail"))
        report = build_report(rows=[prior, current], official_latest={current["source_file"]})
        assessment = report["assessments"][1]
        self.assertEqual(assessment["recalculated_result"], "fail")
        self.assertEqual(assessment["classification"], "cross_commit_reuse")
        self.assertEqual(assessment["recommended_action"], "reverify_with_artifact_digest")

    def test_historical_failure_can_be_explained_without_rewriting_it(self):
        prior = row(generated_at="2026-07-17T10:00:00Z", source_file="status/results/prior.json",
                    trust=trust_record(commit="commit-a", run="1"))
        current = row(generated_at="2026-07-17T11:00:00Z", source_file="status/results/current.json",
                      trust=trust_record(commit="commit-b", run="2", artifact_digest="b" * 64, replay_result="fail"))
        report = build_report(rows=[prior, current], official_latest=set())
        assessment = report["assessments"][1]
        self.assertEqual(assessment["recorded_result"], "fail")
        self.assertEqual(assessment["recalculated_result"], "pass")
        self.assertEqual(assessment["classification"], "legacy_assessment_superseded")
        self.assertFalse(report["decision_boundary"]["historical_snapshots_rewritten"])

    def test_relationship_distinguishes_cross_repository_and_cross_subject(self):
        current = row(generated_at="2026-07-17T11:00:00Z", source_file="status/results/current.json",
                      trust=trust_record(repository="owner/current", run="2"))
        other_repo = row(generated_at="2026-07-17T10:00:00Z", source_file="status/results/other.json",
                         trust=trust_record(repository="owner/other", run="1"))
        other_subject = row(generated_at="2026-07-17T10:00:00Z", source_file="status/results/subject.json",
                            trust=trust_record(subject_id="sbom", run="1"))
        self.assertEqual(relationship(current, other_repo)["classification"], "cross_repository_reuse")
        self.assertEqual(relationship(current, other_subject)["classification"], "cross_subject_conflict")


if __name__ == "__main__":
    unittest.main()
