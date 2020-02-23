import struct

import pytest

import binmap


def test_baseclass():
    b = binmap.Binmap()
    assert type(b) == binmap.Binmap
    assert str(b) == "Binmap"


def test_baseclass_with_keyword():
    with pytest.raises(TypeError) as excinfo:
        binmap.Binmap(temp=10)
    assert "got an unexpected keyword argument 'temp'" in str(excinfo)


def test_illegal_fieldnames():
    with pytest.raises(ValueError) as excinfo:

        class Space(binmap.Binmap):
            _datafields = {
                " ": "B",
            }

    assert "' ' is not a valid parameter name" in str(excinfo)

    with pytest.raises(ValueError) as excinfo:

        class BadName(binmap.Binmap):
            _datafields = {
                "-a": "B",
            }

    assert "'-a' is not a valid parameter name" in str(excinfo)
    with pytest.raises(ValueError) as excinfo:

        class Number(binmap.Binmap):
            _datafields = {
                "1": "B",
            }

    assert "'1' is not a valid parameter name" in str(excinfo)


class Temp(binmap.Binmap):
    _datafields = {"temp": "B"}


class TempHum(binmap.Binmap):
    _datafields = {"temp": "B", "humidity": "B"}


def test_different_classes_eq():
    t = Temp(temp=10)
    th = TempHum(temp=10, humidity=60)
    assert t != th
    assert t.temp == th.temp


class Bigendian(binmap.Binmap):
    _datafields = {"value": "q"}


class Littleedian(binmap.Binmap):
    _byteorder = "<"
    _datafields = {"value": "q"}


def test_dataformats():

    be = Bigendian(value=-10)
    le = Littleedian(value=-10)

    assert be.value == le.value
    assert be.binarydata == b"\xff\xff\xff\xff\xff\xff\xff\xf6"
    assert le.binarydata == b"\xf6\xff\xff\xff\xff\xff\xff\xff"

    assert be.binarydata != le.binarydata

    be.binarydata = b"\xff\xff\xff\xff\xf4\xff\xff\xf6"
    le.binarydata = b"\xff\xff\xff\xff\xf4\xff\xff\xf6"

    assert be.value == -184549386
    assert le.value == -648518393585991681

    assert be.value != le.value
    assert be.binarydata == le.binarydata


class TestTempClass:
    def test_with_argument(self):
        t = Temp(temp=10)
        assert t.temp == 10
        assert str(t) == "Temp, temp=10"

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

    def test_update_binarydata(self):
        t = Temp(binarydata=struct.pack("B", 10))
        assert t.temp == 10
        t.binarydata = struct.pack("B", 20)
        assert t.temp == 20

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
        assert str(th) == "TempHum, temp=10, humidity=60"

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


class TestPadClass:
    def test_create_pad(self):
        p = Pad(temp=10, humidity=60)
        with pytest.raises(AttributeError) as excinfo:
            p._pad1
        assert "Padding (_pad1) is not readable" in str(excinfo)
        assert p.temp == 10
        assert p.humidity == 60
        assert str(p) == "Pad, temp=10, humidity=60"

    def test_parse_data(self):
        p = Pad(binarydata=struct.pack("BxxB", 10, 60))
        with pytest.raises(AttributeError) as excinfo:
            p._pad1
        assert p.temp == 10
        assert "Padding (_pad1) is not readable" in str(excinfo)
        assert p.humidity == 60

    def test_pack_data(self):
        p = Pad()
        p.temp = 10
        p.humidity = 60
        assert p.binarydata == struct.pack("BxxB", 10, 60)

    def test_advanced_pad(self):
        p = AdvancedPad(temp=10, humidity=60)
        with pytest.raises(AttributeError) as excinfo:
            p._pad1
        assert "Padding (_pad1) is not readable" in str(excinfo)
        with pytest.raises(AttributeError) as excinfo:
            p._pad2
        assert "Padding (_pad2) is not readable" in str(excinfo)
        with pytest.raises(AttributeError) as excinfo:
            p._pad3
        assert "Padding (_pad3) is not readable" in str(excinfo)
        assert p.temp == 10
        assert p.humidity == 60

    def test_advanced_parse_data(self):
        p = AdvancedPad(binarydata=struct.pack("BxxB4x", 10, 60))
        with pytest.raises(AttributeError) as excinfo:
            p._pad1
        assert "Padding (_pad1) is not readable" in str(excinfo)
        with pytest.raises(AttributeError) as excinfo:
            p._pad2
        assert "Padding (_pad2) is not readable" in str(excinfo)
        assert p.humidity == 60
        assert p.temp == 10
        assert str(p) == "AdvancedPad, temp=10, humidity=60"

    def test_advanced_pack_data(self):
        p = AdvancedPad()
        p.temp = 10
        p.humidity = 60
        assert p.binarydata == struct.pack("BxxB4x", 10, 60)


class EnumClass(binmap.Binmap):
    _datafields = {
        "temp": "B",
        "wind": "B",
    }

    _enums = {"wind": {0: "North", 1: "East", 2: "South", 4: "West"}}


class TestEnumClass:
    def test_create_class(self):
        pc = EnumClass()
        assert pc
        assert EnumClass.SOUTH == 2

    def test_get_enum(self):
        pc = EnumClass(temp=10, wind=2)
        assert pc.wind == "South"
        assert str(pc) == "EnumClass, temp=10, wind=South"

    def test_enum_binary(self):
        pc = EnumClass(binarydata=struct.pack("BB", 10, 2))
        assert pc.wind == "South"
        assert str(pc) == "EnumClass, temp=10, wind=South"

    def test_set_named_enum(self):
        pc = EnumClass()
        pc.wind = "South"
        assert pc.binarydata == struct.pack("BB", 0, 2)

        with pytest.raises(ValueError) as excinfo:
            pc.wind = "Norhtwest"
        assert "Unknown enum or value" in str(excinfo)

        with pytest.raises(ValueError) as excinfo:
            pc.wind = 1.2
        assert "Unknown enum or value" in str(excinfo)

    def test_colliding_enums(self):
        with pytest.raises(ValueError) as excinfo:

            class EnumCollide(binmap.Binmap):
                _datafields = {
                    "wind1": "B",
                    "wind2": "B",
                }
                _enums = {
                    "wind1": {0: "North"},
                    "wind2": {2: "North"},
                }

        assert "North already defined" in str(excinfo)


class ConstValues(binmap.Binmap):
    _datafields = {"datatype": "B", "status": "B"}
    _constants = {"datatype": 0x15}


class TestConstValues:
    def test_create_class(self):
        c = ConstValues()
        with pytest.raises(AttributeError) as excinfo:
            ConstValues(datatype=0x14, status=1)
        assert "datatype is a constant" in str(excinfo)
        assert c.datatype == 0x15

    def test_set_value(self):
        c = ConstValues(status=1)
        with pytest.raises(AttributeError) as excinfo:
            c.datatype = 0x14
        assert "datatype is a constant" in str(excinfo)
        assert c.datatype == 0x15
        assert c.status == 1
        assert c.binarydata == b"\x15\x01"

    def test_binary_data(self):
        c = ConstValues(binarydata=b"\x15\x01")
        with pytest.raises(ValueError) as excinfo:
            ConstValues(binarydata=b"\x14\x01")
        assert "Constant doesn't match binary data" in str(excinfo)
        assert c.datatype == 0x15
        assert c.status == 1


class AllDatatypes(binmap.Binmap):
    _datafields = {
        "_pad": "x",
        "char": "c",
        "signedchar": "b",
        "unsignedchar": "B",
        "boolean": "?",
        "short": "h",
        "unsignedshort": "H",
        "integer": "i",
        "unsignedint": "I",
        "long": "l",
        "unsignedlong": "L",
        "longlong": "q",
        "unsignedlonglong": "Q",
        "halffloat": "e",
        "floating": "f",
        "double": "d",
        "string": "10s",
        "pascalstring": "15p",
    }


class TestAllDatatypes:
    def test_create_class(self):
        sc = AllDatatypes()
        assert sc

    def test_with_arguments(self):
        sc = AllDatatypes(
            char=b"%",
            signedchar=-2,
            unsignedchar=5,
            boolean=True,
            short=-7,
            unsignedshort=17,
            integer=-15,
            unsignedint=11,
            long=-2312,
            unsignedlong=2212,
            longlong=-1212,
            unsignedlonglong=4444,
            halffloat=3.5,
            floating=3e3,
            double=13e23,
            string=b"helloworld",
            pascalstring=b"hello pascal",
        )
        assert sc.char == b"%"
        assert sc.signedchar == -2
        assert sc.unsignedchar == 5
        assert sc.boolean
        assert sc.short == -7
        assert sc.unsignedshort == 17
        assert sc.integer == -15
        assert sc.unsignedint == 11
        assert sc.long == -2312
        assert sc.unsignedlong == 2212
        assert sc.longlong == -1212
        assert sc.unsignedlonglong == 4444
        assert sc.halffloat == 3.5
        assert sc.floating == 3e3
        assert sc.double == 13e23
        assert sc.string == b"helloworld"
        assert sc.pascalstring == b"hello pascal"
        assert (
            sc.binarydata
            == b"\x00%\xfe\x05\x01\xff\xf9\x00\x11\xff\xff\xff\xf1\x00\x00\x00\x0b\xff\xff\xf6\xf8\x00\x00"
            b"\x08\xa4\xff\xff\xff\xff\xff\xff\xfbD\x00\x00\x00\x00\x00\x00\x11\\C\x00E;\x80\x00D\xf14\x92Bg\x0c"
            b"\xe8helloworld\x0chello pascal\x00\x00"
        )

    def test_with_binarydata(self):
        sc = AllDatatypes(
            binarydata=b"\x00W\xee\x15\x00\xf4\xf9\x10\x11\xff\xff\xff1\x00\x00\x01\x0b\xff\xff\xe6\xf8\x00\x00\x18"
            b"\xa4\xff\xff\xff\xff\xff\xff\xfbE\x00\x00\x00\x00\x00\x01\x11\\C\x01E;\x81\x00D\xf14\xa2Bg\x0c"
            b"\xe8hi world  \x09hi pascal\x00\x00\x00\x00\x00"
        )
        assert sc.char == b"W"
        assert sc.signedchar == -18
        assert sc.unsignedchar == 21
        assert not sc.boolean
        assert sc.short == -2823
        assert sc.unsignedshort == 4113
        assert sc.integer == -207
        assert sc.unsignedint == 267
        assert sc.long == -6408
        assert sc.unsignedlong == 6308
        assert sc.longlong == -1211
        assert sc.unsignedlonglong == 69980
        assert sc.halffloat == 3.501953125
        assert sc.floating == 3000.0625
        assert sc.double == 1.3000184467440736e24
        assert sc.string == b"hi world  "
        assert sc.pascalstring == b"hi pascal"
