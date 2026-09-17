# Measured Security Results

This append-only store contains normalized, report-only container scan snapshots
for ha-CPsWMS. Records preserve severity totals, HIGH/CRITICAL details, image and
artifact identities, source hashes and run context. They support viewer history
and comparison without altering the official DevSecOps result.

The store has its own intake and selection rules. A newer typed-evidence snapshot
does not silently overwrite this history. Original low-severity details and full
producer archives remain subject to the consumer artifact-retention period.
