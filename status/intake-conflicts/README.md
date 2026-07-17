# Intake Conflict Quarantine

This directory stores generated, report-only conflict records when an intake
attempt would overwrite an existing result snapshot with different evidence.

Conflict records do not replace the original snapshot and do not update
`latest_result`. They must be reviewed before the conflicting evidence is
accepted through a separate governance decision.
