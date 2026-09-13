#!/usr/bin/env python3
"""Retained diagnostic channel captures and independent checks; never action consent."""
from pathlib import Path
import subprocess
from lib.governance_lifecycle.adapter import strict_json
from lib.governance_lifecycle.contracts import ROOT, canonical_digest, require, timestamp
from lib.governance_lifecycle.personal_probe import (
    collect_probe, comment_identity, replay_probe_snapshot, validate_request,
)
from generate_personal_channel_probe import REQUEST

CAPTURES='generated/reports/lifecycle-personal-channel'
REPORT='generated/reports/lifecycle-personal-channel-evidence.md'


def prior_comments(snapshots):
    comments={}
    for snapshot in snapshots:
        for comment in snapshot['result']['relevant_comments']:
            comments.setdefault(comment['id'],comment)
    return list(comments.values())


def load_captures(repo=ROOT):
    root=Path(repo); directory=root/CAPTURES
    require(directory.is_dir() and not directory.is_symlink(),'Channel capture directory required')
    request=strict_json((root/REQUEST).read_bytes())
    validate_request(request,root,require_current_head=False)
    captures=[]
    for number,path in enumerate(sorted(directory.iterdir()),1):
        require(path.is_file() and not path.is_symlink() and path.name==f'{number:08d}.json','Unexpected channel capture path or sequence')
        snapshot=strict_json(path.read_bytes())
        require(snapshot['request']==request,'Archived channel request differs')
        require(snapshot['capture_method']=='github_api_get_via_gh','A provider capture is required')
        require(snapshot['previous_comments']==prior_comments(captures),'Channel capture omits or changes prior statement history')
        result=replay_probe_snapshot(snapshot)
        if captures:
            require(timestamp(result['captured_at'])>=timestamp(captures[-1]['result']['captured_at']),'Channel capture time regressed')
        captures.append(snapshot)
    require(bool(captures),'Channel capture history is empty')
    return captures


def render(captures):
    result=captures[-1]['result']
    lines=['# Personal GitHub Channel Evidence','',
        'Context: diagnostic personal-channel probe. No remediation, closure, role change or live activation authorized.','',
        f"Latest retained status: **{result['status']}** as of `{result['captured_at']}`.",
        f"Request digest: `{result['request_digest']}`.",
        'Human presence: explicit personal self-attestation; GitHub authenticates the account.','',
        '| Capture | Captured at | Status | Snapshot digest |','|---|---|---|---|']
    for i,snapshot in enumerate(captures,1):
        item=snapshot['result']
        lines.append(f"| {i:08d} | {item['captured_at']} | {item['status']} | `{canonical_digest(snapshot)}` |")
    lines += ['', '## Retained personal statements','']
    for comment in prior_comments(captures):
        lines.append(f"- [Comment {comment['id']}]({comment['html_url']}), GitHub user ID `{comment['user']['id']}`, issued `{comment['created_at']}`.")
    lines += ['', 'Original provider response bytes, including CRLF line endings, are retained in each capture.',
        'Offline replay verifies consistency. Required PR CI independently rechecks newly published captures against GitHub.',
        'This report describes the last retained observation; recheck the provider before relying on a current statement.', '']
    return '\n'.join(lines)


def validate(repo=ROOT):
    captures=load_captures(repo)
    require((Path(repo)/REPORT).read_text()==render(captures),'Personal channel evidence report differs')
    return captures


def provider_projection(result):
    return {key:result[key] for key in ('request_digest','status','last_statement_id','issues')} | {
        'comments':[comment_identity(c) for c in result['relevant_comments']]}


def verify_new_captures(repo,base_ref,*,collector=collect_probe):
    repo=Path(repo); captures=load_captures(repo)
    accepted=set(subprocess.check_output(['git','ls-tree','-r','--name-only',base_ref,'--',CAPTURES],cwd=repo,text=True).splitlines())
    count=0
    for number,snapshot in enumerate(captures,1):
        if f'{CAPTURES}/{number:08d}.json' in accepted:
            continue
        fresh=collector(snapshot['request'],repo=repo,previous_comments=snapshot['previous_comments'])
        require(timestamp(snapshot['result']['captured_at'])<=timestamp(fresh['result']['captured_at']),'Channel capture claims a future observation')
        require(provider_projection(snapshot['result'])==provider_projection(fresh['result']),'Personal channel provider state differs')
        count+=1
    return count


if __name__=='__main__':
    captures=load_captures()
    (ROOT/REPORT).write_text(render(captures))
    print(f"Rendered {len(captures)} retained personal-channel captures; no lifecycle authorization.")
