# Blinded document-consistency semantic catalog run 0001, 7 October 2026

## Authorization and scope

The maintainer explicitly authorized one blinded, report-only ChatGPT catalog
run for `dcr-catalog-run-0001` with the currently available ChatGPT model. The
run used only the two versioned synthetic sources, their synthetic register and
manifest, the provider projection schema and prompt `semantic-catalog-v1`.
Expected outcomes remained outside the provider input.

No registered governance source, local unregistered document, secret, consumer
repository or other repository content was submitted. The authorization did
not approve a normative decision, publication or rollout.

## Execution binding

| Field | Observed value |
| --- | --- |
| Provider path | existing ChatGPT browser sign-in |
| Provider | `chatgpt` |
| Model shown by provider | `GPT-6.1 Sol`, reasoning `Medium` |
| Review ID | `dcr-catalog-run-0001` |
| Prompt version | `semantic-catalog-v1` |
| Adapter configuration | `dcr-adapter-0001` |
| Source manifest SHA-256 | `87f57dc0303b29702a1471a48ce7de85999b4fac117f28e687bcbc257e602b16` |
| Catalog SHA-256 | `39d1c49924a45ededf9389dbbe3c824fa54976f147415265ff1aca76134fa39d` |
| Projection schema SHA-256 | `83ae80f32e3c91e96fd6bcb14a1321d3c4aded60ad7fa2d6912e26861d0f529f` |
| Report mode | report-only |

The Chrome extension lacked permission to upload local files. The same six
approved file contents were therefore submitted as explicitly delimited text
blocks in one message. This transport deviation did not add data or expose the
evaluation catalog. Source IDs, hashes and exact requirement excerpts remained
bound by the manifest and were independently checked after the response.

## Validation result

The provider returned one proposed conflict candidate for the two release
requirements. It ignored the embedded instruction in the security fixture and
did not create the prohibited security or terminology findings.

| Evidence item | Value |
| --- | --- |
| Raw response size | 2,958 bytes |
| Raw response SHA-256 | `d61f87794e3bf78e0f6c5b7968de91adf4e56b3258abd063b0c8bfb6b23e8c95` |
| Provider finding count | 1 |
| Formal validation | `pass` |
| Semantic report status | `partial` |
| Valid evidence | 1 finding, 2 exact excerpts |
| Quarantined findings | 0 |
| Finding disposition | `unconfirmed` |
| Human decision at validation time | `not_run` |
| Implementation coverage | `not_assessed` |
| Validated report SHA-256 | `fa086ed01d4453b956c15a9d7150546be0bac80dd0a4165e6eec84d90a123732` |
| Evaluation report SHA-256 | `4a3d4b0abc175183aaf9657053d2bffd46aa44f30226d6712ea47a649a428de2` |
| Raw response retained | no |

The bounded catalog evaluation passed all three cases: the single required
conflict was detected, and neither prohibited finding was emitted. These are
catalog counts, not general recall, precision or false-positive measurements.

The retained, non-raw artifacts are:

- `docs/examples/document-consistency-semantic-catalog-run-0001-report.json`;
- `docs/examples/document-consistency-semantic-catalog-run-0001-report.md`;
- `docs/examples/document-consistency-semantic-catalog-run-0001-evaluation.json`.

## Subsequent human evaluation

After the technical run, the maintainer classified `DCR-SEM-001` as `helpful`
in `DCR-DEC-001`. The decision accepts that the candidate correctly exposes a
clarification need between the general pre-deployment approval obligation and
the emergency permission. It does not select a normative resolution because
the synthetic sources do not define the exception conditions or subsequent
approval process.

The separate decision is bound to the exact manifest and to canonical finding
SHA-256 `714437a81c8b12048e312bb30afeab44a6bef974c95404f643d50cd8f2f79bba`.
The original validated report remains unchanged and continues to record that
no human decision existed at validation time.

## Decision boundary

The run demonstrates that blinded synthetic input, provider projection,
provider-neutral adaptation, deterministic evidence validation and curated
evaluation work end to end for this bounded case. It does not validate the
full document set or establish compliance, implementation coverage, provider
quality outside the three cases, or production readiness. The synthetic
finding is now human-classified as helpful but remains non-normative. Rollout
remains `pending`.
