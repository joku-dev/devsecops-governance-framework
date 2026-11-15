# Platform portability — integrated engineering acceptance

Date: 2026-11-15. Source: portability Goal v1.2 and [GCR-2026-180](../../governance/change-requests/GCR-2026-180-portability-acceptance-and-recovery.md). This document is a technical evidence inventory, not personal acceptance, a release, production capacity approval or permission to activate a publisher.

## Source, implementation and operation

The shared evaluator, three CI adapters/templates, independent common verifier, provider-bound persistence/migration, SCM/CI operations, persistent collector, VM integration, exact-source prepared distribution and candidate provider assurance/read models are implemented in dependent feature PRs. They assess five mapped pipeline-L1 controls. The other eleven controls remain `not_evaluated`; `full_baseline_assessment` remains false. Existing published baselines and personally accepted GitHub lifecycle paths are retained.

| Work package | Implemented source | Remaining external boundary |
| --- | --- | --- |
| WP0 | Revision/PR/host inventory, protected file manifest, scoped support/load profiles, ADR-PORT-001 | Actual provider versions/editions and operational capacity targets remain unknown |
| WP1 | Context/result/profile v1, evidence/policy/receipt v2, collector v1 config, strict role/candidate contracts | A contract cannot assign live roles or accept an operation |
| WP2 | Provider-free evaluate/gate core, archived checksum-verified Rego, physical artifact/SBOM/scan binding | Application-owned build/scanner preparation and release approval |
| WP3 | Functional GitHub adapter and reviewed pinned wrapper | New workflow/branch rule adoption on actual consumers |
| WP4 | Functional GitLab CI and Bamboo templates/adapters; separate GitHub/GitLab/Bitbucket DC SCM facts | Installed API/edition and native lint/import/runner acceptance; Bamboo provenance closure remains unresolved |
| WP5 | Common native/local verification, immutable receipts/replay/freshness, schema2 store, stopped-writer legacy migration, candidate index | A verified candidate is not an accepted domain result |
| WP6 | Scoped proposal Git workspace, PR/MR reconciliation, explicit CI dispatch, issuer/subject and review/security candidates | Personal/role authority, platform equivalences and human approvals; accepted legacy publishers are not redirected |
| WP7 | Existing VM entrypoints use shared modules; exact revision/engine compatibility, backup/recovery, offline core package and scale tests | Real Proxmox rollout, OS/scanner preparation, shadow/ownership/publisher activation and capacity approval |
| WP8 | Full pinned validation, adversarial/parity/DOM/systemd tests, revision-bound coordinator role reviews and this handoff | Independent human review and each separately scoped live acceptance |

Source delivery chain, in review order:

| PR | Scope | Source head |
| --- | --- | --- |
| [#368](https://github.com/joku-dev/devsecops-governance-framework/pull/368) | Goal v1.2 | `bf9aa3045382963bcbe53eeb29e54a49823a8312` |
| [#369](https://github.com/joku-dev/devsecops-governance-framework/pull/369) | Shared runtime/M1 | `8d539ff6b3e9cc157482cb151f401df783f39c96` |
| [#370](https://github.com/joku-dev/devsecops-governance-framework/pull/370) | Evidence verifier/store/migration | `e2c343464408750feff068fe20329a0c83968fdb` |
| [#371](https://github.com/joku-dev/devsecops-governance-framework/pull/371) | SCM/CI/Git operation boundaries | `29c7fe1178ec3c2e39ce09718cd42c45d752992b` |
| [#372](https://github.com/joku-dev/devsecops-governance-framework/pull/372) | Persistent collector and VM profile | `71b222abe9548fcec4a29feadd9e22ba447dd062` |
| [#373](https://github.com/joku-dev/devsecops-governance-framework/pull/373) | Prepared offline runtime package | `41b53ef7e3460eeb1e1c6148c20892c96f60a8f1` |
| [#374](https://github.com/joku-dev/devsecops-governance-framework/pull/374) | Executable capacity profile/auditor and first measured reports | `1e83fa671dbaebb3052f0ed74daaf12b46d83ea1` |
| [#375](https://github.com/joku-dev/devsecops-governance-framework/pull/375) | Provider candidates, native default-branch proof and enhanced migration/recovery | `63984f3729402a45e40db3759e04541050cf7e72` |
| [#376](https://github.com/joku-dev/devsecops-governance-framework/pull/376) | Workbench browser sessions across localhost ports | `511d16c492b7c7e9f522bc0b8e8f6c211785f4ac` |

These feature heads are not an installed release or an automatic merge instruction. Resolve current PR refs/checks before integrating in dependency order. A later review/check is bound to its own exact source and does not retroactively certify another head.

PRs #368 and #369 both target main; their Goal v1.2 blob is identical. PR #370 starts the dependent runtime stack, followed by #371–#376. Resolve the current refs again at merge time; do not substitute these feature pins for a published release tag.

A read-only target observation at `2026-11-15T04:14:12Z` found the public active checkout and Workbench Python pin at `edf16239e9274dbc33f38f204ef80f58c989f969`. Workbench and both consumer timers were active; both oneshot service conditions were false. Timer activity therefore does not demonstrate collection. Private operator/deployment metadata could not be read without sudo authentication; its mode is not inferred. A second read-only observation at `2026-11-15T04:31:15Z` confirmed Ubuntu 24.04 x86_64 and a clean tracked checkout (optional Git writes disabled). No target settings/data/code were changed. The original Mac working checkout remains separate from these isolated feature branches. Live simultaneous deployment of the new portable version on Mac and Proxmox remains open.

## Acceptance criteria and scope

“Local” means executable contract/regression evidence; “isolated” means disposable operating-system execution. Neither means a real consumer accepted the profile. Source test paths below are relative to the repository.

| ID | Repo-side evidence | Remaining scope |
| --- | --- | --- |
| AC01 | `test_portable_runtime.py`: three native adapter contexts use actual OPA and equal canonical control/findings/decision results | Real target CI jobs still require import/run acceptance |
| AC02 | Missing repository/commit/protection facts and checkout mismatch fail explicitly in runtime/adapter tests | No inferred identity from display names |
| AC03 | Synthetic/unknown Bamboo input cannot supply a verified pass or successful blocking gate | Bamboo native Specs/job/attempt/SCM closure is explicitly unresolved |
| AC04 | Same finding under report-only/block-on-error retains the decision and changes only the documented exit mapping | No external merge rule is inferred |
| AC05 | Duplicate/invalid JSON, missing policy, OPA/tool and unknown-mode regressions | Technical failure never substitutes a success result |
| AC06 | Provider denial/failure/unsupported and incomplete capability tests; candidate security missing facts remain not_proven | Actual editions/permissions/API behavior still need live confirmation |
| AC07 | GitLab subgroup and opaque Bamboo run/job identities in adapters, transport, links, store and capacity fixtures | Native target keys must be configured from the real instance |
| AC08 | Provider/instance/repository namespaces, replay/storage tests and distinct-repository load audits | No cross-issuer identity aliasing |
| AC09 | Tested/source/target distinction; native MR/pipeline association and exact merge parents; wrong/new SHA is held | Real required-status/merge enforcement belongs to AC16 |
| AC10 | Tampered bytes, forged normalized scan/verdict, wrong commit/baseline/config/artifact and native capture regressions | Candidate JSON cannot supply its own native proof |
| AC11 | Native/local Trust separation, atomic first receipt, replay duplicate/conflict and explicit-time stale/future tests | Historical receipts/time/Trust are not renewed |
| AC12 | Existing result readers/validators and exact 24 protected pilot file hashes; no released baseline mutations | Source delivery is not renewed operating acceptance |
| AC13 | Runtime diagnostics survive technical/gate failures; fresh output/no overwrite, capture retention and lost-publication reconciliation tests | Native CI cancellation/artifact-finalization behavior still needs each target's live test |
| AC14 | Provider-free core tests, empty-environment prepared package evaluation and network-denial controls | Context acquisition still needs native access |
| AC15 | Actual macOS OS network denial and Linux network namespace: local hashed wheels/OPA, complete canonical pass/fail parity; invalid/unprepared packages rejected | OS/Python/Git and scanner images/databases are separate prerequisites |
| AC16 | No new live blocking configured | **Open:** scoped authorization plus real negative/missing/stale mandatory-status merge tests |
| AC17 | Re-signed manifest cannot forge file-derived facts, native SCM/config/run identity or baseline; private operator policy is separate | Native producer/runner administration remains a live trust boundary |
| AC18 | Controller/CLI parity test compares complete receipts/candidates using identical bytes, policy, evaluation time and replay history | Real 24-hour/new-run shadow comparison remains open |
| AC19 | Migration tests retain legacy DB/raw/cache/meta/batches/publication IDs; ambiguous/unclassified/interrupted state fails closed; enhanced disposable VM harness activates migrated schema2 | A real source-to-target activation remains separately authorized |
| AC20 | Persistent collision/replay/physical-job alias tests; lost-reply publisher recovers the same frozen commit without another push/proposal; audited scale identities | A second publisher is never enabled by restoring state |
| AC21 | Real file/Git dependency-closure drift tests plus service pre-work/frozen-commit holds | No fetched code is run to make a mismatch disappear |
| AC22 | Disposable Ubuntu Ansible exact-revision install/update/restart, authenticated Workbench checks, retained drafts/keys/collector state and two-location backups | Actual target update is not performed |
| AC23 | Interrupted migration, failed activation recovery, incompatible schema downgrade halt before stopping service and separate compatible legacy restore | Later v2 evidence remains in the retained root/backup for reconciliation |
| AC24 | Native default-branch proof; 24-hour/new-run fixture guards; source/node ownership, one batch, all-state PR/MR reconciliation and terminal requests | **Open:** actual shadow duration/run and authorized ownership handoff |
| AC25 | Real systemd service UIDs/credential mounts, private queue/raw/public projection permissions and reader/publisher phase separation | Real provider credentials/permission grants remain absent |
| AC26 | Two simultaneous real HTTP Workbench instances reject each other's keys/cookies and retain separate drafts; a shared browser-style cookie jar preserves both logins and logout independence; isolated Ubuntu authenticated service/recovery | No new cross-host deployment or automatic synchronization is claimed |
| AC27 | Actual Mac arm64/Linux x86_64 offline package runs produce identical full canonical pass/fail hashes at documented source/tree/tool versions | Real Proxmox prepared-runtime invocation remains open |
| AC28 | Versioned 1,000/2,000 distinct identity profile, 10% reruns, actual files/OPA, persistent quotas/429/restart, every-execution audit and measured CPU/RSS/disk/API/backlog | Synthetic fixtures and small payloads do not approve production capacity |
| AC29 | Additive verifier/store/proposal/identity/read-model paths; protected ledger/publishers/dependencies remain exact; coordinator review/fingerprint evidence | Existing personal acceptance is not transferred to a new provider/profile |
| AC30 | Candidate support/evidence matrix and explicit profile/role/capability boundaries | **Open:** provider/version-specific live report-only operating acceptance |

The first enhanced Ubuntu run at `7647cc6` stopped because a synthetic migration destination was below a root-owned directory. The fixture correction at `63984f3` provisions a private intake-owned parent for fresh migration/backup/restore paths and adds a fast actual-UID migration/recovery smoke; production permissions are not relaxed. Cookie successor `511d16c` integrates that exact correction. Full local validation passes at 1,151/1,152 tests respectively; native integration results are reported per exact PR/check rather than inferred from a local pass.

## Platform and proof matrix

| Combination | Executed engineering proof | Versions/limits and remaining acceptance |
| --- | --- | --- |
| GitHub SCM / Actions | Native-shaped branch/PR contexts, byte/run/config verifier, PR adapter/reconciliation, separate real Git, actual GitHub Linux test jobs | GitHub.com real test runner; new consumer workflow not adopted. GHES API-origin configuration is contract-tested only; installed GHES version unknown. GitHub PR provenance closure remains held where incomplete. |
| GitLab SCM / GitLab CI | Functional template; subgroup IDs, retry jobs, push and MR/merge-parent metadata, native API fixtures and MR proposal/review candidates | Target version/edition/URL unknown. GitLab lint/import, artifact/run/permission behavior, role equivalences and native enforcement unaccepted. Approval response without reviewed SHA stays unbound. |
| Bitbucket DC SCM / Bamboo | Functional Bamboo template, opaque keys, separate SCM rules/PR operations, bounded acquisition/verification, review candidates | Contract references include Bamboo REST 8.2.3 and Bitbucket DC API documentation; these are not installed versions. Target editions/plugins unknown; artifact integrity is not complete Bamboo provenance. Bitbucket Cloud is excluded. |
| Bamboo with another supported SCM | Explicit CI/SCM separation and evaluation-layer fixture composition | No implied end-to-end profile/edition acceptance or native Specs provenance. The first public candidate index admits the three default pairs above; other compositions are not accepted candidate-index profiles. |
| macOS | Python 3.13.18, OPA 1.18.2 Darwin arm64, real OS-denied network and concurrent HTTP/session tests | Tested evaluation/development host; actual UI deployment state is separate |
| Disposable Linux | Ubuntu 24.04 systemd/UID/credentials/Ansible, Python toolchain, OPA 1.18.2 Linux x86_64, actual network namespace | Reproducible CI fixtures; not the Proxmox target and not full VM/OS offline provisioning |

The two offline full canonical result hashes are `07463468547b2e138c8e5e7fd733084406f44b160b686f2dca8884c5993c51b8` (pass) and `3ef366b6bd53e26cccae8cebed791d303abcddd814354e6f913f6abe8825e9d3` (fail). See the [prepared package guide](../guides/prepared-runtime-package.md) for the actual distinct package/source identities; host-specific OPA/package hashes are intentionally separate. The [capacity profile](../guides/portable-capacity-profile.md) records exact measured source identities and limitations.

An [actual GET-only GitHub.com smoke](../../examples/portable-runtime/provider-assurance-github-get-smoke.json) used the published observer at `7647cc6` without credentials against native metadata and reviews for PR #375. Both PR reads bound the requested head; there were zero review observations/approval participants. The separate security observation correctly retained all 16 criteria as `not_proven` because the installed feature revision differed from native main. No provider mutation, role approval, privileged security assessment or operating acceptance follows. The sanitized evidence retains capture hashes; raw native responses stay private. GitLab/Bamboo/Bitbucket live access remains unavailable.

The localhost browser regression in [GCR-2026-181](../../governance/change-requests/GCR-2026-181-workbench-port-session-isolation.md) fails against exact parent `7647cc6` and passes at `a8387cd`: browser cookies do not distinguish ports, so cookie names now use the actual bound port for login/lookup/logout. Existing global cookies are ignored; sign in again after updating. This changes browser session naming, not keys, drafts, role authority or publisher ownership.

## Operational handoff and external blockers

Use the [portable update/recovery runbook](../guides/portable-vm-update-and-recovery.md), [collector guide](../guides/portable-consumer-service.md), [provider assurance contracts](../guides/provider-assurance-candidates.md) and [common intake guide](../evidence/portable-evidence-intake.md). No endpoint, route, mode or human authority is enabled by this matrix.

| Affected scope | Concrete missing input/decision | Smallest next step |
| --- | --- | --- |
| WP4/WP6, AC06/09/13/17/30 | GitLab/Bamboo/Bitbucket DC target URLs, actual versions/editions/plugins, native producer/job/artifact IDs and least-privilege access | Platform owner supplies the target profile; run native lint/import and an explicitly scoped report-only fixture job, retaining raw native evidence |
| WP6, AC29/30 | Reviewed issuer/subject mapping, role eligibility, personal action consent and operating acceptance for each new profile | Review candidate bindings and explicit capability equivalences using the existing human governance path |
| WP7, AC18/24/25/26/30 | Authorized target update, schema/source reconciliation, private configuration and source-reviewed ownership/node routing | Deploy an approved exact commit in paused mode; inspect/migrate/restore state; then observe shadow for at least 24 hours and a new matching native default-branch run |
| AC16 only | Separate scoped blocking authority and real host branch-rule/check enforcement | After authorization, verify negative/missing/stale results prevent merges in that scope; preserve report-only elsewhere |
| WP7, AC15/27/28 | OS/scanner preparation, real payload/retention/arrival distribution, provider latency/quotas, VM storage/IOPS and agreed SLO thresholds | Prepare a disposable representative target, rerun the versioned load and offline inputs, then obtain explicit capacity approval |

No missing live access prevents continued repo implementation; these remaining decisions cannot be replaced with synthetic success flags. Existing ha-CPsWMS accepted domain results, historical Trust and its separately recorded legacy blocking risk remain in their original sources.
