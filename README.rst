Dataclass for go to and from binary data


It follows dataclass pattern with typehinting as the binary format.
Temperature with one unsigned byte:

.. code-block:: python

   >>> class Temperature(BinmapDataclass):
   ...     temp: unsignedchar = 0
   ...
   >>> t = Temperature()
   >>> t.temp = 22
   >>> print(bytes(t))
   b'\x16'

   >>> t2 = Temperature(b'\x20')
   >>> print(t2.temp)
   32

Temperature and humidity consisting of one signed byte for temperature and
one unsigned byte for humidity:

.. code-block:: python

   >>> class TempHum(BinmapDataclass):
   ...     temp: signedchar = 0
   ...     hum: unsignedchar = 0
   ...
   >>> th = TempHum()
   >>> th.temp = -10
   >>> th.hum = 60
   >>> print(bytes(th))
   b'\xf6<'

   >>> th2 = TempHum(b'\xea\x41')
   >>> print(th2.temp)
   -22
   >>> print(th2.hum)
   65

Only fields can be assigned, so a misspelled name fails right away instead of
being silently added:

.. code-block:: python

   >>> th.humidity = 60
   Traceback (most recent call last):
   ...
   AttributeError: TempHum has no field 'humidity'



Datatypes
---------
Binmap supports all datatypes that standard library `struct <https://docs.python.org/3/library/struct.html>`_ has.
The types works as typehints in the dataclass. When giving an attribute a
typehinted datatype it will be added to the binary output from the class.
Plain `int`, `float` and `bool` work too (packed like `integer`, `floating` and
`boolean`), as does `bytes` with a `stringfield`.


Type checking and editors
-------------------------
Binmap ships type information (`py.typed`), and type checkers and editors see binmap
classes as dataclasses: they know each class's constructor and show fields as plain
Python types (`int`, `float`, `bool` or `bytes`). CI checks this with mypy and with
pyright, the engine behind VS Code's Pylance.

The types in `binmap.types` are `Annotated` aliases that carry the struct format
character in a `StructCode`, so you can define your own:

.. code-block:: python

   >>> from typing import Annotated
   >>> from binmap.types import StructCode
   >>> rgb565 = Annotated[int, StructCode("H")]
   >>> class Pixel(BinmapDataclass):
   ...     colour: rgb565 = 0
   ...
   >>> print(bytes(Pixel(colour=0xF800)))
   b'\xf8\x00'


Strings
-------
`string` and `pascalstring` fields have a fixed length in bytes, set with
`stringfield(length)`. Their values are `bytes`, not `str`. By default a `string` is
`length` zero bytes and a `pascalstring` is empty; `stringfield(length, default=b"...")`
sets another default.

A `string` is padded with zero bytes to its length, and keeps them when parsed:

.. code-block:: python

   >>> class Named(BinmapDataclass):
   ...     name: string = stringfield(8)
   ...
   >>> print(bytes(Named(name=b"binmap")))
   b'binmap\x00\x00'
   >>> print(Named(b"hello\x00\x00\x00").name)
   b'hello\x00\x00\x00'

A `pascalstring` stores the string's length in its first byte, so it holds at most
`length - 1` bytes (and never more than 255), and parsing returns just the string:

.. code-block:: python

   >>> class PascalNamed(BinmapDataclass):
   ...     name: pascalstring = stringfield(8)
   ...
   >>> print(bytes(PascalNamed(name=b"binmap")))
   b'\x06binmap\x00'
   >>> print(PascalNamed(b"\x06binmap\x00").name)
   b'binmap'

A value longer than the field holds is rejected, instead of being cut:

.. code-block:: python

   >>> Named(name=b"much too long")
   Traceback (most recent call last):
   ...
   struct.error: name holds at most 8 bytes, got 13


Padding
-------
Padding is a field type and datatype that is `length` bytes long, and will not show up as
attributes in the dataclass. Trying to assign it a value will be silently
ignored and reading from will raise the `AttributeError` exception.
Padding is also left out of `dataclasses.asdict()`, `dataclasses.astuple()` and
`dataclasses.fields()` of an instance, and is ignored by `==`. `dataclasses.fields()` of
the class still lists padding, so pair `astuple(obj)` with `fields(obj)`, not with
`fields(PaddedData)`.

.. code-block:: python

   >>> class PaddedData(BinmapDataclass):
   ...     temp: signedchar = 0
   ...     pad1: pad = padding(length = 5)
   ...
   >>> pd = PaddedData()
   >>> pd.temp = 14
   >>> print(bytes(pd))
   b'\x0e\x00\x00\x00\x00\x00'
   >>> print(asdict(pd))
   {'temp': 14}

Constant
--------
Constant is fieldtype that always is the given value. Constant could be of any
datatype.

.. code-block:: python

   >>> class Constant(BinmapDataclass):
   ...     signature: unsignedshort = constant(0x1313)
   ...     temp: unsignedchar = 0
   ...
   >>> c = Constant()
   >>> c.temp = 18
   >>> print(bytes(c))
   b'\x13\x13\x12'

   >>> print(c.signature)
   4883
   >>> print(c.temp)
   18

   >>> c.signature = 10
   Traceback (most recent call last):
   ...
   AttributeError: signature is a constant

Enums
-----
Enumfield maps against IntEnum or IntFlag, so you can set the value as a member,
a member's name or a number. A name stores the member it names. A number is stored as
given and has to match one of the enum's values. Either way the value has to fit the
field.

.. code-block:: python

   >>> class WindEnum(IntEnum):
   ...     North = 0
   ...     East = 1
   ...     South = 2
   ...     West = 3
   ...
   >>> class Wind(BinmapDataclass):
   ...     speed: unsignedchar = 0
   ...     direction: unsignedchar = enumfield(WindEnum, default=WindEnum.East)
   ...
   >>> w = Wind()
   >>> print(w)
   Wind(speed=0, direction=<WindEnum.East: 1>)
   >>> w.direction = WindEnum.West
   >>> w.direction
   <WindEnum.West: 3>
   >>> w.direction = 2
   >>> w.direction == WindEnum.South
   True
   >>> w.direction = "North"
   >>> w.direction
   <WindEnum.North: 0>
   >>> print(bytes(w))
   b'\x00\x00'
   >>> w.direction = 7
   Traceback (most recent call last):
   ...
   ValueError: 7 is not a valid WindEnum


Autolength
----------
Autolength field types count the number of bytes in the output, including the
autolength field itself. You can't set an autolength field. Autolength can be
offset, for example to ignore its own length.

.. code-block:: python

   >>> class MyBinStruct(BinmapDataclass):
   ...     length: unsignedchar = autolength()
   ...     temp: signedchar = 0
   ...
   >>> mb = MyBinStruct()
   >>> print(mb)
   MyBinStruct(length=2, temp=0)
   >>> mb.length = 10
   Traceback (most recent call last):
   ...
   AttributeError: length is a constant

Calculated fields
-----------------
Calculated fields calls a function when data is converted to binary value. The
function must be declared when the field is added.

.. code-block:: python

   >>> class WithChecksum(BinmapDataclass):
   ...     temp: signedchar = 0
   ...     hum: unsignedchar = 0
   ...     def chk(self) -> unsignedchar:
   ...         return (self.temp + self.hum) & 0xFF
   ...     checksum: unsignedchar = calculatedfield(chk)
   ...
   >>> wc = WithChecksum()
   >>> wc.temp = -20
   >>> wc.hum = 10
   >>> print(wc)
   WithChecksum(temp=-20, hum=10, checksum=246)
   >>> print(bytes(wc))
   b'\xec\n\xf6'


