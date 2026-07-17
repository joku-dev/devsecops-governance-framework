# Multi-Consumer Readiness

Generated: `2026-07-17T21:56:30Z`

Readiness: `PASS` (report-only)

| Registered | DevSecOps | Architecture | Typed Evidence | Telemetry | Checks |
|---:|---:|---:|---:|---:|---:|
| 3 | 3 | 2 | 1 | 1 | 9 pass / 0 fail |

## Checks

| Check | Result | Reason |
|---|---|---|
| `multiple_consumers_registered` | `pass` | Registry contains 3 distinct consumer repositories. |
| `registry_ids_unique` | `pass` | Every registry entry has a unique owner/repository identifier. |
| `registry_summary_consistent` | `pass` | Registry summary declares 3; observed 3. |
| `devsecops_registry_coverage` | `pass` | The DevSecOps latest-state index covers exactly the registered consumers. |
| `result_storage_isolated` | `pass` | Every indexed result and latest source remains inside its consumer-specific status path. |
| `portfolio_registry_coverage` | `pass` | The portfolio projection contains exactly the registered consumer repositories. |
| `intake_concurrency_isolated` | `pass` | All central intake concurrency groups bind consumer repository and downstream run without cancellation. |
| `telemetry_identity_isolated` | `pass` | Intake event IDs are unique and stored below the matching consumer path. |
| `health_dimensions_registered` | `pass` | Every consumer represented in Intake Health is present in the integration registry. |

## Consumers

| Repository | Mode | DevSecOps | Architecture | Typed Evidence | Telemetry Events |
|---|---|---:|---:|---:|---:|
| `joku-dev/ai-native-engineering-factory` | `report-only` | True | False | False | 0 |
| `joku-dev/governance-framework-demo-consumer` | `report-only` | True | True | True | 3 |
| `joku-dev/ha-CPsWMS` | `block-on-error` | True | True | False | 0 |

Readiness proves isolated central storage, indexing, concurrency, portfolio projection, and telemetry identity. It does not require every consumer to produce every optional evidence domain and does not change enforcement.
