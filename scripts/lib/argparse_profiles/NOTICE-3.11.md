# CPython argparse profile

The complete module is retained from actual pinned CPython 3.11.18.
Original authors include Steven J. Bethard and the Python contributors; Raymond
Hettinger is named as argparse maintainer. The complete accompanying
`LICENSE-3.11.txt` is supplied by that Python distribution.

Composition changes: implicit terminal-width lookup is replaced by an explicit
width requirement; gettext/ngettext are the explicitly admitted English profile;
SUPPRESS is linked to the native scalar with the same value for Action identity
interoperability. Other functions, classes and nested bodies are retained.
The execution composition rejects argument-file expansion before any selected
source access. Replay runs no selected source program and discovers no locale or
terminal defaults.

Original complete module SHA-256: `e878677e158d0bc0fb5119e0df74d94236f3653777bc9f2ea3fee49c167fe001`.
Original complete formatter class SHA-256: `e837fb886b9ed6548a03f3158c3f70db039b64e42d329d320dd9c0679a80d2a6`.
