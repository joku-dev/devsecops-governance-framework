# AXIOM Review Workbench

The Review Workbench provides a guided, authenticated local web application for
source intake and document-review preparation. It reads this repository's real
source register, uses the existing text and requirement extractors, and keeps
new uploads and notes outside the versioned governance model until reviewed.

The public [Governance Workspace](governance-viewer-app.md) remains a read-only
publication surface. The workbench is a separate private operational surface;
it is not included in GitHub Pages or the generated public viewer.

## Start

From the repository checkout, run one command:

```bash
./scripts/start_governance_workbench.sh
```

On first use, the script prepares the pinned local validation environment;
later starts reuse it. Open the URL printed in the terminal, usually
`http://127.0.0.1:8765`, and enter the local access key printed below it. Keep
the terminal open; stop the service with Ctrl+C. The session expires after
eight hours or logout. A new process creates a new random key. An optional
`AXIOM_WORKBENCH_KEY` environment value must contain at least 24 characters;
never put it in Git, URLs, chat, or a browser application configuration file.

For PDF extraction, add the optional pinned parser to the same runtime:

```bash
.venv-validation/bin/python -m pip install --require-hashes -r requirements-source-document-intake.lock
.venv-validation/bin/python scripts/serve_governance_workbench.py
```

Markdown and DOCX do not require the optional PDF parser. Scanned/encrypted
PDFs and DOCX comments/tracked changes are not silently accepted as complete
review content; the existing extractor's warnings/errors remain visible.

## Guided operation

The main workflow is **Dokument wählen → Prüfen → Weitergeben**. The sidebar
contains **Start** and **Dokument wählen**. Start prioritizes resumable local
preparations and offers **Prüfung beginnen** for new work. The document selector
opens an existing preparation or begins a registered-source review directly;
**Neue Datei hinzufügen** opens the upload form. Document title links retain a
read-only view of the original and its exact historical decisions.

The session defaults to **DevSecOps · Policy, Directive und Baseline**. The
**Alle Dokumente einschließlich Architektur** selector reveals the full library
and parked preparations. This is a display filter, never a change to source
status, decisions or retention. Document/version, search and status filters remain
editable; logout resets the session scope.

**Notizen, Vergleich und Historie** contains secondary tools inside a preparation.
A version candidate exposes its predecessor comparison there. **Hintergrund und
weitere Werkzeuge** on Start contains document-scope comparison and baseline
prerequisites. Existing direct links remain supported.

### Three-step review

1. **Dokument wählen:** choose an existing document or prepare a new upload using
   the metadata form below. Existing usable preparations resume at the next open
   requirement, clarification or handoff.
2. **Prüfen:** compare an explicit requirement with its highlighted original and
   record a proposal and rationale. **Speichern und weiter** advances only after a
   successful save, without interrupting navigation elsewhere during a delayed
   request. **Überspringen** leaves the item open and does not save. The three
   status cards show source status, local note progress and open questions;
   formal decisions are expandable separately.
3. **Weitergeben:** review unanswered requirements and document questions and
   download the review ZIP. Complete local notes without clarifications show
   **Zur Übergabe vorbereitet**. Partial work can still be handed off. Zero
   explicit declarations show **Zur Klärung weitergeben**, never completion.

When no explicit declarations are recognized, read the original and choose
**Frage zum Dokument notieren**. This records a document-level proposal; it does
not turn prose or synthetic extraction row IDs into requirements.

### Implementation and impact hints

Each current declaration offers expandable **Umsetzung und Auswirkungen**.
The private response-only projection in `scripts/lib/workbench_impact.py` reads
the source register, lifecycle cases, canonical catalog and artifact register.
It requires a current approved source with matching path and SHA-256, a unique
proposal matching the declaration and wording, an approval evidence path and
exact activation, and an active effective catalog revision with matching wording,
source reference and decision. No connection is inferred from text similarity.

Mappings remain separate. A confirmed mapping requires the exact GRQ revision,
unique mapping ID, matching source references, authorized artifact type, effective
adoption/derivation, equivalent or partial coverage, available decision/equivalence
records and the current artifact SHA-256. The view shows the artifact/rule path,
coverage, decision date, evidence path and authorized enforcement mode.

- **Prüfbedarf:** the exact requirement has confirmed current artifact mappings;
  assess those artifacts when changing the requirement. Partial coverage remains
  explicit and never establishes full implementation.
- **Auswirkung ungeklärt:** authority data, exact bindings or mappings are missing,
  ambiguous, stale or invalid. One invalid mapping keeps the overall indication
  unknown even when other mappings are confirmed. No mapping never means low risk.

The indication is advisory, not a semantic assessment of a proposed text edit.
An authorized `blocking` mapping is not evidence of actual blocking execution.
The present authority records do not provide exact requirement-to-consumer-run or
baseline-publication bindings, so the view explicitly leaves both unlinked and
makes no high/low operational-risk claim. A future high-risk indication needs
separately supported, exact runtime-use evidence. The projection neither parses
OPA semantics nor changes enforcement.

For new versions, a same-explicit-ID predecessor may show **Bisherige Version**
impact separately. This describes the predecessor's authority only and grants no
approval or implementation to the candidate. Projection data is recomputed from
the current checkout on reads and excluded from stored drafts, predecessor
snapshots, ZIP packages and candidate PRs. Saved notes remain proposal-only.

### Prepare a document in three steps

1. **Datei auswählen:** choose Markdown, DOCX or a text-based PDF (maximum
   5 MiB). The filename suggests an editable title and, when explicitly present
   as `v0.5` or similar, a version. No version is invented from a date or other
   filename number. The document needs explicit requirement labels such as
   `DSCB-L1-REQ-001`; no requirements are inferred from prose.
2. **Dokument einordnen:** choose a new document or a new version of a registered
   document. For a version candidate, select the existing document. Its owner
   and domains can fill empty fields; these suggestions remain editable.
   Confirm the version, responsible team/role and affected areas. A free
   technical document ID is suggested against registered sources and local
   drafts. **Technische Dokument-ID anpassen** allows a custom ID. This is a
   document identifier, separate from requirement identifiers; a new version
   receives a new ID and preserves history.
3. **Angaben prüfen:** inspect the summary and use **Zurück** to correct it.
   Only **Dokument vorbereiten** submits the file to the existing local API and
   creates a candidate draft. No source register or normative authority changes.

Back navigation and moving between sections retain the selected file and
entered metadata in browser memory. Nothing is persisted in browser storage.
Logout clears this temporary form state. Successfully prepared drafts continue
under the existing private local filesystem storage. Missing fields and format
or size errors appear beside the form and focus the relevant field.

### Review a registered document

Open **Dokumente**, select an existing document, then choose **Prüfung beginnen**. This creates a local `source_review` for the existing version
and its exact bytes. Uploading the document as a new candidate is unnecessary.
The source register, source status and recorded decisions remain unchanged.

The document's read-only view uses the same requirement selection and source
context as the editable local preparation. **Frühere Vorschläge und
Entscheidungen** displays retained lifecycle cases, including recorded decisions
and activations. A different source hash/path is marked explicitly; no earlier
decision is automatically applied to the current extraction.

### Continue with the prepared draft

- **Anforderungen prüfen:** select or search an explicit declaration. Its ID,
  full statement, origin status and highlighted original locator appear together.
  The complete original stays beside the edit pane on wide screens; on narrow
  screens, use the keyboard-accessible **Anforderung und Prüfnotiz** and
  **Originaltext** tabs. Record a named reviewer, a reason
  and **Bestätigung vorschlagen**, **Ablehnung vorschlagen** or **Klärung
  erforderlich** beside that item. P1 still requires verified author-provided
  provenance. Search and the **Ohne Prüfnotiz** / **Klärungsbedarf** filters do
  not change the progress denominator.
- The progress counter is **Anforderungen mit Prüfnotiz**, never an approval
  count. The latest appended item note determines the local display; all earlier
  notes remain readable. Clarifications remain open until another note records
  a different proposal. Unsaved item and general-note text survives item/tab
  navigation, Browser Back/Forward and reopening in the same session. Logout clears temporary
  text; saved notes remain in the local draft.
- **Frühere Vorschläge:** retained lifecycle cases and older draft rows are
  read-only history. Older inferred/row-ID entries never contribute to current
  extraction or preparation progress. Lifecycle counters in the overall process
  are separately labelled **Frühere Lifecycle-Aufzeichnungen**; their decisions
  and open items retain their governance meaning.
- **Änderungen ansehen**, when a predecessor was selected: matching explicit IDs
  pair declarations even with changed wording. Similarity fallback is review
  support, not authoritative equivalence or a replacement decision.
- **Alle Notizen:** read saved proposals or add a general document note.
  Names are declarations, not enterprise-authenticated reviewer authority.
  Notes remain `proposal_only`. Next-step buttons guide the user between views;
  navigation does not attest that a review was completed.
- **Weitergeben:** inspect the summary of items with/without notes and open
  clarification questions, then download the review ZIP. Partial preparation
  can be handed off; the display does not claim completed review. If no explicit
  requirements were found, check the original and use **Frage zum Dokument
  notieren**; an empty extraction never counts as complete.
  Candidate packets contain exact source bytes, candidate-only register/change
  proposals and notes. Registered-source review packets contain byte-identical
  existing source content, proposal-only notes and a change proposal, with no
  new-source register proposal. Technical hashes and
  additional review conditions are expandable. Inspect the packet before copying
  repository paths to a review branch; do not copy local packet metadata to a
  normative catalog. Optional Draft-PR publication still requires explicit
  publication confirmation.

**Dokumente** shows the registered library. **Dokumentvergleich vorbereiten**
prepares a hashed review scope or displays two originals side by side; this
is not an approved DCR manifest, semantic execution or source promotion.
**Freigabevoraussetzungen** explains existing baseline prerequisites in plain language.
The original contracts and reports remain authoritative; the view cannot
establish fresh consistency or approve a baseline.

### Find, interrupt and resume a review

Document and draft reviews are full pages. Hash links identify a document, draft,
view and optionally a technical requirement-row ID, for example
`#/documents/TEST-SRC-001/current` or
`#/reviews/<draft-id>/requirements?item=<row-id>`. Opening such a link still
requires authentication. Invalid links produce an explicit empty state; an old
requirement link never silently selects an unrelated current requirement.

Browser Back/Forward retains document-list search/status filters, requirement
filters, selection and unsaved inputs within this browser session. Navigation
alone never saves a note. Reload opens the persisted local draft; unsaved inputs
trigger the browser's leave-page warning. Source text, note text and filters are
never written into routes, history state, localStorage or sessionStorage. Logout
clears temporary inputs. A successful save updates the local draft even if the
user navigated elsewhere during the request; it does not move the user back.

Start and document-list actions resume a usable current preparation. They open
the next requirement without a note first, then highlight unresolved
clarifications, then offer handoff. Published preparations point to the existing
Draft PR; no second publication form is offered. The three status cards distinguish source status, local preparation and open
questions. **Formale Entscheidungen und Historie** is expandable separately. Recorded decisions/activations are read from retained
lifecycle records matching the exact saved source ID/path/hash. They are neither
local-note outcomes nor a new source or baseline approval.

### Changed or missing source inputs

Exports and new notes are rejected if HEAD, the source register or any registered
source bytes changed since preparation. The additive read-only `stale_details`
response explains repository/register/source changes and missing source files;
`formal_status` provides the separate historical counts. Both fields are computed
on reads and excluded from stored draft JSON and review packets. Existing draft
storage and the `stale` flag remain compatible.

Changed/missing uploaded originals also lock the preparation. A saved preparation
remains readable even when its registered original or registration was removed.
The recovery action opens the current registered document, the comparison setup,
or a fresh upload, depending on the preparation kind. Restore a missing file or
registration before preparing it again. New preparations start without copied
notes or decisions; the earlier preparation stays intact for manual comparison.

## Optional GitHub Draft-PR adapter

Install and authenticate GitHub CLI (`gh`) separately, configure repository Git
identity and push authentication, then start:

```bash
.venv-validation/bin/python scripts/serve_governance_workbench.py --enable-pr
```

The **Draft-PR erstellen** action requires the user's publication checkbox.
This is particularly relevant for public repositories: uploaded source content
must be suitable for that audience. It does not add a new data-classification
or publication approval to the governance model.

The adapter requires a clean tracked checkout and checks the remote default
branch against the exact draft base,
creates an isolated worktree and branch, commits only candidate/source proposal
files, pushes, and opens a draft PR. It never merges, promotes a source,
changes existing source statuses, rewrites lineage, calls a semantic provider,
or creates a baseline release. It keeps the local draft's PR receipt. A failed
partial attempt is not automatically retried: inspect the retained
`.local/governance-workbench/pr-<draft-id>` worktree and branch before recovery.
The webapp does not run the complete repository validation for a generated PR;
that draft PR must pass the required CI/local checks before merge.

Core intake and packet preparation are platform-neutral. The optional PR
adapter is explicitly GitHub-specific; Bitbucket/Bamboo can consume exported
packages through their existing reviewed change flow.

## Security and storage boundary

- Bind only to loopback (`127.0.0.1`), never expose this development server to
  a LAN, tunnel, public host or reverse proxy. This version is for one local
  maintainer; enterprise hosting needs an HTTPS service, SSO/RBAC, verified
  reviewer identities and a separate operational acceptance.
- Private API data requires a session; cookies use HttpOnly and SameSite=Strict.
  Mutations additionally require the local Origin and a session CSRF token.
- Exact Host allowlisting prevents DNS-rebinding access. CSP, frame protection,
  no-store responses and escaped source rendering protect the browser surface.
- Upload filenames cannot select filesystem paths. Server-generated folders,
  supported-format checks, a request limit and DOCX decompression limits bound
  file handling. Extracted input remains untrusted data.
- Drafts live under ignored `.local/governance-workbench/`, with private Unix
  directory/file permissions. The local filesystem and authenticated Git CLI
  remain the maintainer's trust boundary. No provider receives source data.
- Draft retention is manual: stop the service, export required records, then
  remove unwanted draft folders. Back up needed local drafts through an
  approved private path. Browser storage contains no draft/source persistence.
- The existing public DCR projection is redacted; its findings have no original
  evidence excerpts here. Use the associated private review record for actual
  finding triage. The app does not invent or reconstruct withheld evidence.

## Validation

```bash
.venv-validation/bin/python -m unittest discover -s tests -p test_governance_workbench.py
# Optional development-only DOM regression environment: Node from .node-version
npm ci --ignore-scripts
npm run test:workbench
node --check scripts/workbench/app.js
./scripts/validate_all.sh
```

Tests cover real upload-to-packet behavior, replacement deltas, proposal-only
notes, exact source binding, tampered file rejection, DOCX warning/decompression
handling, filename traversal, session authentication, Origin/Host/CSRF protection,
source escaping and the disabled/explicit PR boundary. DOM regressions additionally cover direct links, Back/Forward, filter and edit
retention, delayed saves/publication, narrow reading tabs, empty extraction,
partial handoff and published/stale states. Python tests exercise the real HTTP
boundary, missing sources, read-only diagnostics and unchanged packet schemas.
`workbench-ui.yml` runs the DOM suite with pinned Node and locked dev dependencies;
production assets need no Node runtime or build. A live GitHub publication is
not part of automated tests. Before broader adoption, smoke-test browser layout
and the optional PR adapter against its intended repository.
