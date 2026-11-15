# Portable runtime M1 — declared local acceptance

For later M2 implementation/evidence and live boundaries, see the
[integrated engineering matrix](platform-portability-acceptance.md).

Date: 15 November 2026. This working record belongs to
[GCR-2026-173](../../governance/change-requests/GCR-2026-173-portable-runtime-m1.md).
The delivery PR and its revision-bound receipt identify the actual source commit.
This record declares local test coverage; it is not an independent review,
operational acceptance or completion of the full platform-portability goal.

| Goal criterion | Local executable evidence | Remaining boundary |
|---|---|---|
| AC01 | Native API-shaped GitHub/GitLab/Bitbucket fixtures → CI context → physical artifact/SBOM/scan → real pinned OPA → identical checks/control decisions | No live provider parity claim |
| AC02/03 | Missing repository/run/tested revision, unknown direct-push fact, placeholder JSON/scanners and unbound subjects cannot yield successful verified approval | Legacy pinned generators retain historical behavior |
| AC04 | One canonical finding, report-only exit 0 versus authorized-mode mapping; synthetic blocking result exits 2 | No new required merge check |
| AC05 | Strict schema/modes, malformed JSON, unverified OPA and missing policy fail technically; diagnostics retained | Live runner toolchain not installed by this record |
| AC06 | API denial/malformed responses, wildcard grants and unsupported bypass/effective rules remain gaps or failures | Installed-version/edition behavior and credentials open |
| AC07 | Opaque Bamboo keys, GitLab subgroup paths and provider/instance-bound repository/run keys | Persistent legacy migration belongs to M2 |
| AC09 | GitHub head/merge and GitLab merged-result distinction; actual checkout mismatch rejected by CLI gate | Real required-status enforcement belongs to AC16 |
| AC13 | Run outputs retained, output reuse refused, redacted technical diagnostics; native finalization configured in all templates | Target CI import/upload/failure behavior still needs live tests |
| AC14 | Provider-free evaluate API with explicit inputs/time and core boundary tests | No assertion that context collection works offline |

The new scope is `pipeline-l1`, with five mapped controls. Other controls remain
`not_evaluated`. Every result retains `evidence_trust: unverified` and external
enforcement `not_verified`; local success does not authorize a release or merge.
The source templates call application-owned `ci/build-and-scan.sh`; that hook
must use real application build/scanner tools and produce the documented inputs.

The final source validation and exact test total are recorded in the delivery
PR and its revision-bound receipt. Producer hooks and CLI/policy/PR regressions
are part of that reviewed source.
Strict MkDocs, JSON Schema checks and YAML parsing are local checks; they do not
replace GitLab lint/Bamboo Specs import or live platform compatibility tests.

M2 remains required: independent common evidence verification and transports,
provider-aware persistence and legacy migration, central operations/publishing,
VM deployment/recovery and the 1,000/2,000-repository load profiles. Real VM
revision, routing, publisher, credentials, accepted status and architecture
baselines remain separate. This candidate does not change their live state.
