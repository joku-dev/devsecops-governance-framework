"""Original dispatcher declarations and recording transitions; no provider execution."""
from collections import Counter
from copy import deepcopy
from datetime import timezone
import json
from lib.result_bytes import strict_json
from lib.result_snapshot_store import explicit_time

MAX_STATE = 64 * 1024
MAX_LOG = 16 * 1024**2
MAX_EVENTS = 10000
DEFAULT_LOG = 'generated/agent-usage/agent-usage.jsonl'


def utc_time(at):
    if not isinstance(at, str) or len(at) > 128: raise ValueError('invalid_dispatch_time')
    try: return explicit_time(at).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    except (ValueError, OverflowError): raise ValueError('invalid_dispatch_time') from None


def state(raw):
    if raw is None: return {'active': False, 'mode': 'window', 'remaining': 0}
    if not isinstance(raw, bytes) or len(raw) > MAX_STATE: raise ValueError('dispatch_recording_state_budget')
    value = strict_json(raw)
    if not isinstance(value, dict): raise ValueError('dispatch_recording_state_object_required')
    value.setdefault('active', False); value.setdefault('mode', 'window'); value.setdefault('remaining', 0)
    if type(value['active']) is not bool or value['mode'] not in ('window', 'continuous'): raise ValueError('invalid_dispatch_recording_state')
    remaining = value['remaining']
    if not (remaining is None and value['mode'] == 'continuous') and (type(remaining) is not int or remaining < 0): raise ValueError('invalid_dispatch_recording_remaining')
    if 'initial_count' in value and (type(value['initial_count']) is not int or value['initial_count'] <= 0): raise ValueError('invalid_dispatch_recording_initial_count')
    for name in ('started_at', 'last_recorded_at', 'completed_at'):
        if name in value:
            if not isinstance(value[name], str): raise ValueError('invalid_dispatch_recording_time')
            utc_time(value[name])
    if 'usage_log' in value: text(value['usage_log'])
    return value


def text(value):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value) or len(value.encode()) > 4096: raise ValueError('invalid_dispatch_usage_field')
    return value


def activate(before, mode, at, *, count=None, usage_log=DEFAULT_LOG):
    timestamp = utc_time(at); text(usage_log)
    if mode == 'window':
        if type(count) is not int or count <= 0: raise ValueError('invalid_dispatch_recording_count')
        return {'active': True, 'initial_count': count, 'mode': 'window', 'remaining': count, 'started_at': timestamp, 'usage_log': usage_log}
    if mode != 'continuous' or count is not None: raise ValueError('invalid_dispatch_recording_mode')
    before = state(json.dumps(before, allow_nan=False).encode())
    value = deepcopy(before); value.update(active=True, mode='continuous', remaining=None, started_at=before.get('started_at') or timestamp, usage_log=usage_log)
    value.pop('completed_at', None); return value


def active(value):
    value = state(json.dumps(value, allow_nan=False).encode())
    return value['active'] and (value['mode'] == 'continuous' or value['remaining'] > 0)


def consume(before, event):
    value = state(json.dumps(before, allow_nan=False).encode())
    if not value['active']: return value, False, value['remaining']
    if value['mode'] != 'continuous' and value['remaining'] <= 0: return value, False, value['remaining']
    if not isinstance(event, dict) or 'timestamp' not in event: raise ValueError('invalid_dispatch_usage_event')
    utc_time(event['timestamp']); value['last_recorded_at'] = event['timestamp']
    if value['mode'] == 'continuous': return value, True, None
    value['remaining'] -= 1
    if value['remaining'] == 0: value.update(active=False, completed_at=event['timestamp'])
    return value, True, value['remaining']


def recording_text(value):
    value = state(json.dumps(value, allow_nan=False).encode()); continuous = value['mode'] == 'continuous'
    lines = ['Governance Agent Usage Recording', '', 'Status: ' + ('active' if active(value) else 'inactive'),
        'Mode: ' + value['mode'], 'Usage log: ' + value.get('usage_log', DEFAULT_LOG),
        'Remaining runs: ' + ('continuous' if continuous else str(value['remaining']))]
    for key, label in [('started_at', 'Started at'), ('last_recorded_at', 'Last recorded at'), ('completed_at', 'Completed at')]:
        if value.get(key): lines.append(label + ': ' + value[key])
    return '\n'.join(lines) + '\n'


def usage_event(dispatch, roles, at, *, run_type='dispatch', provider='none', platform='local', source='manual'):
    if run_type not in ('dispatch', 'provider_review'): raise ValueError('invalid_dispatch_run_type')
    for value in (provider, platform, source): text(value)
    return {'timestamp': utc_time(at), 'run_type': run_type, 'provider': provider, 'platform': platform, 'source': source,
        'changed_paths': dispatch['changed_files'], 'selected_agents': dispatch['selected_agents'],
        'skills': [roles[role]['skill'] for role in dispatch['selected_agents'] if role in roles],
        **{name: dispatch[name] for name in ('release_impact', 'required_validations', 'warnings')}}


def events(raw):
    if raw is None: return []
    if not isinstance(raw, bytes) or len(raw) > MAX_LOG: raise ValueError('dispatch_usage_log_budget')
    try: lines = raw.decode('utf-8').splitlines()
    except UnicodeError: raise ValueError('invalid_dispatch_usage_encoding') from None
    rows = []
    for line in lines:
        if not line.strip(): continue
        value = strict_json(line.encode())
        if not isinstance(value, dict): raise ValueError('dispatch_usage_event_object_required')
        for key in ('selected_agents', 'skills'):
            if key in value and (not isinstance(value[key], list) or any(not isinstance(s, str) for s in value[key])): raise ValueError('invalid_dispatch_usage_list')
        for key in ('provider', 'platform', 'run_type'):
            if key in value and not isinstance(value[key], str): raise ValueError('invalid_dispatch_usage_category')
        rows.append(value)
        if len(rows) > MAX_EVENTS: raise ValueError('dispatch_usage_event_budget')
    return rows


def append(raw, event):
    rows = events(raw)
    if len(rows) >= MAX_EVENTS: raise ValueError('dispatch_usage_event_budget')
    before = raw or b''; separator = b'\n' if before and not before.endswith(b'\n') else b''
    after = before + separator + (json.dumps(event, sort_keys=True, allow_nan=False) + '\n').encode()
    events(after); return after


def summary(raw):
    rows = events(raw); agents = Counter(); skills = Counter(); providers = Counter(); platforms = Counter(); kinds = Counter()
    for row in rows:
        agents.update(row.get('selected_agents', [])); skills.update(row.get('skills', [])); providers.update([row.get('provider', 'unknown')]); platforms.update([row.get('platform', 'unknown')]); kinds.update([row.get('run_type', 'unknown')])
    return {'event_count': len(rows), **{name: dict(sorted(counter.items())) for name, counter in [('agent_counts', agents), ('skill_counts', skills), ('provider_counts', providers), ('platform_counts', platforms), ('run_type_counts', kinds)]}}


def summary_text(value):
    lines = ['Governance Agent Usage Summary', '', 'Events: ' + str(value['event_count']), '']
    for index, (label, key) in enumerate([('Agent usage', 'agent_counts'), ('Skill usage', 'skill_counts'), ('Provider usage', 'provider_counts'), ('Platform usage', 'platform_counts'), ('Run type usage', 'run_type_counts')]):
        if index: lines.append('')
        lines.append(label + ':'); counts = value[key]
        lines.extend([f'- {name}: {count}' for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))] if counts else ['- none'])
    return '\n'.join(lines) + '\n'


ACTIONS = ('dispatch', 'record-window', 'record-continuous', 'recording-status', 'usage-summary')
REQUEST_FIELDS = {'action', 'at', 'count', 'usage_log', 'json', 'log_usage',
                  'run_type', 'provider', 'platform', 'source', 'provider_review'}


def request(action, at, *, count=None, usage_log=DEFAULT_LOG, json_output=False,
            log_usage=False, run_type='dispatch', provider='none', platform='local',
            source='manual', provider_review=None):
    """A finite declaration, never a provider invocation or arbitrary command."""
    value = {'action': action, 'at': at, 'count': count, 'usage_log': usage_log,
        'json': json_output, 'log_usage': log_usage, 'run_type': run_type,
        'provider': provider, 'platform': platform, 'source': source, 'provider_review': provider_review}
    checked_request(value)
    return value


def checked_request(value):
    if not isinstance(value, dict) or set(value) != REQUEST_FIELDS:
        raise ValueError('invalid_dispatch_request')
    if value['action'] not in ACTIONS or value['run_type'] not in ('dispatch', 'provider_review'):
        raise ValueError('invalid_dispatch_operation')
    if any(type(value[key]) is not bool for key in ('json', 'log_usage')):
        raise ValueError('invalid_dispatch_request_flag')
    utc_time(value['at'])
    for key in ('usage_log', 'provider', 'platform', 'source'): text(value[key])
    if value['provider_review'] is not None:
        text(value['provider_review'])
        if value['provider_review'] == 'none': raise ValueError('dispatch_provider_review_requires_provider')
    if value['action'] == 'record-window':
        if type(value['count']) is not int or value['count'] <= 0:
            raise ValueError('invalid_dispatch_recording_count')
    elif value['count'] is not None: raise ValueError('dispatch_count_requires_window')


def wire(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def transition(value, before_state, before_log, *, dispatch=None, roles=None):
    """Derive original output and effects from the inputs that this action uses.

    The caller supplies bytes of the selected log, resolving its logical label
    in a bounded private workspace. This function performs no filesystem writes.
    """
    checked_request(value); action = value['action']
    after_state = before_state; after_log = before_log; event = None; selected_log = None
    if action == 'usage-summary':
        result = summary(before_log); stdout = wire(result) if value['json'] else summary_text(result).encode()
    elif action in ('record-window', 'record-continuous', 'recording-status'):
        # V1's finite-window activation replaces a corrupt previous state without
        # reading it. Status and activation do not inspect an unrelated log.
        previous = None if action == 'record-window' else state(before_state)
        if action == 'record-window':
            result = activate({}, 'window', value['at'], count=value['count'], usage_log=value['usage_log'])
        elif action == 'record-continuous':
            result = activate(previous, 'continuous', value['at'], usage_log=value['usage_log'])
        else: result = previous
        if action != 'recording-status': after_state = wire(result)
        stdout = wire(result) if value['json'] else recording_text(result).encode()
    else:
        if not isinstance(dispatch, dict) or not isinstance(roles, dict):
            raise ValueError('dispatch_selection_and_contracts_required')
        previous = state(before_state); recording = active(previous)
        provider_review = value['provider_review']
        if value['log_usage'] or provider_review is not None or recording:
            selected_log = previous.get('usage_log', DEFAULT_LOG) if recording else value['usage_log']
            event = usage_event(dispatch, roles, value['at'],
                run_type='provider_review' if provider_review is not None else value['run_type'],
                provider=provider_review if provider_review is not None else value['provider'],
                platform=value['platform'], source=value['source'])
            after_log = append(before_log, event)
            if recording:
                updated, appended, _ = consume(previous, event)
                if not appended: raise ValueError('dispatch_recording_transition_conflict')
                after_state = wire(updated)
        from lib.review_planning import render_text
        result = dispatch; stdout = wire(result) if value['json'] else render_text(result).encode()
    return {'state_bytes': after_state, 'log_bytes': after_log, 'stdout': stdout,
            'event': event, 'selected_usage_log': selected_log,
            'state_changed': after_state != before_state, 'log_changed': after_log != before_log,
            'provider_invoked': False}
