# GCR-2026-092: Project Trust and Freshness for every L1 control

The maintainer authorizes an additive, report-only assurance projection for all
16 released L1 control references. It relates each centrally measured control
assessment to the quality of the evidence that supports it without changing the
released baseline or turning evidence quality into a compliance decision.

| Classification | Decision |
|---|---|
| New artifact | `control-evidence-assurance-v1` snapshot linked to one measured L1 run |
| Control result | Preserve `measured`, `partial`, `findings`, and `gap` unchanged |
| Trust | Derive per evidence group and aggregate conservatively per control |
| Missing scope | Add an explicit `missing` evidence group and aggregate the control as `unverified` |
| Freshness | Commit-, artifact-, time-, runtime-, or release-candidate-bound according to evidence type |
| Replay, custody, attestation | Always state `pass`, `fail`, or `not_evaluated`; never infer success |
| Automation | Collect measured L1 assurance with the existing successful ha-CPsWMS mainline typed-evidence intake |
| Viewer | Show assurance dimensions and individual evidence groups for every L1 control |
| Enforcement | Report-only; no deployment approval, risk acceptance, OPA or required-check change |
| Release impact | No mutation of `l1-baseline-v1.1.3`; historical measured L1 snapshots remain readable |

The control-level aggregate may be lower than the Trust level of an individual
artifact. A verified SBOM, scan, test report or API response cannot compensate
for missing organizational approval, full dependency scope, operational records
or another mandatory part of the control.
