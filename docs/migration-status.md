# Migration Status

## Completed

| Area | Status |
|---|---|
| Source DOCX documents imported | Complete |
| Policy and Directive working drafts | Complete |
| Governance document catalog | Complete |
| Document-to-control traceability | Complete |
| L1 control requirements | 16 / 16 complete |
| L2 control requirements | 14 / 14 complete |
| L3 control requirements | 11 / 11 complete |
| Governance requirements | 5 / 5 complete |
| Control-to-platform traceability | 46 / 46 complete |
| Initial evidence catalog | Complete |
| Initial platform capability catalog | Complete |
| Policy-as-code modules | 15 Rego modules, including aggregated DevSecOps and four architecture readiness policies |
| Repository validation script | Complete |
| Traceability CSV generator | Complete |
| Append-only result intake and report-only replay assessment | Complete |
| Typed vulnerability and SBOM evidence intake | Implemented for the current GitHub pilots |
| Measured ha-CPsWMS L1 assessment and per-control assurance | Implemented, report-only |
| Authorized ha-CPsWMS staging deployment and runtime evidence | Implemented for L1-013/014 and partially for L1-016, report-only |
| Integrated read-only Governance Workspace | Complete |

## Still To Refine

The current model is a complete MVP, not yet a fully approved enterprise baseline. The following items should be refined during expert review:

- final evidence naming conventions
- exact verification frequency per control
- exact waiver authority per control
- mapping to concrete tool integrations such as GitLab, GitHub Enterprise, Artifactory, Nexus, SonarQube, Dependency-Track, DefectDojo, or ALM systems
- validation of the Bamboo/Bitbucket Data Center and Jenkins reference adapters against actual company environments
- executable policy input model per selected platform
- enterprise approval and maintenance of the implemented DOCX/PDF rendering pipeline
- production issuer/key lifecycle and operational Trust promotion beyond the implemented signed-attestation pilot
- production-grade monitoring, security-event retention, backup/restore and incident ownership beyond the completed ha-CPsWMS staging run
