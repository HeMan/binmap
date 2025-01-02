import struct
from dataclasses import asdict, astuple
from enum import IntEnum, IntFlag

import pytest

import binmap
from binmap import b_types


def test_baseclass():
    b = binmap.BinmapDataclass()
    assert type(b) == binmap.BinmapDataclass
    assert str(b) == "BinmapDataclass()"


def test_baseclass_with_keyword():
    with pytest.raises(TypeError) as excinfo:
        binmap.BinmapDataclass(temp=10)
    assert "got an unexpected keyword argument 'temp'" in str(excinfo)


class Temp(binmap.BinmapDataclass):
    temp: b_types.unsignedchar = 0


class TempHum(binmap.BinmapDataclass):
    temp: b_types.unsignedchar = 0
    humidity: b_types.unsignedchar = 0


def test_different_classes_eq():
    t = Temp(temp=10)
    th = TempHum(temp=10, humidity=60)
    assert t != th
    assert t.temp == th.temp


class Bigendian(binmap.BinmapDataclass):
    value: b_types.longlong = 0


class Littleedian(binmap.BinmapDataclass, byteorder="<"):
    value: b_types.longlong = 0


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
        assert asdict(t) == {"temp": 10}
        assert astuple(t) == (10,)

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
        assert "format requires 0 <= number <= 255" in str(excinfo)

        with pytest.raises(struct.error) as excinfo:
            t.temp = -1
        assert "format requires 0 <= number <= 255" in str(excinfo)

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
        assert asdict(th) == {"temp": 10, "humidity": 60}
        assert astuple(th) == (10, 60)

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


class Strings(binmap.BinmapDataclass):
    identity: b_types.string = binmap.stringfield(10)


class StringWithDefault(binmap.BinmapDataclass):
    defaultstring: b_types.string = binmap.stringfield(10, default=b"hellohello")


class PascalString(binmap.BinmapDataclass):
    p_string: b_types.pascalstring = binmap.stringfield(10)


class TestStrings:
    def test_strings(self):
        s = Strings()
        assert (
            str(s)
            == "Strings(identity=b'\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00')"
        )
        s1 = Strings(identity=b"1234567890")
        assert s1.identity == b"1234567890"
        assert asdict(s1) == {"identity": b"1234567890"}
        assert astuple(s1) == (b"1234567890",)

    def test_defaultstring(self):
        sd = StringWithDefault()
        assert str(sd) == "StringWithDefault(defaultstring=b'hellohello')"
        sd1 = StringWithDefault(defaultstring=b"worldworld")
        assert sd1.defaultstring == b"worldworld"

    def test_pack_pascalstring(self):
        ps = PascalString(p_string=b"hello")
        assert ps.p_string == b"hello"
        assert bytes(ps) == b"\x05hello\x00\x00\x00\x00"


class DynamicPascalString(binmap.BinmapDataclass):
    dyn_pstring: b_types.pascalstring = binmap.dynlength()


class TestDynamicPascalString:
    def test_dynamic_pascalstring(self):
        dps = DynamicPascalString(dyn_pstring=b"Hello")
        assert bytes(dps) == b"\x05hello"


class Pad(binmap.BinmapDataclass):
    temp: b_types.unsignedchar = 0
    pad: b_types.pad = binmap.padding(2)
    humidity: b_types.unsignedchar = 0


class AdvancedPad(binmap.BinmapDataclass):
    temp: b_types.unsignedchar = 0
    _pad1: b_types.pad = binmap.padding(2)
    humidity: b_types.unsignedchar = 0
    _pad2: b_types.pad = binmap.padding(3)
    _pad3: b_types.pad = binmap.padding(1)


class TestPadClass:
    def test_create_pad(self):
        p = Pad(temp=10, humidity=60)
        with pytest.raises(AttributeError) as excinfo:
            p.pad
        assert "Padding (pad) is not readable" in str(excinfo)
        assert p.temp == 10
        assert p.humidity == 60
        assert str(p) == "Pad(temp=10, humidity=60)"
        # TODO: make it work with asdict/astuple
        return
        assert asdict(p) == {"temp": 10, "humidity": 60}
        assert astuple(p) == (10, 60)

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


class FlagEnum(IntFlag):
    R = 4
    W = 2
    X = 1


class EnumClass(binmap.BinmapDataclass):
    temp: b_types.unsignedchar = 0
    wind: b_types.unsignedchar = binmap.enumfield(WindEnum, default=WindEnum.East)


class FlagClass(binmap.BinmapDataclass):
    perm: b_types.unsignedchar = binmap.enumfield(FlagEnum, default=0)


class TestEnumClass:
    def test_create_class(self):
        ec = EnumClass()
        assert ec

    def test_get_enum(self):
        ec = EnumClass(temp=10, wind=2)
        assert ec.wind == WindEnum.South
        assert str(ec) == "EnumClass(temp=10, wind=2)"
        assert asdict(ec) == {"temp": 10, "wind": 2}
        assert astuple(ec) == (10, 2)

    def test_enum_binary(self):
        ec = EnumClass(b"\x0a\x02")
        assert ec.wind == WindEnum.South
        assert str(ec) == "EnumClass(temp=10, wind=2)"

    def test_set_named_enum(self):
        ec = EnumClass()
        ec.wind = WindEnum.South
        assert ec.wind == 2
        assert bytes(ec) == b"\x00\x02"

        with pytest.raises(KeyError) as excinfo:
            ec.wind = "Norhtwest"
        assert "'Norhtwest'" in str(excinfo)

        with pytest.raises(ValueError) as excinfo:
            ec.wind = 1.2
        assert "1.2 is not a valid WindEnum" in str(excinfo)

    def test_set_numeric_enum(self):
        ec = EnumClass()
        ec.wind = 2
        assert ec.wind == WindEnum.South
        assert bytes(ec) == b"\x00\x02"
        assert str(ec) == "EnumClass(temp=0, wind=2)"


class TestFlagClass:
    def test_create_class(self):
        fc = FlagClass()
        assert fc

    def test_get_enum(self):
        fc = FlagClass(perm=6)
        assert fc.perm & FlagEnum.R
        assert fc.perm & (FlagEnum.R | FlagEnum.W)
        assert not fc.perm & FlagEnum.X
        assert str(fc) == "FlagClass(perm=6)"
        assert asdict(fc) == {"perm": 6}
        assert astuple(fc) == (6,)

    def test_enum_binary(self):
        fc = FlagClass(b"\x03")
        assert fc.perm & FlagEnum.W
        assert fc.perm & (FlagEnum.W | FlagEnum.X)
        assert not fc.perm & FlagEnum.R


class ConstValues(binmap.BinmapDataclass):
    datatype: b_types.unsignedchar = binmap.constant(0x15)
    status: b_types.unsignedchar = 0


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
        assert asdict(c) == {"datatype": 0x15, "status": 1}

    def test_binary_data(self):
        c = ConstValues(b"\x15\x01")
        with pytest.raises(ValueError) as excinfo:
            ConstValues(b"\x14\x01")
        assert "Constant doesn't match binary data" in str(excinfo)
        assert c.datatype == 0x15
        assert c.status == 1


class AllDatatypes(binmap.BinmapDataclass):
    _pad: b_types.pad = binmap.padding(1)
    char: b_types.char = b"\x00"
    signedchar: b_types.signedchar = 0
    unsignedchar: b_types.unsignedchar = 0
    boolean: b_types.boolean = False
    short: b_types.short = 0
    unsignedshort: b_types.unsignedshort = 0
    integer: b_types.integer = 0
    unsignedint: b_types.unsignedinteger = 0
    long: b_types.long = 0
    unsignedlong: b_types.unsignedlong = 0
    longlong: b_types.longlong = 0
    unsignedlonglong: b_types.unsignedlonglong = 0
    halffloat: b_types.halffloat = 0.0
    floating: b_types.floating = 0.0
    double: b_types.double = 0.0
    string: b_types.string = binmap.stringfield(10)
    pascalstring: b_types.pascalstring = binmap.stringfield(15)


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
        assert (
            str(sc)
            == "AllDatatypes(char=b'%', signedchar=-2, unsignedchar=5, boolean=True, short=-7, unsignedshort=17, integer=-15, unsignedint=11, long=-2312, unsignedlong=2212, longlong=-1212, unsignedlonglong=4444, halffloat=3.5, floating=3000.0, double=1.3e+24, string=b'helloworld', pascalstring=b'hello pascal')"  # noqa: E501
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


class TestInheritance:
    def test_simple_inheritance(self):
        class Child(Temp):
            humidity: b_types.unsignedchar = 0

        ch = Child()
        ch.temp = 10
        ch.humidity = 40

        assert ch.temp == 10
        assert ch.humidity == 40

        assert bytes(ch) == b"\x0a\x28"
        assert asdict(ch) == {"temp": 10, "humidity": 40}
        assert astuple(ch) == (10, 40)

    def test_simple_inheritance_binary(self):
        class Child(Temp):
            humidity: b_types.unsignedchar = 0

        ch = Child(b"\x10\x30")
        assert ch.temp == 16
        assert ch.humidity == 48

    def test_const_inheritance(self):
        class Child(ConstValues):
            humidity: b_types.unsignedchar = 0

        ch = Child()
        with pytest.raises(AttributeError) as excinfo:
            ch.datatype = 14
        assert "datatype is a constant" in str(excinfo)
        ch.status = 1
        ch.humidity = 40

        assert ch.datatype == 0x15
        assert ch.status == 1
        assert ch.humidity == 40
        assert bytes(ch) == b"\x15\x01\x28"

    def test_const_inheritance_binary(self):
        class Child(ConstValues):
            humidity: b_types.unsignedchar = 0

        ch = Child(b"\x15\x05\x30")
        assert ch.datatype == 0x15
        assert ch.status == 5
        assert ch.humidity == 48

    def test_enum_inheritanec(self):
        class Child(EnumClass):
            humidity: b_types.unsignedchar = 0

        ch = Child()
        ch.temp = 10
        ch.wind = WindEnum.West
        ch.humidity = 40

        assert ch.temp == 10
        assert ch.wind == WindEnum.West
        assert ch.humidity == 40
        assert bytes(ch) == b"\x0a\x03\x28"

    def test_enum_inheritance_binary(self):
        class Child(EnumClass):
            humidity: b_types.unsignedchar = 0

        ch = Child(b"\x12\x01\x25")
        assert ch.temp == 18
        assert ch.wind == WindEnum.East
        assert ch.humidity == 37


class AutoLength(binmap.BinmapDataclass):
    length: b_types.unsignedchar = binmap.autolength()
    temp: b_types.signedchar = 0


class AutoLengthOffset(binmap.BinmapDataclass):
    length: b_types.unsignedchar = binmap.autolength(offset=-1)
    temp: b_types.signedchar = 0


class AutoLengthOffsetPositive(binmap.BinmapDataclass):
    length: b_types.unsignedchar = binmap.autolength(offset=1)
    temp: b_types.signedchar = 0


class TestAutolength:
    def test_autolength(self):
        al = AutoLength()
        al.temp = 10

        assert al.length == 2
        assert str(al) == "AutoLength(length=2, temp=10)"
        assert asdict(al) == {"length": 2, "temp": 10}
        assert astuple(al) == (2, 10)
        assert bytes(al) == b"\x02\x0a"

    def test_autolength_bin(self):
        with pytest.raises(ValueError) as excinfo:
            AutoLength(b"\x01\x0a")
        assert "Length doesn't match" in str(excinfo)
        al = AutoLength(b"\x02\x0a")
        assert al.length == 2
        assert al.temp == 10

    def test_autolength_inheritance(self):
        class Child(AutoLength):
            humidity: b_types.unsignedchar = 0

        alc = Child()
        alc.temp = 20
        alc.humidity = 40
        assert bytes(alc) == b"\x03\x14\x28"

        assert alc.length == 3

    def test_autolength_offset(self):
        alo = AutoLengthOffset()
        alo.temp = 10

        assert alo.length == 1
        assert bytes(alo) == b"\x01\n"

        alop = AutoLengthOffsetPositive()
        alop.temp = 10
        assert bytes(alop) == b"\x03\n"

        assert alop.length == 3


class CalculatedField(binmap.BinmapDataclass):
    temp: b_types.signedchar = 0
    hum: b_types.unsignedchar = 0

    def chk(self) -> b_types.unsignedchar:
        return (self.temp + self.hum) & 0xFF

    checksum: b_types.unsignedchar = binmap.calculatedfield(chk)


class CalculatedFieldLast(binmap.BinmapDataclass):
    temp: b_types.signedchar = 0

    def chk_last(self):
        checksum = 0
        for k, v in self.__dict__.items():
            if k.startswith("_") or callable(v):
                continue
            checksum += v
        return checksum & 0xFF

    checksum: b_types.unsignedchar = binmap.calculatedfield(chk_last, last=True)
    hum: b_types.unsignedchar = 0


class TestCalculatedField:
    def test_calculated_field(self):
        cf = CalculatedField()
        cf.temp = -27
        cf.hum = 10

        assert str(cf) == "CalculatedField(temp=-27, hum=10, checksum=239)"
        assert asdict(cf) == {"temp": -27, "hum": 10, "checksum": 239}
        assert cf.checksum == 239
        assert bytes(cf) == b"\xe5\x0a\xef"

    def test_calculated_field_binary(self):
        cf = CalculatedField(b"\xe2\x12\xf4")
        assert cf.temp == -30
        assert cf.hum == 18
        assert cf.checksum == 244

        with pytest.raises(ValueError) as excinfo:
            CalculatedField(b"\xe4\x18\x00")
        assert "Wrong calculated value" in str(excinfo)

    def test_calculated_field_set(self):
        cf = CalculatedField()
        with pytest.raises(AttributeError) as excinfo:
            cf.checksum = 10
        assert "Can't set a calculated field" in str(excinfo)

    def test_calculated_field_last(self):

        cfl = CalculatedFieldLast()
        cfl.temp = 10
        cfl.hum = 20

        assert cfl.checksum == 30
        assert bytes(cfl) == b"\x0a\x14\x1e"

    def test_calculated_field_last_inherit(self):
        class CalculatedFieldLastInherit(CalculatedFieldLast):
            lux: b_types.unsignedinteger = 0

        cfli = CalculatedFieldLastInherit()
        cfli.temp = 10
        cfli.hum = 20
        cfli.lux = 401
        assert bytes(cfli) == b"\x0a\x14\x00\x00\x01\x91\xaf"

        with pytest.raises(ValueError) as excinfo:
            CalculatedFieldLastInherit(b"\x0b\x20\x00\x00\x01\x30\x00")
        assert "Wrong calculated value" in str(excinfo)

    def test_calculated_field_multi_last(self):
        with pytest.raises(ValueError) as excinfo:

            class CalculatedFieldMultiLast(binmap.BinmapDataclass):
                temp: b_types.unsignedchar = 0

                def chk(self):
                    return 0

                checksum1: b_types.unsignedchar = binmap.calculatedfield(chk, last=True)
                checksum2: b_types.unsignedchar = binmap.calculatedfield(chk, last=True)

        assert "Can't have more than one last" in str(excinfo)

    def test_calculated_field_multi_last_inherit(self):
        with pytest.raises(ValueError) as excinfo:

            class CalculatedFieldMultiLastInherit(CalculatedFieldLast):
                def chk2(self):
                    return 0

                checksum2: b_types.unsignedchar = binmap.calculatedfield(
                    chk2, last=True
                )

        assert "Can't have more than one last" in str(excinfo)
