"""Prepare or verify a real personal statement for one private local demo only."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from experiments.state_binding import prototype as p
from lib.governance_lifecycle.personal_probe import collect_bound, assess_bound_comments, statement_body
from lib.governance_lifecycle.live_evidence import github_get

REPOSITORY = "joku-dev/devsecops-governance-framework"


def assert_private():
    metadata = p.strict_json(github_get("repos/" + REPOSITORY))
    p.need(metadata.get("private") is True and metadata.get("full_name", "").lower() == REPOSITORY,
           "private_repository_required")


def prepare(root, discussion, subject):
    assert_private()
    issue = p.strict_json(github_get(f"repos/{REPOSITORY}/issues/{discussion}"))
    p.need(bool(issue.get("pull_request")) and issue.get("number") == discussion, "private_pr_required")
    account = p.strict_json(github_get(f"user/{subject}"))
    p.need(account.get("type") == "User" and account.get("id") == subject, "human_account_required")
    root = p.initialize(root)
    p.record(root, "evidence", {"run": "explicit-synthetic-personal-demo", "result": "fail"})
    grant = p.fixture_approve(root, p.prepare(root, "Personally authorized PRIVATE LOCAL TEST artifact"))
    request = {"request_type": "private-prototype-local-demo", "version": "1", "repository_id": REPOSITORY,
               "discussion_number": discussion, "required_subject_id": f"github-user:{subject}",
               "required_role": "prototype_reviewer", "official_state": False,
               "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
               "purpose": "Authorize exactly one local test artifact publication in the isolated prototype; "
                          "no production remediation, deployment, operating acceptance or patent assertion.",
               "prototype_grant": grant}
    p.write_json(root / "personal-request.json", request)
    (root / "PERSONAL-STATEMENT.txt").write_text(statement_body(request), encoding="utf-8")
    (root / "READ-ME-FIRST.md").write_text(
        "# Persönlicher, privater Demonstrationslauf\n\n"
        "Bitte personal-request.json vollständig prüfen. Die darin gebundene Aktion schreibt genau ein lokales "
        "Testartefakt. Alle Beobachtungen bleiben synthetische Testdaten.\n\n"
        f"Die benannte Person (GitHub-ID {subject}) kann danach PERSONAL-STATEMENT.txt selbst als Kommentar unter "
        f"https://github.com/{REPOSITORY}/pull/{discussion} abgeben.\n\n"
        "Codex gibt diese Erklärung nicht stellvertretend ab. Der folgende Ausführungsbefehl prüft sie direkt "
        "bei GitHub unter der lokalen Schreibsperre. Jede gebundene Änderung erfordert einen neuen Antrag.\n\n"
        "```bash\n.venv-validation/bin/python experiments/state_binding/human_demo.py execute "
        f"--workspace {root.relative_to(REPO) if root.is_relative_to(REPO) else root}\n```\n",
        encoding="utf-8")
    return {"prepared": True, "human_statement_issued": False, "request_digest": p.digest(request),
            "workspace": str(root), "discussion": f"https://github.com/{REPOSITORY}/pull/{discussion}"}


def execute(root):
    assert_private()
    root = p.workspace(root)
    request = p.read_json(root / "personal-request.json")
    p.need(request["repository_id"] == REPOSITORY, "repository_scope")
    grant = request["prototype_grant"]

    def check_provider(actual_grant):
        p.need(actual_grant == grant, "personal_grant_changed")
        # No injected transport argument in this command; GitHub is independently
        # queried twice by collect_bound. No comments are posted by this script.
        capture = collect_bound(request, assessor=assess_bound_comments)
        p.validate_human_capture(capture, actual_grant)
        return capture

    transaction = p.execute(root, grant, personal_verifier=check_provider)
    return {"published": True, "transaction_id": transaction["transaction_id"],
            "provider_statement_verified": True, "official_state": False,
            "human_presence": "self_attested_not_provider_attested"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "execute"))
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--discussion-number", type=int)
    parser.add_argument("--subject-id", type=int)
    args = parser.parse_args()
    if args.operation == "prepare":
        if not (args.discussion_number and args.subject_id):
            parser.error("prepare requires --discussion-number and --subject-id")
        result = prepare(args.workspace, args.discussion_number, args.subject_id)
    else:
        result = execute(args.workspace)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
