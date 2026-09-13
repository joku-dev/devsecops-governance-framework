# GCR-2026-075: Personal Channel Confirmation and CRLF Compatibility

The maintainer personally posted the exact bound statement on PR #87. GitHub's
comment API returned CRLF line endings, revealing that the LF-only marker check
silently ignored valid input. Normalize CRLF only when parsing; retain original
provider bytes and raw comment identity for edit/deletion checks.

| Field | Classification |
|---|---|
| Artifact types | Parser fix, regression tests, retained diagnostic provider captures, generated reference report and operating updates |
| Target paths | Lifecycle scripts/tests, `generated/reports/lifecycle-personal-channel/`, dedicated report and evidence guide |
| Owner | Governance analysis and evidence/intake; repository stewardship and release management |
| Source Document Intake | No; an actual diagnostic channel test, not a normative source |
| Evidence contract impact | Accept equivalent transport line endings without changing the signed request digest or personal assertion |
| Runtime impact | GET-only verification; no action consent or live activation |
| Release impact | None; released baselines and enforcement unchanged |
| Validation | Pinned full suite, strict docs, CRLF/edit negatives, offline capture replay and independent GitHub recheck in required PR CI |

Accepted diagnostic capture files are preserved by the existing Git-prefix check.
Replaying stored bytes demonstrates consistency; only a fresh provider recheck
can substantiate a newly published capture. The first confirmed channel test
remains distinct from action-specific consent and LD-07 operating acceptance.
