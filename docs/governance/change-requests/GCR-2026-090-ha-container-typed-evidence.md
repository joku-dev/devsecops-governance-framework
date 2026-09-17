# GCR-2026-090: Complete ha-CPsWMS container Typed Evidence intake

The maintainer authorizes connecting the existing five real container scans to
Typed Evidence Trust, including central verification of complete image archives.
The earlier viewer corrections exposed this missing integration.

Add the fixed `ha-cpswms-container-trust-v1` collector profile, producer declaration
and completion notification, central archive verification and per-image viewer
projection. Admit all five images together only from a successful main push run;
keep older snapshots, released governance outcomes and latest-selection rules.

| Classification | Decision |
|---|---|
| New artifacts | Collector implementation/tests, producer manifest and notification, operational typed snapshots |
| Source-document intake | None: operational evidence, no new normative source |
| Contract impact | Additive fixed consumer profile and optional typed-index container projection |
| Release impact | No changes to released baselines, OPA behavior or existing consumer contract |
| Enforcement | Report-only; execution/integrity failures prevent intake; findings do not block delivery |
| Verification | Full archive hash, Docker config/layers, revision label, run/commit/attempt, raw Trivy and manifest checks |
| Limits | Co-collected evidence, no independent attestation, no deployment/risk approval |
| Validation | Negative archive/context tests, all existing examples and history, full pinned validation, strict docs, browser and real producer-to-intake run |

Use the standing technical review exception after checks and restore protections.
This does not stand in for personal lifecycle acceptance or an independent review.
