# Bounded document-consistency semantic pilot 2, 7 October 2026

## Authorization and scope

The maintainer explicitly authorized one further manual, report-only model run
after merge of the provider-neutral stabilization in PR #227. The authorization
retained the earlier scope and handling boundaries:

- `DSCB-STD-REQ-001`;
- `PRA-STD-REQ-001`;
- four versioned synthetic calibration files;
- existing ChatGPT Pro sign-in with model training disabled;
- applicable ChatGPT retention accepted because Zero Data Retention was not
  confirmed;
- raw response deleted after deterministic validation and technical triage.

The five local unregistered documents, secrets, consumer repositories and all
other repository content remained excluded. The run authorized no publication,
normative decision, compliance claim or rollout.

## Preflight and isolated execution

The temporary read-only execution directory contained exactly the two
requirements-only source extracts, their manifest, the provider projection
schema, four synthetic calibration files, the prompt and the local run
configuration. Both source hashes and the manifest hash matched the versioned
repository values before execution. Total prompt, source and calibration input
was 25,809 bytes.

| Field | Observed value |
| --- | --- |
| Provider path | existing ChatGPT Pro sign-in through Codex CLI |
| Provider label | `openai-codex-chatgpt` |
| Model | `gpt-6-luna` |
| Codex CLI | `0.159.2` |
| Prompt version | `phase2-live-pilot-2` |
| Adapter configuration | `dcr-adapter-0001` |
| Source manifest SHA-256 | `9aabf243290cff3157ee427647c643c8dbb676f2c9a64092a2067dd0b9628002` |
| Projection schema SHA-256 | `83ae80f32e3c91e96fd6bcb14a1321d3c4aded60ad7fa2d6912e26861d0f529f` |
| Execution | ephemeral, read-only, no persisted Codex session |
| Report mode | report-only |
| Provider cost observation | unavailable through the ChatGPT Pro run |

The structured-output preflight and provider execution both completed without
the schema compatibility failures observed in the first pilot.

## Validation result

The provider returned a schema-valid projection containing no finding
candidates and two explicit limitations. The adapter applied no normalization.
The authoritative repository validator then passed schema, manifest, current
source hashes and execution metadata with no errors or quarantined records.

| Evidence item | Value |
| --- | --- |
| Raw response size | 523 bytes |
| Raw response SHA-256 | `7c130838816294824a1bcc9d9d62916d8bc3f07d70ecc19562c273882afb351b` |
| Provider-declared finding count | 0 |
| Adapter normalization count | 0 |
| Formal validation | `pass` |
| Semantic status | `partial` |
| Validated finding count | 0 |
| Quarantined finding count | 0 |
| Human finding evaluation | `not_run`; there was no finding to classify |
| Implementation coverage | `not_assessed` |
| Validated JSON SHA-256 | `64191e59cebafc60cff99dc1eb84f3fe6a882d1f61d1e2af1815685ba4cfe2cc` |
| Raw and transient response retained | no |

The provider stated that no evidence-backed candidate was identified in the
two permitted extracts and that the bounded extracts do not establish whether
potentially related requirements apply to the same circumstances. This is a
bounded no-candidate observation. It is not evidence that the sources are
consistent, complete or compliant.

The versioned validated reports are:

- `docs/examples/document-consistency-review-phase2-live-pilot-report.json`;
- `docs/examples/document-consistency-review-phase2-live-pilot-report.md`.

## Assessment and decision boundary

The second run closes the technical execution gap demonstrated by the first
pilot: provider structured output, deterministic adaptation and authoritative
validation now work end to end. It does not establish semantic effectiveness.
With no real candidate, usefulness, false positives, triage effort and human
classification cannot be measured. Known misses also remain unmeasured because
the two real extracts have no approved semantic expected-result catalog.

The rollout decision therefore remains `pending`. A methodology comparison or
Mistral run would require a separate scoped authorization and should reuse the
same manifest, projection, adapter boundary and evaluation criteria.
