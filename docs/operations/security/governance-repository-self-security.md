# Governance Repository Self-Security

## Purpose

This operating guide protects the repository that defines, evaluates, and
distributes governance. Consumer results are not sufficient evidence that the
governance authority itself is trustworthy.

The self-security profile is defined in:

```text
model/controls/governance-repository-security.yaml
```

The live assessment is produced by:

```text
scripts/assess_governance_repository_security.py
```

## Trust Boundary

Repository content cannot be its own complete root of trust. The assessment
therefore combines two control planes:

1. versioned repository controls such as CODEOWNERS, dependency configuration,
   workflows, tests, release metadata, and assessment logic;
2. externally enforced GitHub settings such as branch rules, required checks,
   security features, workflow restrictions, and signature requirements.

If the GitHub API cannot supply a required observation, the criterion fails
visibly. Missing evidence is never interpreted as a pass.

## Profile Scope

The initial report-only profile evaluates:

- default-branch protection;
- pull-request and approval requirements;
- required Governance CI;
- force-push and deletion protection;
- signed-change requirements;
- secret scanning and push protection;
- dependency security and CodeQL;
- private vulnerability reporting;
- full-SHA pinning for third-party Actions;
- restriction to approved GitHub Action sources;
- workflow permission restrictions;
- explicit ownership of critical paths;
- direct automated writes to `main`;
- cryptographically verified release tags.

## Run Locally

Authenticate the GitHub CLI, fetch release tags, and run:

```bash
GH_TOKEN="$(gh auth token)" \
python3 scripts/assess_governance_repository_security.py
```

Outputs:

```text
generated/reports/governance-repository-security.json
generated/reports/governance-repository-security.md
```

The GitHub workflow runs the same assessment for pull requests, `main`, daily,
and on manual dispatch. Findings remain report-only during the initial
observation period.

## Current Activation State

As of 2026-07-18, GitHub secret scanning, secret push protection, dependency
alerts, automated security updates, and private vulnerability reporting are
enabled. The versioned change adds
Dependabot configuration, CodeQL, dependency review, full-SHA Action pinning,
expanded CODEOWNERS, and the report-only self-security workflow.

The initial assessment recorded 7 passing and 9 failing criteria. Consult the
latest workflow assessment artifact for the current live settings; the versioned
report is a dated observation, not a security attestation.

GCR-2026-051 authorized the implemented writer migration: four operational writers now propose
review PRs using scope-specific allowlists and immutable historical evidence.
The desired GitHub configuration is versioned in `.github/main-ruleset.json`.
The live ruleset was verified active on 9 September 2026 after the migration:
one required approving review, three strict required checks, resolved threads,
stale approval dismissal, no force push/deletion and no bypass. PR #60 exercised
the real intake publication path. PR #61 used a separately authorized temporary
review exception and restored the one-review rule immediately afterward; that
exception is not a standing permission. See the
[operations handbook](../guides/governance-repository-operations-handbook.md).

## Administrative Observation On 11 September 2026

The restored protection still requires one review, strict checks and no standing
bypass. Central PRs #64 and #67 used separately authorized exceptions that were
restored and audited immediately after their merges.

The authenticated assessment confirmed 12 of 16 criteria and four gaps:
`GRS-005` signed-change enforcement, `GRS-010` repository-level SHA-pinning
requirements, `GRS-014` signatures on the three historical release tags and
`GRS-016` restriction of Actions sources. All active workflow references are
already SHA-pinned. Secret scanning, push protection, Dependabot security
updates and read-only default workflow permissions were verified enabled.

The scheduled token cannot observe every administrative setting. Its unknown
values are not proof that a setting is disabled. Preserve those observation
limits and read the [current platform state](../status/current-governance-platform-state.md)
for the dated report context. Future signed releases need a separate process;
do not rewrite existing released tags to clear historical findings.

## Safe Activation Sequence

The sequence below explains activation dependencies. Steps 1–5 are implemented
on the central repository as of 9 September 2026; steps 6–8 remain separate
hardening decisions. When setting up a replacement repository, verify each
step instead of assuming versioned configuration has activated live settings:

1. merge the self-security profile, evaluator, SHA-pinned Actions, Dependabot,
   CodeQL, dependency review, CODEOWNERS expansion, and security policy;
2. enable secret scanning, push protection, dependency alerts, and automated
   security updates;
3. observe Governance CI, CodeQL, dependency review, and self-security on
   `main`;
4. replace direct intake and portfolio pushes with a reviewed bot-PR path or a
   separately protected evidence store;
5. apply the versioned `main` ruleset: one approving review, stale approval
   dismissal, resolved conversations, an up-to-date branch, and required
   `validate-and-report`, `Analyze Python`, and `Governance Repository Security`
   checks from GitHub Actions; prohibit deletion and force push, with no bypass;
6. restrict Actions to approved publishers and require full commit-SHA pinning;
7. establish independent CODEOWNER review and commit signing, then publish new
   signed baseline tags and attestations through separate changes;
8. after a successful observation period and accountable approval, consider
   making selected self-security criteria blocking.

Do not activate step 5 before step 4. First merge the workflow migration and
enable Actions PR creation while preserving read-only default token permissions.
Exercise a real intake, verify that it opens a PR without moving main, and check
the three explicitly dispatched validations. Test the proposed rules on a
disposable branch before applying them to main. Read back the effective rules
for main and rerun the live assessment after activation.

There is no automatic approval, merge, or administrator bypass. A maintainer can
review bot-authored PRs; a maintainer-authored PR needs another authorized person.
At the 9 September observation only `joku-dev` is a collaborator, so independent reviewer
onboarding remains necessary for those PRs. Do not impersonate that reviewer or
weaken protection to complete a merge. Conflicting operational PRs need
reconciliation and regenerated projections before their final review.

## Normative And Operational Write Separation

The target state separates frequently changing evidence from normative
governance:

| Data class | Examples | Required write path |
|---|---|---|
| Normative governance | controls, policies, schemas, workflows, releases | reviewed PR with required owners and checks |
| Operational evidence | snapshots, intake events, conflicts, indexes | bot PR or separately protected evidence store |
| Generated presentation | reports, graph, viewer | deterministic regeneration from accepted source and evidence |

A bot that collects evidence must not be able to change normative governance.
GitHub token permissions alone are repository-wide, so path restrictions must
come from the write architecture and review flow rather than an assumption that
the bot will only stage intended paths.

## Enforcement Boundary

The current profile is `active_report_only`:

- it does not edit GitHub settings;
- it does not block pull requests;
- it does not authorize bypass;
- it does not change released baselines;
- it does not classify the governance authority as trusted when criteria fail.

Moving to blocking behavior requires a separate governance decision after the
automated-write migration and an observed stable period.
