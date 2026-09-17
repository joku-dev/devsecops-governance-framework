# Repository Security Hardening, 17 September 2026

## Purpose And Decision Boundary

This record describes the repository controls implemented under
`GCR-2026-094`, their live GitHub state, their portable security intent and the
remaining prerequisites. It is a dated implementation record, not a security
certification.

The change does not modify released DevSecOps or architecture baselines,
consumer evidence contracts, OPA decisions or consumer blocking modes. The
self-security assessment remains report-only.

## Implemented GitHub Controls

| Control | State after hardening | Evidence |
|---|---|---|
| Action publishers | `selected`; GitHub-owned Actions plus `open-policy-agent/setup-opa@*` | GitHub Actions permissions API read-back |
| Action references | full commit SHA required by the repository | `sha_pinning_required=true`; workflow scan |
| Default workflow token | read-only by default | GitHub workflow-permissions API |
| Main review rule | one live approval, CODEOWNER review, stale-review dismissal, last-push approval and resolved threads | ruleset `22622881` |
| Required checks | Governance CI, CodeQL, Self-Security, Consumer Lifecycle Guard and Dependency Review | ruleset `22622881` |
| Destructive changes | force push and branch deletion prohibited; no bypass actor | ruleset `22622881` |
| Secret protection | secret scanning and push protection enabled | repository security settings |
| Extended secret patterns | requested through the repository API but remained disabled | platform capability read-back |
| Secret validity checks | requested through the repository API but remained disabled | platform capability read-back |
| Python installation integrity | exact versions and package hashes required by intake, operations, portfolio, retry and docs publication | `requirements-validation.lock`, `requirements-docs.lock` |

Extended secret patterns and validity checks must remain recorded as
unavailable or disabled until a future read-back reports `enabled`. An accepted
API request is not evidence that the account plan activated the capability.

## Corrected Self-Security Evidence

The evaluator previously recognized only four scopes of
`publish_operational_update.py`. It therefore misclassified the consumer
lifecycle publisher, lifecycle pilot publisher and typed-evidence assurance
publisher as possible direct default-branch writers. The evaluator now accepts
only the explicit reviewed publisher commands and still fails any unknown
`contents: write` workflow or a workflow containing `git push`.

GRS-002 now represents the target state: two independent approvals, required
CODEOWNER review and approval after the latest push. The live repository has
only one human collaborator, so the criterion remains open even though the two
additional review protections are active. This prevents a single-person
configuration from being reported as the desired independent-review state.

## Dependency Integrity

`requirements-validation.txt` and `requirements-docs.txt` remain the concise
version inputs. Their corresponding `.lock` files contain the complete resolved
sets and accepted distribution hashes. Intake, operations, portfolio, retry and
documentation publication install with `pip --require-hashes`; an altered or
unlisted artifact is rejected.

The pull-request smoke test on the supported Python 3.11 runner exposed a
resolver difference that was not active on the Python 3.14 development host:
`referencing` requires `typing-extensions` on Python versions before 3.13. The
two locks therefore include `typing-extensions==4.16.0` and hashes for its wheel
and source distribution explicitly. Lock review must cover every supported
runner version; a successful lock installation on the development host alone
is insufficient evidence.

Governance CI, Self-Security and `bootstrap_validation_env.sh` are bound into the
personally accepted lifecycle implementation manifest. Their exact-version
installation remains unchanged so the accepted manual lifecycle pilot stays
effective. Full hash-lock coverage needs a new immutable operating-acceptance
revision and personal confirmation; this security change does not silently
replace that accepted implementation.

The existing lifecycle source profile also pins Self-Security model `0.2.0` and
the earlier evaluator bytes. Its retained receipts remain valid historical
evidence. Do not run a new lifecycle `observe` operation against the hardened
`0.3.0` implementation until a new preparation and operating-profile revision
has been created and personally accepted. Unit fixtures replay the historical
reference commit instead of pretending that the old profile describes the new
implementation.

Regenerate and review both locks whenever a Python version input changes:

```bash
pip-compile --generate-hashes \
  --output-file=requirements-validation.lock requirements-validation.txt
pip-compile --generate-hashes \
  --output-file=requirements-docs.lock requirements-docs.txt
```

## Portable Control Intent

The control objective is independent of GitHub. Migration changes the adapter,
not the governance meaning.

| Portable objective | GitHub implementation | Bitbucket Data Center / Bamboo implementation |
|---|---|---|
| Protect the authoritative branch | repository ruleset | Bitbucket branch permissions and merge checks |
| Require independent change review | approvals, CODEOWNERS and last-push approval | default reviewers and project/repository merge policy |
| Require verified validation | required GitHub checks | Bamboo plan result exposed as a required Bitbucket build status |
| Restrict executable dependencies | selected Actions and full SHA pins | controlled Bamboo tasks/plugins, pinned container/tool versions and reviewed Specs |
| Minimize automation authority | read-only default token and scoped publisher permissions | separate least-privilege Bamboo/Bitbucket service identities |
| Separate evidence from governance | scoped automation branch and reviewed PR | evidence artifact store or scoped branch/PR publication |
| Preserve dependency integrity | hash-locked Python packages and OPA checksums | the same locks and checksums executed by Bamboo agents |
| Preserve release integrity | signed commits/tags and protected release references | standard Git signatures and protected Bitbucket tag/reference permissions |
| Normalize security evidence | shared schemas and artifact bundle | Bamboo artifacts consumed through the same bundle validation and intake |

The current Bamboo templates assume Bamboo Data Center 12.1.9. Actual company
Bitbucket/Bamboo versions, YAML Specs support, plugins, agent operating systems,
credential facilities and merge-check APIs must be verified before rollout.
Begin with a disposable repository in `report-only` mode and compare its
normalized bundle with the GitHub result before cutover.

## Open Work Requiring External Input

| Item | Why it remains open | Required input |
|---|---|---|
| Two live approvals | only `joku-dev` is currently a collaborator | second independent reviewer identity and role |
| Short-lived collector identity | creating and installing a GitHub App requires an owner and selected repository scope | App owner/organization and installation decision |
| Signed-change enforcement | human and automation signing plus recovery must be tested before blocking main | approved signing identities and recovery owner |
| Future signed release tags | historical tags must not be rewritten; the future publication path needs a tested signer | release signer and key custody decision |
| Off-site backup | the repository cannot select its own independent recovery location | backup destination, retention and recovery owners |
| Enhanced secret scanning | the current account read-back remains disabled | eligible GitHub plan/configuration or alternative scanner |
| Hardened lifecycle observations and full hash-lock coverage | the accepted lifecycle source profile and three install paths are pinned to the earlier implementation | new preparation/operating/request revisions and personal acceptance |

## Verification

Use these checks after any relevant settings or workflow change:

```bash
gh api repos/joku-dev/devsecops-governance-framework/actions/permissions
gh api repos/joku-dev/devsecops-governance-framework/actions/permissions/selected-actions
gh api repos/joku-dev/devsecops-governance-framework/rulesets/22622881
python3 scripts/assess_governance_repository_security.py
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh
```

The generated report is a point-in-time observation. Historical unsigned tags
remain visible as an integrity finding; they are not rewritten to improve a
current score.
