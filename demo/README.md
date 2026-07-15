# Demo Environment

This folder contains a small local demonstration environment for the governance-as-code repository.

It shows how:

- a sample service can be represented,
- release candidate inputs can be evaluated against OPA governance policies,
- governance reports and the status viewer can be generated in one end-to-end run.

## Contents

- `sample-service/`: minimal example service
- `inputs/release-candidate-green.json`: compliant release candidate
- `inputs/release-candidate-red.json`: intentionally non-compliant release candidate
- `model/evidence/`: example evidence artifacts

## Run

```bash
python3 scripts/run_demo.py
```

Outputs are written to `generated/demo/`.
