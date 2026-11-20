# CPython argparse profile

The complete module is retained from actual pinned CPython 3.12.3.
Original authors include Steven J. Bethard and the Python contributors; Raymond
Hettinger is named as argparse maintainer. The complete accompanying
`LICENSE-3.12.txt` is supplied by that Python distribution.

Composition changes: implicit terminal-width lookup is replaced by an explicit
width requirement; gettext/ngettext are the explicitly admitted English profile;
SUPPRESS is linked to the native scalar with the same value for Action identity
interoperability. Other functions, classes and nested bodies are retained.
The execution composition rejects argument-file expansion before any selected
source access. Replay runs no selected source program and discovers no locale or
terminal defaults.

Original complete module SHA-256: `29395feb61bc376ca4ff9d44069af8d914ec2a1f25a4bd7978f6e2afef5bc07f`.
Original complete formatter class SHA-256: `ebf3bba744ae3c9bc849d5dc098881ae91da6580ab29aef492776fb830ae9a16`.
