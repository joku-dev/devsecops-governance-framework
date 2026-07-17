# Evidence Agent Provenance

This directory stores explicit, append-only links between an evidence subject
and an agent participation record. It distinguishes selection, execution,
review, and approval. Provenance is report-only metadata and never raises an
Evidence Trust level.

Records validate against `schemas/evidence-agent-provenance.schema.json`.
Only an explicit recorded association is shown; the repository does not infer
agent involvement from changed paths or timestamps.
