# WP-ECV-001 External Consumer Validation — Wave 1 retest and Wave 2 results

**Execution date:** 2026-10-06 (UTC)
**Scope:** Re-run cJSON and go-httpbin with the merged PR #215 candidate, then run two newly selected upstream projects, Marked and Gson, in separate private pilot repositories.
**Disposition:** Technical integration works across four projects, but all four report-only governance decisions remain `fail`. Do not admit any consumer or describe these runs as compliance passes.

This is a follow-up to [the 2026-10-05 pilot record](external-consumer-validation-pilot-2026-10-05.md). That record remains an accurate historical account of its earlier runs; this document records the subsequent tests.

## Summary

| Consumer | Source pin | Consumer run | Consumer job | Baseline decision | Main observed issue |
|---|---|---|---|---|---|
| cJSON | `DaveGamble/cJSON` `c859b25da02955fef659d658b8f324b5cde87be3` | [37442608835](https://github.com/joku-dev/governance-eval-cjson/actions/runs/37442608835), PR head `73bd8721a23db68d1e1fafd07499adcdd59beeba` | success | `fail` | `repository.direct_push_allowed` was `true`; no Trivy findings |
| go-httpbin | `mccutchen/go-httpbin` `34888fd21d6667e9f0c842db483ba595b9c8c094` | [37442715864](https://github.com/joku-dev/governance-eval-go-httpbin/actions/runs/37442715864), PR head `87b40dfb0f5b97d344bb197f49b12c8445d97620` | success | `fail` | Direct push allowed; one `unknown` severity finding |
| Marked | `markedjs/marked` tag `v18.1.0`, commit `e809386482250c5c856d54e34b5930ee7a5faa4f` | [37444280115](https://github.com/joku-dev/governance-eval-marked/actions/runs/37444280115), main commit `9662e1ee84d252715b1b1a6a92a510d1e4fe3e97` | success | `fail` | `repository.direct_push_allowed` was `true`; no Trivy findings |
| Gson | `google/gson` commit `845664ba1c307e6c1910d07cfed2f622e0ad8df1` (`2.14.1-SNAPSHOT`) | [37444325741](https://github.com/joku-dev/governance-eval-gson/actions/runs/37444325741), main commit `bc7658f8735d5f41a78d8916897aa3419565e913` | success | `fail` | Direct push allowed; Trivy maximum severity `medium` |

All four consumer workflows produced a build artifact, a source-tree CycloneDX SBOM, a Trivy scan, and a governance run input. The v1.2.1 report-only gate job succeeded in each run. This means the workflow executed successfully; it does **not** change the failed governance decision. The gate reported `blocks_merge: false`, so findings were visible without blocking the pilot workflow.

The Marked test ran `npm ci`, the upstream `npm test`, and packed `marked-18.1.0.tgz`. The Gson test ran upstream Maven `verify` and `javadoc:jar`, and packaged the Gson JAR. Neither source tree was edited to make the test pass; integration and pilot files were added alongside the pinned upstream source.

## Findings

### Governance decisions

The gate artifacts for cJSON, Marked, and Gson each say:

```text
expected repository.direct_push_allowed=False, got True
```

For go-httpbin the same control failed, and the scan added:

```text
CVE-2026-39824 in golang.org/x/sys v0.41.0; severity unknown; fixed version v0.44.0
```

Trivy reported `max_severity: unknown`, exceeding the configured `high` maximum. The finding is not evidence that the dependency is safe. It needs a separate dependency review and rescan.

The pilot repositories are private and were created under the same `joku-dev` owner. GitHub API reads for private-repository branch protection and rulesets returned HTTP 403 under the current plan. An import push to each repository's `main` succeeded, but this does not establish the absence of organization-level rules or bypass conditions. Accordingly, the `direct_push_allowed: true` facts were producer-declared and are consistent with the observed push; the central intake's `branch_protected: false` is **not an authoritative protection measurement**, because its helper maps API errors to `false`.

The four `governance-eval-*` repositories are separate private repositories, not GitHub forks of their upstream projects (`fork=false`, no parent repository in GitHub metadata). They contain imported, pinned source snapshots for the pilot.

The two Wave 2 `.governance/repository-facts.json` files also say that branch rules were queried before import. That statement is inaccurate. A corrected measurement-source sentence was prepared in the isolated local clones but could not be committed or pushed because the configured SSH signing agent was unavailable in the sandbox. The remote facts files were left untouched. If these pilot repositories are retained or retested, correct those files and rerun before relying on their repository-facts record.

### Security scans and produced artifacts

| Consumer | Trivy result | Built artifact SHA-256 |
|---|---|---|
| cJSON | `none`, zero findings | `c8a3ee84902c6c4ff4fdd660bbf1091511ad027bde0c25d78be0ad84d8e443b9` |
| go-httpbin | `unknown`, one finding (`CVE-2026-39824`) | `c8ce24db66ccbaadc72a17976cbc71072796361f4231438eceaedaa744456f0f` |
| Marked | `none`, zero findings | `1db8f1caf4582846035890a154a904e59b5990d36579567ad873dd2b4977a600` |
| Gson | `medium`, six records covering three unique CVEs in Guava and Okio | `99b53ca06707602a957850200a88504717a570b17270a93ac84f1e0bd7c05767` |

The Gson scan records CVE-2023-2976 and CVE-2020-8908 in `com.google.guava:guava`, and CVE-2023-3635 in `com.squareup.okio:okio`; each record has a fixed-version field. The measured result remains the scanner output for the pinned source/dependency tree, not a general safety statement about Gson.

For each run, the pipeline evidence and the downloaded governance run input both declared `external_direct_downloads_detected: true`; the values matched. This is producer-declared evidence of dependency downloads, not independent observation of consumer network egress.

### Central intake and Trust

The four runs were ingested by `scripts/intake_github_actions_run.py` using an isolated checkout at governance `main` commit `901d06d0c2f5ff62bb9aff987d04fbd9d35e8235`. The snapshots are local-only and append-only within `/private/tmp/ecv-intake-20261006`:

| Consumer / run | Local snapshot | Governance-result Trust |
|---|---|---|
| cJSON / `37442608835` | `status/results/joku-dev__governance-eval-cjson/2026-10-06T09-24-38Z-run-37442608835.json` | `integrity_verified` |
| go-httpbin / `37442715864` | `status/results/joku-dev__governance-eval-go-httpbin/2026-10-06T09-26-36Z-run-37442715864.json` | `integrity_verified` |
| Marked / `37444280115` | `status/results/joku-dev__governance-eval-marked/2026-10-06T09-39-18Z-run-37444280115.json` | `integrity_verified` |
| Gson / `37444325741` | `status/results/joku-dev__governance-eval-gson/2026-10-06T09-40-55Z-run-37444325741.json` | `integrity_verified` |

For all four, central intake verified subject digests, run/commit association, artifact association, freshness, replay context, and recorded custody. `baseline_ref_resolved` failed because the pilot wrapper was selected by immutable governance merge SHA, while the run's authoritative reusable-workflow metadata did not resolve that candidate as a released tagged baseline. The wrapper file was present at governance commit `901d06d`; release tag `v1.2.1` was not published. Trust therefore remains `integrity_verified`, not `provenance_verified`.

Trust here describes the **captured governance-result artifact and its custody**. It does not establish the integrity, safety, or provenance of the application source or built package, and it does not override the `fail` governance decision.

### Other upstream GitHub workflows

The Gson repository also ran workflows copied from the upstream source. In initial run `37444325741`, `Build`, `Check Android compatibility`, Maven dependency review, and Actions dependency review succeeded. `CodeQL` (`37444323921`) and `Scorecard` (`37444323929`) failed during checkout with GitHub's `Repository not found` response for the private pilot repository; their analysis steps did not run. These are separate from the successful ECV workflow and its governance result. A later dependency-update PR triggered additional upstream runs; those PR-branch runs are not part of the four main pilot snapshots above.

## Evaluation and limitations

1. **Cross-project portability:** the integration executed for C/C++, Go, JavaScript/Node, and Java/Maven projects. That is useful evidence of technical portability across build ecosystems.
2. **Independent organization operation:** not tested. All pilot repositories are private and under one owner; the tests do not validate another team's credentials, permissions, branch policy, or independent review.
3. **Policy enforcement:** not tested as a blocking control. Every consumer run was report-only and allowed the workflow job to succeed while the baseline decision failed.
4. **Baseline release provenance:** not established. The workflow wrapper is pinned by a governance merge SHA, but is not yet an independently released/tagged baseline.
5. **Branch protection:** not independently measured for the private pilots because the current GitHub plan denied the API queries. Direct push succeeded, and producer facts disclose that. The central intake's `false` protection value is only a fallback value after query failure.
6. **Signatures:** no signed application artifact or producer attestation was emitted in these runs. The Trust assessor did not evaluate signature validity, issuer trust, or subject matching.
7. **Vulnerabilities:** go-httpbin has one `unknown` severity finding; Gson has six Trivy finding records at medium/low severity, including three unique CVEs. None of the findings was waived or suppressed by the pilot.

## State and next actions

- The two Wave 1 consumer updates remain PR-branch runs; these tests did not merge their consumer PRs.
- `governance-eval-marked` and `governance-eval-gson` were created as private pilot repositories. Do not add them to the official consumer registry based on these tests.
- No intake snapshot was copied into official `status/`, generated indexes, or the viewer. The official portfolio and ha-CPsWMS status are unchanged.
- Keep all four consumers report-only. Do not publish the v1.2.1 release tag based solely on this test result.
- Before another iteration: correct Wave 2 repository-facts measurement text; determine a supported way to measure private branch/ruleset state; resolve the go-httpbin finding; make the candidate baseline resolve through released authoritative metadata; and obtain an independent reviewer/operator if the goal is to validate organizational independence.

## Follow-up verification (2026-10-06)

The central DevSecOps and architecture GitHub Actions intake helpers are
updated in [PR #217](https://github.com/joku-dev/devsecops-governance-framework/pull/217)
so only a successful, well-formed branch API response can produce a boolean
`repository.branch_protected` value. API failures now produce `null` and a
separate `repository.branch_protection_lookup.status: "unavailable"`; HTTP
status or error type is recorded without the error message. Existing
append-only snapshots remain historical records and are not rewritten. The
pilot's previous `false` values must therefore continue to be read as unknown,
not as confirmed unprotected branches.

The remediation candidates were first verified in isolated working copies,
then submitted to the separate private pilot repositories for review:
[cJSON PR #1](https://github.com/joku-dev/governance-eval-cjson/pull/1),
[go-httpbin PR #2](https://github.com/joku-dev/governance-eval-go-httpbin/pull/2),
and [Gson PR #3](https://github.com/joku-dev/governance-eval-gson/pull/3).
All three point to the published signed tag, and none changes its upstream
project.

Updating the nested go-httpbin example module from `golang.org/x/sys` v0.41.0
to v0.44.0 removed the reported CVE-2026-39824 finding. In fresh tagged run
[37467832720](https://github.com/joku-dev/governance-eval-go-httpbin/actions/runs/37467832720),
the consumer build, race tests, SBOM, Trivy scan, and report-only baseline job
succeeded; the scan had zero findings. Its governance decision remains `fail`
because the producer declares `repository.direct_push_allowed: true`; it does
not block the PR. A temporary local intake assessment reached
`provenance_verified`. An earlier retry selected a stale same-name artifact
and failed to find its run input; the fresh single-attempt run completed
correctly.

For Gson, dependency management scoped to the benchmark-only `metrics` module
selected Guava 33.7.0-jre and Okio 1.17.6, removing CVE-2023-2976,
CVE-2020-8908, and CVE-2023-3635. Remote run
[37467911213](https://github.com/joku-dev/governance-eval-gson/actions/runs/37467911213)
completed its Maven build, consumer evidence, and report-only gate; the remote
Trivy scan had zero findings. Its governance decision also remains `fail`
because `repository.direct_push_allowed` is `true`. The successful branch
endpoint lookup reports `protected: false`; detailed ruleset access remains
unavailable. A temporary local intake assessment reached
`provenance_verified`.

cJSON run [37467713254](https://github.com/joku-dev/governance-eval-cjson/actions/runs/37467713254)
also completed its consumer build and report-only gate with zero Trivy
findings. Its temporary local intake assessment reached `provenance_verified`.

GitHub's authoritative `referenced_workflows` metadata for all three runs
reports `refs/tags/l1-baseline-v1.2.1` and its signed tag object. The branch
API reported `protected: false` for these run snapshots; detailed ruleset
queries remain unavailable. All three consumer PRs remain unmerged. No run
was added to official status indexes or the viewer.
