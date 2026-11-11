---
name: binmap
description: Declare fixed-size binary record layouts (network packets, file headers, device and sensor protocols) as Python dataclasses with the binmap library. Type hints choose the struct format, bytes(obj) packs and Cls(data) parses. Use when code imports binmap or subclasses BinmapDataclass, or when the user wants binmap to read or write binary data with constants, padding, length fields, enums, fixed-size strings or checksums.
license: MIT
compatibility: Requires Python 3.11 or newer and the binmap package (pip install binmap). binmap itself has no dependencies.
---

# binmap

binmap turns a dataclass into a binary record layout built on the standard `struct`
module. Each field's type hint chooses its binary format. The fields are packed in the
order they're declared. `bytes(obj)` packs a record and `Cls(data)` parses one.

Every `python` block below runs on its own as a test in binmap's repository.

## Before you start

- **Check the version.** This skill describes binmap 2.0. If
  `hasattr(binmap, "BinmapError")` is false, an older release is installed. It
  behaves differently in ways that matter; see
  [Releases 1.2.1 and older](#releases-121-and-older).
- **Records have a fixed size.** binmap has no variable-length fields, no arrays
  (except fixed-size byte strings), no nested records and no bit fields. For a
  variable-length message, parse a fixed header with binmap and slice the rest
  yourself (see [Recipes](#recipes)). Use `IntFlag` for flag bits.

## Quick start

```python
from binmap import BinmapDataclass, calculatedfield, constant
from binmap.types import signedchar, unsignedchar, unsignedshort


class Reading(BinmapDataclass, byteorder="<"):
    magic: unsignedshort = constant(0xA55A)
    temp: signedchar = 0
    hum: unsignedchar = 0

    def chk(self) -> int:
        return (self.temp + self.hum) & 0xFF

    checksum: unsignedchar = calculatedfield(chk)


reading = Reading(temp=-20, hum=10)
data = bytes(reading)
assert data == b"\x5a\xa5\xec\x0a\xf6"

parsed = Reading(data)  # raw bytes are the only positional argument
assert parsed == reading
assert (parsed.temp, parsed.hum, parsed.checksum) == (-20, 10, 246)
```

## Core rules

1. **Subclass `BinmapDataclass`, and don't add `@dataclass`.** The base class makes
   every subclass a dataclass itself; adding the decorator raises `TypeError`.
2. **Give every field a default:** `= 0`, or one of the field functions below. Without
   one, defining the class raises
   `TypeError: non-default argument ... follows default argument`.
3. **Declaration order is wire order.** Inherited fields come first. No alignment
   padding is added, except with `byteorder="@"`.
4. **The byte order is a class keyword, and defaults to big-endian:**
   - `">"` (the default) or `"!"`: big-endian (network order), standard sizes.
   - `"<"`: little-endian, standard sizes.
   - `"="`: native order, standard sizes.
   - `"@"`: native order, native sizes and alignment, like C structs.

   `struct` itself defaults to `"@"`, so pass `byteorder=` explicitly when you port a
   `struct` format string.
5. **Packing and parsing:**
   - `bytes(obj)` packs.
   - `Cls(data)` creates an instance from `bytes`, `bytearray` or `memoryview`.
     `obj.frombytes(data)` updates an existing instance.
   - The data must be exactly the size of the record; `len(bytes(Cls()))` gives it.
   - Set fields with keyword arguments: `Cls(temp=1)`.
6. **Values are checked when they're assigned**: in the constructor, by attribute
   assignment and while parsing. A value that couldn't be packed raises right away,
   and the field keeps its old value. Only declared fields can be assigned, so a typo
   such as `obj.tmep = 1` raises `BinmapAttributeError`.
7. **Instances are ordinary dataclasses:** `repr`, `==`, `dataclasses.asdict`,
   `astuple` and `replace`, `copy` and `pickle` all work.

## Field types

Import the types from `binmap.types` (also available as `binmap.b_types`), or use
the single-letter aliases in `binmap.st`, which are named after the `struct` format
characters:

| `binmap.types` | `binmap.st` | Bytes | Value |
|---|---|---|---|
| `char` | `st.c` | 1 | `bytes` of length 1 |
| `signedchar` | `st.b` | 1 | `int`, -128 to 127 |
| `unsignedchar` | `st.B` | 1 | `int`, 0 to 255 |
| `boolean` | | 1 | `bool` (`True`, `False`, 0 or 1) |
| `short` | `st.h` | 2 | `int` |
| `unsignedshort` | `st.H` | 2 | `int` |
| `integer` | `st.i` | 4 | `int` |
| `unsignedinteger` | `st.I` | 4 | `int` |
| `long` | `st.l` | 4 (8 with `"@"` on 64-bit Linux and macOS) | `int` |
| `unsignedlong` | `st.L` | 4 (8 with `"@"` on 64-bit Linux and macOS) | `int` |
| `longlong` | `st.q` | 8 | `int` |
| `unsignedlonglong` | `st.Q` | 8 | `int` |
| `halffloat` | `st.e` | 2 | `float` |
| `floating` | `st.f` | 4 | `float` |
| `double` | `st.d` | 8 | `float` |
| `string` | `st.s` | `length` | `bytes`; needs `stringfield(length)` |
| `pascalstring` | `st.p` | `length` | `bytes`; needs `stringfield(length)` |
| `pad` | `st.x` | `length` | none; needs `padding(length)` |

- **Plain Python types work too,** but check their sizes:
  - `int` is a 4-byte signed `integer`;
  - `float` is a 4-byte `floating`, **not** a `double`;
  - `bool` is a `boolean`;
  - `bytes` is a `string`, and needs `stringfield(length)`.
- **Values are strict about types.**
  - Integer fields take `int` or anything with `__index__`, such as NumPy integers.
    They reject `float`.
  - Float fields take `int` or `float`.
  - `char`, `string` and `pascalstring` take `bytes`, never `str`.
- **Your own type:** `Annotated[<Python type>, StructCode("<struct code>")]`.

```python
from typing import Annotated

from binmap import BinmapDataclass, st
from binmap.types import StructCode, double, unsignedshort

rgb565 = Annotated[int, StructCode("H")]  # your own name for a struct code


class Pixel(BinmapDataclass, byteorder="<"):
    x: unsignedshort = 0
    y: st.H = 0  # the same type as x, by its struct format character
    colour: rgb565 = 0
    brightness: double = 1.0


assert len(bytes(Pixel())) == 2 + 2 + 2 + 8
assert bytes(Pixel(x=1, y=2, colour=0xF800))[:6] == b"\x01\x00\x02\x00\x00\xf8"
```

## Field functions

Use these as a field's default to give it special behaviour. All of them are in the
top-level `binmap` package.

```python
from enum import IntEnum

from binmap import (
    BinmapDataclass,
    autolength,
    calculatedfield,
    constant,
    enumfield,
    padding,
    stringfield,
)
from binmap.types import pad, string, unsignedchar, unsignedshort


class Kind(IntEnum):
    PING = 1
    DATA = 2


class Packet(BinmapDataclass):  # big-endian by default
    magic: unsignedshort = constant(0xCAFE)
    length: unsignedchar = autolength()  # the size of the whole record
    kind: unsignedchar = enumfield(Kind, default=Kind.PING)
    reserved: pad = padding(2)  # 2 zero bytes, not readable
    name: string = stringfield(4)  # exactly 4 bytes, zero-padded
    value: unsignedshort = 0

    def calculate_checksum(self) -> int:
        # Use the other fields. Calling bytes(self) here would recurse forever.
        return (self.kind + self.value + sum(self.name)) & 0xFF

    checksum: unsignedchar = calculatedfield(calculate_checksum)


packet = Packet(kind=Kind.DATA, name=b"temp", value=513)
data = bytes(packet)
assert data == b"\xca\xfe\x0d\x02\x00\x00temp\x02\x01\xb9"
assert packet.length == len(data) == 13

parsed = Packet(data)  # checks magic, length and checksum against the data
assert parsed == packet
assert type(parsed.kind) is int  # parsed enum values are plain ints...
assert Kind(parsed.kind) is Kind.DATA  # ...so convert them to get the member
```

- **`constant(value)`:** the field always holds `value`.
  - It's not a constructor argument, and assigning it raises `BinmapAttributeError`.
  - Parsing data that holds another value raises `BinmapValueError`.
- **`autolength(offset=0)`:** the record's size in bytes, including this field, plus
  `offset`.
  - Use a negative offset to leave bytes out, e.g. `autolength(-3)` to skip a 3-byte
    header.
  - It can't be set, and parsing checks it.
- **`padding(length=1)`:** use it with the `pad` type. It packs `length` zero bytes
  and ignores those bytes when parsing.
  - Reading the field raises `BinmapAttributeError`, and assigning it is silently
    ignored.
  - It's left out of `repr`, `==`, `asdict()`, `astuple()` and
    `dataclasses.fields(obj)`.
  - `dataclasses.fields(Cls)` on the *class* still lists it, so don't zip that with
    `astuple(obj)`.
- **`stringfield(length, default=b"")`:** required for `string`, `pascalstring` and
  plain `bytes` fields. See [Strings](#strings).
- **`enumfield(EnumClass, default=...)`:** the value must belong to an `IntEnum` or
  `IntFlag`. **Always give a default:** without one, both `Cls()` and `Cls(data)`
  raise. See [Enums and flags](#enums-and-flags).
- **`calculatedfield(function, last=False)`:** the value is `function(obj)`,
  calculated whenever the field is read or the record is packed.
  - Define the function in the class body *above* the field, and annotate its return
    type (`-> int`) for type checkers. A `lambda` also works.
  - The function must not read its own field, or call `bytes(self)`, `asdict(self)`
    or `astuple(self)`; all of these recurse forever.
  - The field can't be set. Parsing checks the data against the function's result,
    after all other fields are set, so checksums are verified automatically.
  - `last=True` packs the field at the very end, after the fields that subclasses
    add. Only one such field is allowed per class hierarchy. See
    [Inheritance](#inheritance-and-a-trailing-checksum).

## Strings

```python
from binmap import BinmapDataclass, stringfield
from binmap.types import pascalstring, string


class Names(BinmapDataclass):
    fixed: string = stringfield(6)  # always 6 bytes, padded with zero bytes
    pascal: pascalstring = stringfield(6)  # a length byte, then up to 5 bytes


names = Names(fixed=b"abc", pascal=b"abc")
assert bytes(names) == b"abc\x00\x00\x00" + b"\x03abc\x00\x00"

parsed = Names(bytes(names))
assert parsed.fixed == b"abc\x00\x00\x00"  # a string keeps the zero bytes
assert parsed.fixed.rstrip(b"\x00").decode("ascii") == "abc"
assert parsed.pascal == b"abc"  # a pascalstring gives just the string

try:
    names.fixed = b"too long!"  # never silently cut
except ValueError as error:
    assert str(error) == "fixed holds at most 6 bytes, got 9"
else:
    raise AssertionError("9 bytes should be rejected")
```

- **Values are always `bytes`.** Encode and decode text yourself.
- **Defaults:** a `string` defaults to `length` zero bytes, and a `pascalstring` to
  `b""`.
- **Sizes:** a `pascalstring` holds at most `length - 1` bytes, and never more than
  255.

## Enums and flags

```python
from enum import IntEnum, IntFlag

from binmap import BinmapDataclass, enumfield
from binmap.types import unsignedchar


class Mode(IntEnum):
    OFF = 0
    ON = 1


class Status(IntFlag):
    READY = 1
    ERROR = 2
    BUSY = 4


class Device(BinmapDataclass):
    mode: unsignedchar = enumfield(Mode, default=Mode.OFF)
    status: unsignedchar = enumfield(Status, default=Status(0))


device = Device(mode=Mode.ON)
device.mode = 0  # a number must be one of the enum's values
device.status = Status.READY | Status.BUSY  # any combination of flags
assert bytes(device) == b"\x00\x05"

parsed = Device(b"\x01\x03")
assert Mode(parsed.mode) is Mode.ON
assert Status.ERROR in Status(parsed.status)

try:
    device.mode = 7
except ValueError as error:
    assert str(error) == "7 is not a valid Mode"
else:
    raise AssertionError("7 should be rejected")
```

- **Accepted values:** a member, or a number that is one of the enum's values. For an
  `IntFlag`, any combination of flags.
- **Names:** a member's name, such as `device.mode = "ON"`, also works and stores the
  member. Type checkers see the field as an `int`, though, and flag the name, so use
  members in type-checked code.
- **Parsed values** are plain `int`s. Convert them with `Mode(value)` to get the
  member.

## Inheritance and a trailing checksum

A subclass's fields come after its parent's, except a `calculatedfield(last=True)`,
which always comes last. The function is bound when the parent class is defined.
So, to include fields that subclasses add, let it call a method that subclasses
override:

```python
from binmap import BinmapDataclass, calculatedfield
from binmap.types import unsignedchar, unsignedshort


class Message(BinmapDataclass):
    kind: unsignedchar = 0

    def body_sum(self) -> int:
        return 0  # subclasses add their own fields

    def calculate_checksum(self) -> int:
        return (self.kind + self.body_sum()) & 0xFF

    checksum: unsignedchar = calculatedfield(calculate_checksum, last=True)


class Temperature(Message):
    value: unsignedshort = 0

    def body_sum(self) -> int:
        return self.value


reading = Temperature(kind=1, value=0x0102)
assert bytes(reading) == b"\x01" + b"\x01\x02" + b"\x03"  # checksum last
# repr and asdict() follow declaration order, not wire order
assert repr(reading) == "Temperature(kind=1, checksum=3, value=258)"

try:
    Temperature(b"\x01\x01\x02\x00")
except ValueError as error:
    assert str(error) == "checksum: the data has 0, but the calculated value is 3"
else:
    raise AssertionError("a wrong checksum should be rejected")
```

## Errors

Everything binmap raises derives from `binmap.BinmapError`, and also from the matching
built-in exception:

| Exception | Also a | Raised for |
|---|---|---|
| `BinmapValueError` | `ValueError`, `struct.error` | A value out of range or too long, or not one of the enum's. Data of the wrong size, or data that doesn't match a constant, autolength or calculated field. A bad `byteorder` or default when the class is defined. |
| `BinmapTypeError` | `TypeError`, `struct.error` | A value of the wrong type, such as `str` for a number or `float` for an `int`. Data to parse that isn't bytes. A field type binmap can't pack, or two `last=True` fields, when the class is defined. |
| `BinmapAttributeError` | `AttributeError` | Assigning a name that isn't a field. Setting a constant, autolength or calculated field. Reading padding. |

- **Parsing is all-or-nothing:** if `frombytes()` raises, the instance is unchanged.
- **Python's own errors:** the dataclass constructor raises a plain `TypeError` for an
  unknown keyword argument, which includes passing a constant or autolength field.

```python
import binmap
from binmap import BinmapDataclass
from binmap.types import signedchar


class Reading(BinmapDataclass):
    temp: signedchar = 0


reading = Reading(temp=5)
try:
    reading.temp = 300
except ValueError as error:  # a binmap.BinmapValueError
    # The text after "temp: " comes from struct, and varies between Python versions
    assert "format requires -128 <= number <= 127" in str(error)
else:
    raise AssertionError("300 should be rejected")
assert reading.temp == 5  # a rejected value changes nothing

try:
    Reading(b"\x01\x02")
except binmap.BinmapError as error:  # catches everything binmap raises
    assert str(error) == "Reading needs 1 byte of data, got 2"
else:
    raise AssertionError("2 bytes should be rejected")
```

## Recipes

### A fixed header with a variable-length payload

```python
from binmap import BinmapDataclass, constant
from binmap.types import unsignedchar, unsignedshort


class Header(BinmapDataclass):
    magic: unsignedshort = constant(0xBEEF)
    kind: unsignedchar = 0
    payload_length: unsignedshort = 0


HEADER_SIZE = len(bytes(Header()))

# Parsing: the header first, then the payload it describes
frame = b"\xbe\xef\x01\x00\x03abcEXTRA"
header = Header(frame[:HEADER_SIZE])
payload = frame[HEADER_SIZE : HEADER_SIZE + header.payload_length]
assert (header.kind, payload) == (1, b"abc")

# Building: pack the header and append the payload
payload = b"hello"
frame = bytes(Header(kind=2, payload_length=len(payload))) + payload
assert frame == b"\xbe\xef\x02\x00\x05hello"
```

### Many records in a row

```python
from binmap import BinmapDataclass
from binmap.types import floating, unsignedinteger


class Sample(BinmapDataclass, byteorder="<"):
    timestamp: unsignedinteger = 0
    value: floating = 0.0


SIZE = len(bytes(Sample()))
data = b"".join(bytes(Sample(timestamp=t, value=t / 2)) for t in range(3))

samples = [Sample(data[i : i + SIZE]) for i in range(0, len(data), SIZE)]
assert [sample.value for sample in samples] == [0.0, 0.5, 1.0]
```

For a file, read `SIZE` bytes at a time from a file opened with `"rb"`. A short last
chunk raises `BinmapValueError`.

## Type checkers and editors

binmap ships type hints (`py.typed`).
- **Constructors:** mypy and pyright (VS Code's Pylance) treat every subclass as a
  dataclass, so they check its constructor's arguments.
- **Fields:** they appear as plain `int`, `float`, `bool` or `bytes`.
- **Typos:** a misspelled field name, such as `obj.tmep = 1`, is reported.
- **Calculated fields:** annotate the function's return type, so the field's type
  matches it.

## Releases 1.2.1 and older

On PyPI, 1.2.1 is the latest release until 2.0 is published. If
`hasattr(binmap, "BinmapError")` is false, the installed release differs from
everything above:

- **Python 3.14 and newer aren't supported.**
- **Errors:** there's no `BinmapError`. Bad values raise `struct.error`, and invalid
  data, enum names and classes raise `ValueError` or `KeyError`.
- **Unknown attributes:** assigning one is silently accepted.
- **Strings:** values that are too long are silently cut.
- **Types:** they're `NewType`s, so type checkers reject `temp: unsignedchar = 0`.
  There's no `StructCode`, so you can't define your own types.
- **Enums:** setting an enum field by name stores the string, and `bytes()` then
  fails. Use members or numbers.
- **Padding:** `asdict()` and `astuple()` fail on classes with padding.
