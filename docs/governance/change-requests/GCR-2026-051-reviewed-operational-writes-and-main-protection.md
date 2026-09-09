# Governance Change Request

## Change ID

`GCR-2026-051`

## Decision

On 9 September 2026 the maintainer instructed "jetzt nummer 4", referring to
migrating direct automated main writes to reviewed PRs, then enabling branch
protection, mandatory checks, and reviews for the governance repository.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact | Operational publication helper, workflow migration, GitHub ruleset, and operating guidance |
| Type | Internal repository control and governance change record |
| Owner | Repository Owner / Governance Platform Lead |
| Source Document Intake required | no; no new normative source or source-register change |
| Evidence contract impact | none; existing ledgers remain append-only |
| Runtime governance impact | none |
| Repository enforcement impact | reviewed PRs and required checks on main |
| Release impact | none |

## Implementation And Rollout

The DevSecOps, architecture, typed-evidence, and portfolio writers use
`scripts/publish_operational_update.py`. Each execution can publish only its
allowlisted operational files on a unique automation branch and open a PR.
Existing evidence cannot be modified or deleted. Failed attempts remain
eligible for publication before the workflow reports its failure. Parallel
executions retain separate proposals; conflicts require reconciliation and
regeneration. Official indexes and viewer state change only on merge.

Enable GitHub's combined Actions PR creation/approval setting so GITHUB_TOKEN
can create the proposals. Keep default token permissions read-only; the four
writers explicitly request contents, pull-request, and Actions write access.
They never approve or merge. Cross-repository artifact credentials remain
separate from publication. Explicit workflow dispatch starts the three required
checks; a maintainer may also need to approve queued PR workflow runs.

Merge and validate the migration before activating `.github/main-ruleset.json`.
Exercise a real intake and verify the proposal, unchanged main, and check runs.
Verify rejection of direct updates, force pushes, deletion, and unreviewed merges
on a disposable protected branch. Then activate the same rules for main and
read back its effective configuration. Retain the live assessment in the
self-security workflow artifact rather than rewriting an older observation.

The rules require one approving review, dismissal of stale reviews, resolved
conversations, an up-to-date branch, and three checks from GitHub Actions:
`validate-and-report`, `Analyze Python`, and `Governance Repository Security`.
Deletion and force pushes are forbidden; no actor has a bypass. Independent
CODEOWNER review and signatures are separate follow-up work. Only `joku-dev`
is a collaborator at preparation time: bot PRs can be reviewed by that maintainer,
while maintainer-authored PRs need a second authorized person.

## Protection Verification

On 9 September 2026 the same rules were applied to a disposable verification
branch. GitHub rejected a direct fast-forward update, a forced rewind, branch
deletion (HTTP 422), and an unreviewed merge in PR #58 (HTTP 405). The merge
response explicitly required one approval and all three checks. The branch
remained unchanged; PR #58 was closed and the temporary branches and ruleset
were removed. Main protection is activated separately after migration.

## Validation And Release Decision

Use real local Git repositories to test publication isolation, allowlists,
immutable history, symlink rejection, parallel runs, and no-change behavior.
Test that the self-security collector reads only rules applicable to main and
does not assume unknown write-capable workflows are safe. Run the pinned
bootstrap, full validation suite, strict documentation build, and GitHub checks.

No baseline release is required. The self-security assessment remains
report-only; its successful job does not mean all assessed criteria pass.
Consumer enforcement modes, risk-review deadlines, OPA policies, and released
baseline packages remain governed by their existing decisions.
