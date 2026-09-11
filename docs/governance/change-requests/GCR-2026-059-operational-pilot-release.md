# GCR-2026-059: Publish the operational pilot repository release

## Request And Classification

The maintainer requested approval/merge of documentation PR #73 and publication
of a release. This follows the documentation refresh in GCR-2026-058.

| Field | Value |
|---|---|
| Artifact intake classification | Repository release statement and derived publication asset manifest |
| Target | `v0.2.0-public-adoption`, repository adoption/operations release line |
| Version impact | Minor since the first public adoption release; central capabilities and operating process extended |
| Source document intake | None; no new normative source or candidate derivation |
| Baseline effect | Existing DevSecOps and architecture L1 packages/tags retained |
| Runtime, schema and policy change in this preparation | None |
| Consumer migration | Existing baseline pins remain valid; new adoption templates explicitly select report-only |
| Publication owner | Repository maintainer; release explicitly requested |

## Change

Add the release statement, baseline/central-operations migration guidance,
versioned asset manifest and release navigation. Publish the four already
verified Office/PDF artifacts byte-for-byte with checksums and a signed tag on
reviewed main. Scope, dated evidence and open findings remain visible in the
release statement. The repository release is distinct from a baseline release.

## Review And Validation

Required checks apply to the final PR head. The maintainer account authored
PR #73, so an independent GitHub approval is still required under the active
ruleset. The release request does not itself record an independent review or
authorize changing that rule; any scoped exception must be separately recorded
and restored after the merge. No standing bypass is introduced.

Run the pinned full suite and strict MkDocs build; verify asset hashes against
their tracked sources and preserve all existing baseline checksums and tags.
After merge, verify the required mainline jobs and Pages, create and verify the
new signed tag, publish the prepared release and check downloaded asset hashes.
Publication status is recorded by GitHub rather than inferred from this GCR.
