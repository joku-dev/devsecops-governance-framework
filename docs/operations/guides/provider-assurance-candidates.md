# Provider assurance candidates

[GCR-2026-179](../../governance/change-requests/GCR-2026-179-provider-assurance-candidates.md) introduces separate candidate observations. Existing personally accepted GitHub lifecycle and self-security paths remain in place. This guide describes technical contracts, not a role assignment or operating acceptance.

## Identity, review participation and authority

`subject()` in `scripts/lib/portable_intake/assurance.py` binds provider, canonical HTTPS issuer, opaque native subject ID and kind (`user`, `bot`, `group`, `application`) to a SHA256 key. Display names, usernames and email aliases do not define identity. The same ID on another issuer/provider or of another kind is a different subject.

`role_candidate()` binds that subject to a role identifier, repository key and source revision. Its versioned `schemas/provider-role-candidate-v1.schema.json` contract permits only candidate status and false values for live authority, personal consent and operating acceptance. Source review, role assignment, personal action consent and acceptance of a running service remain separate decisions. No JSON flag from a producer can activate those paths.

The GET-only observer checks native repository and PR/MR identity and its head revision before and after capture. Bounded review pages and the private native capture support inspection. Observed participants do not prove independent human review, role eligibility, code ownership, personal consent or acceptance:

| Profile | Native observation | Commit binding and boundary |
| --- | --- | --- |
| GitHub / GHES candidate | PR reviews with native user/review IDs and states | Exact `commit_id`; latest event per native actor. Dismissed, negative or other-revision reviews cannot count as current approval participants. |
| GitLab candidate | MR `approved_by` native users | This response alone does not establish the approved commit. Participants are retained with `revision_bound: false`; zero bound approvals are claimed. |
| Bitbucket Data Center candidate | Native PR reviewers/status | `lastReviewedCommit` must equal the requested revision. An absent value stays unbound. This is distinct from Bitbucket Cloud. |

Changing the PR/MR head during capture fails. GET-only credentials remain on the configured issuer origin; GitHub.com explicitly uses `api.github.com`. Edition/version fields must be provided or explicitly `null` (unknown). Endpoint availability and semantics must be confirmed against the actual installed products; these are contract/fixture profiles, not live compatibility approvals.

## Self-security capability boundary

The new observer retains all 16 existing GRS definitions, titles, thresholds and profile version/digest. It does not rewrite the accepted assessment or pretend that GitHub Actions restrictions are GitLab/Bamboo equivalents.

For GitHub, a private instance of the installed legacy assessment module uses the new GET-only transport; the accepted module's globals and entrypoint stay unchanged. Static workflow/ownership/release facts are used only for an exact clean installed revision that matches the native `main` default branch. Any acquisition error conservatively makes this candidate assessment `not_proven`; missing booleans cannot become a pass. Other default branches require an explicit successor profile rather than reinterpreting the accepted one.

GitLab resolves the actual default branch and commit, and observes its native `protected` boolean for GRS-001. Related pipeline/discussion merge settings are reported separately. They do not establish required governance checks, two independent role-approved reviews, signature enforcement or GitHub-specific supply-chain semantics. The remaining criteria are `not_proven` / `requires_equivalence_review`. Bitbucket DC checks its native default-branch revision; version/plugin-dependent security criteria remain unproved. Unknown versions, unavailable permissions and unsupported capabilities never imply success. These limitations are explicit candidates for the later platform-owner equivalence review.

Prepare a private copy of the [synthetic profile example](../../examples/portable-runtime/provider-assurance-profile.example.json), set mode `0600`, and supply a separate read credential file with mode `0600`:

```bash
python scripts/observe_provider_assurance.py reviews --profile /private/profile.json --credential-file /private/reader-token --revision EXACT_HEAD_SHA --change-id NATIVE_CHANGE_ID --output-root /private/fresh-review-capture
python scripts/observe_provider_assurance.py security --profile /private/profile.json --credential-file /private/reader-token --revision EXACT_INSTALLED_SHA --output-root /private/fresh-security-capture
```

Each output root must be fresh. Candidate JSON and bounded raw API capture remain private; the latter is retained even on failure. No credential, raw provider body or private identity mapping enters the public candidate index.

## Separate candidate read model

`scripts/generate_portable_candidate_index.py` reads immutable `status/portable/v2/candidates/<repository-key>/<native-execution-key>.json` documents and generates only `generated/portable-intake/index.json`. Optional `--root`/`--output` arguments support disposable fixtures and private artifacts; another in-checkout destination is rejected.

The v1 candidate schema rejects added approval/full-baseline flags. The generator validates repository/native execution keys, exact provider run links, path identity, revision/event context, duplicate JSON keys, symlinks, and bounded files/count/total bytes. It preserves each source candidate and original declared Trust; parsing JSON is not a fresh native provenance verification. Producer execution hashes remain opaque because a public GitHub candidate carries a physical job ID rather than its producer's logical job name.

Contexts are branch, pull request or manual. Even a branch called `main` is not treated as proven mainline. PR executions remain separate because the public envelope does not carry a native PR ID. Latest **candidate** pointers stay inside this read model; no accepted domain index, current-main demo, historical result, official latest or operating acceptance is changed. Consumers must use existing accepted indexes for those purposes.

## Default-branch shadow and retained legacy state

The private collector now binds native default-branch metadata and capture-file SHA256 to each task's bundle/verifier context. A shadow comparison requires this private proof, the exact committed candidate bytes and the full 24-hour/new-run window. Feature-branch pushes, missing metadata, altered captures and old verifier records cannot supply acceptance. Existing immutable receipts/public candidate envelopes retain their format and historical Trust. The verifier change starts a new shadow window; it does not renew prior acceptance.

The Workbench projection exposes retained legacy queue counts and a reconciliation notice alongside the portable queue. Old batches/PR mappings remain retained and require their original reconciliation path; visibility does not transfer publication ownership. The Ubuntu harness exercises a stopped-writer legacy migration, same-revision engine change, actual portable systemd restart, retained raw/queue/meta/batch IDs, installed-version schema2 backup, incompatible downgrade halt before stopping Workbench, and explicit compatible legacy restore. It runs only on a marked disposable Ubuntu host. Actual Proxmox rollout, 24-hour shadow, owner handoff and publisher activation remain separate operating steps.
