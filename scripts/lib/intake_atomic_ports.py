"""Explicit atomic-output native/replay composition; no authority is inherited."""
from lib.intake_atomic_json import IntakeAtomicJSON
from lib.intake_atomic_effects import AtomicScope,ReplayAtomicEffects
from lib.providers.intake_atomic_effects import NativeAtomicEffects
from lib.providers.consumer_lifecycle_storage import Record,read_record,encode,AUTHORITY
from lib.portable.contracts import ROOT


def native(root,targets,*,cwd,record,forbidden_roots=()):
    scope=AtomicScope(root,targets,cwd=cwd)
    return NativeAtomicEffects(scope,record,forbidden_roots=(ROOT,*forbidden_roots))


def program(effects):
    return IntakeAtomicJSON(path_factory=effects.path,native=effects,temporary=effects)
