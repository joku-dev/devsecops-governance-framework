# V2 private Review Workbench

This candidate moves the complete existing local Workbench flow into an explicit
V2 instance. It preserves source selection, candidate uploads, original text and
warnings, explicit requirement identifiers, predecessor comparison, notes,
recorded history, implementation hints, review scopes, ZIP handoff and explicit
proposal publication. The existing browser navigation and authenticated HTTP
routes remain. [Guided operation](governance-review-workbench.md#guided-operation)
describes those screens.

## Start and stop

Use a fresh admitted V2 installation with its prepared Workbench dependencies:

```sh
/private/operator/axiom-v2/mac/axiom-v2 workbench
```

The service prints its loopback URL. Enter the key held in that installation's
private `instance/workbench-key.json`; the service does not print the key or put
it in an environment variable. Stop with Ctrl+C. The key survives a process
restart, while in-memory sessions expire after eight hours/logout and are lost
on restart. Cookies use the actual port so Mac and VM logins stay separate.
Each installation has its own instance, key, drafts, queue and port. No automatic
synchronization or active-service takeover occurs.

A source checkout can run the same explicit route:

```sh
python scripts/axiom_v2.py --instance /private/operator/instance workbench
python scripts/serve_governance_workbench.py --instance /private/operator/instance
```

The direct server facade requires `--instance` and forwards its existing port,
state, projection and publication options to V2 admission. It cannot silently
create checkout-local product state. The instance fixes its port, draft root
and consumer projection; conflicting overrides fail. The old standalone shell
bootstrap belongs to retained V1. A V2 environment must first be installed or
explicitly initialized with its pinned tools; full bootstrap/update service
orchestration remains separate Goal work.

## Private state and live source observations

Draft JSON and exact uploaded bytes live under `instance/state/workbench/`.
Native publication attempts have a separate private recovery directory under
`instance/state/workbench-publications/`. They are retained for reconciliation;
unknown outcomes never cause an automatic retry. Product files, source register,
models, policies, baselines and accepted result indexes are not changed by local
preparation. A running server holds a process-owned lease; a second server or an
offline backup/restore on the same workspace fails with a busy diagnostic.

The explicit local data adapter reads the admitted product's working governance
data. Newly registered/unregistered and missing source files remain visible;
this is a live observation, not an atomic immutable repository snapshot. Native
Git reads only observe identity. Requirement extraction and process projection
call the existing neutral functions and run no producer program or AI provider.
Candidate source destinations must match the declared source ID and upload
suffix; registered-source and review-scope paths stay in the source-documents
namespace. These checks also apply to coherent imported archives with matching
hashes. Bounded file reads and private upload/draft guards reject links, nonregular,
ambiguous or unsafe inputs. Unsupported private files produce an execution
error rather than a successful extraction.

Uploaded requirement rows use `state/workbench/<draft-id>/source.<format>` as a
logical path in the private instance namespace. Registered source paths keep
their repository-relative meaning. The explicit V1 comparison profile changes
only those validated upload `source_path` labels from the old checkout-local
prefix; complete remaining objects and packet members are compared. Upload
bytes, hashes, identifiers, lines, text, warnings and note meanings are retained.
A ZIP's container timestamps are not cross-host identity evidence.

Every read checks saved context against current commit, register and source
hashes. Missing/changed sources and changed uploads keep the existing preparation
visible with stale diagnostics and block further notes/export. Historical source
and requirement decisions remain recorded history. Notes are proposals; an
identifier, completed preparation or a matching artifact does not approve an
unreviewed source, derive governance or grant operating authority.

## Explicit draft backup and restore

Stop the Workbench first. Backups cover every saved draft and upload, including
an interrupted empty draft directory. The closed archive retains file bytes and
hashes, source/runtime identity and the original node as metadata. It is private
and reproducible. An existing destination is not overwritten; output inside the
product, instance or Git metadata is rejected.

```sh
/private/operator/axiom-v2/mac/axiom-v2 workbench backup \
  --output /private/operator/backups/workbench.zip
/private/operator/axiom-v2/mac/axiom-v2 workbench verify-backup \
  --archive /private/operator/backups/workbench.zip --sha256 <saved-backup-sha256>
/private/operator/axiom-v2/fresh/axiom-v2 workbench restore \
  --archive /private/operator/backups/workbench.zip --sha256 <saved-backup-sha256>
```

Keep the SHA-256 returned by `backup` independently for the later commands.
Verification reads the archive without creating a workspace or changing drafts.
Restore requires an empty destination workspace, validates every descriptor,
draft schema, source destination and upload hash before replacing that empty directory, and records
the source node separately from the new node. It never copies keys, credentials,
sessions, publisher settings, collector state or native publication worktrees.
This is a **draft workspace backup**, not a full installation/instance backup or
a claim that update/service/recovery parity is complete.

Same-source restore is the default. Importing schema-compatible historical draft
data after an explicit product update needs a separate operator choice:

```sh
/private/operator/axiom-v2/fresh/axiom-v2 workbench restore \
  --archive /private/operator/backups/workbench.zip --sha256 <saved-backup-sha256> \
  --allow-source-change
```

This reads data only; it cannot load executable code from the archive. Saved
contexts, proposal notes, historical links and exact upload bytes remain
unchanged. The new Workbench reevaluates staleness against its current source;
changed repository/source bindings keep old preparations read-only until a fresh
preparation. Source compatibility, a digest or successful restore is not human
approval, verified Trust or operating acceptance. A future incompatible draft
schema needs a separately reviewed migration rather than silent conversion.

## Publication and delivery evidence

ZIP export works offline. Proposal publication additionally requires
`--enable-pr --publication-profile /private/operator/publication.json`, an
explicit in-UI confirmation and the existing independently scoped native
credentials. Development instances cannot enable publication. The adapter
checks repository/clone identity, exact current remote base, clean source and
candidate-only files, then requires a confirmed native draft response. No merge,
source promotion, automatic governance decision or paid provider is invoked.

The focused tests rerun the entire existing Workbench suite on a disjoint private
instance and independently execute SHA-pinned full original V1 modules. They
compare complete registered/candidate/scope objects, saved data, packet files,
process projection, working source changes and negative/stale outcomes. Separate
HTTP tests preserve authentication, Host/Origin/CSRF, per-port cookies, logout,
private consumers, idle connections and serialized notes. Backup tests cover
exact restoration, historical imports, tampering and private/resource boundaries.
These local tests are distinct from complete pinned validation, revision-bound
coordinator review, CI and actual installed Mac/Linux execution. The complete
22-area/135-entrypoint/37-CI/16-operating-workflow Goal remains in progress.
