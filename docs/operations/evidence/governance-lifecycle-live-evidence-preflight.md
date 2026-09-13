# Live Evidence Preflight

The read-only adapter checks a Self-Security run against the pinned producer in
the [disabled live preparation](governance-lifecycle-live-preparation.md).
[GCR-2026-072](../../governance/change-requests/GCR-2026-072-lifecycle-live-evidence-preflight.md)
records its scope. It creates a diagnostic capture, not an accepted lifecycle
observation, Finding, decision or closure.

## Capture and replay

```bash
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/preflight_lifecycle_live_evidence.py \
  --run-id 34757612640 \
  --output-dir /tmp/clg-evidence-34757612640
.venv-validation/bin/python scripts/preflight_lifecycle_live_evidence.py \
  --verify-bundle /tmp/clg-evidence-34757612640
```

The command uses authenticated `gh api` GET requests against GitHub.com only.
Credentials stay in `gh`; no API token or authorization header is stored.
No workflows are dispatched and no GitHub settings or messages are changed.
The operator selects an explicit run; there is no implicit latest-state update.

The destination must be new. Inside the repository, only
`generated/reports/lifecycle-live-preflight/` is permitted. Validation completes
before creating the capture directory, and exclusive creation prevents replacing
an existing capture. The completion manifest is written last. An interrupted
write can leave an incomplete directory; use a new destination for the retry.
An incomplete capture cannot pass replay. No operational publisher scope exists.

The bundle retains the raw archive and extracted JSON report, original API
responses before and after capture, source files read at the run's full commit,
the exact profile and a digest manifest. Replay checks the complete inventory,
raw hashes, report extraction, producer/criterion consistency and projection.
It does not call GitHub or independently authenticate saved API responses.

## Supported source and checks

The preparation fixes repository numeric ID and name, `main` plus `push`, the
Self-Security workflow path, artifact name and five producer source digests.
The collector binds workflow numeric identity, full commit, run, artifact and
repository/fork metadata. It compares metadata before/after the download to
reject races, checks the GitHub archive SHA-256, and rejects ambiguous or
unexpected ZIP members without extracting arbitrary paths.

The source model and report schema must match the pinned bytes. All explicit
criterion definitions and report counters are checked; GRS-002 is additionally
checked against the captured integer review count. The report's observation time
must lie between run start and artifact creation, followed by run completion and
capture. This checks internal timing; age in seconds is reported without an
approved freshness verdict.

The ten successful checks are:

- repository identity;
- mainline run context;
- workflow identity;
- first-attempt binding;
- artifact/run association;
- archive integrity;
- pinned producer revision;
- source profile and criterion;
- producer timeline;
- report consistency.

Only the first run attempt is supported. GitHub's current artifact metadata does
not independently bind an artifact to a rerun attempt, so all reruns are rejected.
PR, branch, manual, scheduled, failed and incomplete runs are rejected. A new
adapter/profile review is needed before broadening those contexts.

## Meaning and remaining acceptance

`acceptance_status: not_evaluated`, `official_state: false` and the diagnostic
record type are fixed in the output. The API capture establishes what the
selected GitHub provider returned and checks consistency against the pinned
source; it does not grant an accepted Trust level or replace the nine lifecycle
admission checks with ten diagnostic checks.

The Self-Security producer reads repository settings during execution. Its PASS
is an observation at that time; it does not prove uninterrupted branch protection
throughout a commit's history. Source API errors remain in the original report.
No artificial FAIL is created when the selected run reports PASS.

The maintainer has now confirmed trust roots, retention, freshness/skew and
replay policy (LD-04/05). The [durable pilot intake](governance-lifecycle-durable-pilot-intake.md)
applies them in a separate retained validation flow. Personal consent verification
and accountable operating acceptance (LD-07) remain prerequisites for live use.
The [dated live reference](../reference-runs/2026-09-13-clg-live-evidence-preflight.md)
records the actual first capture separately from official state.
