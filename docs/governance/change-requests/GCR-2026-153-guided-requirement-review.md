# GCR-2026-153 — Guided requirement review in the Workbench

## Intent and classification

On 7 November 2026 the maintainer authorized the proposed next Workbench step:
review explicit requirements beside their original source, distinguish current
extraction from retained proposals, and exercise a complete document-to-packet
flow. This change specifies and implements local review preparation.

- Class: Workbench interaction, local draft contract, read-only history projection,
  regression tests and explanatory operations documentation.
- Full Source Document Intake: not required; no source or register changes.
- Source history, lifecycle cases/decisions, authority ledger, OPA, released
  baselines and accepted pilot fingerprints remain unchanged.
- Release impact: no baseline release; the local draft schema gains an additive
  `source_review` kind and continues to accept existing drafts.

Native browser verification also reproduced a connection-handling issue: a
browser socket opened ahead of its request blocked the single-connection server.
Use the standard threaded HTTP server for connection handling and serialize
actual handlers with a request lock. Session checks and draft read/append/write
operations remain serialized. An idle-connection/concurrent-note regression
checks responsiveness and retention of all submitted notes.

## Review flow

1. Open a registered document and choose **Prüfung vorbereiten**, or continue an
   uploaded candidate. A registered-source review references the existing source
   and version; it does not require uploading it as a new candidate.
2. **Anforderungen prüfen** shows only explicit declarations from the captured
   source. Select/search an item, compare its statement with the original text
   and locator, and record **Bestätigung vorschlagen**, **Ablehnung vorschlagen**
   or **Klärung erforderlich** with a named reviewer and reason.
3. The latest note for that exact item drives local preparation progress. An
   unresolved clarification remains visible. Notes are append-only proposals;
   progress never means source, requirement or baseline approval.
4. **Weitergeben** summarizes items with/without notes and clarification needs,
   then exports the existing private ZIP. Incomplete review is allowed and named
   explicitly so clarification can be handed off.

Retained lifecycle proposals, decisions and activations are displayed separately
as read-only history with their case/source binding. Historical draft rows from
the old extractor are also kept outside current extraction and progress. No
historical proposal is automatically deleted, rejected, confirmed or relabelled
as a fresh explicit requirement. Aggregate lifecycle counters are labelled as
retained records rather than a count of newly extracted requirements.

## Acceptance criteria

1. A registered DSCB document can start a local review without changing source
   bytes, source status, register, lifecycle decisions or normative artifacts.
2. Selecting a current requirement shows its identifier, complete statement,
   origin status, exact locator and highlighted source context together. The full
   original remains available. Search and the unnoted/clarification filters do
   not change the denominator of preparation progress.
3. Each saved item note survives reopening and export; the latest outcome drives
   progress while every earlier note remains readable. Unsaved text survives
   item/tab navigation in the current session; logout clears temporary text.
4. Older inferred/row-ID draft entries and recorded lifecycle proposals are
   accessible only in a separate history view, never counted as current items.
   Recorded decisions/activations and stale source bindings remain visible.
5. Zero explicit requirements produces an actionable empty state and no claim
   of complete review. Stale or already-published drafts cannot gain new notes;
   stale packages cannot export. Existing hash and publication consent checks
   continue to apply.
6. A registered-source packet includes byte-identical original content and
   proposal-only notes, with no new-source register proposal or authority change.
7. Exercise the actual DSCB extraction and an isolated HTTP source-review → note
   → reopen → ZIP flow, plus a client flow covering navigation, progress,
   history separation, escaping and clarification handoff. Run pinned bootstrap
   and full repository validation before committing.

## Validation evidence

Pinned bootstrap and complete `validate_all.sh` passed all 810 tests, including
21 Workbench tests and both Node client regression scripts. The HTTP regression
exercises authentication/CSRF, registered-source review creation, an item note,
reopening and ZIP export. Schema regressions retain the candidate-only authority
constraint; changed source metadata/bytes and published notes are guarded.

A separate synthetic jsdom flow exercised registered-source preparation,
highlighted original context, HTML escaping, read-only history, unsaved text
across item/tab navigation, append-only progress, clarification handoff, export,
reopening, stale locks, empty extraction and logout reset.
Delayed-save cases additionally verify that switching items/tabs during an
in-flight save preserves text entered for another item, blocks duplicate edits
to the pending note and restores the empty-extraction question action after
search/filter redraws.

The real `DSCB-STD-REQ-001` acceptance run found 46 explicit declarations and 55
retained historical proposals with matching source binding. A proposal-only
clarification note survived reopening and the ZIP contained byte-identical
registered source bytes with no register proposal. Source/register identities
and historical cases were unchanged after the run.

Native Chrome verification on the isolated local preview opened the real DSCB
document, displayed original context, prepared a registered-source review and
saved an explicitly labelled UI-test clarification note. The view showed
`1 of 46` items with a note, `45` unnoted and `1` clarification; the handoff
preserved that distinction and the browser completed the review ZIP download.
The separate history view showed all 55 retained proposals and recorded
decisions/activations. This was an operational flow test, not a substantive
requirement decision.

Regenerate the advisory implemented-requirement artifact inventory with its
existing generator to record the extended local draft schema hash; requirement
decisions and migration mappings remain unchanged.
