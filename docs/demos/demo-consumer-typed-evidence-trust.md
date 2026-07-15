# Demo Consumer Typed Evidence Trust

## Demo Goal

Show how an application repository produces vulnerability evidence and how the
central governance repository independently verifies and displays its Trust.
The demo deliberately keeps evidence quality separate from a governance pass
or delivery gate.

## Validated Starting Point

| Component | Validated state |
|---|---|
| Consumer | `joku-dev/governance-framework-demo-consumer` |
| Consumer commit | `4ec2b2bd53560e010ebb1c078c4d3bd41b0bfcc6` |
| Workflow run | `29432884108` on `main` |
| Scanner | Trivy `v0.70.0` |
| Findings | `0` |
| Central integrity | `pass` |
| Central Freshness | `pass` |
| Effective Trust | `integrity_verified` |
| Enforcement | `report_only` |

## Story In Four Steps

1. Open the consumer workflow run and show the `application-evidence`
   artifact. The consumer runs a real scanner, normalizes its output, and
   packages both the scan and evaluated artifact.
2. Explain that the producer's Trust record is only a claim carried with the
   evidence. The central governance repository downloads the complete artifact
   and recomputes both SHA-256 digests.
3. Open `status/typed-evidence-results-index.json` and show the recorded run,
   scanner, findings, integrity, Freshness, and `co_collected` binding.
4. Open `generated/viewer/status-viewer.html`, select **Typed Evidence Trust**,
   and show the same state as a central portfolio projection.

## Repeat The Intake

From the governance repository:

```bash
python3 scripts/intake_evidence_trust_github_actions_run.py \
  --repository-id joku-dev/governance-framework-demo-consumer \
  --run-id 29432884108
python3 scripts/generate_typed_evidence_results_index.py
python3 scripts/generate_status_viewer.py
```

For private repositories or automated cross-repository intake, provide
`GH_RESULT_INTAKE_TOKEN` with Actions read access. The workflow
`.github/workflows/intake-evidence-trust.yml` exposes the same operation as a
manual or repository-dispatch flow.

## What To Say Explicitly

- `integrity_verified` means the central verifier reproduced the expected
  content digests; it is not a vulnerability acceptance decision.
- Freshness `pass` means the evidence was within the provisional 24-hour
  window at verification time.
- `co_collected` means scan and artifact were captured together; it is not a
  scanner-signed attestation.
- `report_only` means a failed Trust check remains visible but does not block
  delivery or change governance `latest_result`.

## Safe Failure Demonstration

For a local explanation, copy the downloaded artifact to a temporary directory,
change either subject, and run the central verification test. The expected
result is `unverified` with a failed content-digest check. Do not alter the
committed validated snapshot or the historical GitHub Actions artifact.
