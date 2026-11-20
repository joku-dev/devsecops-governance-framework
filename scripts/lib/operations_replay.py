"""Finite ordered retained calls. No program, URL, source file or clock access."""
import json

ERRORS={'OSError':OSError,'FileNotFoundError':FileNotFoundError,'FileExistsError':FileExistsError,
        'PermissionError':PermissionError,'NotADirectoryError':NotADirectoryError,'IsADirectoryError':IsADirectoryError,
        'ValueError':ValueError,'KeyError':KeyError,'TypeError':TypeError,'RuntimeError':RuntimeError,
        'UnicodeDecodeError':None,'RecursionError':RecursionError}


class ReplayCalls:
    def __init__(self,events,blob,*,expected_opened):
        if not events or events[0]!=expected_opened:raise ValueError('operations_replay_opening_changed')
        self.events=events;self.blob=blob;self.position=1
    def peek(self):
        if self.position>=len(self.events):raise ValueError('operations_replay_event_missing')
        return self.events[self.position]
    def take(self):
        if self.position>=len(self.events):raise ValueError('operations_replay_event_missing')
        row=self.events[self.position];self.position+=1
        if not isinstance(row,dict):raise ValueError('operations_replay_event_invalid')
        return row
    def call(self,action,arguments,*,encoding='json'):
        intent=self.take();number=self.position-1
        if intent!={'kind':'intent','operation':number,'action':action,'arguments':arguments}:
            raise ValueError('operations_replay_call_changed')
        outcome=self.take()
        if outcome.get('operation')!=number:raise ValueError('operations_replay_outcome_changed')
        if outcome.get('kind')=='failed':
            if set(outcome)!={'kind','operation','exception','message'} or not isinstance(outcome['message'],str):
                raise ValueError('operations_replay_failure_changed')
            error=ERRORS.get(outcome['exception'])
            if error is None:raise ValueError('operations_replay_failure_requires_incomplete_review')
            raise error(outcome['message'])
        if set(outcome)!={'kind','operation','encoding','value'} or outcome['kind']!='returned' or outcome['encoding']!=encoding:
            raise ValueError('operations_replay_return_changed')
        raw=self.blob(outcome['value'])
        return raw if encoding=='bytes' else json.loads(raw)
    def finish(self,result):
        if self.position!=len(self.events)-1 or self.take()!={'kind':'terminal','state':'complete','exit_code':result['exit_code']}:
            raise ValueError('operations_replay_terminal_changed')
