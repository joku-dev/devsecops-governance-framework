# License And Permissions

## Purpose

This document defines the repository-level license posture, permitted use,
access expectations, and contribution permissions for the DevSecOps Governance
as Code repository.

It is intended as an operational governance and repository-control document. It
does not replace formal legal review, procurement terms, customer contracts, or
employment agreements.

## Repository Status

Unless a separate, approved license file or written agreement states otherwise,
all repository content is treated as controlled internal material.

Rights holder: `Joern Kutscher`.

Recommended default for this repository: controlled internal use with all rights
reserved. This is the safest default for governance-as-code material because the
repository contains policy intent, control baselines, architecture governance,
evidence models, release artifacts, and provider/agent operating rules.

Default posture:

| Area | Default |
|---|---|
| Copyright | All rights reserved by the repository owner or sponsoring organization. |
| Public open-source license | Not granted by default. |
| External redistribution | Not permitted without written approval. |
| Internal reuse | Permitted for authorized users within the approved scope. |
| Governance authority | Remains with the named governance owners, not with tooling or AI providers. |

If this repository is later released under an open-source or customer-specific
license, that approved license must be added as the controlling license document
and this file must be updated to reference it.

## No License Granted

No license, assignment, transfer, waiver, or other right is granted by access to
this repository, by possession of a copy, by receipt of repository content, by
reviewing the repository, or by contribution to the repository, except as
expressly stated in this document or in a separate written agreement approved by
the rights holder.

There is no implied license. In particular, no permission is granted to use,
copy, modify, merge, publish, distribute, sublicense, sell, host, mirror, train
models with, create derivative works from, or otherwise exploit this repository
or its contents without prior written approval from the rights holder or
designated governance authority.

Access to the repository is conditional and limited. Access does not by itself
create ownership rights, reuse rights, publication rights, sublicensing rights,
commercial rights, or any right to make the repository available to another
person, organization, model provider, hosting service, or public platform.

## Recommended License Model

The usual professional approach for this type of repository is to keep the
governance content controlled by default and license only clearly separated
parts more openly when there is a deliberate reason.

Recommended model:

| Content Type | Recommended Default | Reason |
|---|---|---|
| Governance policy, directives, baselines, controls, waivers, release packages | Controlled internal use / all rights reserved | These artifacts define organizational obligations and audit posture. |
| Source documents, imported standards, customer or program material | Use only under the source license, contract, or explicit approval | These artifacts may carry third-party or confidentiality restrictions. |
| OPA policies, scripts, schemas, and CI templates | Internal by default; Apache-2.0 may be considered for a public reusable toolkit | Apache-2.0 is commonly used where patent and contribution terms matter. |
| Human-readable public documentation | Internal by default; CC BY 4.0 may be considered only for deliberately public guidance | Governance content should not become public accidentally. |
| AI agent contracts, prompts, routing rules, and skills | Same license posture as the repository content they operate on | Agent behavior is part of the governed operating model. |
| Generated reports, viewer output, and evidence snapshots | Same restrictions as their source data | Generated artifacts may reveal internal status, risks, or compliance posture. |

Do not mix incompatible postures in one artifact. If a file contains both
reusable open tooling and controlled governance content, split the reusable part
into a separate artifact before applying a more permissive license.

## Open-Source Or External Publication Path

If the repository owner decides to publish part of this repository externally,
the following path should be completed before publication:

1. Identify exactly which directories or artifacts are in scope.
2. Remove or replace confidential, customer-specific, export-controlled, or
   organization-specific content.
3. Verify third-party license compatibility.
4. Select the license per artifact type.
5. Add a controlling `LICENSE` file and, where needed, file-level notices.
6. Update this document and the README to describe the published scope.
7. Record governance-owner and legal approval.
8. Tag or release the approved publication package.

Common publication choices:

| Publication Goal | Common License Choice |
|---|---|
| Reusable software, scripts, schemas, and policy-as-code examples | Apache-2.0 |
| Very simple sample code with minimal governance sensitivity | MIT |
| Public explanatory documentation | CC BY 4.0 |
| Internal or customer-specific governance baseline | No public license; contract or written permission only |

Absence of an explicit public license means no public reuse rights are granted.

## Scope Of Covered Material

This policy applies to repository content including, but not limited to:

- governance documentation and operating models
- DevSecOps control models
- architecture runtime governance models
- policy-as-code rules
- schemas, templates, and examples
- generated reports and viewer artifacts
- CI/CD integration templates
- agent contracts, prompts, dispatch rules, and review workflows
- release packages and baseline artifacts

Third-party dependencies, tools, standards, and imported source documents remain
subject to their own licenses and contractual restrictions.

## Permitted Internal Use

Authorized users may use this repository to:

- evaluate and improve DevSecOps governance controls
- generate traceability, evidence, status, and baseline reports
- integrate approved application repositories with the central governance
  baseline
- operate report-only governance checks and approved enforcement workflows
- prepare reviews, audits, release candidates, and management readouts
- create derived internal documents where source lineage is preserved
- use approved AI or automation providers as execution assistants under the
  repository governance rules

Internal reuse must preserve attribution, source lineage, validation evidence,
and release/baseline version references where applicable.

## Restricted Or Prohibited Use

The following actions require explicit written approval from the repository owner
or designated governance authority:

- publishing the repository or substantial excerpts outside the approved
  organization
- relicensing repository content
- using repository content in commercial offerings, customer deliverables, or
  public training material
- modifying released baseline packages without an approved release process
- removing source lineage, provenance, authorship, or review metadata
- bypassing required validation, review, waiver, or approval controls
- using AI-generated output as final governance authority without human review
- uploading controlled source documents, generated evidence, or confidential
  artifacts to unapproved external services
- granting persistent graph-write, policy-enforcement, or release-publication
  rights to automation without explicit governance approval
- copying, forking, cloning, mirroring, scraping, indexing, or archiving the
  repository for an external party without written authorization
- training, fine-tuning, evaluating, or benchmarking AI models or retrieval
  systems on repository content without written authorization
- creating derivative repositories, templates, baselines, consulting assets,
  training assets, or customer deliverables from repository content without
  written authorization
- removing, obscuring, or changing copyright, license, confidentiality,
  provenance, source-lineage, or restriction notices

## Confidentiality And Controlled Distribution

Repository content should be treated as confidential or controlled unless it is
clearly marked as public by the rights holder.

Authorized users must:

- restrict access to approved users and approved systems
- use repository content only for approved work
- protect local copies, exports, generated reports, and downstream artifacts
- avoid uploading repository content to unapproved external services
- notify the repository owner or governance owner if unauthorized disclosure is
  suspected

Public availability of a repository path, accidental disclosure, broad read
permissions, or technical ability to clone the repository does not grant
permission to use, redistribute, publish, sublicense, or create derivative works.

## Access And Permission Model

Access should follow least privilege.

| Role | Typical Permissions | Notes |
|---|---|---|
| Reader | Read documentation, models, reports, and released baselines. | Suitable for auditors, stakeholders, and consuming teams. |
| Contributor | Propose changes through branches or pull requests. | Must follow validation and review requirements. |
| Maintainer | Merge approved changes, run release workflows, and maintain repository structure. | Must protect released baselines and generated artifacts. |
| Governance Owner | Approve policy, directive, baseline, waiver, and release changes. | Owns governance decisions and acceptance criteria. |
| Automation Agent | Execute deterministic checks or assisted review tasks. | Must not approve its own output or override governance rules. |
| External Party | No access by default. | Requires contract, NDA, or written authorization. |

Administrative access must be limited to users who need repository configuration,
branch protection, secret management, release publication, or CI/CD integration
rights.

Access may be revoked at any time if a user, automation account, or external
party exceeds the approved scope, violates this policy, or creates unacceptable
governance, confidentiality, legal, security, or compliance risk.

## AI And Automation Permissions

AI providers, coding agents, and workflow automation are execution aids. They do
not receive governance authority by being used.

AI and automation may:

- inspect repository content within approved access boundaries
- propose changes, summaries, reviews, or evidence reports
- execute deterministic validation commands
- prepare draft artifacts for human review
- record provider-backed review events when such execution actually occurred

AI and automation must not:

- approve policy, directive, baseline, waiver, or release decisions
- weaken validation, evidence, review, or human approval requirements
- write persistent governance graph state unless explicitly authorized
- disclose repository content to unapproved external systems
- replace required subject-matter or governance-owner review
- retain repository content outside approved retention and logging boundaries
- use repository content for model training, fine-tuning, evaluation, embedding
  indexes, or product improvement unless explicitly approved in writing

Provider-specific adapters must remain projections of the model-neutral
governance contracts. Shared governance rules belong in the model-neutral
repository layer.

## Contribution Permissions

By contributing to this repository, contributors confirm that:

- they are authorized to submit the contribution
- the contribution does not knowingly violate third-party rights
- required source lineage and references are preserved
- generated outputs are reproducible or clearly marked as generated artifacts
- confidential, customer, export-controlled, secret, or personal data is not
  introduced unless explicitly approved and handled under the correct controls

Contributions remain subject to repository review, validation, and governance
approval rules. Acceptance of a contribution does not change the repository
license posture.

Contributors retain no right to publish, redistribute, sublicense, or separately
commercialize repository content merely because they contributed to it, unless a
separate written agreement grants those rights.

## Third-Party Content

Third-party material must be tracked and used only under compatible terms.

Before adding third-party content, verify:

- origin and owner
- license or contract basis
- redistribution rights
- modification rights
- attribution requirements
- confidentiality or export restrictions
- compatibility with repository publication and release goals

Do not copy external standards, vendor documentation, customer material, or
proprietary examples into the repository unless their use is approved and
traceable.

## Secrets And Sensitive Information

The repository must not contain live secrets, private keys, production
credentials, personal access tokens, or unapproved confidential data.

Sensitive examples must use placeholders and clearly indicate that they are not
valid credentials. If a secret or sensitive artifact is committed accidentally,
treat it as compromised and follow the incident and credential-rotation process
for the affected system.

## Termination And Remedies

Any permission granted under this document terminates automatically for a user,
automation account, or external party that violates this policy or exceeds its
approved scope.

Upon termination or written request from the rights holder or governance owner,
the affected party must stop using the repository content and delete or return
unauthorized copies, exports, generated artifacts, mirrors, derivatives, and
cached materials where legally and technically possible.

The rights holder reserves all rights and remedies available under applicable
law, contract, confidentiality obligations, employment obligations, and
repository access policies.

## Governing Law And Disputes

Governing law, venue, and dispute-resolution rules are to be assigned by the
rights holder or applicable written agreement.

Until assigned, this document should not be interpreted as waiving any rights,
claims, remedies, confidentiality obligations, contractual obligations, or
statutory protections available to the rights holder.

## Baseline And Release Permissions

Released baselines are controlled artifacts.

Only approved maintainers or release owners may:

- create release candidates
- publish baseline packages
- update release statements
- change release checksums
- mark downstream results as validated against a released baseline

Any change to a released baseline requires an explicit release or migration flow.
Historical release artifacts should not be edited in place unless the governance
owner approves a documented correction.

## Waivers And Exceptions

Exceptions to this license and permissions policy require written approval from
the appropriate governance owner.

Each exception should record:

- requester
- scope
- reason
- affected artifacts or repositories
- approval authority
- expiry date or review date
- required compensating controls

Temporary exceptions must not become permanent operating practice without formal
policy update.

## Review And Maintenance

This document should be reviewed when:

- the repository is shared outside the original team
- a new provider, platform, or customer integration is introduced
- released baseline publication rules change
- governance ownership changes
- an open-source, commercial, customer, or internal license is selected
- audit findings identify ambiguity in access or reuse permissions

Recommended review cadence: at least once per major baseline release or once per
calendar year, whichever comes first.

## Approval

| Field | Value |
|---|---|
| Document owner | To be assigned |
| Rights holder | To be assigned |
| Governance owner | To be assigned |
| Legal reviewer | To be assigned where required |
| Governing law | To be assigned where required |
| Initial effective date | To be assigned |
| Last reviewed | To be assigned |
| Next review | To be assigned |

Until the approval fields are completed, this document should be treated as a
professional repository-control draft and not as final legal advice.
