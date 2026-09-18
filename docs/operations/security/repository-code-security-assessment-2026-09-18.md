# Repository Code Security Assessment, 18 September 2026

## Scope And Assessment Standard

This dated review covers the executable code in `scripts/`, the maintained
Governance Workspace JavaScript in `apps/governance-viewer/`, active GitHub
workflows, the two pinned Python dependency sets and live GitHub security
alerts. Generated copies, retained historical releases and evidence snapshots
were not treated as separate active implementations.

The review uses OWASP ASVS 5.0 as the technical verification reference, NIST
SSDF 1.1 for secure-development practice and GitHub's Actions hardening guidance
for workflow supply-chain controls:

- <https://owasp.org/projects/asvs>
- <https://csrc.nist.gov/pubs/sp/800/218/final>
- <https://docs.github.com/en/code-security/tutorials/secure-your-organization/protect-against-threats>

This is an evidence-based code assessment, not a certification or proof that
the repository is free of every vulnerability.

## Result

The reviewed code has a strong baseline after GCR-2026-096, but the pre-change
state did not fully meet the expected secure-input and credential-handling
requirements. Two relevant trust-boundary defects were confirmed and corrected.
No known vulnerable pinned Python package, open GitHub security alert, command
injection or unsafe Python deserialization was found in the reviewed scope.

| ID | Initial severity | Finding | Resolution |
|---|---|---|---|
| RCS-001 | high | The default `urllib` redirect behavior could forward a GitHub bearer token from the API request to a different HTTPS origin used for artifact storage. | HTTPS-only redirect handler removes authorization on every origin change; downgrade and credential-bearing URLs are rejected; response sizes and timeouts are bounded. |
| RCS-002 | high | Five active intake paths extracted complete external ZIP artifacts without shared limits for members, expanded bytes, compression ratio, duplicate targets or special file types. | All five paths use one fail-closed extractor that validates the whole archive before writing and rejects traversal, absolute/Windows paths, duplicates, symlinks, devices, encryption and resource-limit violations. |
| RCS-003 | medium | CodeQL scanned Python but not the maintained viewer JavaScript. | `javascript-typescript` was added to the existing required CodeQL job. The check context stays `Analyze Python` to preserve branch protection. |
| RCS-004 | medium | Two XML ingestion paths did not consistently enforce explicit input size and DTD/entity rejection. | Candidate workbook XML and measured JUnit parsing now reject oversized content and DTD/entity declarations before `ElementTree` parsing. |
| RCS-005 | informational | Bandit and Semgrep identify SHA-1 calls although they are used for stable non-security IDs and the Git object format. | `usedforsecurity=False` and scanner annotations document the bounded non-cryptographic use. SHA-256 remains the evidence-integrity algorithm. |

## Verification Evidence

| Check | Result |
|---|---|
| GitHub Code Scanning alerts | 0 open before the change |
| GitHub Dependabot alerts | 0 open |
| GitHub Secret Scanning alerts | 0 open |
| `pip-audit 2.10.1`, `requirements-validation.lock` | 7 dependencies, 0 known vulnerabilities |
| `pip-audit 2.10.1`, `requirements-docs.lock` | 22 dependencies, 0 known vulnerabilities |
| Bandit 1.9.4 after hardening | 0 high, 0 medium; remaining low-confidence/low-severity diagnostics are reviewed uses of list-form subprocess calls, standard-library XML imports and false-positive literals |
| Semgrep 1.177.0 | Python, JavaScript and secret rules; no unresolved finding after documenting the two required non-security SHA-1 uses |
| Targeted attack regression tests | traversal, absolute and Windows paths, case-colliding targets, symlinks, member/count/expanded-size limits, cross-origin credential stripping and HTTPS downgrade rejection |

The dependency result is time-bound to 18 September 2026. Dependabot and the
weekly CodeQL schedule provide continued observation, while future changes
still require review and validation.

## Existing Safeguards

- Actions are restricted to GitHub-owned Actions and the selected OPA setup
  Action; repository settings require full commit-SHA pinning.
- Workflow permissions are explicit and the default token is read-only.
- Secret scanning, push protection and Dependabot security updates are enabled.
- Python validation and documentation dependencies have exact versions and
  hash-locked transitive distributions on the active intake/publication paths.
- Shell execution is avoided in the reviewed Python subprocess calls; commands
  use argument lists and no production `shell=True`, `eval`, `exec`, pickle or
  unsafe YAML loader was found.
- Viewer data crosses a dedicated projection and escaping boundary, with
  hostile-input browser tests retained as defense against stored XSS.

## Residual Security Work

The generated Self-Security observation from 17 September reports 13 of 16
criteria passing. Its three open items remain separate from the corrected code
defects:

- `GRS-002`: the live repository has one required approval rather than the
  two-independent-reviewer target;
- `GRS-005`: signed changes are not required on the default branch;
- `GRS-014`: the three historical release tags are not cryptographically
  verified.

Those controls need reviewer identities, signing custody and release-process
decisions. Rewriting historical tags merely to clear the finding would damage
the existing release record. Extended non-provider secret patterns and secret
validity checks also remain disabled in the live repository settings.

The CodeQL job name is intentionally still `Analyze Python` because it is a
required branch-protection context. Its configuration now covers both Python
and JavaScript; a later ruleset migration may rename the context only through a
coordinated settings and workflow change.

## Reproduction

Run the repository checks from a clean checkout:

```bash
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh

pip-audit -r requirements-validation.lock --disable-pip
pip-audit -r requirements-docs.lock --disable-pip
bandit -r scripts demo
semgrep scan --config p/python --config p/javascript --config p/secrets scripts apps demo
```

The last three tools are independent audit tools and are not installed by the
repository bootstrap. Record their versions and vulnerability-database date
when reproducing the assessment.
