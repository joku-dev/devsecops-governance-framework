# GCR-2026-139: One-Time Public Projection of the DCR Pilot

**Status: approved for one redacted, report-only projection; implementation and protected-branch review pending.**

## Summary

- Propose a one-time, redacted public Viewer projection for the bounded Codex DCR pilot `dcr-codex-once-2026-10-09`.
- Publish only scope, freshness, structural-inventory totals, partial semantic status, and finding metadata; withhold source identifiers, document details, finding text, recommendations, reviewer identity, and decision rationale.
- Keep the full semantic report and hash-bound human decisions in approved non-public storage; expose only a status that their details are withheld.
- Do not enable recurring runs, automatic publication, blocking enforcement, source changes, or production rollout.

## Change ID

```text
GCR-2026-139
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `status/document-consistency-public-projection.json`, projection code/schema and this request |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not relevant |
| Source status | not applicable |

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact name | One-time redacted DCR pilot projection and publication decision |
| Artifact type | evidence / generated / documentation |
| Target path | `status/document-consistency-public-projection.json`, projection adapter/schema and generated Viewer data |
| Owner | Repository Maintainer / Governance Platform Lead |
| Source Document Intake required? | no |
| Evidence contract impact | additive, only if a distinct targeted-comparison count is added to the public projection |
| Runtime governance impact | report-only |
| Release impact | none |
| Validation required | report, manifest and human-decision hash validation; public projection schema validation; generated-bundle redaction review; `./scripts/bootstrap_validation_env.sh` and `./scripts/validate_all.sh` before merge |

## Why This Change Is Needed

The Viewer currently shows `dcr-phase2-provider-not-run`, a two-source report
with semantic status `not_run`. A separate bounded local pilot has since been
validated, and the maintainer has recorded pilot-level interpretations for its
three proposed findings. Publishing the existing Viewer state as if it
represented this pilot would be stale. Publishing the internal report or
decision records directly would expose semantic prose and human rationale.

This request proposes a narrowly scoped public projection while preserving the
pilot's actual limits. The run manifest contains ten registered, sanitized
Requirements extracts at reviewed commit
`0fb6809ba26a5ef587d58ea16b1791f91f48c159` (manifest SHA-256
`5dd9356d97f2dfd4b4d891d9f365abb09a61c508ef974882d93d937a0e021c38`). The
structural inventory contains 310 sections and 2,138 requirement rows. The
semantic work was three targeted relationship comparisons involving four
architecture extracts. It was not an exhaustive semantic review of the ten
documents or their 2,138 rows. The validated semantic report status is
`partial`, and its three evidence-backed findings remain proposals in the
report contract.

## Requested Publication Decision

The repository maintainer approved **one publication** of this projection on
2026-10-09 after reviewing the stated scope and limitations. The approval
applies only to this review ID, source-manifest hash and one generated Viewer
snapshot, after freshness checks, decision-hash validation and redaction
inspection pass. It does not authorize a later report, expanded source scope,
automatic publishing, scheduling, blocking behavior or production rollout.

## Proposed Public Allowlist

| Field | Proposed public value |
|---|---|
| Review ID | `dcr-codex-once-2026-10-09` |
| Overall status | `partial` |
| Reviewed commit | `0fb6809ba26a5ef587d58ea16b1791f91f48c159`, only if its freshness check still passes at projection generation |
| Source scope | Count of 10; omit source IDs, titles, paths, versions, owners and per-document rows |
| Structural inventory | 310/310 sections and 2,138/2,138 requirement rows; label explicitly as structural inventory, not semantic assessment |
| Semantic coverage | `partial`; requirement/section semantic-coverage counts remain `not_measured` / null because the review assessed targeted relationships, not each row or section |
| Targeted comparison count | 3, with no implied population denominator; add an explicit projection field only if the schema and Viewer label it as targeted and non-exhaustive |
| Findings | Three metadata rows: finding ID, category, proposed state, evidence validity and unconfirmed disposition; no source IDs or excerpts |
| Human decisions | `recorded_locally_details_withheld`; do not expose classifications, reviewer identity/role, rationale or next actions |
| Limitations | State that the run is partial, targeted, report-only and does not prove consistency, compliance, implementation or normative approval |

Withhold source excerpts, section contexts, semantic statements,
interpretations, recommendations, decision rationales, reviewer names/roles,
private source identifiers, local filesystem paths, raw provider response,
full report and decision files. The full report and human decisions must be
retained in an approved non-public location and referenced by hashes; the
current `/tmp` directory is temporary and is not an adequate long-term audit
store.

## Implementation And Publication Conditions

1. Keep `rollout-decision-v2.json` unchanged; this decision permits only the
   bounded one-time projection and does not change general rollout readiness.
2. Read the full report, source manifest and
   hash-bound human decisions from non-public inputs and emits only the
   allowlisted public projection. Do not check the raw inputs into a public
   path.
3. Represent targeted semantic comparisons separately from section and
   requirement coverage. Do not infer that 2,138 rows were semantically
   reviewed from their structural inventory.
4. Omit document/source identifiers and prose from the public projection.
   Preserve any candidate-source status internally; do not expose source identifiers
   or imply that a candidate is normative.
5. Bind the projection to current source-register and source-file hashes. If
   any source or register hash differs from the manifest, mark the review stale
   and stop publication pending a new review or explicit stale-evidence
   decision.
6. Inspect all generated surfaces, including JSON, HTML, JavaScript bundles,
   fallback pages, downloads and source maps, for withheld fields.
7. Publish the approved snapshot only through the normal protected-branch
   PR/merge path. No direct write to `main`.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | No source interpretation or precedence change; report-only metadata only |
| OPA policies | None |
| Schemas and evidence contracts | Additive projection metadata only if required to represent three targeted comparisons accurately |
| Viewer, status indexes or intake | One reviewed DCR projection; current stale/not-run projection replaced only after approval and validation |
| Release package or baseline | None |
| Downstream repositories | None |

## Derived Artifacts

- One validated, redacted public DCR projection for the specified review ID.
- A Viewer snapshot showing partial status, structural counts and targeted
  semantic coverage without publishing internal finding text or human
  decisions.
- Hash-bound private inputs retained outside the public projection.

## Governance Behavior

- [x] Report-only governance behavior
- [ ] Documentation-only
- [ ] Blocking governance behavior
- [ ] Release packaging only

The projection is informational. It does not establish compliance, accept
findings as normative facts, or change a consumer gate.

## Release Decision

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

## Validation Plan

- [x] Verify source-manifest and current-source hashes against the reviewed
  commit.
- [x] Verify each human decision against the exact canonical finding hash.
- [x] Validate the redacted projection against its schema.
- [x] Assert that public output contains no source IDs, excerpts, semantic
  prose, reviewer identity, decision rationale, raw response or private path.
- [x] Confirm the Viewer distinguishes structural inventory from targeted
  semantic comparisons and leaves population coverage unmeasured.
- [ ] Inspect every generated/public surface for withheld fields.
- [ ] Run `./scripts/bootstrap_validation_env.sh` and
  `./scripts/validate_all.sh` before merge.
- [ ] Review and merge through the normal protected-branch process.

## Reviewer Notes

- Current readiness remains `limited_pilot_ready`; production rollout remains
  `pending`.
- Existing approval for another one-time projection, if any, does not cover
  this review ID, ten-source manifest or current finding metadata.
- The three local human decisions are separate from the validated semantic
  report. Public output must not present the report's `human_decisions` field
  as `not_run` if the new projection has a separate local adjudication; use
  only the approved withheld-details status.
- The full report and decisions were consumed from local files under
  `/tmp/dcr-full-local/`; they are not copied into the public repository.
