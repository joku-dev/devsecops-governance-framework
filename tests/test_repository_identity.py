from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]

# Keep the former identity out of this test's own source so the scanner can
# inspect every tracked file without exempting itself.
LEGACY_REPOSITORY_TOKEN = "devsecops-governance-" + "as-code"

# These directories contain immutable release packages, captured downstream
# evidence, or dated reference runs. Their repository identity is historical
# evidence and must not be rewritten.
HISTORICAL_PREFIXES = (
    "docs/operations/reference-runs/",
    "releases/",
    "status/architecture-results/",
    "status/results/",
)

# Active compatibility and explanatory files may retain only the currently
# reviewed number of legacy references. Any additional occurrence requires an
# intentional update to this inventory.
EXACT_ALLOWANCES = {
    ".github/workflows/devsecops-baseline-l1-v1.0.0.yml": 1,
    ".github/workflows/devsecops-baseline-l1-v1.1.0.yml": 1,
    ".github/workflows/devsecops-baseline-l1-v1.1.1.yml": 1,
    ".github/workflows/devsecops-baseline-l1-v1.1.2.yml": 1,
    "docs/demos/demo-guide-2026-07-02-ha-cpswms.md": 13,
    "docs/operations/status/ha-cpswms-governance-lessons-learned.md": 1,
    "docs/operations/status/ha-cpswms-governance-validation-status.md": 2,
    "docs/releases/l1-baseline-v1.0.0-release-statement.md": 2,
    "docs/releases/l1-baseline-v1.1.0-release-statement.md": 1,
    "docs/releases/l1-baseline-v1.1.1-release-statement.md": 1,
    "docs/releases/release-and-migration-model.md": 1,
    "generated/governance-compliance-result.json": 12,
    "scripts/check_repo_governance_integration.py": 3,
}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return [path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


class RepositoryIdentityTests(unittest.TestCase):
    def test_legacy_identity_is_limited_to_reviewed_history_and_compatibility(self):
        tracked = set(tracked_files())
        missing_allowances = sorted(set(EXACT_ALLOWANCES) - tracked)
        self.assertEqual(
            missing_allowances,
            [],
            msg="Repository identity allowance references missing tracked files",
        )

        violations = []
        for relative_path in sorted(tracked):
            path = ROOT / relative_path
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, IsADirectoryError):
                continue

            count = content.count(LEGACY_REPOSITORY_TOKEN)
            if count == 0 or relative_path.startswith(HISTORICAL_PREFIXES):
                continue

            expected = EXACT_ALLOWANCES.get(relative_path)
            if expected is None:
                lines = [
                    str(number)
                    for number, line in enumerate(content.splitlines(), start=1)
                    if LEGACY_REPOSITORY_TOKEN in line
                ]
                violations.append(
                    f"{relative_path}:{','.join(lines)} has {count} unreviewed legacy reference(s)"
                )
            elif count != expected:
                violations.append(
                    f"{relative_path} has {count} legacy reference(s); expected {expected}"
                )

        self.assertEqual(violations, [], msg="\n".join(violations))


if __name__ == "__main__":
    unittest.main()
