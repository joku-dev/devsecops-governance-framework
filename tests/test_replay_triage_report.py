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
                 replay_result="pass", evidence_type=None, subjects=None):
    source = {
        "repository_id": repository, "commit_id": commit, "workflow_name": "Governance",
        "run_id": run, "run_attempt": 1, "artifact_name": artifact,
    }
    if artifact_digest:
        source["artifact_digest"] = artifact_digest
    capture = {"source": source, "subjects": subjects or [{"id": subject_id, "digest": digest}]}
    if evidence_type:
        capture["evidence_type"] = evidence_type
    return {
        "model_id": "evidence-trust-model-v1", "effective_level": "integrity_verified",
        "checks": [{"id": "replay_key_unique", "result": replay_result, "reason": "stored"}],
        "capture": capture,
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
        assessments = report["assessments"]
        summary = report["summary"]
        self.assertEqual(summary["assessments"], len(assessments))
        self.assertEqual(summary["recorded_failures"], sum(row["recorded_result"] == "fail" for row in assessments))
        self.assertEqual(summary["recalculated_failures"], sum(row["recalculated_result"] == "fail" for row in assessments))
        self.assertEqual(
            summary["legacy_assessments_superseded"],
            sum(row["classification"] == "legacy_assessment_superseded" for row in assessments),
        )
        latest_findings = [
            row["source_file"]
            for row in assessments
            if row["official_latest"] and row["recalculated_result"] == "fail"
        ]
        self.assertEqual(summary["official_latest_findings"], len(latest_findings))
        self.assertEqual(report["official_latest_findings"], latest_findings)
        self.assertFalse(any(report["decision_boundary"].values()))

    def test_all_intake_workflows_regenerate_and_propose_replay_triage(self):
        from publish_operational_update import allowed
        for workflow_name in (
            "intake-governance-result.yml",
            "intake-architecture-result.yml",
            "intake-evidence-trust.yml",
        ):
            content = (ROOT / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")
            self.assertGreaterEqual(content.count("python3 scripts/generate_replay_triage_report.py"), 1)
            self.assertGreaterEqual(content.count("python3 scripts/generate_status_viewer.py"), 1)
            self.assertLess(
                content.index("python3 scripts/generate_replay_triage_report.py"),
                content.index("python3 scripts/generate_status_viewer.py"),
            )
            self.assertTrue(all(allowed("generated/reports/replay-triage.json", scope)
                                for scope in ("devsecops", "architecture", "typed-evidence")))
            self.assertTrue(all(allowed("generated/reports/replay-triage.md", scope)
                                for scope in ("devsecops", "architecture", "typed-evidence")))
            self.assertGreaterEqual(content.count("python3 scripts/generate_blocking_readiness.py"), 1)
            self.assertTrue(all(allowed("generated/reports/blocking-readiness.json", scope)
                                for scope in ("devsecops", "architecture", "typed-evidence")))
            self.assertGreaterEqual(content.count("python3 scripts/generate_blocking_mode_alignment.py"), 1)
            self.assertTrue(all(allowed("generated/reports/blocking-mode-alignment.json", scope)
                                for scope in ("devsecops", "architecture", "typed-evidence")))
            self.assertGreaterEqual(content.count("python3 scripts/generate_multi_consumer_readiness.py"), 1)
            self.assertTrue(all(allowed("generated/reports/multi-consumer-readiness.json", scope)
                                for scope in ("devsecops", "architecture", "typed-evidence")))
            self.assertTrue(all(allowed("generated/reports/multi-consumer-readiness.md", scope)
                                for scope in ("devsecops", "architecture", "typed-evidence")))
            self.assertLess(
                content.index("python3 scripts/generate_replay_triage_report.py"),
                content.index("python3 scripts/generate_blocking_readiness.py"),
            )
            self.assertLess(
                content.index("python3 scripts/generate_blocking_readiness.py"),
                content.index("python3 scripts/generate_blocking_mode_alignment.py"),
            )

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

    def test_different_evidence_types_can_reuse_shared_subject_digests(self):
        shared = {"id": "image_manifest", "digest": "a" * 64}
        sbom = trust_record(
            evidence_type="sbom",
            subjects=[shared, {"id": "sbom_document", "digest": "b" * 64}],
        )
        vulnerability = trust_record(
            evidence_type="vulnerability_scan",
            subjects=[shared, {"id": "vulnerability_report", "digest": "c" * 64}],
        )
        prior = row(generated_at="2026-07-17T10:00:00Z", source_file="status/results/sbom.json", trust=sbom)
        current = row(generated_at="2026-07-17T11:00:00Z", source_file="status/results/vulnerability.json", trust=vulnerability)
        self.assertEqual(relationship(current, prior)["classification"], "compatible_reuse")

        same_subjects_other_type = trust_record(evidence_type="vulnerability_scan", subjects=[shared])
        same_subjects_row = row(
            generated_at="2026-07-17T11:30:00Z",
            source_file="status/results/same-subject-other-type.json",
            trust=same_subjects_other_type,
        )
        shared_only_prior = row(
            generated_at="2026-07-17T10:00:00Z",
            source_file="status/results/shared-subject.json",
            trust=trust_record(evidence_type="sbom", subjects=[shared]),
        )
        self.assertEqual(relationship(same_subjects_row, shared_only_prior)["classification"], "compatible_reuse")

        report = build_report(rows=[prior, current], official_latest={current["source_file"]})
        assessment = report["assessments"][1]
        self.assertEqual(assessment["recorded_result"], "pass")
        self.assertEqual(assessment["recalculated_result"], "pass")
        self.assertEqual(assessment["classification"], "compatible_reuse")

    def test_changed_subject_content_within_same_evidence_type_remains_conflict(self):
        from lib.result_ledger import apply_replay_assessment

        prior = trust_record(evidence_type="sbom", subjects=[{"id": "sbom_document", "digest": "a" * 64}])
        current = trust_record(evidence_type="sbom", subjects=[{"id": "sbom_document", "digest": "b" * 64}])
        assessed = apply_replay_assessment(current, [prior])
        self.assertEqual(assessed["checks"][0]["result"], "fail")

        prior_row = row(generated_at="2026-07-17T10:00:00Z", source_file="status/results/prior.json", trust=prior)
        current_row = row(generated_at="2026-07-17T11:00:00Z", source_file="status/results/current.json", trust=current)
        self.assertEqual(relationship(current_row, prior_row)["classification"], "same_context_content_conflict")


if __name__ == "__main__":
    unittest.main()
