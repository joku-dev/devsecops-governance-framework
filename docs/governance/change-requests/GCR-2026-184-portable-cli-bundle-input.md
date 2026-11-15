# GCR-2026-184: Portable CLI bundle input compatibility

## Classification and intent

Correct executable evidence verification and its regression coverage. This is an
evidence-contract implementation correction, not a new governance source or
normative control. Source-document intake is not required. Released baselines,
OPA decisions, protected pilot artifacts and accepted result indexes are outside
the change.

## Observed problem

The first real ha-CPsWMS portable producer runs exposed a mismatch: the runtime
CLI writes `evaluation-input.json` as `{payload, subjects}`, while the common
verifier read it as a flat payload. Export retained the correct original bytes,
but subsequent verification failed with `normalized_input_does_not_match_files`.
Programmatic fixtures had supplied a flat payload and missed this CLI boundary.
The failure occurs independently of the separate missing live SCM protection
facts; fixing the envelope does not resolve or waive that capability gap.

## Resulting behavior

The verifier recognizes the exact CLI envelope, requires an object payload and
subjects identical to the result's ordered manifest, then derives critical facts
from the supplied files and performs the unchanged real-OPA recomputation.
Missing/extra envelope members or changed subjects are rejected even when the
bundle manifest is rehashed. Existing flat v2 inputs retain their checks and
remain readable. Exported evidence and historical receipt bytes are not rewritten.

## Validation and release implications

Regression coverage executes the real runtime CLI, bundle CLI, ZIP transport and
common verifier with synthetic native acquisition and pinned OPA. Additional
cases compare retained flat/enveloped inputs and reject altered subjects,
unexpected envelope members, forged payload facts and non-object inputs. Run the
complete pinned repository validation, viewer generation and strict docs build
before delivery. The final PR records actual outcomes and revision-bound role
review evidence.

The shared verifier source digest changes. Existing source-bound receipts and
shadow windows must not be renewed or upgraded silently. Mac and VM comparison
must select the same reviewed verifier revision; active services require the
usual controlled update before using it operationally. The original runtime
result keeps its own runtime pin and Trust. No native provenance, M2 acceptance,
publisher activation, enforcement change or released baseline is granted here.
