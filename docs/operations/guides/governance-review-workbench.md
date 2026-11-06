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

The start page offers **Dokument hinzufügen** and **Dokumente öffnen**. Local
work in progress appears under **Deine Entwürfe**. The full governance process
and open registered-source reviews are expandable details; they are status
projections, not proof that the Workbench performed or approved those phases.

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

### Continue with the prepared draft

- **Anforderungen ansehen:** compare the explicit declarations with the document
  text and source locations. P1 requires verified author-provided provenance;
  an unverified explicit identifier does not gain authority. No P2 prose
  candidates are generated. Historical proposals remain historical records.
- **Änderungen ansehen**, when a predecessor was selected: matching explicit IDs
  pair declarations even with changed wording. Similarity fallback is review
  support, not authoritative equivalence or a replacement decision.
- **Notizen:** record a reasoned proposal for a requirement or the document.
  Names are declarations, not enterprise-authenticated reviewer authority.
  Notes remain `proposal_only`. Next-step buttons guide the user between views;
  navigation does not attest that a review was completed.
- **Weitergeben:** download the review ZIP. It contains exact source bytes,
  candidate-only register/change proposals and notes. Technical hashes and
  additional review conditions are expandable. Inspect the packet before copying
  repository paths to a review branch; do not copy local packet metadata to a
  normative catalog. Optional Draft-PR publication still requires explicit
  publication confirmation.

**Dokumente** shows the registered library. **Dokumente gemeinsam prüfen**
prepares a hashed review scope or displays two originals side by side; this
is not an approved DCR manifest, semantic execution or source promotion.
**Freigabestand** explains existing baseline prerequisites in plain language.
The original contracts and reports remain authoritative; the view cannot
establish fresh consistency or approve a baseline.

Exports and new notes are rejected if HEAD, the source register or any registered
source bytes changed since preparation. If an uploaded file changes on disk,
its package export is rejected too. Recreate the draft/package against the
updated checkout; old notes are retained for audit, not silently rebound.

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
node --check scripts/workbench/app.js
./scripts/validate_all.sh
```

Tests cover real upload-to-packet behavior, replacement deltas, proposal-only
notes, exact source binding, tampered file rejection, DOCX warning/decompression
handling, filename traversal, session authentication, Origin/Host/CSRF protection,
source escaping and the disabled/explicit PR boundary. A live GitHub publication
is not part of automated tests. Browser layout and live PR adapter operation
require a maintainer smoke test before broader adoption.
