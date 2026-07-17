# Collection Attempts

This directory contains append-only, report-only records for failed or partial
evidence collection attempts. An attempt record is operational history; it does
not replace a successful evidence snapshot and does not change governance
enforcement.

Records validate against `schemas/evidence-collection-attempt.schema.json`.
Identical retries are idempotent. A changed payload for the same attempt ID is
kept in `status/intake-conflicts/collection-attempts/` for review.

Retrying collection is a manual operator action. Use the `Retry Collection
Attempt` GitHub Actions workflow with the repository-relative path of a record
whose errors are all marked `retryable`. The original record remains unchanged;
the selected existing intake workflow performs the new attempt.
