# mypy: warn-unused-ignores
# pyright: reportUnnecessaryTypeIgnoreComment=true
"""Everyday binmap code, as users write it in their editors.

CI runs mypy and pyright (the engine behind VS Code's Pylance) on this file, and
it must have no errors. assert_type() pins what an editor shows on hover. The
lines in _not_allowed() must each be an error: their "type: ignore" comments
fail the check if the error goes away. tests/test_typecheck.py also runs this
file, so it has to work at runtime too.
"""

from enum import IntEnum
from typing import assert_type

from binmap import (
    BinmapDataclass,
    autolength,
    b_types,
    calculatedfield,
    constant,
    enumfield,
    padding,
    stringfield,
)
from binmap.types import (
    pad,
    pascalstring,
    signedchar,
    string,
    unsignedchar,
    unsignedshort,
)


class TempHum(BinmapDataclass):
    temp: signedchar = 0
    hum: unsignedchar = 0


class Wind(IntEnum):
    North = 0
    East = 1


class Packet(BinmapDataclass, byteorder="<"):
    length: unsignedchar = autolength()
    kind: unsignedshort = constant(0x1313)
    temp: signedchar = 0
    _pad: pad = padding(2)
    wind: unsignedchar = enumfield(Wind, default=Wind.East)
    name: string = stringfield(8)
    nick: pascalstring = stringfield(8)

    def chk(self) -> unsignedchar:
        return (self.temp + self.wind) & 0xFF

    checksum: unsignedchar = calculatedfield(chk)


class Child(TempHum):
    lux: b_types.unsignedshort = 0


th = TempHum(temp=-10, hum=60)
th.temp = 22
th.frombytes(b"\x16<")
assert_type(bytes(th), bytes)

parsed = TempHum(b"\xf6<")
assert_type(parsed.temp, int)
assert_type(parsed.hum, int)

packet = Packet(temp=5, wind=Wind.North, name=b"binmap")
assert_type(packet.name, bytes)
assert_type(packet.name.decode("ascii"), str)
assert_type(packet.nick, bytes)
assert_type(packet.kind, int)
assert_type(packet.length, int)
assert_type(packet.checksum, int)

child = Child(temp=1, hum=2, lux=400)
assert_type(child.lux, int)


def _not_allowed() -> None:
    """Never called: each line must be reported by the type checkers."""
    Packet(kind=1)  # type: ignore[call-arg]  # constants aren't arguments
    Packet(length=3)  # type: ignore[call-arg]  # nor is an autolength
    TempHum(tmp=1)  # type: ignore[call-arg]  # no such field
    TempHum(temp="hot")  # type: ignore[arg-type]
    packet.name = "text"  # type: ignore[assignment]  # strings are bytes

    class WrongFactory(BinmapDataclass):
        # a string field's factory on a number field
        temp: unsignedchar = stringfield(4)  # type: ignore[assignment]

    def wrong_checksum(self: object) -> int:
        return 0

    class WrongCalculation(BinmapDataclass):
        # the function returns int, but the field holds bytes
        name: string = calculatedfield(wrong_checksum)  # type: ignore[assignment]
