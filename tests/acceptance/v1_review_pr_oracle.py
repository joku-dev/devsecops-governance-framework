"""Fingerprint-bound original committed-scope/contract functions on actual native Git."""
import ast
import sys
import tempfile
from pathlib import Path


def load(native, metadata, metadata_oracle):
    _,scope=metadata_oracle.load(metadata)
    routing=sys.modules[native.package+'.agent_routing']
    scope.update(tempfile=tempfile,git_output=native.review.git_output,
        load_role_contracts=routing.load_role_contracts,load_routing_contract=routing.load_routing_contract,
        routing_reasons_for_contract=routing.routing_reasons_for_contract)
    source=Path(metadata)/'agent_review_status.py.txt';tree=ast.parse(source.read_bytes());nodes=[]
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name in ('committed_scope','expected_reviews'):nodes.append(node)
        elif isinstance(node,ast.Assign) and any(isinstance(n,ast.Name) and n.id=='SHA' for n in node.targets):nodes.append(node)
    assert len(nodes)==3
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),scope)
    # Only native functions are exposed here; never install operator-subject stubs.
    scope.pop('status_with_declared_inputs',None)
    return scope
