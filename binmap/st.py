"""Single-letter aliases for the types in :mod:`binmap.types`, named after their
:py:mod:`struct` format characters."""

from typing import TypeAlias

from binmap import types

_b: TypeAlias = types.boolean
c: TypeAlias = types.char
d: TypeAlias = types.double
f: TypeAlias = types.floating
e: TypeAlias = types.halffloat
i: TypeAlias = types.integer
l: TypeAlias = types.long  # noqa: E741
q: TypeAlias = types.longlong
x: TypeAlias = types.pad
p: TypeAlias = types.pascalstring
h: TypeAlias = types.short
b: TypeAlias = types.signedchar
s: TypeAlias = types.string
B: TypeAlias = types.unsignedchar
I: TypeAlias = types.unsignedinteger  # noqa: E741
L: TypeAlias = types.unsignedlong
Q: TypeAlias = types.unsignedlonglong
H: TypeAlias = types.unsignedshort
