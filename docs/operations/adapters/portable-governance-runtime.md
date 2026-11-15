# Portable Governance Runtime v1 — Pipeline-L1 Candidate

For the integrated candidate and actual live boundaries after this increment, see the
[WP0–WP8 / AC01–AC30 engineering matrix](../planning/platform-portability-acceptance.md).

This is the executable M1 candidate for the platform-portability goal, linked to
[GCR-2026-173](../../governance/change-requests/GCR-2026-173-portable-runtime-m1.md).
It adds a shared evaluator, provider adapters and versioned contracts. It is not
a released baseline, operational acceptance or a completed M2 implementation.

## Execution and boundaries

`scripts/governance_runtime.py` exposes four commands:

| Command | Input and behavior | Exit status |
|---|---|---|
| `context` | Real application checkout, reviewed profile and native CI/SCM context | 0 for a normalized context; missing facts remain visible |
| `evaluate` | Context JSON plus `evaluation-input.json`; no provider credentials/network required | 0 when evaluation completed, including findings; 2 when incomplete/error |
| `gate` | Canonical result, actual application checkout and optional mode | report-only findings: 0; blocking findings: 1; invalid/incomplete/stale result: 2 |
| `run` | Collection, physical evidence checks, evaluation and gate in one invocation | Same gate contract; preserves available context/input/result/diagnostics |

`report-only` and `block-on-error` are the only modes. Unknown modes and
`waiver-required` are rejected; no environment flag grants a waiver. A complete
`pass` concerns **pipeline-l1 scope only**, never all 16 L1 controls. Five mapped
controls have pipeline checks and unchanged Rego evaluation; remaining controls
are `not_evaluated` and need their own governed evidence/review. The result sets
`full_baseline_assessment: false` and `evidence_trust: unverified` explicitly.
An evaluated candidate is not provenance-verified evidence or approval.

Execution, decision, evidence trust and requested/observed enforcement remain
separate. No adapter asserts `blocks_merge: true`; external enforcement remains
`not_verified`. Synthetic contexts are visibly marked and cannot yield a
successful blocking gate. A missing required fact or tool error exits 2 even in
report-only. No existing required merge check is configured by these templates.

## Reproducible dependencies and invocation

Use a reviewed full runtime commit, Python 3.12 or 3.13, dependencies installed
with `pip install --require-hashes -r requirements-validation.lock`, and the
checksum/version-pinned OPA from `scripts/install_validation_opa.py`. Keep the
runtime checkout, virtual environment and reviewed consumer profile outside the
untrusted application checkout on prepared GitLab/Bamboo agents. The GitHub
wrapper checks out its requested runtime separately and verifies a 40-character
commit reference. Adopt only a reviewed commit; no portable release tag exists.

```bash
/opt/axiom/venv/bin/python /opt/axiom/runtime/scripts/governance_runtime.py run \
  --ci gitlab-ci --profile /etc/axiom/consumer.json --checkout /work/application \
  --artifact dist/application-source.tar.gz --sbom security/sbom.cyclonedx.json \
  --scan security/vulnerability-scan.json --output-directory /work/portable-evidence \
  --mode report-only --opa /opt/axiom/venv/bin/opa
```

The output directory must be fresh. Preserve each run separately; retries do
not overwrite an existing result. For separate evaluation use its `context.json`
and `evaluation-input.json` as `--context` and `--input`; then call `gate` with
`--result result.json --checkout /work/application`. Evaluation uses an explicit
`--at` timestamp when deterministic comparison is needed. Gate binds the result
to the actual checked-out commit and the same runtime/baseline digests.

The versioned `config/portable-runtime-compatibility.json` registry selects
compatible baseline packages. Each consumer profile pins baseline ID, checksum
manifest digest, domain and scope. The context records those bindings plus
actual runtime/adapter versions and runtime source digest; mismatches are held.
The registry also pins the official full Linux OPA 1.18.2 builds used by the
preserved CI. The existing static/Mac pins remain unchanged; unknown hashes or
versions are rejected before execution. The installer still selects its verified
static Linux builds. The initial registered baseline is the checksum-verified `releases/l1/v1.1.3` snapshot. Its source
revision, package digest, runtime source digest, adapter and OPA versions are
recorded separately. The released L1 wrapper still pins its historical reusable
workflow; existing wrappers, released bytes, protected pilot files and CLIs are
unchanged. New candidate adoption is explicit.

Evaluation itself works without network once runtime/dependencies/OPA and
normalized inputs are prepared. Context collection needs native provider APIs;
the installer can use its existing mirror/cache/offline options. This is no
claim that public scanners or their databases work offline.

## Real evidence inputs

Supply the application artifact, a CycloneDX SBOM with `components` and a
`metadata.component` identity, and normalized vulnerability JSON. The SBOM
component must bind the artifact using a `SHA-256` hash; a missing binding is a
finding. Vulnerability evidence needs `scanner`, `max_severity`, `findings`
(each finding has a recognized `severity`) and `artifact_sha256`. The summary
must agree with findings and the actual artifact digest. Placeholder scanners,
empty JSON objects, absent files, unsafe paths and mismatched subjects cannot
produce success. These structural/integrity checks do not authenticate the
scanner; native provenance and central verification belong to M2.

Build, scanner execution and scanner-format normalization are responsibilities
of the application pipeline. The templates call its application-owned
`ci/build-and-scan.sh` hook; provide that executable with real tools or replace
the producer task with your existing build/scanner job. The governance repository
does not supply an application-specific build implementation. Add its real build/scanner tasks before the Bamboo
evaluation task or provide retained artifacts from preceding GitLab jobs. The
GitHub wrapper downloads the named application artifact into a separate subtree;
retain the configured relative artifact/SBOM/scan paths when uploading it.
No template creates synthetic security results for product use. Raw build and
security files are retained in native CI artifacts as well as the assessment
JSON, so M2 transports can recompute their digests instead of trusting a hash
without accessible source bytes.

## Providers, identities and capability limits

The profile schema is `portable-profile-v1.schema.json`; context and result have
separate v1 schemas. Example profiles are under `docs/examples/portable-runtime/`.
Replace example identities/endpoints with reviewed real values. Store tokens in
the configured secret environment variable; never put token values into profiles.
API requests require HTTPS, reject credential-bearing URLs and redirects, bound
response size/time and redact errors. Native repository identity must match the
configured provider response. Repository keys include provider, canonical
instance origin and opaque native ID; run keys additionally include CI instance,
run/job and attempt. GitLab subgroup paths and Bamboo keys are not cast to ints.

| Profile | Native acquisition and limits | Current acceptance |
|---|---|---|
| GHA-01 | GitHub repository/branch/classic protection; only explicit admin enforcement and empty bypass allowances prove the supported no-direct-push case. Active repository rulesets with explicit empty bypass actors are supported; other bypass/inherited configurations remain unknown. PR head/base/merge and actual checkout are distinguished. | Implemented and fixture-tested; new live path open |
| GL-01 | GitLab API v4; all matching protected-branch rules, paginated project approval rules; branch/detached-MR/merged-result contexts | Implemented and fixture-tested; installed version/edition and live path open |
| BB-01 | Bitbucket DC REST repository identity, paginated exact-branch PR-only restrictions without exemptions and effective required-approvers settings; Bamboo native build/job keys and checkout | Implemented and fixture-tested; installed Bitbucket/Bamboo versions and live path open |

The following independent fields refer to the source revision bound by the
public delivery-PR review receipt. API references are GitHub REST 2022-11-28,
GitLab API v4, Bitbucket REST 1.0/branch-permissions 2.0 and Bamboo Specs YAML v2;
installed product versions/editions remain unconfirmed.

| Profile | implementiert | lokal_geprüft | syntax_geprüft (target system) | live_geprüft | offen |
|---|---|---|---|---|---|
| GHA-01 | yes | API fixtures + real OPA | no; YAML parsed only | no | Actual workflow call, credentials, failure/artifact behavior and native provenance |
| GL-01 | yes | API fixtures + real OPA | no; YAML parsed only | no | Version/edition, CI lint/import, real MR/run and evidence binding |
| BB-01 | yes | API fixtures + real OPA | no; YAML parsed only | no | Both product versions, Specs import, real native/restart evidence and live restrictions |

Test cases and limits are mapped in the
[declared M1 acceptance record](../planning/portable-runtime-m1-acceptance.md).

Unsupported branch matchers, unavailable effective settings or permission errors
remain explicit capability gaps. The GitHub workflow's default token may lack
administration-read access; an explicitly provisioned read-only SCM token can be
passed through `scm_read_token` for that lookup. No permissions are auto-granted.
GitLab/Bamboo reader secrets likewise require the documented read APIs only.
Bamboo's configured event is an operator declaration, not independent native
provenance. GitHub currently records its native logical job key (`GITHUB_JOB`), not a
REST job-execution ID; independent job binding remains M2 work. GitLab retries
use distinct native job IDs; Bamboo restart/attempt
provenance remains a separate M2/live capability to validate.

CI and SCM are independently configured. GitLab SCM with Bamboo is locally
composed in tests; this is not an extra live support profile. Profiles must
belong to a trusted runtime/operator configuration. An editable application
profile or changed consumer pipeline cannot establish central trust or authority.

## Migration, VM and acceptance

Use the updated GitLab and Bamboo template entrypoints and the new GitHub
`devsecops-portable-v1.yml` wrapper. Legacy generators remain callable for old
pins; their known unknown-context weakness is not retroactively fixed in a
historical baseline. Diagnostics are archived with each CI system's finalization
mechanism. Templates need target-system syntax/import checks before deployment;
YAML parsing alone is not a platform compatibility certificate.

Mac and VM use the same pure evaluator modules. No systemd/Linux-only import
enters the core. This change does not alter the VM queue, routing, credentials,
publisher, installed revision or Workbench. M2 still must deliver a shared
verifier, native artifact/run proofs, legacy identity migration, provider-aware
persistent state, central publishing and isolated VM migration/recovery/scale
acceptance. Existing report-only/shadow defaults and the single publisher remain.

Reference contracts checked against the official [GitLab variables](https://docs.gitlab.com/ci/variables/predefined_variables/),
[protected branches](https://docs.gitlab.com/api/protected_branches/),
[approval rules](https://docs.gitlab.com/api/merge_request_approvals/),
[GitHub protection API](https://docs.github.com/en/rest/branches/branch-protection),
[Bitbucket repository API](https://developer.atlassian.com/server/bitbucket/rest/v900/api-group-repository/)
and [Bamboo YAML Specs](https://confluence.atlassian.com/bamboo1200/bamboo-specs-yaml-format-1680481857.html).
These references do not confirm installed versions or a successful live import.
