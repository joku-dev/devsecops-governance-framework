"""Bounded inert original release input graph, shared by capture and replay."""
import json
from pathlib import Path
import yaml
from lib.validation_files import MAX_FILES,relative

POLICY='model/governance/release-signing-policy.yaml'


def collect(reader):
    requested=set()
    def read(name):
        relative(name)
        if any(part.casefold()=='.git' for part in Path(name).parts):raise ValueError('release_git_metadata_artifact_forbidden')
        requested.add(name)
        if len(requested)>MAX_FILES:raise ValueError('release_input_count_budget')
        return reader(name)
    raw=read(POLICY);policy=None
    if raw is not None:
        depth=count=aliases=0
        try:
            for event in yaml.parse(raw):
                count+=1
                if isinstance(event,yaml.events.CollectionStartEvent):depth+=1
                if isinstance(event,yaml.events.CollectionEndEvent):depth-=1
                if isinstance(event,yaml.events.AliasEvent):aliases+=1
                if count>100000 or depth>100 or aliases>1000:raise ValueError('release_policy_yaml_budget')
            policy=yaml.safe_load(raw)
        except (yaml.YAMLError,UnicodeError,RecursionError):pass
    if not isinstance(policy,dict) or not isinstance(policy.get('legacy_attestation'),dict):return requested
    config=policy['legacy_attestation'];manifest=None
    if isinstance(config.get('signature'),str):read(config['signature'])
    if isinstance(config.get('manifest'),str):
        payload=read(config['manifest'])
        if payload is not None:
            try:manifest=json.loads(payload.decode('utf-8'))
            except (ValueError,UnicodeError,RecursionError):pass
    if not isinstance(manifest,dict) or not isinstance(manifest.get('legacy_tags'),list):return requested
    if len(manifest['legacy_tags'])>MAX_FILES:raise ValueError('release_manifest_record_budget')
    for record in manifest['legacy_tags']:
        if not isinstance(record,dict) or not isinstance(record.get('artifacts'),list):continue
        if len(record['artifacts'])>MAX_FILES:raise ValueError('release_manifest_artifact_budget')
        for artifact in record['artifacts']:
            if not isinstance(artifact,dict) or not isinstance(artifact.get('path'),str):continue
            payload=read(artifact['path'])
            if payload is None or artifact.get('role')!='package_checksums':continue
            try:lines=payload.decode('utf-8').splitlines()
            except UnicodeError:continue
            if len(lines)>MAX_FILES:raise ValueError('release_checksum_entry_budget')
            for line in lines:
                parts=line.split(maxsplit=1)
                if len(parts)==2 and len(parts[0])==64:read(parts[1].lstrip('* '))
    return requested
