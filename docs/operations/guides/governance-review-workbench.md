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

The worklist now shows the repository's current intake phases and the next
reported action for each: source intake, extraction, P1 identifier/lifecycle
review, P2 `inferred_candidate` review, consistency, decision proposals,
baseline, and implementation. “Bereich öffnen” takes the user to the closest
available workbench area. Phase statuses and counts come from the intake report
and are a status projection, not proof that the workbench itself performed or
approved that phase. In particular, P1 requires a verified author identifier;
unverified extraction row IDs stay separate, and prose candidates stay P2.

1. **Meine Arbeitsliste:** see candidate/draft/review sources, owners and the
   next suggested action, along with persisted local drafts.
2. **Quellenbibliothek:** filter by owner, ID, title or status; inspect original
   extracted text and requirement candidates with source locators.
3. **Quelle einreichen:** choose a Markdown, DOCX or PDF file (maximum 5 MiB),
   a new stable ID, title, owner, version and domains. Optionally select the
   registered source it may replace. A new version uses a new ID so existing
   history is preserved. The upload remains a local candidate, not a register
   change or an authority decision.
4. Inspect **Anforderungen & Original** and **Versionsvergleich**. The existing
   heuristic English normative extractor and delta matcher supply suggestions,
   not exhaustive extraction, authoritative equivalence or semantic findings.
   Unverified table identifiers remain extraction row IDs and do not receive P1.
5. Save reasoned **Notizen** against the source or an extracted requirement.
   Reviewer names are declarations; this local application does not verify
   enterprise reviewer authority. All notes remain `proposal_only`.
6. Download **Entscheidungspaket** as ZIP. For source candidates it contains the
   exact uploaded bytes, a proposed candidate-only register and change proposal,
   plus local packet metadata. Inspect the packet before copying the repository
   paths into a review branch. Do not copy the local packet metadata to a
   normative catalog.
7. Alternatively, select registered sources under **Review vorbereiten**. The
   workbench creates a hashed scope package and allows source-level notes. This
   is not an approved DCR manifest, provider input or a semantic execution. It
   does not convert candidate sources to approved sources.
8. **Baseline & Freigabe** shows the existing readiness projection and blocking
   reasons. It consumes existing report snapshots and cannot establish fresh,
   exhaustive consistency or approve a versioned baseline.

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
