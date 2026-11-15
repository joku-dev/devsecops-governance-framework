#!/usr/bin/env python3
"""Portable AXIOM pipeline-l1 candidate. Existing released CLIs stay unchanged."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import re
import subprocess

from jsonschema import ValidationError
import sys

from lib.provider_ports import checked_out_revision, collect_context, CI_PROVIDERS
from lib.portable.contracts import validate
from lib.portable.runtime import baseline, evaluate, gate, prepare_evidence, read_json, source_digest


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    temporary.replace(path)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest='command', required=True)
    context = commands.add_parser('context', help='Normalize a real checkout and native CI/SCM facts')
    for command in (context, commands.add_parser('run', help='Collect, evaluate and map the gate mode')):
        command.add_argument('--ci', required=True, choices=CI_PROVIDERS)
        command.add_argument('--profile', required=True)
        command.add_argument('--checkout', default='.')
        if command is context:
            command.add_argument('--output', required=True)
        else:
            command.add_argument('--output-directory', required=True)
            command.add_argument('--artifact', required=True)
            command.add_argument('--sbom', required=True)
            command.add_argument('--scan', required=True)
            command.add_argument('--governance-input')
            command.add_argument('--mode', default='report-only', choices=['report-only','block-on-error'])
            command.add_argument('--max-severity', default='high')
            command.add_argument('--opa', default=shutil.which('opa'))
            command.add_argument('--at')
    evaluation = commands.add_parser('evaluate', help='Evaluate explicitly normalized inputs without provider access')
    evaluation.add_argument('--context', required=True)
    evaluation.add_argument('--input', required=True, help='JSON with payload and hashed subjects from collection')
    evaluation.add_argument('--output', required=True)
    evaluation.add_argument('--opa', default=shutil.which('opa'))
    evaluation.add_argument('--mode', default='report-only', choices=['report-only','block-on-error'])
    evaluation.add_argument('--max-severity', default='high')
    evaluation.add_argument('--at')
    decision = commands.add_parser('gate', help='Map a canonical result to exit 0/1/2')
    decision.add_argument('--result', required=True)
    decision.add_argument('--mode', choices=['report-only','block-on-error'])
    decision.add_argument('--checkout', default='.', help='Actual application checkout to bind the tested commit')
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    diagnostic = (Path(args.output_directory)/'diagnostics.json' if args.command=='run'
                  else Path(args.output).with_suffix('.diagnostics.json') if hasattr(args,'output') else None)
    try:
        if args.command == 'gate':
            result = read_json(args.result)
            if result['context']['revision']['tested'] != checked_out_revision(args.checkout):
                raise ValueError('result_checkout_mismatch')
            if result['runtime']['source_digest'] != source_digest() or result['baseline'] != baseline(baseline_id=result['context']['governance']['baseline_id'])[1]:
                raise ValueError('result_runtime_or_baseline_mismatch')
            return gate(result, args.mode)
        if args.command in ('context','run'):
            profile = read_json(args.profile)
            context = collect_context(args.ci, profile, os.environ, args.checkout)
            if args.command == 'context':
                write(args.output, context)
                return 0
            output = Path(args.output_directory)
            if output.exists() and any(output.iterdir()):
                raise ValueError('output_directory_already_used')
            write(output/'context.json', context)
            payload, subjects = prepare_evidence(context,args.checkout,args.artifact,args.sbom,args.scan,
                                                 read_json(args.governance_input) if args.governance_input else None)
            write(output/'evaluation-input.json', {'payload':payload,'subjects':subjects})
            target = output/'result.json'
        else:
            context = read_json(args.context)
            evidence = read_json(args.input)
            payload, subjects = evidence['payload'], evidence['subjects']
            target = Path(args.output)
        if not args.opa:
            raise ValueError('opa_not_available')
        result = evaluate(context,payload,subjects,opa=Path(args.opa).resolve(),mode=args.mode,
                          max_severity=args.max_severity,at=args.at)
        if args.command == 'run' and checked_out_revision(args.checkout) != context['revision']['tested']:
            raise ValueError('checkout_changed_during_evaluation')
        code = gate(result) if args.command == 'run' else (0 if result['execution']=='complete' else 2)
        write(target, result)
        if diagnostic:
            write(diagnostic, {'schema_version':'1.0.0','execution':result['execution'],'exit_code':code,'diagnostics':result['diagnostics']})
        return code
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError, AttributeError, RecursionError, ValidationError, subprocess.SubprocessError) as error:
        # Never expose provider bodies, credentials, arbitrary paths or untrusted exception text.
        if diagnostic and not diagnostic.exists():
            code = str(error) if isinstance(error,ValueError) and re.fullmatch('[a-z][a-z0-9_:.-]{0,100}',str(error)) else type(error).__name__
            try:
                write(diagnostic, {'schema_version':'1.0.0','execution':'error','diagnostics':[code]})
            except OSError:
                pass
        print('Governance runtime failed; inspect the redacted diagnostics artifact.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
