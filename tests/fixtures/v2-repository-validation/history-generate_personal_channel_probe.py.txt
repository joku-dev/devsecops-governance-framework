#!/usr/bin/env python3
"""Render the bound personal statement for the appointed person to issue themselves."""
from lib.governance_lifecycle.adapter import strict_json
from lib.governance_lifecycle.contracts import ROOT, require
from lib.governance_lifecycle.personal_probe import validate_request, statement_body

REQUEST='model/governance/lifecycle/personal-channel/00000001.json'
TEMPLATE='generated/reports/lifecycle-personal-channel-statement.md'


def render(request):
    return ('# Persönlicher GitHub-Kanaltest\n\n'
        f"Diskussion: https://github.com/{request['repository_id']}/pull/{request['discussion_number']}\n\n"
        'Bitte als `joku-dev` selbst einen neuen Kommentar mit dem folgenden vollständigen Inhalt posten. '
        'Die Erklärung prüft ausschließlich den persönlichen Freigabekanal. '
        'Sie gibt keine Behebung, keinen Abschluss und keine Live-Aktivierung frei.\n\n'
        '```text\n'+statement_body(request)+'```\n\n'
        'Nicht durch Codex oder eine andere Automation posten lassen. Einen abgegebenen Kommentar '
        'nicht bearbeiten oder löschen; Ablehnung und Widerruf werden als neue, referenzierende Kommentare erfasst.\n')


def validate(repo=ROOT):
    request=strict_json((repo / REQUEST).read_bytes())
    validate_request(request,repo,require_current_head=False)
    require((repo / TEMPLATE).read_text()==render(request),'Personal statement template differs')
    return request


if __name__=='__main__':
    request=strict_json((ROOT / REQUEST).read_bytes())
    validate_request(request,ROOT)
    (ROOT / TEMPLATE).write_text(render(request))
    print('Rendered personal-channel statement; nothing posted to GitHub.')
