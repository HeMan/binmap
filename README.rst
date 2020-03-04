Dataclass for go to and from binary data


It follows dataclass pattern with typehinting as the binary format.
Temperature with one unsigned byte:

.. code-block:: python
    @binmapdataclass
    class Temperature(BinmapDataclass):
        temp: unsignedchar = 0

    t = Temperature()
    t.temp = 22
    print(bytes(t))
    b'\x16'

    t2 = Temperature(b'\x20')
    print(t2.temp)
    32

Temperature and humidity consisting of one signed byte for temperature and
one unsiged byte for humidity:

.. code-block:: python
    @binmapdataclass
    class TempHum(BinmapDataclass):
        temp: signedchar = 0
        hum: unsignedchar = 0

    th = TempHum()
    th.temp = -10
    th.humidity = 60
    print(bytes(th))
    b'\xfc<'

    th2 = TempHum(b'\xea\x41')
    print(th2.temp)
    -22
    print(th2.hum)
    65


