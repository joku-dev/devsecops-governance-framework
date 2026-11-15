# Portable collector capacity measurements

This is the synthetic engineering profile from [GCR-2026-177](../../governance/change-requests/GCR-2026-177-portable-capacity-profile.md). It does not grant production capacity or publisher activation. Measurements use core/controller source `b7d13de9dc77f043aa4b8cc6df8d536fd34a4329` on this Mac; later systemd fixture fixes do not change that measured source identity.

The versioned load profile `tests/capacity/portable-intake-v1.json` contains 1,000 or 2,000 distinct repository identities, three CI providers across two instances each, one execution plus 10% reruns, 4 KiB physical artifacts and 10% repositories with critical findings. IDs and display paths repeat across realms intentionally. Each execution gets its own actual producer evaluation, artifact archive, native fixture acquisition, collector OPA evaluation and durable receipt. Synthetic contexts remain held and cannot publish. Native APIs are zero-latency fixtures; this does not measure real provider latency or prove Bamboo provenance.

| Distinct repositories | Executions | Processing wall time | Native calls | Worker peak RSS | Retained operations bytes |
| --- | --- | --- | --- | --- | --- |
| 1,000 | 1,100 | 390.09 s | 10,447 | 58.52 MiB | 61,631,270 |
| 2,000 | 2,200 | 1,287.57 s | 20,935 | 77.05 MiB | 118,903,049 |

Actual hardware is Darwin arm64, 10 logical CPUs, Python 3.13.18. Preparation and worker/child CPU times are recorded separately in the reports. Both tests exit one real worker process with a claimed task pending and recover it in a second process. All receipts survive. Injected 429 responses, the shared persistent hourly API budget and 25-task cycle limit remain active. The virtual clock advances 60 seconds per cycle; maximum simulated queue ages of 3,120/6,900 seconds are not measured elapsed latency. Recovery took under 1 ms in these local fixtures, not a guaranteed recovery SLO.

The checked-in [1,000-repository report](../../examples/portable-runtime/capacity-1000-candidate.json) and [2,000-repository report](../../examples/portable-runtime/capacity-2000-candidate.json) include source, benchmark and profile hashes. A separate audit compares every expected physical task to its stored receipt, repository, attempt, producer decision and file/baseline verification, including negative decisions. Zero missing receipts, identity collisions or remote publications were found. Raw catalogs, credentials and databases stay outside Git.

Reproduce with the pinned validation environment and OPA on PATH:

```bash
python tests/capacity/run_portable_intake.py --repositories 1000 --output-root /private/tmp/axiom-capacity-new-1000
python tests/capacity/summarize_portable_intake.py --measurement-root /private/tmp/axiom-capacity-new-1000 --output /private/tmp/axiom-capacity-new-1000-audited.json
```

Use `--repositories 2000` for the second scale; use `6` for the inexpensive integration smoke. Every output root must be fresh. Do not run simultaneous measurements on shared hardware or change the benchmark while its child workers are running. The optional capacity CI workflow runs only six repositories.

Remaining production limits: target provider versions/editions, API latency/quotas, actual artifact sizes and retention, daily arrival peaks, hardware/IOPS and agreed throughput/latency thresholds. Revalidating a large registry each cycle is a measured CPU cost: doubling this fixture took more than twice the wall time. Publication freezes at most 25 candidates in one active batch, so human PR/MR throughput can dominate daily processing. These small artifacts do not size real scan/SBOM retention or approve the current VM disk. Repeat on disposable representative Linux hardware with an agreed load before a 1,000–2,000-repository capacity approval.

## Hardened collector repeat

The same frozen profile/harness was repeated against collector source `7647cc6df3a1abe5d8df797c191d558771067b7d`, after native default-branch proof and retained legacy projection were added. The [1,000-repository repeat](../../examples/portable-runtime/capacity-1000-hardened-candidate.json) and [2,000-repository repeat](../../examples/portable-runtime/capacity-2000-hardened-candidate.json) retain that exact measured source and evaluator/verifier digests. Later Workbench cookie and disposable-fixture corrections do not change the measured collector algorithms; they are not relabelled as benchmarked revisions.

| Repositories | Executions | Processing wall | Worker / OPA-child CPU | Native calls | Worker peak RSS | Operations bytes |
| --- | --- | --- | --- | --- | --- | --- |
| 1,000 | 1,100 | 385.11 s | 287.45 / 99.67 s | 10,447 | 58.39 MiB | 62,456,954 |
| 2,000 | 2,200 | 1285.85 s | 1088.25 / 201.51 s | 20,935 | 77.14 MiB | 120,501,617 |

Both repeats retain all expected receipts: 110/220 negative decisions and 990/1,980 positive decisions match their own producer result and native identity. No missing receipt, identity collision or publication was found; each run recovers one previously claimed task in a second real worker process. Maximum queue ages remain 3,120/6,900 seconds on the explicit simulated clock; they are not measured network latency.

The [measurement context](../../examples/portable-runtime/capacity-hardened-measurement-context.json) discloses a concurrent 158.239-second full validation on another checkout during part of the 2,000-repository repeat. Hardware was shared; observed wall time includes that activity. Worker and OPA-child CPU are measured separately; parent preparation, aggregate host memory, real provider latency, scanner jobs and human review are outside the table. These repeat measurements do not grant production capacity acceptance.
