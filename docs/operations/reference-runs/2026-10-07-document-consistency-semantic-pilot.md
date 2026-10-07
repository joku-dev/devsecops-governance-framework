# Bounded document-consistency semantic pilot, 7 October 2026

## Authorization and scope

The maintainer authorized one manual, report-only provider run through the
existing ChatGPT Pro sign-in. The authorized input was limited to:

- `DSCB-STD-REQ-001`;
- `PRA-STD-REQ-001`;
- the versioned synthetic semantic-review fixtures.

The five local unregistered documents, secrets, consumer repositories and all
other repository content were excluded. Model training was disabled in the
account data controls. Zero Data Retention was not available or confirmed, and
the maintainer explicitly accepted the applicable ChatGPT retention for this
bounded pilot. The run authorized no publication, normative decision,
compliance claim or production rollout.

## Isolated execution

The run used an isolated temporary directory containing exactly the two
sanitized requirement extracts, their source manifest, four synthetic
calibration files and a temporary response-schema copy. Hashes for both real
sources and the manifest matched the versioned repository values before the
provider call.

| Field | Observed value |
| --- | --- |
| Provider path | existing ChatGPT sign-in through Codex CLI |
| Provider label requested in the response | `openai-codex-chatgpt` |
| Model | `gpt-6-luna` |
| Codex CLI | `0.159.2` |
| Prompt version | `phase2-live-pilot-1` |
| Declared configuration | `dcr-config-0001` |
| Execution mode | ephemeral, read-only sandbox |
| Actual model run | completed |
| Report mode | report-only |
| CLI token observation | 13,808 tokens |
| Provider cost observation | unavailable through the ChatGPT Pro run |

The checked-in `dcr-config-0001` remains a provider-neutral candidate with
provider status `not_configured`. The one-time authorization did not promote or
rewrite that immutable candidate. Consequently, this observation is not a
reproducible active reviewer configuration.

## Structured-output preflight

Three attempted starts were rejected by the provider before semantic
processing because the repository's Draft 2020-12 validation schema contains
keywords outside the provider's Structured Outputs subset:

1. a `const` without an explicit adjacent type;
2. `uniqueItems`;
3. `oneOf` for the nullable search scope.

No model response resulted from those preflight attempts. The actual authorized
run therefore used prompt-constrained JSON without provider-side schema
enforcement. The repository validator remained the only acceptance boundary.
This compatibility gap must be resolved with a separate provider projection or
normalizing adapter before another live run.

## Provider output and validation result

The model returned one unconfirmed candidate and reported that all 111 rows had
been reviewed. It did not reproduce the synthetic prompt-injection instruction
or the deliberately fabricated quotation. The response was still rejected
before finding-level validation:

```text
semantic response schema error at findings.0.applicability.status:
'context_missing' is not one of ['same_context', 'different_context', 'unknown']
```

The model placed a semantic-state value in the applicability-status field.
Because the response failed the authoritative schema, the repository produced
no validated report, no accepted or quarantined finding record, and no human
decision artifact. The candidate must not be repaired retrospectively or used
as governance evidence.

| Evidence item | Value |
| --- | --- |
| Raw response size | 2,784 bytes |
| Raw response SHA-256 | `72ed715571a1628597225c51a2c5f523407905bf2e46ddfcc9e69b70e4aa023d` |
| Provider-declared finding count | 1 |
| Schema validation | fail closed |
| Validated finding count | 0 |
| Human finding evaluation | `not_run` |
| Raw response retained | no; deleted after validation and technical triage |

The digest is recorded only to identify the rejected bytes. The raw response is
not committed and cannot be reconstructed from this record.

## Pilot assessment

The run demonstrates the intended trust boundary: plausible model text does not
become a finding unless it satisfies the repository contract. It also exposes
two operational gaps:

- the provider-facing structured-output schema must be projected from, rather
  than equated with, the authoritative repository schema;
- the adapter must normalize or reject enumerated fields before the
  authoritative validator and must record an immutable active configuration.

The run does not supply a successful real semantic pilot baseline. Usefulness,
false positives, known misses, triage effort and provider-output stability
remain unevaluated. The rollout decision remains `pending`.

## Decision boundary

This observation records an authorized but schema-rejected provider run. It
does not approve another provider call, publish content, confirm a finding,
change source authority, modify a released baseline or authorize production
rollout.
