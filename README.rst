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
one unsiged byte for humidity:

.. code-block:: python

   >>> class TempHum(BinmapDataclass):
   ...     temp: signedchar = 0
   ...     hum: unsignedchar = 0
   ...
   >>> th = TempHum()
   >>> th.temp = -10
   >>> th.humidity = 60
   >>> print(bytes(th))
   b'\xfc<'

   >>> th2 = TempHum(b'\xea\x41')
   >>> print(th2.temp)
   -22
   >>> print(th2.hum)
   65



Datatypes
---------
Binmap supports all datatypes that standard library `struct <https://docs.python.org/3/library/struct.html>`_ has.
The types works as typehints in the dataclass. When giving an attribute a
typehinted datatype it will be added to the binary output from the class.


Padding
-------
Padding is a field type and datatype that is `length` bytes long, and will not show up as
attributes in the dataclass. Trying to assign it a value will be silently
ignored and reading from will raise the `AttributeException` exception.

.. code-block:: python

   >>> class PaddedData(BinmapDataclass):
   ...     temp: signedchar = 0
   ...     pad1: pad = padding(length = 5)
   ...
   >>> pd = PaddedData()
   >>> pd.temp = 14
   >>> print(bytes(pd))
   b'\x0e\x00\x00\x00\x00\x00'

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
   AttributeError: signature is a constant

Enums
-----
Enumfield maps agaings IntEnum or IntFlag so that you could set the value
either as the enum or as the numeric value.

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
   >>> print(w.direction)
   <WindEnum.West: 3>
   >>> w.direction = 2
   >>> print(w.direction)
   <WindEnum.South: 2>


Autolength
----------
Autolenght field types counts number of bytes in the output, including the
autolength field it self. You can't set an autolenght field. Autolength can be
offseted, for example to ignore it's own length.

.. code-block:: python

   >>> class MyBinStruct(BinmapDataclass):
   ...     length: unsignedchar = autolength()
   ...     temp: signedchar = 0
   ...
   >>> mb = MyBinStruct()
   >>> print(mb)
   MyBinStruct(length=2, temp=0)
   >>> mb.length = 10
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


