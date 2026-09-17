# Governance Change Request

## Change ID

`GCR-2026-094`

## Decision

On 17 September 2026 the maintainer authorized implementation and complete
documentation of the proposed governance-repository security hardening while
preserving the later Bitbucket Data Center and Bamboo migration path.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact | Repository security profile, live GitHub settings, dependency locks, evaluator correction and operating documentation |
| Type | model, workflow, security configuration, test and documentation |
| Owner | Repository Owner / Governance Platform Lead |
| Source Document Intake required | no; no source document or source register changes |
| Evidence contract impact | additive; self-security observation records review-rule details |
| Runtime governance impact | report-only self-security assessment only |
| Repository enforcement impact | stricter Action-source policy, immutable Action references, CODEOWNER/last-push approval and required Dependency Review |
| Release impact | none |

## Why This Change Is Needed

The live repository had SHA-pinned workflow references but did not enforce that
property in GitHub, allowed all Action publishers, and did not require the
existing Dependency Review check. The stored ruleset had also drifted from the
effective rules. The self-security evaluator classified three reviewed PR
publisher implementations as potential direct `main` writers. Python versions
were exact but installations did not verify distribution hashes.

Independent review, signed default-branch changes, signed future releases,
short-lived collector credentials and off-site recovery still require named
people or external infrastructure. They remain explicit findings rather than
being represented as complete.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | no normative policy or directive change |
| DevSecOps controls | self-security profile `0.3.0` strengthens GRS-002 to two independent approvals plus CODEOWNER and last-push approval |
| Platform model | GitHub enforcement is documented as an adapter; equivalent Bitbucket/Bamboo controls are mapped |
| Architecture governance | no runtime marker, gate or baseline change |
| OPA policies | none |
| Schemas and evidence contracts | additive observation fields only; report schema remains compatible |
| Viewer, status indexes or intake | no consumer result or viewer semantics change |
| Release package or baseline | no released package changes |
| Downstream repositories | none; central workflow execution is more tightly restricted |

## Implemented Scope

- Restrict GitHub Actions to GitHub-owned Actions plus
  `open-policy-agent/setup-opa` and require full commit SHA references.
- Require the existing `Dependency Review` check on `main`.
- Require CODEOWNER review and approval after the latest push.
- Synchronize `.github/main-ruleset.json` with the effective required checks.
- Correct the evaluator allowlist for all reviewed operational PR publishers.
- Add hash-locked Python dependency installations for central workflows outside
  the accepted lifecycle implementation manifest and for documentation builds.
- Record the portable control objectives and the Bitbucket/Bamboo mapping.

The repository still has one human collaborator. The live approval count stays
at one until a second independent reviewer is appointed. The report-only model
now exposes this as a failed GRS-002 target instead of treating one approval as
the desired end state.

## Governance Behavior

- [ ] Documentation-only
- [x] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

The GitHub repository settings enforce existing repository protection. The
self-security result itself remains report-only and does not change consumer
enforcement.

## Release Decision

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Released DevSecOps and architecture baselines, consumer evidence contracts and
consumer enforcement modes are unchanged.

## Validation Plan

- [x] Targeted evaluator unit tests
- [x] Live GitHub settings read-back
- [x] `./scripts/bootstrap_validation_env.sh`
- [x] `./scripts/validate_all.sh` (`579` tests passed)
- [x] Lock-consistency test module (`8` tests passed)
- [x] Strict MkDocs build from `requirements-docs.lock`
- [x] Mainline Actions restriction smoke tests: Governance CI run `35271498188` and Self-Security run `35271501198` succeeded
- [x] Python 3.11 PR smoke test found the conditional `referencing` dependency; both locks now pin and hash `typing-extensions==4.16.0`
- [x] Pull-request checks on GitHub: CodeQL/Analyze Python `35273463730`, Dependency Review `35273463801`, Self-Security `35273463807`, Governance CI `35273463841`, Operations `35273463855` and Lifecycle Guard `35273463862` passed

All planned validation was completed before merge.

## Remaining Decisions

- Appoint at least one second independent reviewer before raising the live
  approval count from one to two.
- Select the GitHub App ownership and installation model before replacing the
  producer-read PAT.
- Select an off-site backup target and accountable recovery owners.
- Validate commit/tag signing for human and automation identities before
  enforcing signatures or protecting future release-tag creation.
- Prepare and personally accept a new lifecycle implementation revision before
  admitting observations from Self-Security profile `0.3.0` or switching
  Governance CI, Self-Security and the local bootstrap to the hash locks; the
  current accepted profile, receipts and implementation manifest remain
  immutable.
