# Offline Review Quality Evaluation

`review-quality-v1.json` contains ten synthetic cases: eight known defects and
two benign counterexamples. It covers candidate derivation, released-package
mutation, blocking-mode changes, non-mainline latest promotion, stale review
binding, execution claims, private-text publication and CI/compliance confusion.
Labels restate existing repository boundaries; they introduce no new control.

`scripts/evaluate_agent_reviews.py --prepare NEW_DIRECTORY` creates private prompt
and response-schema packets without calling a model. Gold expectations remain
outside the packets. The neutral role contract and skill are included and
fingerprinted. The prompt prohibits tools, writes, network and delegation.
Actual model calls, if later explicitly authorized, must be recorded separately.

For offline grading, supply JSON with `evaluation_digest` and `packet_set_digest` from the manifest and
`records`: each record has a `case_id` and structured `response` matching its case
schema. Optional `trace_file` plus `trace_sha256` bind supplied runtime metadata.
The trace is not authenticated by hashing it. Requested/observed model identities
remain distinct; missing measurements stay unknown. Raw responses and reasons
are not copied into the report.
Each supplied runtime record must also bind `case_id`, `evaluation_digest`, `packet_set_digest` and a
distinct `run_id`, with the measured `elapsed_seconds`, optional token `usage`,
and requested/observed model fields. Preserve original event streams separately;
these case associations are declarations, not provider attestations. Reusing one
run for multiple cases or supplying a different case/revision is rejected.
Grade from the same prompt/role/skill checkout used for preparation. A changed
packet digest rejects responses even when the case dataset itself is unchanged.

The grader counts taxonomy true/false positives, missed findings, severity matches
and three impact/context classifications. Missing or invalid cases reduce
coverage, recall and classification accuracy; duplicate/unknown cases are
rejected. Precision/recall with zero denominators are null. Aggregate elapsed
time and token counters require complete measurement coverage; cached input is
reported separately and never added to input tokens. Sums of case elapsed times
are not batch wall-clock duration or a monetary cost estimate.

Compare the same complete case set and revision, provider permissions, model
effort and measurement coverage. One response set per candidate is appropriate.
Repeat runs to assess variance, and have a human assess reasoning and evidence
quality. A structured-label score does not establish general model superiority,
independent approval or reviewer identity. Unit-test gold answers and synthetic
trace fixtures are tests, never published live-model benchmark results. No CI
job calls a model and this change does not select a different production model.
