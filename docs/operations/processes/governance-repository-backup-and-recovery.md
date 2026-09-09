# Governance Repository Backup And Recovery

## Scope And Status

This is the operator procedure for backing up and rehearsing recovery of the
central repository. It does not claim that an off-site backup service, storage
location or recovery SLA has already been commissioned. Before the pilot,
Repository Owner and Governance Platform Lead must record the backup location,
access owners/deputy, frequency, retention and acceptable data loss/recovery time.

Treat the Git repository, original evidence artifacts and GitHub settings as
separate recovery components. An Actions artifact alone is not a full backup.
The daily report retains diagnostics for 30 days; longer preservation must be
selected deliberately for accepted audit/pilot evidence.

## Backup Inventory

| Component | Capture | Important limit |
|---|---|---|
| Git history, branches and tags | Fresh mirror clone plus refs and commit IDs | Does not include LFS payloads automatically, secrets, issues or GitHub settings |
| Accepted normalized evidence | Versioned `status/` snapshots, events and indexes in the mirror | Original producer archives may contain additional evidence |
| Selected original artifacts | Producer/central run IDs, metadata, downloaded files and digests | Download before expiry; do not rely on links remaining downloadable |
| Rules and repository configuration | Ruleset details, effective main rules, Actions and Pages settings | API exports are observations, not directly importable requests |
| Reviews and decisions | Relevant PR/review records and GCRs | Git history alone does not contain review approvals or PR-only exceptions |
| Credentials | Locations, owners, scope, expiry and recovery route in a secret manager | GitHub does not export secret plaintext; recreate/rotate as required |
| Environment configuration | Referenced environments, protections, variables, access/owner inventory | Reapply only after checking the intended recovery target |

Mirror cloning and separate LFS retrieval are described by
[GitHub's backup guide](https://docs.github.com/en/repositories/archiving-a-github-repository/backing-up-a-repository).

## 1. Capture Git And Configuration

Run from an authenticated workstation. Choose a fresh directory on the agreed
protected backup storage; do not reuse an old mirror as the only historical copy.
Example (replace the storage path before running):

```bash
BACKUP_ROOT='/path/to/protected-storage/governance-YYYY-MM-DD'
GOVERNANCE_REPO='joku-dev/devsecops-governance-framework'
umask 077
mkdir -m 700 -p "$BACKUP_ROOT/settings" "$BACKUP_ROOT/artifacts" "$BACKUP_ROOT/reviews"
git clone --mirror "https://github.com/$GOVERNANCE_REPO.git" "$BACKUP_ROOT/repository.git"
git --git-dir="$BACKUP_ROOT/repository.git" fsck --full
git --git-dir="$BACKUP_ROOT/repository.git" for-each-ref \
  --format='%(objectname) %(refname)' > "$BACKUP_ROOT/git-refs.txt"
git --git-dir="$BACKUP_ROOT/repository.git" rev-parse refs/heads/main > "$BACKUP_ROOT/main-commit.txt"
```

Check exit codes and investigate missing objects. If tracked LFS objects are
present, run `git lfs fetch --all` inside the mirror with Git LFS installed and
verify those payloads are included in storage. A mirror fetch at a later date
can prune history; use dated snapshots/retention rather than overwriting the
only verified copy.

Export settings with an identity authorized to observe them:

```bash
gh api "repos/$GOVERNANCE_REPO/rulesets" --paginate --slurp > "$BACKUP_ROOT/settings/rulesets.json"
for RULESET_ID in $(gh api "repos/$GOVERNANCE_REPO/rulesets" --paginate --jq '.[].id'); do
  gh api "repos/$GOVERNANCE_REPO/rulesets/$RULESET_ID" > "$BACKUP_ROOT/settings/ruleset-$RULESET_ID.json"
done
gh api "repos/$GOVERNANCE_REPO/rules/branches/main" > "$BACKUP_ROOT/settings/effective-main-rules.json"
gh api "repos/$GOVERNANCE_REPO/actions/permissions" > "$BACKUP_ROOT/settings/actions-permissions.json"
gh api "repos/$GOVERNANCE_REPO/actions/permissions/workflow" > "$BACKUP_ROOT/settings/workflow-permissions.json"
gh api "repos/$GOVERNANCE_REPO/pages" > "$BACKUP_ROOT/settings/pages.json"
gh api "repos/$GOVERNANCE_REPO/environments" --paginate --slurp > "$BACKUP_ROOT/settings/environments.json"
gh variable list --repo "$GOVERNANCE_REPO" --json name,value > "$BACKUP_ROOT/settings/variables.json"
gh secret list --repo "$GOVERNANCE_REPO" --json name,updatedAt > "$BACKUP_ROOT/settings/secret-inventory.json"
```

Record API failures or inherited rules separately; an empty/failed export is not
a successful backup. Protect variables and settings according to their actual
content. Review each referenced environment's rules, environment variables and
secret inventory separately where used; the top-level list is not a complete
export of all environment configuration. Inventory relevant collaborator/team
access and security settings under the approved administrative access procedure.

For PR-only review/exception evidence, substitute the actual PR number:

```bash
PR_NUMBER='61'
gh api "repos/$GOVERNANCE_REPO/pulls/$PR_NUMBER" > "$BACKUP_ROOT/reviews/pr-$PR_NUMBER.json"
gh api "repos/$GOVERNANCE_REPO/pulls/$PR_NUMBER/reviews" --paginate --slurp > "$BACKUP_ROOT/reviews/pr-$PR_NUMBER-reviews.json"
gh api "repos/$GOVERNANCE_REPO/issues/$PR_NUMBER/comments" --paginate --slurp > "$BACKUP_ROOT/reviews/pr-$PR_NUMBER-comments.json"
```

PR #61 is a historical example containing its restored temporary review
exception. Inventory all PRs relevant to the recovery/pilot decision, not only
this example. Secret inventory exports contain names/metadata only.

## 2. Preserve Selected Original Evidence

Record which producer and central runs need retention and why. For each selected
run, use a distinct destination and check artifact expiry first:

```bash
EVIDENCE_REPO='owner/producer'
EVIDENCE_RUN_ID='REPLACE_WITH_ACTUAL_RUN_ID'
EVIDENCE_DEST="$BACKUP_ROOT/artifacts/producer-$EVIDENCE_RUN_ID"
mkdir -p "$EVIDENCE_DEST"
gh api "repos/$EVIDENCE_REPO/actions/runs/$EVIDENCE_RUN_ID/artifacts" \
  --paginate --slurp > "$EVIDENCE_DEST/artifact-metadata.json"
gh run download "$EVIDENCE_RUN_ID" --repo "$EVIDENCE_REPO" --dir "$EVIDENCE_DEST/files"
```

Replace placeholders and include repository identity in the inventory/destination
when several producers are involved. Preserve run metadata and available source
artifact digests. Calculate a local SHA-256 manifest for retained files and verify
it after copying to protected storage. For example, from the backup root:

```bash
python3 - "$BACKUP_ROOT" <<'PY'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()
manifest = {str(p.relative_to(root)): digest(p)
            for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'backup-sha256.json'}
(root / 'backup-sha256.json').write_text(json.dumps(manifest, indent=2) + '\n')
PY
```

This manifest detects later file changes against the captured copy; it is not a
signed attestation of source authenticity. Preserve the original evidence/run
binding as well. Record expired/missing artifacts as a coverage gap rather than
claiming the Git snapshots recreate every original archive.

## 3. Rehearse Recovery Locally

Use a fresh local directory, not the live GitHub repository. Set `BACKUP_ROOT` to
the retained snapshot and `RECOVERY_ROOT` to a new working location:

```bash
RECOVERY_ROOT='/path/to/isolated-recovery/governance-YYYY-MM-DD'
python3 - "$BACKUP_ROOT" <<'PY'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()
for name, expected in json.loads((root / 'backup-sha256.json').read_text()).items():
    if digest(root / name) != expected:
        raise SystemExit('Checksum mismatch: ' + name)
print('Backup file checksums verified')
PY
git clone --no-hardlinks "$BACKUP_ROOT/repository.git" "$RECOVERY_ROOT"
git -C "$RECOVERY_ROOT" switch main
git -C "$RECOVERY_ROOT" fsck --full
```

Compare recovered `main` and tag/branch refs with the inventory. The local
clone's origin is the backup mirror; it must not be changed to the live remote
for this drill. The worktree's `refs/remotes/origin/*` represent mirror branches;
compare their object IDs to the captured `refs/heads/*` rather than expecting
identical ref namespaces.

From the recovered checkout:

```bash
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh
python3 -m venv .venv-docs
.venv-docs/bin/python -m pip install -r requirements-docs.txt
.venv-docs/bin/mkdocs build --strict
.venv-validation/bin/python scripts/generate_governance_graph.py
.venv-validation/bin/python scripts/generate_status_viewer.py
git diff --exit-code -- status/ releases/
```

Network access is needed for pinned dependency/tool downloads, but the drill
does not publish anything. Inspect the generated viewer and report links.
Timestamp-only generated differences are expected; accepted `status/` records
and released packages must remain unchanged. Check retained artifacts against
the manifest and their recorded producer run identity.

## 4. Restore Service After An Actual Incident

Repository Owner must designate the target repository and approved recovery
point. First recover locally as above. Inventory changes since that point and
retain any surviving newer evidence before deciding what to restore.

For an intact live repository, use reviewed corrective PRs. If recovery requires
a new empty remote, keep Actions/Pages and dispatch connections disabled until
its identity, protections and data are checked. Import only intended branches
and tags into that approved target. Do not mirror-push into the existing live
repository or overwrite released tags as an incidental recovery step.

Reapply reviewed settings deliberately: raw API exports contain read-only IDs
and metadata and cannot be blindly POSTed. Compare the intended main policy in
`.github/main-ruleset.json` with the captured effective rules, including inherited
controls. Recreate environment protections, access, variables and secret locations;
restore secret values only from the secret manager or issue replacements through
[token maintenance](../security/github-access-and-token-maintenance.md).

Before reconnecting consumers and schedules, verify required reviews/checks,
force-push/deletion protection and no unintended bypass, then validate a genuine
consumer intake through a bot PR. Re-enable Pages and scheduled reporting on the
approved target and verify their outputs. A repository identity change also
requires the documented baseline/integration migration assessment.

## Recovery Acceptance Record

Record backup timestamp/location, main SHA, baseline tags, settings export
coverage, artifact/run inventory, manifest verification, validation/build results,
reviewed viewer output, elapsed recovery time, actual data gaps and named owner.
Compare measured recovery and data loss with the agreed pilot targets. A local
drill proves recoverability of the captured data, not that off-site retention,
credential recovery or a production cutover has already been proven.

Return to the [operations handbook](../guides/governance-repository-operations-handbook.md)
for daily monitoring and pilot exit decisions.
