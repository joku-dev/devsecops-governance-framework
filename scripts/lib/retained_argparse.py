from lib.argparse_profiles.cpython311 import HelpFormatter as Formatter311, ArgumentParser as Parser311
from lib.argparse_profiles.cpython312 import HelpFormatter as Formatter312, ArgumentParser as Parser312
from lib.argparse_profiles.cpython313 import HelpFormatter as Formatter313, ArgumentParser as Parser313
"""Explicit complete producer parser profiles, without native discovery."""

PROFILES={
    'cpython-3.11-argparse-v1':(11,Formatter311),
    'cpython-3.12-argparse-v1':(12,Formatter312),
    'cpython-3.13-argparse-v1':(13,Formatter313),
}

def validate_context(value):
    if (type(value) is not dict or set(value)!={'schema_version','implementation','version','profile','width','translation_profile'}
            or type(value['schema_version']) is not int or value['schema_version']!=1
            or type(value['implementation']) is not str or value['implementation']!='cpython' or type(value['profile']) is not str or value['profile'] not in PROFILES
            or type(value['version']) is not list or len(value['version'])!=3
            or any(type(n) is not int or not 0<=n<=1000000 for n in value['version'])
            or value['version'][:2]!=[3,PROFILES[value['profile']][0]]
            or type(value['width']) is not int or not -1<=value['width']<=4094
            or type(value['translation_profile']) is not str or value['translation_profile']!='stdlib-en-v1'):
        raise ValueError('retained_argparse_context_changed')
    return value

def formatter_factory(context):
    validate_context(context)
    width=context['width'];formatter=PROFILES[context['profile']][1]
    return lambda prog:formatter(prog,width=width,indent_increment=2,max_help_position=24)

PARSERS={'cpython-3.11-argparse-v1':Parser311,'cpython-3.12-argparse-v1':Parser312,'cpython-3.13-argparse-v1':Parser313}

def parser_base(context):
    validate_context(context)
    return PARSERS[context['profile']]

# Complete code/license closure required by each capture composition.
COMPONENTS=('retained_argparse.py','providers/retained_argparse.py','argparse_profiles/__init__.py',
    'argparse_profiles/cpython311.py','argparse_profiles/cpython312.py','argparse_profiles/cpython313.py',
    'argparse_profiles/LICENSE-3.11.txt','argparse_profiles/LICENSE-3.12.txt','argparse_profiles/LICENSE-3.13.txt',
    'argparse_profiles/NOTICE-3.11.md','argparse_profiles/NOTICE-3.12.md','argparse_profiles/NOTICE-3.13.md')
