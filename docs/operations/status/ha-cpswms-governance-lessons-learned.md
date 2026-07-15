# ha-CPsWMS Governance Lessons Learned

## Purpose

This document records the practical lessons learned from integrating `joku-dev/ha-CPsWMS` with the central repository then named `joku-dev/devsecops-governance-as-code`. The current repository identity is `joku-dev/devsecops-governance-framework`.

It complements the pure status documentation by explaining what worked, what failed first, what had to be corrected, and what other repositories should copy from this rollout.

## Final Outcome

The repository `joku-dev/ha-CPsWMS` reached a successful `L1` governance state with:

- released central baseline `l1-baseline-v1.1.3`
- protected `main` branch
- successful baseline gate on `main`
- successful CI on `main`
- uploaded governance run input artifact
- uploaded control evaluation artifact
- full structured `L1` control coverage

Final main-branch governance run:

- run ID: `28302814664`
- baseline ref: `l1-baseline-v1.1.3`
- result: `16/16 pass`, `0 fail`, `0 not_tested`

## What Changed During The Rollout

The rollout did not become successful in one single step.

Instead, it improved in several stages:

1. baseline workflow consumption was stabilized
2. governance run input was added
3. static analysis evidence was added
4. traceability evidence was added
5. operations evidence was added

This sequence matters because it shows how governance-as-code should usually be introduced:

- first make the integration technically work
- then replace placeholders with real evidence
- then improve control coverage step by step

## Key Lessons Learned

### 1. A Released Workflow Interface Is Essential

Pointing consumer repositories at `main` is too unstable for governance use.

The rollout only became reliable after the consumer repository used a released and tagged baseline wrapper.

Practical lesson:

- downstream repositories should consume released workflow entrypoints
- those entrypoints should be pinned by Git tag or full commit SHA

### 2. Release Packaging Errors Must Be Fixed With New Releases

The first `v1.1.0` consumer release introduced the governance run input path, but the internal wrapper pin still pointed to an older reusable workflow.

That produced a startup failure in the consumer repository.

The correct fix was not to overwrite the old release, but to publish patch releases:

- `v1.1.1`
- then `v1.1.2`
- and later `v1.1.3` for run-context-aware release evaluation

Practical lesson:

- treat released governance workflow packages like real software releases
- fix packaging defects through versioned patch releases
- do not silently rewrite existing tags

### 3. Real Evidence Is Better Than Artificially Green Inputs

At first, the governance run input intentionally marked several areas as `false`.

That produced real failed controls instead of pretending compliance.

This was the correct choice because it made the remaining work visible:

- traceability
- static analysis
- operational traceability

Practical lesson:

- never mark governance input fields as `true` only to make the report green
- use the failed controls as a worklist

### 4. Control Coverage Improves Best Through Small Evidence Increments

The fastest way to improve the result was not a giant redesign.

Instead, the repository improved one area at a time:

- static analysis evidence
- traceability evidence
- operations evidence

This reduced governance friction because every step was:

- understandable
- reviewable
- testable
- visible in the viewer

Practical lesson:

- improve governance coverage incrementally
- each new evidence artifact should remove one real ambiguity

### 5. A Viewer Becomes Much More Useful With History

The status viewer initially showed only a single state snapshot.

After the rollout, it was extended to show repository result history and coverage development.

That made these transitions visible:

- `13/16`
- `15/16`
- `16/16`

Practical lesson:

- governance dashboards should show progression, not only current status
- this makes improvement work explainable to teams and reviewers

## Evidence Improvements That Closed The Remaining Gaps

### Static Analysis Evidence

Added:

- `security/ruff-report.json`
- `security/bandit-report.json`
- `security/static-analysis-summary.json`

Result:

- `DSCB-L1-REQ-004` moved to `pass`

### Traceability Evidence

Added:

- `governance/traceability.json`

This created explicit links between:

- requirement sources
- tests
- reports

Result:

- `DSCB-L1-REQ-001` moved to `pass`

### Operations Evidence

Added:

- `governance/operations-evidence.json`

This recorded:

- deployed artifact/version reference
- deployment reference source
- security event evidence sources

Result:

- `DSCB-L1-REQ-016` moved to `pass`

## Recommended Reuse Pattern For Other Repositories

Other repositories should follow this rollout order:

1. consume the released central baseline wrapper
2. make the baseline job run successfully
3. add `governance/governance-run-input.json`
4. add real static-analysis evidence
5. add real traceability evidence
6. add real operations evidence
7. observe the trend in the central viewer

This keeps governance onboarding practical and avoids trying to solve everything at once.

## Recommended Governance Practice Going Forward

For future consumer repositories, the following should now be treated as standard:

- use `l1-baseline-v1.1.3` or newer released wrappers
- produce governance run input explicitly
- produce control-improving evidence incrementally
- record successful runs back into the central governance repository
- regenerate the viewer after each meaningful improvement

## Summary

The `ha-CPsWMS` rollout proved that the governance-as-code repository is not only theoretically usable but practically operational.

More importantly, it showed that:

- governance releases behave like software releases
- evidence quality matters more than optimistic claims
- control coverage can be improved step by step
- a centralized history viewer makes governance progress visible and auditable
