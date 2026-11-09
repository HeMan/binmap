"""
Type aliases for binmap fields.

Each alias is ``Annotated[<Python type>, StructCode(<struct format character>)]``.
Type checkers and editors see the plain Python type (``int``, ``float``, ``bool``
or ``bytes``), so ``temp: unsignedchar = 0`` and ``t.temp = 22`` type-check, while
binmap reads the ``StructCode`` to know how the field is packed.
"""

from dataclasses import dataclass
from typing import Annotated, TypeAlias


@dataclass(frozen=True)
class StructCode:
    """
    Marks a type alias with the :py:mod:`struct` format character it packs as.

    Use it to define your own aliases, e.g.
    ``rgb565 = Annotated[int, StructCode("H")]``.

    :param str code: struct format character, such as ``"B"`` or ``"h"``
    """

    code: str


char: TypeAlias = Annotated[bytes, StructCode("c")]
signedchar: TypeAlias = Annotated[int, StructCode("b")]
unsignedchar: TypeAlias = Annotated[int, StructCode("B")]
boolean: TypeAlias = Annotated[bool, StructCode("?")]
short: TypeAlias = Annotated[int, StructCode("h")]
unsignedshort: TypeAlias = Annotated[int, StructCode("H")]
integer: TypeAlias = Annotated[int, StructCode("i")]
unsignedinteger: TypeAlias = Annotated[int, StructCode("I")]
long: TypeAlias = Annotated[int, StructCode("l")]
unsignedlong: TypeAlias = Annotated[int, StructCode("L")]
longlong: TypeAlias = Annotated[int, StructCode("q")]
unsignedlonglong: TypeAlias = Annotated[int, StructCode("Q")]
halffloat: TypeAlias = Annotated[float, StructCode("e")]
floating: TypeAlias = Annotated[float, StructCode("f")]
double: TypeAlias = Annotated[float, StructCode("d")]
string: TypeAlias = Annotated[bytes, StructCode("s")]
pascalstring: TypeAlias = Annotated[bytes, StructCode("p")]
pad: TypeAlias = Annotated[int, StructCode("x")]
