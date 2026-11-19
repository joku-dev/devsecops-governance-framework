"""Instance-bound complete compliance creation, inspection and explicit legacy view."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import secrets
import sys

from lib import compliance_operation as contract
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT
from lib.portable.runtime import source_digest
from lib.provider_ports import (execute_complete_compliance_operation,
    load_complete_compliance_operation, complete_compliance_request)
from lib.result_assessments import identity
from lib.result_snapshot_store import explicit_time


class ComplianceContext:
    def __init__(self, instance_root, settings):
        self.instance=private_directory(Path(instance_root)).resolve()
        self.settings=deepcopy(settings)
        self.binding={'node_id':settings['node_id'],'runtime_source_digest':source_digest(),
            'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),
            'source_tree':git_read(ROOT,'rev-parse','HEAD^{tree}').decode().strip(),
            'product_source_root':str(ROOT),'instance_root':str(self.instance)}
        if (settings['development'] or any(settings[k]!=self.binding[k]
                for k in ('node_id','runtime_source_digest','source_revision'))
                or settings['source_root']!=str(ROOT)):
            raise ValueError('complete_compliance_current_installed_instance_required')
        self.root=private_directory(private_directory(self.instance/'state')/'compliance')
        self.operations=private_directory(self.root/'operations')

    def assert_current(self):
        if (source_digest()!=self.binding['runtime_source_digest']
                or git_read(ROOT,'rev-parse','HEAD').decode().strip()!=self.binding['source_revision']
                or git_read(ROOT,'rev-parse','HEAD^{tree}').decode().strip()!=self.binding['source_tree']):
            raise ValueError('complete_compliance_runtime_changed')

    def create(self, *, package, package_pin, at, output_file, cwd,
               target_repo=None, input_file=None, skip_unit_tests=False, fail_on_findings=False):
        self.assert_current();explicit_time(at)
        operation=secrets.token_hex(32)
        header=contract.binding({'schema_version':1,'kind':'product-complete-compliance',
            'operation_id':operation,**self.binding,'package_sha256':package_pin,
            'assessed_at':at,'engine_profile':contract.PROFILE,**contract.AUTHORITY})
        selected=contract.options({'cwd':str(cwd),'output_file':str(output_file),
            'target_repo':None if target_repo is None else str(target_repo),
            'input_file':None if input_file is None else str(input_file),
            'skip_unit_tests':skip_unit_tests,'fail_on_findings':fail_on_findings})
        reserve(self.root,8*1024**3)
        root=self.operations/operation;root.mkdir(mode=0o700)
        execute_complete_compliance_operation(root,header,selected,package)
        self.assert_current()
        return operation,load_complete_compliance_operation(root,header,self.settings)

    def inspect(self, operation):
        self.assert_current();operation=identity(operation)
        root=self.operations/operation
        packet=complete_compliance_request(root)
        header=contract.binding(packet['binding'])
        if header['operation_id']!=operation or any(header[k]!=v for k,v in self.binding.items()):
            raise ValueError('complete_compliance_node_runtime_or_source_changed')
        value=load_complete_compliance_operation(root,header,self.settings)
        self.assert_current();return value

    def status(self):
        values=[]
        for path in sorted(self.operations.iterdir()):
            try:
                result=self.inspect(path.name)
                values.append({'operation_id':path.name,'state':result['state'],
                    'execution':result['execution'],'modern_exit':result['modern_exit']})
            except (ValueError,OSError,KeyError,TypeError):
                values.append({'operation_id':path.name,'state':'pending_incomplete_or_invalid'})
        return values


def parser():
    result=argparse.ArgumentParser(prog='axiom-v2 validation',allow_abbrev=False)
    sub=result.add_subparsers(dest='operation',required=True)
    create=sub.add_parser('compliance',allow_abbrev=False)
    create.add_argument('--profile',required=True,choices=(contract.PROFILE,))
    create.add_argument('--package',required=True,type=Path)
    create.add_argument('--sha256',required=True)
    create.add_argument('--at',required=True)
    create.add_argument('--output-file',required=True,type=Path)
    create.add_argument('--target-repo',type=Path)
    create.add_argument('--input-file',type=Path)
    create.add_argument('--skip-unit-tests',action='store_true',
        help='Explicit original nested-test scope; records actual not_run, never a default skip.')
    create.add_argument('--fail-on-findings',action='store_true')
    create.add_argument('--output',choices=('json','legacy'),default='json',
        help='Legacy explicitly retains original wire/finding exit, including known original limitations.')
    inspect=sub.add_parser('compliance-inspect',allow_abbrev=False)
    inspect.add_argument('--assessment',required=True)
    sub.add_parser('compliance-status',allow_abbrev=False)
    return result


def run(arguments, instance_root, settings):
    args=parser().parse_args(arguments)
    context=ComplianceContext(instance_root,settings)
    if args.operation=='compliance-status':
        print(json.dumps({'operations':context.status(),**contract.AUTHORITY},indent=2));return 0
    if args.operation=='compliance-inspect':
        print(json.dumps(context.inspect(args.assessment),indent=2));return 0
    operation,value=context.create(package=args.package,package_pin=args.sha256,at=args.at,
        output_file=args.output_file,cwd=Path.cwd(),target_repo=args.target_repo,input_file=args.input_file,
        skip_unit_tests=args.skip_unit_tests,fail_on_findings=args.fail_on_findings)
    if args.output=='legacy':
        sys.stdout.write(value.get('legacy_stdout',''))
        if value.get('original_finding_exit') in (0,1):
            return value['original_finding_exit']
        return 2
    print(json.dumps({'assessment_id':operation,**value},indent=2))
    return value['modern_exit']
