# Governance Lifecycle Scenario Viewer (CLG-06.2)

CLG-06.2 presents the verified [CLG-06.1 overview](governance-lifecycle-overview.md)
in a separate read-only page:

```text
generated/viewer/governance-lifecycle-viewer.html
```

This viewer shows synthetic GRS-002 scenarios. It does not update the official
consumer status viewer or accept observations, decisions, waivers or closures.
Its scenario selector and event filters only change the displayed subset.
[GCR-2026-068](../../governance/change-requests/GCR-2026-068-governance-lifecycle-viewer.md)
records classification, scope and review expectations.

## Generate and open

Regenerate the overview after accepted synthetic history changes, then build the
viewer. Choose an explicit overview `as_of` that includes the latest recorded
transaction in all three scenarios:

```bash
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/generate_governance_lifecycle_overview.py \
  --as-of 2026-09-14T00:10:00Z
.venv-validation/bin/python scripts/generate_governance_lifecycle_viewer.py
.venv-validation/bin/python scripts/validate_governance_lifecycle_ledger.py
python3 -m http.server 8000 --bind 127.0.0.1 --directory generated/viewer
```

Open `http://127.0.0.1:8000/governance-lifecycle-viewer.html`. The standalone HTML
also supports local file opening: data, styles and the application script are
embedded; no network fetch is required. The documented timestamp is a synthetic
evaluation instant, not a claim about live state on 14 September.

`--output /tmp/lifecycle-viewer.html` writes a separate HTML copy. The generator
first verifies the overview and Markdown report against all accepted histories.
It refuses to write over ledger, model, status, script or schema inputs and the
official consumer viewer, including through symlink aliases.

For a different evaluation instant, regenerate the overview and then the page.
There is no browser clock, automatic refresh or client-side expiry calculation.
The checked-in overview must continue to cover its accepted histories. Use the
CLG-06.1 historical JSON/Markdown command for an earlier cutoff without replacing
current checked-in outputs.

## Walk through the scenarios

The page opens with **Closure & reopening**. Its finding is currently open,
although its history contains one closure and one reopening. Completed work and
PASS are separate dimensions. In the event history, the 14:10 receipt has an
older 13:05 effective time; it does not reopen the finding. The newer 14:20 FAIL
does. Expand an event's references to inspect its finding ID and the immutable
event/transaction digests.

Select **Evidence conflict**. The finding needs clarification, even though its
latest accepted evidence is PASS. Quarantine is counted separately from the
three accepted failures. Its retained remediation case shows revoked
authorization and its recorded target; work progress is not presented as an
active approval.

Select **Time-limited exceptions**. The finding remains open with full coverage
of three explicit failing observations. The page separately shows covered and
uncovered observation references, renewed decision need, and the revoked,
expired, withdrawal and active exception records. Expiry is evaluated at the
fixed snapshot instant and does not invent a new event.

Use **Event type** to select one category, **Search this scenario** to match event
text, finding/reference IDs, revision or UTC time, and **Reset filters** to return
to the full selected history. The visible/total event count reflects the filter;
summary cards continue to describe the full selected scenario. Changing
scenario resets both event filters. A search with no matches shows an explicit
empty result rather than hiding the rest of the finding state.

Native labeled controls, visible keyboard focus and expandable reference details
support keyboard use. Cards and detail panels stack at narrow widths; the event
table has its own horizontal scroll area. With JavaScript disabled, the page
points to the generated Markdown report instead of claiming a displayed state.

## Presentation and publication boundary

The same synthetic finding identity occurs in three independent histories.
The page shows one scenario at a time and computes no portfolio total. It embeds
the unchanged verified overview. Presentation text never upgrades fixture consent
to authenticated human approval; LD-01–05 and LD-07 remain open.

The generator safely encodes JSON and the page creates data-derived DOM content
as text. A Content Security Policy allows only the exact embedded application
script and local inline styles; network connections and forms are disabled.
The browser is a presentation surface, not a second lifecycle kernel or an
approval channel. Its context check is not a substitute for repository replay.

`validate_governance_lifecycle_ledger.py` also checks byte-for-byte viewer equality
with the deterministic rendering of the verified overview. The
`lifecycle-synthetic` publisher adds exactly the new HTML path to its existing
closure-history and derived-report allowlist and validates the viewer before
branch creation or push. After appending history, regenerate pilot output,
overview and viewer in that order. Other ledger domains, profiles and consumer
indexes remain outside that publisher scope.

Tests cover deterministic data embedding, script-element escaping, the script
hash in the security policy, labeled controls, protected output paths, rejection
of a forged overview before writing, and stale/modified viewer rejection before
publication. Browser checks cover scenario switching, filtering, reset, empty
results, expandable references and desktop/narrow layouts. Full pinned
validation and strict MkDocs remain required before committing.
