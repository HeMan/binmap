Class for go to and from binary data


It's designed to be easy to create mappings by just having a
``_datafields`` classs attribute.

Temperature with one unsigned byte:

.. code-block:: python

    class Temperature(Binmap):
        _datafields = {"temp": "B"}

    t = Temperature()
    t.temp = 22
    print(t.binarydata)
    b'\\x16'

    t2 = Temperature(binarydata=b'\\x20')
    print(t2.temp)
    32

Temperature and humidity consisting of one signed byte for temperature and
one unsiged byte for humidity:

.. code-block:: python

    class TempHum(Binmap):
        _datafields = {"temp": "b", "hum": "B"}

    th = TempHum()
    th.temp = -10
    th.humidity = 60
    print(th.binarydata)
    b'\\xfc<'

    th2 = TempHum(binarydata=b'\\xea\\x41')
    print(th2.temp)
    -22
    print(th2.hum)
    65


