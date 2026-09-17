# GCR-2026-091: Add subject-bound SBOM Typed Evidence Trust

The maintainer authorizes extending the ha-CPsWMS five-image intake so that
CycloneDX SBOMs receive their own centrally verified Typed Evidence records.
The existing vulnerability records remain valid and continue to be selected by
the compatibility `latest_result` field.

| Classification | Decision |
|---|---|
| New artifacts | SBOM collector profile, separate typed snapshot, multi-type latest projection and viewer row |
| Source-document intake | None: implementation of the existing provisional SBOM freshness policy |
| Contract impact | Additive `ha-cpswms-container-evidence-v2` producer declaration; legacy v1 remains readable |
| Release impact | No released baseline, OPA or enforcement change |
| Enforcement | Report-only; invalid or incomplete SBOM evidence prevents the complete intake |
| Verification | Central SBOM SHA-256/size, CycloneDX structure, component count, Trivy execution/version, image ID, complete Docker archive and source revision |
| Freshness | `freshness-sbom-subject-bound`; pass requires the SBOM and archive to resolve to the same immutable image |
| Limits | Co-collected evidence without independent producer attestation, release approval or risk acceptance |
| Validation | Negative mutation/binding tests, schemas, full validation, strict docs, browser acceptance and real mainline intake |

Use the standing technical review exception only after required checks pass and
restore repository protections immediately after each merge.
