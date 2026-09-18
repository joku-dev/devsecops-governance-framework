# Staging Deployment Evidence

The staging deployment intake preserves a real, authorized runtime observation
without changing an earlier CI assessment or a released baseline.

The current result covers the isolated `ha-cpswms-stg-01` VM and the deployed
ha-CPsWMS commit `5d5772d989b0080ae041969315742c8fbbca6dfe`. The producer bundle
is versioned in the application repository. The central normalized snapshot is
stored append-only under `status/staging-deployment-results/`.

The intake performs these checks:

- every bundle file is covered exactly once by `SHA256SUMS`;
- every receipt artifact record matches the actual file hash and size;
- approval, target, deployed commit and source run agree;
- the source run is an admitted successful mainline measured-L1 run;
- the result is staging-only, report-only and has no failed runtime checks;
- the intake occurs within seven days of the observed deployment;
- the normalized record has a deterministic evidence binding.

Run the intake with the immutable evidence-repository commit:

```bash
.venv-validation/bin/python scripts/intake_staging_deployment_evidence.py \
  --bundle /path/to/ha-CPsWMS/deployment/staging/evidence/<bundle> \
  --evidence-repository-commit <full-commit>
```

The Governance Workspace shows the result under **Repositories → ha-CPsWMS →
Staging**. The L1 view presents the later staging contribution for controls 013,
014 and 016 separately from the immutable CI measurement. Evidence Trust is
`integrity_verified`; independent attestation, production authorization and
general vulnerability risk acceptance are outside this result.
