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

The current live assessment reports 7 passing and 8 failing criteria. This is
an honest transition state, not a security attestation. Default-branch rules,
required reviews and checks, signed changes, elimination of direct automated
`main` writes, repository-level SHA enforcement, and verified release tags
remain open.

## Safe Activation Sequence

Apply protections in this order:

1. merge the self-security profile, evaluator, SHA-pinned Actions, Dependabot,
   CodeQL, dependency review, CODEOWNERS expansion, and security policy;
2. enable secret scanning, push protection, dependency alerts, and automated
   security updates;
3. observe Governance CI, CodeQL, dependency review, and self-security on
   `main`;
4. replace direct intake and portfolio pushes with a reviewed bot-PR path or a
   separately protected evidence store;
5. create a `main` ruleset that requires PRs, approvals, CODEOWNER review,
   Governance CI, conversation resolution, signed changes, and protection from
   deletion or force push;
6. restrict Actions to approved publishers and require full commit-SHA pinning;
7. publish new signed baseline tags and attestations through a separate release
   change;
8. after a successful observation period and accountable approval, consider
   making selected self-security criteria blocking.

Do not activate step 5 before step 4. The current intake workflows use scoped
file staging and validation but still require `contents: write` and direct
pushes to `main`. Enabling branch protection first would either break intake or
create an overly broad bypass.

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
