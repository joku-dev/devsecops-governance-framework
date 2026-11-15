# GCR-2026-177 — Reproducible portable intake capacity profile

Date: 2026-11-15. Status: implementation and measurement candidate.

Following GCR-2026-176 / PR #372, this increment implements the portability Goal's WP7/WP8 synthetic capacity evidence. Classification under the [artifact intake process](../../operations/processes/new-artifact-intake-process.md): versioned executable test profile, deterministic native API fixtures, measured processing/recovery reports and operational documentation. It is not a normative source, consumer adoption, authority decision or production capacity approval.

The scenarios use 1,000 and 2,000 distinct provider/instance/repository identities, one run and 10% reruns, real bounded artifact files, the shared native capture/file verifier and actual pinned OPA. Rate limits and a real worker-process restart exercise the existing durable SQLite queue. Remote API data is simulated locally and no proposal is published. Results must distinguish producer preparation, processing wall/CPU/RSS/disk/API costs, simulated clock/quotas and recovery. Zero-latency API fixtures cannot establish a production SLA. Actual target versions, latency, payload/retention distributions and operator capacity acceptance remain open.
