import binmap
import pytest
import struct


class Temp(binmap.Binmap):
    _datafields = {"temp": "B"}


class TempHum(binmap.Binmap):
    _datafields = {"temp": "B", "humidity": "B"}


class Pad(binmap.Binmap):
    _datafields = {"temp": "B", "_pad1": "xx", "humidity": "B"}


class AdvancedPad(binmap.Binmap):
    _datafields = {
        "temp": "B",
        "_pad1": "xx",
        "humidity": "B",
        "_pad2": "3x",
        "_pad3": "x",
    }


class Property(binmap.Binmap):
    _datafields = {
        "temp": "B",
        "wind": "B",
    }

    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

    @property
    def winddirection(self):
        if self.wind == Property.NORTH:
            return "North"
        if self.wind == Property.EAST:
            return "East"
        if self.wind == Property.SOUTH:
            return "South"
        if self.wind == Property.WEST:
            return "West"

    @winddirection.setter
    def winddirection(self, value):
        self.wind = value


def test_baseclass():
    b = binmap.Binmap()
    assert type(b) == binmap.Binmap


def test_baseclass_with_keyword():
    with pytest.raises(TypeError) as excinfo:
        binmap.Binmap(temp=10)
    assert "got an unexpected keyword argument 'temp'" in str(excinfo)


def test_different_classes_eq():
    t = Temp(temp=10)
    th = TempHum(temp=10, humidity=60)
    assert t != th
    assert t.temp == th.temp


class TestTempClass:
    def test_with_argument(self):
        t = Temp(temp=10)
        assert t.temp == 10

    def test_without_argument(self):
        t = Temp()
        assert t.temp == 0
        assert t.binarydata == struct.pack("B", 0)

    def test_unknown_argument(self):
        with pytest.raises(TypeError) as excinfo:
            Temp(hum=60)
        assert "got an unexpected keyword argument 'hum'" in str(excinfo)

    def test_value(self):
        t = Temp()
        t.temp = 10
        assert t.binarydata == struct.pack("B", 10)

    def test_raw(self):
        t = Temp(binarydata=struct.pack("B", 10))
        assert t.temp == 10

    def test_change_value(self):
        t = Temp(temp=10)
        assert t.binarydata == struct.pack("B", 10)

        t.temp = 20
        assert t.binarydata == struct.pack("B", 20)

    def test_value_bounds(self):
        t = Temp()
        with pytest.raises(struct.error) as excinfo:
            t.temp = 256
        assert "ubyte format requires 0 <= number <= 255" in str(excinfo)

        with pytest.raises(struct.error) as excinfo:
            t.temp = -1
        assert "ubyte format requires 0 <= number <= 255" in str(excinfo)

    def test_compare_equal(self):
        t1 = Temp(temp=10)
        t2 = Temp(temp=10)
        assert t1.temp == t2.temp
        assert t1 == t2

    def test_compare_not_equal(self):
        t1 = Temp(temp=10)
        t2 = Temp(temp=20)
        assert t1.temp != t2.temp
        assert t1 != t2


class TestTempHumClass:
    def test_with_argument(self):
        th = TempHum(temp=10, humidity=60)
        assert th.temp == 10
        assert th.humidity == 60

    def test_without_argument(self):
        th = TempHum()
        assert th.temp == 0
        assert th.humidity == 0
        assert th.binarydata == struct.pack("BB", 0, 0)

    def test_raw(self):
        th = TempHum(binarydata=struct.pack("BB", 10, 70))
        assert th.temp == 10
        assert th.humidity == 70

    def test_change_values(self):
        th = TempHum(temp=10, humidity=70)
        th.temp = 30
        th.humidity = 30
        assert th.temp == 30
        assert th.humidity == 30
        assert th.binarydata == struct.pack("BB", 30, 30)

    def test_compare_equal(self):
        th1 = TempHum(temp=10, humidity=70)
        th2 = TempHum(temp=10, humidity=70)
        assert th1.temp == th2.temp
        assert th1 == th2

    def test_compare_not_equal(self):
        th1 = TempHum(temp=10, humidity=70)
        th2 = TempHum(temp=20, humidity=60)
        th3 = TempHum(temp=10, humidity=60)
        th4 = TempHum(temp=20, humidity=70)
        assert (th1.temp != th2.temp) and (th1.humidity != th2.humidity)
        assert th1 != th2
        assert th1 != th3
        assert th1 != th4
        assert th2 != th3
        assert th2 != th4


class TestPadClass:
    def test_create_pad(self):
        p = Pad(temp=10, humidity=60)
        assert p.temp == 10
        with pytest.raises(AttributeError) as excinfo:
            p._pad1
        assert "Padding (_pad1) is not readable" in str(excinfo)
        assert p.humidity == 60

    def test_parse_data(self):
        p = Pad(binarydata=struct.pack("BxxB", 10, 60))
        assert p.temp == 10
        with pytest.raises(AttributeError) as excinfo:
            p._pad1
        assert "Padding (_pad1) is not readable" in str(excinfo)
        assert p.humidity == 60

    def test_pack_data(self):
        p = Pad()
        p.temp = 10
        p.humidity = 60
        assert p.binarydata == struct.pack("BxxB", 10, 60)

    def test_advanced_pad(self):
        p = AdvancedPad(temp=10, humidity=60)
        assert p.temp == 10
        assert p.humidity == 60
        with pytest.raises(AttributeError) as excinfo:
            p._pad1
        assert "Padding (_pad1) is not readable" in str(excinfo)
        with pytest.raises(AttributeError) as excinfo:
            p._pad2
        assert "Padding (_pad2) is not readable" in str(excinfo)
        with pytest.raises(AttributeError) as excinfo:
            p._pad3
        assert "Padding (_pad3) is not readable" in str(excinfo)

    def test_advanced_parse_data(self):
        p = AdvancedPad(binarydata=struct.pack("BxxB4x", 10, 60))
        assert p.temp == 10
        with pytest.raises(AttributeError) as excinfo:
            p._pad1
        assert "Padding (_pad1) is not readable" in str(excinfo)
        assert p.humidity == 60

    def test_advanced_pack_data(self):
        p = AdvancedPad()
        p.temp = 10
        p.humidity = 60
        assert p.binarydata == struct.pack("BxxB4x", 10, 60)


class TestPropertyClass:
    def test_create_class(self):
        pc = Property()
        assert pc

    def test_get_wind(self):
        pc = Property(temp=10, wind=2)
        assert pc.winddirection == "South"

    def test_wind_binary(self):
        pc = Property(binarydata=struct.pack("BB", 10, 0))
        assert pc.wind == Property.NORTH
        assert pc.winddirection == "North"
