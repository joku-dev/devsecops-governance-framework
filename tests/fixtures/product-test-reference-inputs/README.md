# Immutable comparison inputs for full own-product tests

These are engineering conformance fixtures, not new governance sources,
accepted downstream evidence, released baselines or operating consent. They
preserve two exact source snapshots needed by existing original comparisons:

- `v1`: `6b557fefe295b58272d2271326576ca3a3687197`, 2,033 source files;
- `lifecycle-pilot`: `c2250325f34d938ea4f607036e003a36a3f2f9da`, 1,319 source files.

`manifest.json` pins both compressed archives, their sizes, original commits,
complete trees and explicit lack of inherited authority. Each archive contains
the complete original source inventory and raw commit, with every Git blob,
file mode, byte length and SHA-256 descriptor. Admission reconstructs the tree
and original commit before any reference objects enter a disposable test clone.
Neither parent history nor a connection to the original hosting service is
needed. These unprepared data archives are not installation packages.

The helper in `tests/acceptance/product_reference_inputs.py` accepts only the
two fixed identities. It requires a fresh private parentless test checkout,
keeps its current HEAD/tree/working files unchanged, and adds the two separate
reference roots under `refs/axiom-test-inputs/`. Complete original assertions
continue to read their exact historical bytes. The helper starts no archived
entrypoint. Existing tests may explicitly execute their known pinned original
functions for comparison; inspected consumer programs are never a fallback.

Normal working checkouts, shared/symlinked Git directories, corrupt archives,
coherently changed source trees and automatic reuse of interrupted preparations
are rejected. Supplying the fixtures does not mean the full test suite ran or
passed; its actual exit, test/skip counts and raw outputs remain separate proof.
Production/service/update recovery and the full compliance orchestrator remain
separate Goal work.

The engineering controller `tests/integration/run_product_unit_tests.py` uses
the actual prepared Python environment and requires a pinned prepared package
from the **same source revision and exact controller/helper bytes**. It admits a
fresh complete source copy, prepares the two reference roots, checks pinned
tools, then runs the complete fixed `python -B -m unittest discover -s tests`
command. It accepts no inspected repository, arbitrary program or smaller test
selection. Logs are bounded to 8 MiB per stream, the own command has a one-hour
wall limit, and actual failures/skips remain visible. It does not attest kernel
network/process-tree isolation or execute the full compliance orchestrator.

From the matching source checkout, with Git, Node and OpenSSL available:

```sh
/private/operator/candidate/venv/bin/python -B \
  tests/integration/run_product_unit_tests.py \
  --package /private/operator/prepared-v2.zip --sha256 <independent-package-pin> \
  --output-root /private/operator/new-product-test-run
```

The output root must be fresh and outside the checkout. The input package,
prepared environment, services, keys and existing instances stay unchanged.
The owned test projection retains known generated timestamp/display-path effects
as exact before/after bytes with independent pins. Only the closed nineteen
known generated paths and their specific metadata fields may differ; changes to
governance meaning, unknown files or other source bytes invalidate the result.
Native tool fingerprints are
observed separately; no token, SSH agent or ambient provider environment is
forwarded to the test subprocess.

Reproduce into a **new empty destination** from a local repository containing
the two fixed commits, without changing the source checkout:

```sh
python tests/acceptance/freeze_product_reference_inputs.py \
  --repository /private/operator/reference-repository \
  --destination /private/operator/new-reference-inputs
```

No Source Document Intake promotion or register mutation applies: the original
sources and historical approvals retain their own original context inside
comparison data. Current control derivation, Trust and personal action consent
continue to require their ordinary separate processes.
