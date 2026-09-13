#!/usr/bin/env python3
"""Generate the separate action-validation projection; never publish official state."""
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ROOT, require
from lib.governance_lifecycle.pilot_actions import project_actions

INDEX='status/governance-lifecycle-pilot-actions.json'
REPORT='generated/reports/governance-lifecycle-pilot-actions.md'


def render(index):
    return '\n'.join(['# GitHub Pilot Action Validation','',
        f"As of: `{index['as_of']}`. Revision: `{index['revision']}`.",
        f"Finding state: **{index['finding_state']}**. Actions: **{index['counts']['actions']}**.",
        f"Pilot roles active: `{str(index['roles_active']).lower()}`.",
        f"Active decision: `{index['active_decision_ref']}`.",
        f"Active closure: `{index['active_closure_ref']}`.",'',
        'The personal channel probe is not action consent. A PASS without a prior failure creates no finding.',
        'Decision, progress and closure statements require their own exact request digest and current state revision.',
        'Retained consent can be withdrawn; no automated remediation is performed.',
        'This is a diagnostic eligibility projection, not operational activation or official consumer status.',
        index['limitation'],''])


def validate(repo=ROOT):
    index=project_actions(repo)
    require(strict_json((repo/INDEX).read_bytes())==index,'Pilot action index differs')
    require((repo/REPORT).read_text()==render(index),'Pilot action report differs')
    return index


if __name__=='__main__':
    index=project_actions()
    (ROOT/INDEX).write_bytes(json_bytes(index));(ROOT/REPORT).write_text(render(index))
    print('Rendered pilot action validation; no operational activation.')
