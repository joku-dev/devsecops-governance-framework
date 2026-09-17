# Typed Evidence Results

This append-only store contains centrally verified evidence snapshots grouped by
repository and evidence type. The current contracts cover vulnerability scans
and CycloneDX SBOMs. Each snapshot binds producer artifacts to repository,
commit, workflow run and attempt, and records content integrity, Freshness,
replay and the effective Evidence Trust level.

`status/typed-evidence-results-index.json` selects the latest mainline result per
evidence type. Typed evidence does not inherit Trust from a governance result and
does not itself grant compliance, production approval or risk acceptance.
