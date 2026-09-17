# Measured L1 Results

This append-only store contains centrally recomputed, report-only assessments of
the 16 released L1 controls for the bounded ha-CPsWMS pilot. The intake verifies
selected JUnit, SAST, SBOM, vulnerability, image, GitHub API and deployment
records against the exact repository, commit, workflow run and attempt.

Statuses `measured`, `partial`, `findings` and `gap` describe evidence coverage.
They do not replace the official baseline evaluation, approve production use or
accept risk. The associated evidence-quality statement is stored separately in
`status/control-evidence-assurance/`.
