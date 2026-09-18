# GCR-2026-096: Repository Code Security Hardening

## Intent

Der Maintainer hat eine Prüfung des ausführbaren Repository-Codes gegen
gängige Sicherheitsanforderungen beauftragt. Die Prüfung deckt Python- und
JavaScript-Code, Abhängigkeiten, GitHub-Workflows, Intake-Vertrauensgrenzen und
die live gemeldeten GitHub-Sicherheitsbefunde ab. Bestätigte technische
Schwachstellen werden im selben Change behoben.

## Artifact Classification

| Field | Decision |
|---|---|
| Artifact | Code-Sicherheitsbewertung, sichere Download-/Archivbibliotheken, Scanner-Abdeckung und Regressionstests |
| Type | security hardening, test, workflow and documentation |
| Target | `scripts/`, `.github/workflows/codeql.yml`, `tests/`, `docs/` |
| Owner | Repository Owner / Governance Platform Lead |
| Source Document Intake required | no; no new governance source is introduced |
| Evidence contract impact | none; accepted result schemas and stored snapshots remain unchanged |
| Runtime governance impact | none; intake transport is hardened without changing governance outcomes |
| Repository enforcement impact | CodeQL additionally analyzes JavaScript under the existing required check context |
| Release impact | none; released baseline packages and tags remain unchanged |

## Findings And Decisions

1. GitHub artifact downloads used the default Python redirect handler. That
   handler copies the `Authorization` header into redirected requests, including
   redirects to another origin. Use an HTTPS-only handler that strips
   authorization when the origin changes, adds timeouts and bounds response
   sizes.
2. Five active intake paths extracted complete external ZIP files without a
   common preflight for member count, expanded size, duplicate destinations,
   special files or compression ratio. Replace all `extractall` calls with a
   fail-closed extractor and cover malicious archives with tests.
3. CodeQL analyzed Python only although the Governance Workspace contains
   maintained JavaScript. Add `javascript-typescript` while keeping the existing
   `Analyze Python` check name stable because main protection requires that
   context.
4. XML inputs need explicit size and DTD/entity rejection. Add these checks to
   the candidate-workbook importer and measured JUnit parser.
5. SHA-1 uses are non-cryptographic: one preserves deterministic candidate IDs,
   the other verifies Git's SHA-1 object identity. Mark this intent explicitly
   instead of treating either value as a security signature.

## Validation Plan

- [x] malicious archive and redirect regression tests
- [x] Bandit 1.9.4 without high or medium findings
- [x] Semgrep 1.177.0 Python, JavaScript and secret rules without unresolved findings
- [x] `pip-audit` for both hash-locked dependency sets: no known vulnerabilities
- [x] GitHub open-alert read-back: zero Code Scanning, Dependabot and Secret Scanning alerts before the change
- [x] `./scripts/bootstrap_validation_env.sh`
- [x] `./scripts/validate_all.sh` (`588` tests passed)
- [x] strict documentation build
- [x] pull-request checks on GitHub: Governance CI `35303873574`, CodeQL/Analyze Python `35303873612`, Dependency Review `35303873584`, Self-Security `35303873596` and Consumer Lifecycle Guard `35303873613` passed

## Release Decision

No DevSecOps or architecture baseline release is required. The change hardens
the central implementation and expands repository-local static analysis; it
does not alter released policy behavior or consumer enforcement mode.
