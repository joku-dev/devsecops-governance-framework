# Official Release Statement: L1 Baseline v1.1.1

## Release Identification

- Release name: `L1 Baseline v1.1.1`
- Intended release tag: `l1-baseline-v1.1.1`
- Repository: `joku-dev/devsecops-governance-as-code`
- Release status: `prepared in repository`

## Statement

This patch release corrects the released workflow wrapper used by downstream repositories.

The fix ensures that `governance_run_input_path` is accepted by the released `L1` wrapper and forwarded to a compatible reusable workflow commit.

## Release Intent

This release preserves revision safety while correcting a packaging defect found during real downstream validation with `ha-CPsWMS`.
