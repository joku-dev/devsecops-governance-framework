# GCR-2026-105 — Private research prototype

## Decision and artifact classification

On 20 September 2026 the maintainer authorized a bounded private prototype,
reproducible experiments and a confidential technical dossier for possible
patent evaluation. The repository must remain private. This records research
authorization; it is not personal operating acceptance or a patentability finding.

| Field | Value |
|---|---|
| Artifact type | Experimental code, test evidence and explanatory design |
| Target path | `experiments/state_binding/` and `tests/test_state_binding_prototype.py` |
| Owner | Repository maintainer |
| Source Document Intake required? | No; no normative source or register change |
| Evidence contract impact | Isolated experiment format only |
| Runtime governance impact | None on existing consumers; local experimental writes fail closed |
| Release impact | None; confidential branch, no baseline release |
| Validation | Focused experiments, independent verification and full repository suite |

## Scope

Implement a single-context filesystem prototype and retain reproducible
positive, negative and concurrency results. Keep detailed research material
outside the website source/output trees. Protect against accidental Pages
publication while the confidential research marker exists. No fingerprinted
pilot implementation, retained transaction, source register, policy, baseline,
status index or consumer integration changes are authorized by this GCR.

## Review and remaining decisions

The maintainer authorized implementation of the bounded experimental design.
Technical review focuses on faithful comparisons, observable write effects,
replay determinism, correction semantics and stated trust boundaries.
Real personal declarations must be made by the person; fixture declarations
must remain identifiable. Patent counsel evaluates novelty, inventive step,
disclosures and inventorship separately. No public publication is authorized.

## Validation record

The experiment README and retained dossier record exact commands, source
fingerprints, results and remaining limits. Only task-scoped changes may be
committed; local office files and original work-package inputs remain untracked.

Observed on 20 September 2026: bootstrap succeeded; OPA/runtime, repository and
agent-provenance validation passed; all 640 unit tests passed; strict MkDocs
build passed. The full test process disabled inherited commit signing only for
its temporary fixture repositories. No stored signing configuration changed.
The experiment includes 18 filesystem scenarios, independent replay and 27
unmodified existing pilot/acceptance comparison tests. All 83 implementation
files named by the existing operating acceptances remain byte-identical to the
starting main revision. Exact run artifacts are retained outside the site tree.
