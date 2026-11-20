"""Observe trusted native stdlib parser identity, English language and width."""
import argparse,hashlib,inspect,sys
from lib.retained_argparse import validate_context

# Exact full-module source identities from the pinned Python distributions.
# Unsupported/modified standard libraries require an explicit new profile.
MODULE_SOURCES={('cpython', 3, 11): ('cpython-3.11-argparse-v1', 'e878677e158d0bc0fb5119e0df74d94236f3653777bc9f2ea3fee49c167fe001'), ('cpython', 3, 12): ('cpython-3.12-argparse-v1', '29395feb61bc376ca4ff9d44069af8d914ec2a1f25a4bd7978f6e2afef5bc07f'), ('cpython', 3, 13): ('cpython-3.13-argparse-v1', '51d0cac86f746dccdb2488515ee0c2ad0969c599a0e2d6006cdbbce5cd00b3cb')}
TRANSLATION_INPUTS=[' (default: %(default)s)', '%(heading)s:', '%(prog)s: error: %(message)s\n', '%(prog)s: warning: %(message)s\n', '%r is not callable', "'required' is an invalid argument for positionals", '.__call__() not defined', 'ambiguous option: %(option)s could match %(matches)s', 'argument "-" with mode %r', 'argument %(argument_name)s: %(message)s', "argument '%(argument_name)s' is deprecated", "can't open '%(filename)s': %(error)s", 'cannot have multiple subparser arguments', 'cannot merge actions - two groups are named %r', "command '%(parser_name)s' is deprecated", 'conflicting subparser alias: %s', 'conflicting subparser: %s', 'dest= is required for options like %r', 'expected at least one argument', 'expected at most one argument', 'expected one argument', 'ignored explicit argument %r', 'invalid %(type)s value: %(value)r', 'invalid choice: %(value)r (choose from %(choices)s)', 'invalid conflict_resolution value: %r', 'invalid option string %(option)r: must start with a character %(prefix_chars)r', 'mutually exclusive arguments must be optional', 'not allowed with argument %s', 'one of the arguments %s is required', "option '%(option)s' is deprecated", 'options', 'positional arguments', "show program's version number and exit", 'show this help message and exit', 'subcommands', 'the following arguments are required: %s', 'unexpected option string: %s', 'unknown parser %(parser_name)r (choices: %(choices)s)', 'unrecognized arguments: %s', 'usage: ']
PLURAL_INPUTS=[['conflicting option string: %s', 'conflicting option strings: %s'], ['expected %s argument', 'expected %s arguments']]

def capture_context():
    version=list(sys.version_info[:3]);key=(sys.implementation.name,*version[:2])
    if key not in MODULE_SOURCES:raise ValueError('retained_argparse_native_profile_not_admitted')
    profile,sha=MODULE_SOURCES[key]
    if hashlib.sha256(inspect.getsource(argparse).encode()).hexdigest()!=sha:
        raise ValueError('retained_argparse_native_formatter_changed')
    native=argparse.HelpFormatter('axiom')
    if native._indent_increment!=2 or native._max_help_position!=min(24,max(native._width-20,4)):
        raise ValueError('retained_argparse_native_defaults_changed')
    if any(argparse._(text)!=text for text in TRANSLATION_INPUTS):
        raise ValueError('retained_argparse_translation_not_admitted')
    if any(argparse.ngettext(a,z,1)!=a or argparse.ngettext(a,z,2)!=z for a,z in PLURAL_INPUTS):
        raise ValueError('retained_argparse_translation_not_admitted')
    return validate_context({'schema_version':1,'implementation':'cpython','version':version,
        'profile':profile,'width':native._width,'translation_profile':'stdlib-en-v1'})
