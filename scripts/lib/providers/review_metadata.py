"""Finite compatibility adapter for the original PR event envelope; no native calls."""
import re

REVIEW_EVENT_PROFILES=('legacy-pr-review-event-v1',)


def committed_review_event(profile,value):
    if profile not in REVIEW_EVENT_PROFILES:raise ValueError('unsupported_review_event_profile')
    if not isinstance(value,dict):raise ValueError('invalid_review_event_envelope')
    pr=value.get('pull_request',{})
    try:base=pr.get('base',{}).get('sha','');head=pr.get('head',{}).get('sha','');description=pr.get('body') or ''
    except AttributeError:raise ValueError('invalid_review_event_envelope') from None
    if any(not isinstance(v,str) or not re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})',v) for v in (base,head)):
        raise ValueError('full_review_event_commit_required')
    return {'base_commit':base,'head_commit':head,'description':description}


def review_event(profile,value):
    event=committed_review_event(profile,value);description=event['description']
    if not isinstance(description,str) or len(description.encode())>1048576:raise ValueError('review_description_byte_budget')
    return event
