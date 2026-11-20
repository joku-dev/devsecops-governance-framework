# CPython argparse profile

The complete module is retained from actual pinned CPython 3.13.18.
Original authors include Steven J. Bethard and the Python contributors; Raymond
Hettinger is named as argparse maintainer. The complete accompanying
`LICENSE-3.13.txt` is supplied by that Python distribution.

Composition changes: implicit terminal-width lookup is replaced by an explicit
width requirement; gettext/ngettext are the explicitly admitted English profile;
SUPPRESS is linked to the native scalar with the same value for Action identity
interoperability. Other functions, classes and nested bodies are retained.
The execution composition rejects argument-file expansion before any selected
source access. Replay runs no selected source program and discovers no locale or
terminal defaults.

Original complete module SHA-256: `51d0cac86f746dccdb2488515ee0c2ad0969c599a0e2d6006cdbbce5cd00b3cb`.
Original complete formatter class SHA-256: `650974d76b2cc4276b7f714d3656f1fdc85514d4ece71d8974736031df45fd2f`.
