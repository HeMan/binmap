import struct
from enum import IntEnum

import pytest

import binmap


def test_baseclass():
    b = binmap.BinmapDataclass()
    assert type(b) == binmap.BinmapDataclass
    assert str(b) == "BinmapDataclass()"


def test_baseclass_with_keyword():
    with pytest.raises(TypeError) as excinfo:
        binmap.BinmapDataclass(temp=10)
    assert "got an unexpected keyword argument 'temp'" in str(excinfo)


@binmap.binmapdataclass
class Temp(binmap.BinmapDataclass):
    temp: binmap.unsignedchar = 0


@binmap.binmapdataclass
class TempHum(binmap.BinmapDataclass):
    temp: binmap.unsignedchar = 0
    humidity: binmap.unsignedchar = 0


def test_different_classes_eq():
    t = Temp(temp=10)
    th = TempHum(temp=10, humidity=60)
    assert t != th
    assert t.temp == th.temp


@binmap.binmapdataclass
class Bigendian(binmap.BinmapDataclass):
    value: binmap.longlong = 0


@binmap.binmapdataclass
class Littleedian(binmap.BinmapDataclass, byteorder="<"):
    value: binmap.longlong = 0


def test_dataformats():
    be = Bigendian(value=-10)
    le = Littleedian(value=-10)

    assert be.value == le.value
    assert bytes(be) == b"\xff\xff\xff\xff\xff\xff\xff\xf6"
    assert bytes(le) == b"\xf6\xff\xff\xff\xff\xff\xff\xff"

    assert bytes(be) != bytes(le)

    be.frombytes(b"\xff\xff\xff\xff\xf4\xff\xff\xf6")
    le.frombytes(b"\xff\xff\xff\xff\xf4\xff\xff\xf6")

    assert be.value == -184549386
    assert le.value == -648518393585991681

    assert be.value != le.value
    assert bytes(be) == bytes(le)


class TestTempClass:
    def test_with_argument(self):
        t = Temp(temp=10)
        assert t.temp == 10
        assert bytes(t) == b"\x0a"
        assert str(t) == "Temp(temp=10)"

    def test_without_argument(self):
        t = Temp()
        assert t.temp == 0
        assert bytes(t) == b"\x00"

    def test_unknown_argument(self):
        with pytest.raises(TypeError) as excinfo:
            Temp(hum=60)
        assert "got an unexpected keyword argument 'hum'" in str(excinfo)

    def test_value(self):
        t = Temp()
        t.temp = 10
        assert bytes(t) == b"\x0a"

    def test_raw(self):
        t = Temp(b"\x0a")
        assert t.temp == 10

    def test_update_binarydata(self):
        t = Temp(b"\x0a")
        assert t.temp == 10
        t.frombytes(b"\x14")
        assert t.temp == 20

    def test_change_value(self):
        t = Temp(temp=10)
        assert bytes(t) == b"\x0a"

        t.temp = 20
        assert bytes(t) == b"\x14"

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
        assert str(th) == "TempHum(temp=10, humidity=60)"

    def test_without_argument(self):
        th = TempHum()
        assert th.temp == 0
        assert th.humidity == 0
        assert bytes(th) == b"\x00\x00"

    def test_raw(self):
        th = TempHum(b"\x0a\x46")
        assert th.temp == 10
        assert th.humidity == 70

    def test_change_values(self):
        th = TempHum(temp=10, humidity=70)
        th.temp = 30
        th.humidity = 30
        assert th.temp == 30
        assert th.humidity == 30
        assert bytes(th) == b"\x1e\x1e"

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


@binmap.binmapdataclass
class Pad(binmap.BinmapDataclass):
    temp: binmap.unsignedchar = 0
    pad: binmap.pad = binmap.padding(2)
    humidity: binmap.unsignedchar = 0


@binmap.binmapdataclass
class AdvancedPad(binmap.BinmapDataclass):
    temp: binmap.unsignedchar = 0
    _pad1: binmap.pad = binmap.padding(2)
    humidity: binmap.unsignedchar = 0
    _pad2: binmap.pad = binmap.padding(3)
    _pad3: binmap.pad = binmap.padding(1)


class TestPadClass:
    def test_create_pad(self):
        p = Pad(temp=10, humidity=60)
        with pytest.raises(AttributeError) as excinfo:
            p.pad
        assert "Padding (pad) is not readable" in str(excinfo)
        assert p.temp == 10
        assert p.humidity == 60
        assert str(p) == "Pad(temp=10, humidity=60)"

    def test_parse_data(self):
        p = Pad(b"\x0a\x10\x20\x3c")
        with pytest.raises(AttributeError) as excinfo:
            p.pad
        assert "Padding (pad) is not readable" in str(excinfo)
        assert p.temp == 10
        assert p.humidity == 60

    def test_pack_data(self):
        p = Pad()
        p.temp = 10
        p.humidity = 60
        assert bytes(p) == b"\x0a\x00\x00\x3c"

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
        p = AdvancedPad(b"\n\x00\x00<\x00\x00\x00\x00")
        with pytest.raises(AttributeError) as excinfo:
            p._pad1
        assert "Padding (_pad1) is not readable" in str(excinfo)
        with pytest.raises(AttributeError) as excinfo:
            p._pad2
        assert "Padding (_pad2) is not readable" in str(excinfo)
        assert p.humidity == 60
        assert p.temp == 10
        assert str(p) == "AdvancedPad(temp=10, humidity=60)"

    def test_advanced_pack_data(self):
        p = AdvancedPad()
        p.temp = 10
        p.humidity = 60
        assert bytes(p) == b"\n\x00\x00<\x00\x00\x00\x00"


class WindEnum(IntEnum):
    North = 0
    East = 1
    South = 2
    West = 3


@binmap.binmapdataclass
class EnumClass(binmap.BinmapDataclass):
    temp: binmap.unsignedchar = 0
    wind: binmap.unsignedchar = binmap.enumfield(WindEnum, default=WindEnum.East)


class TestEnumClass:
    def test_create_class(self):
        ec = EnumClass()
        assert ec

    def test_get_enum(self):
        ec = EnumClass(temp=10, wind=2)
        assert ec.wind == WindEnum.South
        assert str(ec) == "EnumClass(temp=10, wind=2)"

    def test_enum_binary(self):
        ec = EnumClass(b"\x0a\x02")
        assert ec.wind == WindEnum.South
        assert str(ec) == "EnumClass(temp=10, wind=2)"

    def test_set_named_enum(self):
        ec = EnumClass()
        ec.wind = WindEnum.South
        assert bytes(ec) == b"\x00\x02"

        with pytest.raises(KeyError) as excinfo:
            ec.wind = "Norhtwest"
        assert "'Norhtwest'" in str(excinfo)

        with pytest.raises(ValueError) as excinfo:
            ec.wind = 1.2
        assert "1.2 is not a valid WindEnum" in str(excinfo)


@binmap.binmapdataclass
class ConstValues(binmap.BinmapDataclass):
    datatype: binmap.unsignedchar = binmap.constant(0x15)
    status: binmap.unsignedchar = 0


class TestConstValues:
    def test_create_class(self):
        c = ConstValues()
        with pytest.raises(TypeError) as excinfo:
            ConstValues(datatype=0x14, status=1)
        assert "__init__() got an unexpected keyword argument 'datatype'" in str(
            excinfo
        )
        assert c.datatype == 0x15

    def test_set_value(self):
        c = ConstValues(status=1)
        with pytest.raises(AttributeError) as excinfo:
            c.datatype = 0x14
        assert "datatype is a constant" in str(excinfo)
        assert c.datatype == 0x15
        assert c.status == 1
        assert bytes(c) == b"\x15\x01"

    def test_binary_data(self):
        c = ConstValues(b"\x15\x01")
        with pytest.raises(ValueError) as excinfo:
            ConstValues(b"\x14\x01")
        assert "Constant doesn't match binary data" in str(excinfo)
        assert c.datatype == 0x15
        assert c.status == 1


@binmap.binmapdataclass
class AllDatatypes(binmap.BinmapDataclass):
    _pad: binmap.pad = binmap.padding(1)
    char: binmap.char = b"\x00"
    signedchar: binmap.signedchar = 0
    unsignedchar: binmap.unsignedchar = 0
    boolean: binmap.boolean = False
    short: binmap.short = 0
    unsignedshort: binmap.unsignedshort = 0
    integer: binmap.integer = 0
    unsignedint: binmap.unsignedinteger = 0
    long: binmap.long = 0
    unsignedlong: binmap.unsignedlong = 0
    longlong: binmap.longlong = 0
    unsignedlonglong: binmap.unsignedlonglong = 0
    halffloat: binmap.halffloat = 0.0
    floating: binmap.floating = 0.0
    double: binmap.double = 0.0
    string: binmap.string = binmap.stringfield(10)
    pascalstring: binmap.pascalstring = binmap.stringfield(15)


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
            bytes(sc)
            == b"\x00%\xfe\x05\x01\xff\xf9\x00\x11\xff\xff\xff\xf1\x00\x00\x00\x0b\xff\xff\xf6\xf8\x00\x00"
            b"\x08\xa4\xff\xff\xff\xff\xff\xff\xfbD\x00\x00\x00\x00\x00\x00\x11\\C\x00E;\x80\x00D\xf14\x92Bg\x0c"
            b"\xe8helloworld\x0chello pascal\x00\x00"
        )

    def test_with_binarydata(self):
        sc = AllDatatypes(
            b"\x00W\xee\x15\x00\xf4\xf9\x10\x11\xff\xff\xff1\x00\x00\x01\x0b\xff\xff\xe6\xf8\x00\x00\x18"
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
