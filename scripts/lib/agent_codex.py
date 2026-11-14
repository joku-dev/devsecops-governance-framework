"""Thin Codex CLI projection of neutral role/execution contracts."""
import json
from pathlib import Path
import tomllib

from .agent_review import fingerprint


def load_adapter(root: Path, role: str) -> dict:
    name=f'.codex/agents/{role}.toml'
    fingerprint(root,name)
    adapter=tomllib.loads((root/name).read_text())
    if not all(isinstance(adapter.get(k),str) and adapter[k].strip()
               for k in ('model','model_reasoning_effort','developer_instructions')):
        raise ValueError('Provider adapter requires explicit model, reasoning effort and instructions')
    return adapter


def codex_command(root,adapter,directory):
    # Values stay separate argv elements; no shell interpolation or arbitrary switches.
    return ['codex','--no-daemon','-a','never','exec','--ignore-user-config','--ephemeral',
            '--sandbox','read-only','--model',adapter['model'],
            '-c','model_reasoning_effort='+json.dumps(adapter['model_reasoning_effort']),
            '--output-schema',str(directory/'response.schema.json'),
            '--output-last-message',str(directory/'response.json'),'--json','--cd',str(root),'-']


def observations(path):
    model,usage=None,None
    if not path.exists():
        return model,usage
    if path.stat().st_size > 10*1024*1024:
        raise ValueError('Provider event stream exceeds 10 MiB')
    for line in path.read_text().splitlines():
        try:
            event=json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get('type') in ('thread.started','turn.started') and isinstance(event.get('model'),str):
            model=event['model']
        if event.get('type')=='turn.completed' and isinstance(event.get('usage'),dict):
            values=event['usage']
            if all(type(values.get(k)) is int and values[k]>=0
                   for k in ('input_tokens','cached_input_tokens','output_tokens')):
                usage=usage or {k:0 for k in ('input_tokens','cached_input_tokens','output_tokens')}
                for key in usage:
                    usage[key]+=values[key]
    return model,usage
