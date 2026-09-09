# GitHub Access And Token Maintenance

## Scope And Ownership

Use this procedure to set up, verify, rotate and recover GitHub access for
central collection and optional producer dispatch. Repository Owner authorizes
access; a named credential owner and deputy perform maintenance. Record their
names, the token/application owner, selected repositories, permissions, expiry,
secret location, last successful verification and next review date in the
restricted credential inventory. Do not record token values in Git, PRs or logs.

The public repository documents the procedure, not secret values or a claim that
all credentials have already been inventoried. Complete the inventory for the
selected pilot before relying on unattended collection.

## Separate The Two Directions

| Location and credential | Purpose | Required repository permission |
|---|---|---|
| Central repository `GH_RESULT_INTAKE_TOKEN` | Read producer run metadata/artifacts | Actions read on each selected producer repository |
| Producer repository `GH_RESULT_INTAKE_TOKEN` (only if it sends dispatch) | Send `repository_dispatch` to the central repository | Contents write on the central repository for this API |
| Central intake workflow `GITHUB_TOKEN` | Push its automation branch, open PR and dispatch checks | Explicit contents, pull-requests and Actions write from the workflow |
| Daily report `GITHUB_TOKEN` | Read operating observations | Contents, Actions and pull-requests read; some administrative settings remain inaccessible |

The same secret name in different repositories does not mean it should contain
the same credential. Prefer separately scoped credentials for collection and
dispatch. Metadata access accompanies repository access; additional endpoints
must be assessed individually. GitHub documents the permissions for
[artifact access](https://docs.github.com/en/rest/actions/artifacts) and
[repository dispatch](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event).

Contents write is broader than a dispatch-only capability. Select only the
central target, preserve its branch rules and never add the credential as a
bypass actor. If this grant is not acceptable for a pilot, use authenticated
manual intake and leave automatic producer dispatch unconfigured.

## Initial Setup

1. Confirm the selected repository list and account/organization access. For a
   fine-grained PAT, choose the intended resource owner and selected repositories,
   set the needed permissions and an explicit expiry. Complete organization
   approval/SSO requirements where applicable. A GitHub App can be used when
   the organization already operates an appropriate installation and renewal path.
2. Create separate read and dispatch credentials if both directions are used.
   Record expiry and a rotation reminder before expiry in the team's established
   calendar/credential manager. This repository does not automatically discover
   PAT expiry from Actions secrets.
3. In the central repository open **Settings → Secrets and variables → Actions**
   and set `GH_RESULT_INTAKE_TOKEN` to the producer-read credential. Alternatively,
   use the CLI's interactive input, which avoids placing the token in a command:

   ```bash
   gh secret set GH_RESULT_INTAKE_TOKEN --repo joku-dev/devsecops-governance-framework
   ```

4. If automatic dispatch is selected, set the producer-side secret in that
   producer repository to its separate central-dispatch credential. Verify the
   producer workflow uses the expected event type and payload in the
   [intake guide](../evidence/governance-result-intake-and-viewer-usage.md).
5. Preserve read-only default workflow permissions. The central Actions setting
   permitting PR creation must be enabled for bot PR publication; its UI also
   permits approvals, but the publisher implementation only creates PRs.
6. Record the completed setup and perform the verification below. Do not infer
   that a listed secret is valid: secret names/timestamps do not reveal expiry
   or whether the remote repository still grants access.

GitHub CLI documents [interactive or stdin secret input](https://cli.github.com/manual/gh_secret_set).

## Verify Access Through The Real Path

1. Select a current, genuine producer mainline run whose artifacts still exist.
2. Run the appropriate central intake workflow on `main` using that producer
   repository and run ID. This exercises the stored collection credential,
   rather than merely testing the maintainer's personal CLI session.
3. Check collection, normalization, telemetry, validation and PR publication.
   Review run/artifact provenance and verify that the existing ledger was not
   rewritten. A successful intake may still contain governance findings.
4. For automatic dispatch, trigger a genuine eligible producer run and confirm
   its dispatch reaches the central workflow with the correct payload. A manual
   central run does not by itself verify producer-dispatch permission.
5. Review/merge the operational PR through normal protections and record both
   run links and the verification time in the credential inventory.

For a read-only diagnostic under an already authorized CLI identity:

```bash
gh auth status
gh api repos/OWNER/PRODUCER/actions/runs/RUN_ID/artifacts \
  --jq '.artifacts[] | {id,name,expired,expires_at}'
```

Replace the repository/run placeholders. This diagnostic tests the current CLI
identity, not the secret stored in Actions. Do not print or retrieve token values
as a troubleshooting shortcut.

## Planned Rotation

1. Review upcoming expiries and the last successful real collection weekly
   during the pilot; arrange rotation before the recorded expiry.
2. Create the replacement credential with the approved repository scope and
   permissions. Retain the still-valid old credential only in the approved
   secret manager during this short verification window.
3. Update the relevant Actions secret via the UI or interactive CLI command.
4. Verify the actual collection/dispatch path as above. If it fails, diagnose
   permissions and restore the previous still-valid value from the secret
   manager when authorized; GitHub cannot return the old secret plaintext.
5. After success, revoke the old credential and record new expiry, owner and
   verification evidence. If read and dispatch credentials are separate, rotate
   and verify them independently.

## Expiry, Revocation Or Suspected Exposure

| Symptom | Investigation / recovery |
|---|---|
| 401 / bad credentials | Check expiry or revocation; issue a replacement and update the affected secret |
| 403 | Check repository selection, endpoint permission, organization approval/SSO and API limits; inspect the run context |
| 404 | Verify repository/run/artifact identity and visibility; it can mean absence or inaccessible data, not just a permission error |
| Artifact expired/unavailable | A new token cannot restore deleted artifacts; use retained evidence or produce a new genuine run |
| Collection succeeds but PR creation fails | Inspect central GITHUB_TOKEN permissions and Actions PR-creation setting; the producer-read token is not the publisher credential |
| Daily security report shows missing settings | Arrange scoped administrative verification; do not give the reporting workflow broad write access or mark unknown as pass |

For suspected exposure, revoke the affected credential promptly, preserve logs
without secret values, notify the accountable owner through the agreed incident
channel and scope the affected access. Issue a replacement only after assessing
the exposure. For ordinary expiry, replace access, rerun the collector and retain
its earlier failed attempt. Do not delete evidence or disable review to conceal
an access failure.

## Recovery Evidence

Record the affected credential identifier (never its value), incident/change
reference, owner, scope, cause, replacement/revocation times, successful producer
and central run URLs, resulting PR and remaining limitations. Return to the
[daily triage routine](../guides/governance-repository-operations-handbook.md)
only after the affected path has been verified.
