"""Compose complete synthetic ledger algorithms with explicit validation/effects."""
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.synthetic_lifecycle_reports import SyntheticPilot,SyntheticExceptions
from lib.synthetic_ledger_packets import SyntheticObservations,SyntheticActions,SyntheticExceptions as ExceptionPackets
from lib.synthetic_ledger_store import SyntheticLedgerStore
from lib.synthetic_ledger_programs import (SyntheticHistoryDemo,SyntheticActionDemo,
    SyntheticClosureDemo,SyntheticExceptionDemo,SyntheticObservationIntake,SyntheticActionIntake)

PROGRAMS={'synthetic':('run_governance_lifecycle_synthetic_demo.py',SyntheticHistoryDemo),
 'action':('run_governance_lifecycle_action_demo.py',SyntheticActionDemo),
 'closure':('run_governance_lifecycle_closure_demo.py',SyntheticClosureDemo),
 'exception':('run_governance_lifecycle_exception_demo.py',SyntheticExceptionDemo),
 'observation':('intake_governance_lifecycle_observation.py',SyntheticObservationIntake),
 'record':('intake_governance_lifecycle_action.py',SyntheticActionIntake)}


def compose(root,*,validator_class,path_factory,argument_parser,argv,native,locking,temporary):
 context=RepositoryLifecycle(root,validator_class=validator_class,path_factory=path_factory)
 context.store=SyntheticLedgerStore(context,path_factory=path_factory,native=native,locking=locking,temporary=temporary)
 context.synthetic=SyntheticObservations(root,context)
 context.synthetic_actions=SyntheticActions(root,context)
 context.synthetic_exceptions=ExceptionPackets(root,context)
 # Report generation remains the complete preceding reporting implementation.
 report_options={'path_factory':path_factory,'argument_parser':argument_parser,'argv':[]}
 context.report_pilot=SyntheticPilot(root,context,**report_options)
 context.report_exceptions=SyntheticExceptions(root,context,**report_options)
 programs={}
 for name,(filename,cls) in PROGRAMS.items():
  programs[name]=cls(root,context,path_factory=path_factory,
      argument_parser=lambda _filename=filename,**options:argument_parser(prog=_filename,**options),argv=argv)
 context.demo_synthetic=programs['synthetic']
 return context,programs
