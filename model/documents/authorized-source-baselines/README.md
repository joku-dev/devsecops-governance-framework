# Authorized Source Baselines

Store each human-reviewed baseline decision as
`source-baseline-YYYYMMDD.json`, conforming to
`schemas/authorized-source-baseline.schema.json`.

A candidate record means the exact source set has completed P1 lifecycle and
exact-scope consistency review and is awaiting a human decision. An approved
record must identify the approver, decision date and governance decision
record. The `authorized_source_set_sha256` binds the sorted source IDs,
versions, repository paths, approved status and file hashes. When an approved
source changes, create a new baseline record and mark the previous one
`superseded`; never rewrite its source set or decision history.

The generated process status report is not a baseline record. It does not
create or approve entries in this directory.
