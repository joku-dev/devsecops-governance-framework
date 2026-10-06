# GCR-2026-115: Preserve the producer direct-download declaration

## Intent

Make `pipeline-evidence.json` carry the same producer-declared
`external_direct_downloads_detected` value as the configured
`governance-run-input.json`. This repairs the ECV-01 artifact disagreement
without claiming that the reusable workflow or central intake independently
measured consumer network traffic.

## Current failure

The v1.2.0 reusable workflow generates pipeline evidence before it stages the
optional governance run input. It reads `EXTERNAL_DIRECT_DOWNLOADS_DETECTED`
from its own job environment and silently defaults to `false`. A caller cannot
pass arbitrary job environment through `workflow_call`, so the value in a
consumer's run input can be `true` while pipeline evidence says `false`.

## Change

When `governance_run_input_path` is configured, read
`pipeline.external_direct_downloads_detected` from that file before producing
pipeline evidence. Require the file to exist, parse as JSON, and contain a
boolean at that location; fail the evidence collection step if any condition
is unmet. Emit that declared boolean into pipeline evidence. When no run-input
path is configured, preserve the existing environment-variable fallback for
backward compatibility.

The consumer producer remains responsible for its declaration. The value is
based on the consumer workflow's explicit dependency and tool-download steps;
it is not a packet-level or centrally observed egress measurement. Intake must
continue to retain source attribution for both artifacts.

## Impact

| Area | Impact |
|---|---|
| Controls, OPA, schemas | No change |
| Gate mode and blocking | No change; report-only remains report-only |
| Workflow behavior | Pipeline evidence now mirrors the configured producer declaration; invalid configured run input fails closed |
| Release impact | Prepare a backward-compatible patch release after review |
| Official indexes and viewer | No update until fresh consumer results are reviewed |
| Consumer registry | No admission is implied |

## Validation evidence

The regression fixture executes the actual embedded `Collect pipeline
evidence` script and verifies `true`, `false`, missing-file and invalid-type
cases. Full repository validation and the consumer round trip through the
versioned patch release are required before ECV-01 is reconsidered.

## Decision boundary

This change reconciles two copies of a producer declaration. It does not prove
that the declaration is accurate, measure consumer egress, close the full
closed-governance loop, admit either private pilot repository, or establish
independent review.
