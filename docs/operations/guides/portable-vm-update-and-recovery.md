# Portable VM update and recovery

## Recorded target update, 15 November 2026

The authorized Proxmox update from `edf1623` to the full Main commit
`59bc6d12c1944abcdcacfb40cf38bb88044ea29f` completed successfully. Candidate
validation, authenticated Workbench smoke and independent VM/controller backup
checks passed. The legacy collector engine was preserved; no new portable
configuration, schema migration or publisher activation was performed. The
[dated platform state](../status/current-governance-platform-state.md) distinguishes
this installed revision from the later Main guide/CI update `4f6f5bb`.
The commands below remain the procedure for a separately authorized next update.

This is the engineering runbook from [GCR-2026-180](../../governance/change-requests/GCR-2026-180-portability-acceptance-and-recovery.md), building on [VM installation](linux-vm-installation.md), [collector operations](portable-consumer-service.md) and [intake migration](../evidence/portable-evidence-intake.md). Commands below are for an approved operating change; publishing a candidate PR does not authorize executing them on the target.

## Compatibility and prerequisites

| Source/data | Target engine | Required action |
| --- | --- | --- |
| Fresh installation | legacy by default | Existing setup; no credential/config means no active collection |
| Schema1 legacy state | legacy / preserve | Exact source update and normal checked backup; retain old batches, watermarks and raw bytes |
| Schema1 legacy state | portable-v1 | Halt until stopped-writer backup-first migration into a separate fresh root is verified and explicitly selected |
| Schema2 complete state | portable-v1 / preserve | Installed-version v2 backup, compatible source validation and controlled update |
| Schema2 state | legacy or code without a compatible portable operator | Halt before stopping the running service; no code-only downgrade or fallback |
| Verified schema2 backup with retained original legacy database | legacy restore | Restore original legacy bytes to a fresh root; retain all later v2 evidence for reconciliation, then explicitly select legacy |
| Interrupted/mismatched migration or restored other node/host | any active processing | Hold; inspect and rebuild a fresh candidate or verified restore. Paused inspection is permitted; copied node IDs do not transfer ownership |

Use one approved full 40-character commit containing the runtime, adapters, verifier, collector, IaC and compatible schemas. Runtime, adapter and baseline versions/digests are separate. Preserve the existing private deployment and both VM/controller backups. Check disk reserve for retained raw files, candidate runtime, backups and recovery copies. Do not reclaim history to make a failing capacity check pass.

The private controller config accepts `repository_url` for a credential-free HTTPS internal Git mirror and `consumer_engine` (`preserve`, `legacy`, `portable-v1`), in addition to host/user/SSH/key/backup fields. Default `preserve` updates the current engine; a fresh installation defaults to legacy. A mirror used for online installation is not a full offline VM image. The [prepared package](prepared-runtime-package.md) covers offline evaluation only after OS/Python/Git/tools are ready. Scanner images/databases require separate pinned, refreshed sources; no empty scan is supplied as success.

## Controlled source update

Keep the active collector configuration paused while changing engines or reconciling source ownership. SSH host verification remains enabled. `--ask-become-pass` requests the operator's sudo credential without persisting it; the automation does not grant new sudo privileges.

```bash
./scripts/deploy_vm.sh check --config /PRIVATE/vm.json
./scripts/deploy_vm.sh update --config /PRIVATE/vm.json --revision APPROVED_FULL_COMMIT_SHA --ask-become-pass
./scripts/deploy_vm.sh status --config /PRIVATE/vm.json
```

Preparation validates the exact target and dependency/tool locks, reads the persisted schema without opening a writable database and checks portable service-UID imports before activation. A changed executable closure causes `application_update_required` during collection; data reconciliation never executes fetched code to bypass it. The installed runtime performs a schema-compatible backup before switching versions. Public dependencies are readable by the separate intake UID; private keys/config/state retain private modes.

Activation stops the relevant writers, retains code/runtime/config/state and independent backup copies, switches the checked exact candidate and checks actual Workbench login/data/logout. Failed activation restores the previous compatible executable/service version and reports failure. It never silently resets drafts/credentials to an old snapshot. Verify retained draft/source bytes, consumer schema/queues/batches/PR IDs, authenticated access, service restart and projection after update.

## Explicit legacy migration

First update compatible code while preserving legacy operation. Stop both poll/work timers and services before obtaining a consistent state and mapping. The private mapping must establish each original GitHub repository/native identity, CI issuer and `workflow-aggregate` scope; unknown or contradictory identities halt.

```bash
sudo systemctl stop axiom-consumer-poll.timer axiom-consumer-work.timer axiom-consumer-poll.service axiom-consumer-work.service
sudo -u axiom-intake /srv/axiom/venvs/INSTALLED_FULL_SHA/bin/python /srv/axiom/repository/scripts/intake_portable_evidence.py migrate-legacy --root /var/lib/axiom/consumers --destination /PRIVATE/FRESH_V2_CANDIDATE --legacy-mapping /PRIVATE/legacy-mapping.json
```

Use an existing protected parent owned by `axiom-intake` for that candidate/mapping. The command preserves the original root, makes and verifies a consistent backup, retains the original SQLite database, maps every legacy job/file/meta/batch/publication and writes the completed marker last. Keep an interrupted candidate for diagnosis; rebuild from the unchanged source into another fresh directory. Do not remove legacy batches merely because the new queue is empty.

Inspect schema2, original/raw checksums, mapping digest and retained batch/PR identities before any activation. Reconcile original legacy publication work through its original compatible operator/remote identity; do not create a new portable batch for it. Retain the stopped original root and two-location backups. Selecting the verified candidate as the active data root is a separate operator step, with both writers stopped and correct ownership maintained.

Provision the root-owned `0600` portable operator config with `mode: paused` and a new private node ID; provision reader/publisher credentials separately as described in the collector guide. Use a controller config with `consumer_engine: portable-v1` for the explicit next update. The same service/timer names change engine, so a second writer is not introduced. A paused projection and legacy reconciliation notice must be visible before shadow observation starts.

## Recovery and downgrade

For a compatible source predecessor:

```bash
./scripts/deploy_vm.sh rollback --config /PRIVATE/vm.json --ask-become-pass
```

The previous receipt records both revision and engine. Rollback still probes schema compatibility; schema2 cannot be opened by legacy code merely because its commit is known. An incompatible rollback must leave the live Workbench/process unchanged and report a controlled halt.

For explicit data recovery, first stop both collectors and create/verify a fresh schema2 backup with the **currently installed compatible** Python and CLI. Restore into a fresh path:

```bash
sudo -u axiom-intake /srv/axiom/venvs/INSTALLED_FULL_SHA/bin/python /srv/axiom/repository/scripts/intake_portable_evidence.py backup --root /var/lib/axiom/consumers --destination /PRIVATE/FRESH_V2_BACKUP
sudo -u axiom-intake /srv/axiom/venvs/INSTALLED_FULL_SHA/bin/python /srv/axiom/repository/scripts/intake_portable_evidence.py verify-backup --root /var/lib/axiom/consumers --destination /PRIVATE/FRESH_V2_BACKUP
sudo -u axiom-intake /srv/axiom/venvs/INSTALLED_FULL_SHA/bin/python /srv/axiom/repository/scripts/intake_portable_evidence.py restore-legacy --root /PRIVATE/FRESH_LEGACY_RESTORE --destination /PRIVATE/FRESH_V2_BACKUP
```

`restore` instead of `restore-legacy` creates a compatible v2 restore. Neither overwrites a live root. Check original bytes, database integrity and preserved publications. Retain the current v2 root/backup, including evidence received after migration or an earlier backup. Reconcile that later work before any ownership change. An explicit switch to the verified legacy restore and `consumer_engine: legacy` can then precede a compatible code downgrade. Code with no collector disables its units while retaining operations state; never point that code at a schema2 root.

## Shadow, ownership and Mac coexistence

Start with empty source routes/default CI ownership. Shadow collection uses readers only and publishes nothing. Require at least 24 hours plus a new matching native **default-branch** execution after that window; a branch name, stale receipt, synthetic fixture, raw JSON flag or old runtime proof is insufficient. Compare time/replay-dependent values with the recorded evaluation state rather than rewriting the original receipt. A verifier change begins a new shadow window.

Before source-reviewed owner/node routing or private publish mode is enabled, reconcile old batches and all native PR/MR states. Keep exactly one publisher owner per repository/domain/scope and at most one active frozen batch. Lost responses reuse the stored commit and remote request; a consciously declined request stays closed. Reviewed candidate bytes do not become official compliance results by merging a proposal.

Mac and VM use independent checkouts, sessions, keys, drafts, collector roots/node IDs and backups. Git source equality does not synchronize private state or grant a second publication owner. Test each Workbench login/data/logout independently. Transfer selected drafts only through the existing explicit verified archive flow. A restore on another host holds active collection until reconciliation, even with a copied node ID.

Workbench cookies now use the actual bound port so a Mac UI and an SSH-forwarded VM UI on different localhost ports can retain independent browser logins and logout. After updating from the old global cookie name, sign in again; private keys and drafts are retained. This is session naming, not a transfer of authentication or publication authority.

Port-specific names prevent collisions between these trusted Workbench instances; ports are not a cookie security boundary ([RFC 6265, section 8.5](https://www.rfc-editor.org/rfc/rfc6265.html#section-8.5)). If separate host cookie scopes are desired, use `http://localhost:8765` for the Mac and `http://127.0.0.1:8766` for the forwarded VM; both hostnames are already supported by the loopback-only server.
