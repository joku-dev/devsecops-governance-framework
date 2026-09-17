# GCR-2026-086: Integrate technical views into Governance Workspace

## Intent

The maintainer requested the technical viewer's functions inside the new,
more accessible application. Preserve one navigation concept and source semantics.

## Artifact classification

| Field | Decision |
|---|---|
| Artifact type | Frontend, presentation adapter, generated viewer, tests and operational documentation |
| Target | apps/governance-viewer/, scripts/lib/viewer_technical.py, generated/viewer/app/, tests/, docs/operations/ |
| Owner | Repository maintainer |
| Source Document Intake | Not required; existing evidence and models are presented, no normative source introduced |
| Evidence contract impact | None; additive internal application projection |
| Runtime governance impact | Read-only; official selection, trust, replay, lifecycle and enforcement unchanged |
| Release impact | No released baseline, package or tag changes |
| Validation | Full pinned validation, strict docs, projection coverage/escaping/URL tests, desktop/mobile browser acceptance |

## Implementation boundary

Reuse the existing technical renderer's section contents through a script-free
HTML projection. Every technical section has one registered application route.
Unknown sections fail generation so additions cannot silently disappear. The
already-native container findings stay native; technical sources, cards and
rows retain their content. Absent optional sections explicitly show missing data.

The projection excludes inline scripts and event/style attributes, checks URL
schemes and rebases links. Status JSON links go to their Git source because the
existing Pages deployment does not publish the status directory. Browser-side
filtering, pagination and graph selection use a separate first-party module under
the existing CSP. No iframe, remote script, new backend or credentials are added.

Evidence contains Trust, Replay, provenance, run history and artifacts. Governance
contains graph, runtime reference artifacts, controls, model, source intake and
open work. Operations contains integration status, intake health, collection
attempts, conflicts and agent usage. Mainline, manual, branch and PR contexts remain
separate; runtime/demo reference artifacts are labelled. The old static document
remains a compatibility fallback for bookmarks and operation without JavaScript.

The application data is rebuilt from versioned sources during Pages publication.
Personally accepted lifecycle implementation files and publication allowlists
remain unchanged. The standing maintainer-authorized technical review exception
applies to this PR; validate before merge and restore ordinary review requirements.
