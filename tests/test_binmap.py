import copy
import pickle
import struct
from dataclasses import asdict, astuple, fields, replace
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

    def test_value_bounds_in_constructor(self):
        with pytest.raises(struct.error) as excinfo:
            Temp(temp=256)
        assert "format requires 0 <= number <= 255" in str(excinfo)

    def test_wrong_type(self):
        t = Temp()
        with pytest.raises(struct.error) as excinfo:
            t.temp = "10"
        assert "required argument is not an integer" in str(excinfo)

        with pytest.raises(struct.error) as excinfo:
            t.temp = 1.5
        assert "required argument is not an integer" in str(excinfo)

    def test_failed_assignment_keeps_value(self):
        t = Temp(temp=5)
        with pytest.raises(struct.error):
            t.temp = 256
        assert t.temp == 5
        assert bytes(t) == b"\x05"

    def test_wrong_length_binarydata(self):
        with pytest.raises(struct.error) as excinfo:
            Temp(b"\x0a\x0b")
        assert "unpack requires a buffer of 1 bytes" in str(excinfo)

        t = Temp()
        with pytest.raises(struct.error) as excinfo:
            t.frombytes(b"")
        assert "unpack requires a buffer of 1 bytes" in str(excinfo)

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


class TestUnknownAttributes:
    def test_assign_unknown_attribute(self):
        th = TempHum(temp=10, humidity=60)
        with pytest.raises(AttributeError) as excinfo:
            th.hum = 40
        assert "TempHum has no field 'hum'" in str(excinfo)
        # name and obj let Python suggest similar fields for typos, e.g.
        # "humidty" -> "Did you mean: 'humidity'?"
        assert excinfo.value.name == "hum"
        assert excinfo.value.obj is th
        assert not hasattr(th, "hum")
        assert bytes(th) == b"\x0a\x3c"

    def test_assign_unknown_attribute_baseclass(self):
        b = binmap.BinmapDataclass()
        with pytest.raises(AttributeError) as excinfo:
            b.temp = 10
        assert "BinmapDataclass has no field 'temp'" in str(excinfo)

    def test_assign_unknown_attribute_inherited(self):
        class Child(Temp):
            humidity: b_types.unsignedchar = 0

        ch = Child()
        ch.temp = 10
        ch.humidity = 60
        with pytest.raises(AttributeError) as excinfo:
            ch.hum = 40
        assert "Child has no field 'hum'" in str(excinfo)
        assert bytes(ch) == b"\x0a\x3c"

    def test_assign_padding_is_ignored(self):
        p = Pad(temp=10, humidity=60)
        p.pad = 5
        assert bytes(p) == b"\x0a\x00\x00\x3c"

    def test_property_setter(self):
        class Celsius(binmap.BinmapDataclass):
            raw: b_types.short = 0

            @property
            def celsius(self):
                return self.raw / 10

            @celsius.setter
            def celsius(self, value):
                self.raw = round(value * 10)

        c = Celsius()
        c.celsius = 21.5
        assert c.raw == 215
        assert bytes(c) == b"\x00\xd7"

    def test_copy_and_pickle(self):
        th = TempHum(temp=10, humidity=60)
        for clone in (copy.copy(th), copy.deepcopy(th), pickle.loads(pickle.dumps(th))):
            assert clone == th
            assert bytes(clone) == b"\x0a\x3c"
            clone.temp = 11
            with pytest.raises(AttributeError):
                clone.hum = 40


class Strings(binmap.BinmapDataclass):
    identity: b_types.string = binmap.stringfield(10)


class StringWithDefault(binmap.BinmapDataclass):
    defaultstring: b_types.string = binmap.stringfield(10, default=b"hellohello")


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

    def test_asdict_astuple_parsed_data(self):
        p = Pad(b"\x0a\x10\x20\x3c")
        assert asdict(p) == {"temp": 10, "humidity": 60}
        assert astuple(p) == (10, 60)

    def test_advanced_asdict_astuple(self):
        p = AdvancedPad(temp=10, humidity=60)
        assert asdict(p) == {"temp": 10, "humidity": 60}
        assert astuple(p) == (10, 60)

    def test_inherited_padding_asdict_astuple(self):
        class Child(Pad):
            _pad2: b_types.pad = binmap.padding(1)
            lux: b_types.unsignedshort = 0

        c = Child(temp=10, humidity=60, lux=400)
        assert bytes(c) == b"\x0a\x00\x00\x3c\x00\x01\x90"
        assert asdict(c) == {"temp": 10, "humidity": 60, "lux": 400}
        assert astuple(c) == (10, 60, 400)

    def test_replace(self):
        p = Pad(temp=10, humidity=60)
        p2 = replace(p, temp=20)
        assert str(p2) == "Pad(temp=20, humidity=60)"
        assert bytes(p2) == b"\x14\x00\x00\x3c"

    def test_fields(self):
        # Instances hide padding so dataclass helpers never try to read it. The
        # class keeps every field: the wire format and subclasses need them.
        assert [f.name for f in fields(Pad(temp=1))] == ["temp", "humidity"]
        assert [f.name for f in fields(Pad)] == ["temp", "pad", "humidity"]

    def test_compare(self):
        assert Pad(temp=10, humidity=60) == Pad(temp=10, humidity=60)
        assert Pad(temp=10, humidity=60) != Pad(temp=11, humidity=60)
        # The padding bytes aren't kept, so they can't make instances differ
        assert Pad(b"\x0a\x10\x20\x3c") == Pad(b"\x0a\x00\x00\x3c")

    def test_advanced_compare(self):
        assert AdvancedPad(temp=10, humidity=60) == AdvancedPad(temp=10, humidity=60)
        assert AdvancedPad(temp=10, humidity=60) != AdvancedPad(temp=10, humidity=61)

    def test_inherited_padding_compare(self):
        class Child(Pad):
            _pad2: b_types.pad = binmap.padding(1)
            lux: b_types.unsignedshort = 0

        assert Child(temp=1, lux=2) == Child(temp=1, lux=2)
        assert Child(temp=1, lux=2) != Child(temp=1, lux=3)


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


INTEGER_TYPES = [
    (b_types.signedchar, "b"),
    (b_types.unsignedchar, "B"),
    (b_types.short, "h"),
    (b_types.unsignedshort, "H"),
    (b_types.integer, "i"),
    (b_types.unsignedinteger, "I"),
    (b_types.long, "l"),
    (b_types.unsignedlong, "L"),
    (b_types.longlong, "q"),
    (b_types.unsignedlonglong, "Q"),
]


class TestIntegerBounds:
    @pytest.mark.parametrize("byteorder", [">", "<"])
    @pytest.mark.parametrize("datatype, code", INTEGER_TYPES)
    def test_assignment_accepts_exactly_what_packs(self, datatype, code, byteorder):
        class Value(binmap.BinmapDataclass, byteorder=byteorder):
            v: datatype = 0

        bits = 8 * struct.calcsize(byteorder + code)
        if code.islower():  # signed
            lowest, highest = -(2 ** (bits - 1)), 2 ** (bits - 1) - 1
        else:
            lowest, highest = 0, 2**bits - 1

        value = Value()
        for valid in (lowest, highest):
            value.v = valid
            assert struct.unpack(byteorder + code, bytes(value)) == (valid,)
        for invalid in (lowest - 1, highest + 1):
            with pytest.raises(struct.error):
                value.v = invalid
            with pytest.raises(struct.error):
                Value(v=invalid)
        assert value.v == highest

    def test_native_byteorder_uses_native_sizes(self):
        class Native(binmap.BinmapDataclass, byteorder="@"):
            v: b_types.long = 0

        highest = 2 ** (8 * struct.calcsize("@l") - 1) - 1
        native = Native(v=highest)
        assert bytes(native) == struct.pack("@l", highest)
        with pytest.raises(struct.error):
            native.v = highest + 1


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

    def test_inherited_value_bounds(self):
        class Child(Temp):
            humidity: b_types.unsignedchar = 0

        ch = Child()
        with pytest.raises(struct.error) as excinfo:
            ch.temp = 256
        assert "format requires 0 <= number <= 255" in str(excinfo)

        with pytest.raises(struct.error) as excinfo:
            Child(temp=-1)
        assert "format requires 0 <= number <= 255" in str(excinfo)

    def test_multilevel_inheritance(self):
        class Child(Temp):
            humidity: b_types.unsignedchar = 0

        class Grandchild(Child):
            lux: b_types.unsignedshort = 0

        gc = Grandchild(temp=1, humidity=2, lux=3)
        assert bytes(gc) == b"\x01\x02\x00\x03"

        with pytest.raises(struct.error) as excinfo:
            gc.temp = 256
        assert "format requires 0 <= number <= 255" in str(excinfo)

        with pytest.raises(struct.error) as excinfo:
            gc.humidity = -1
        assert "format requires 0 <= number <= 255" in str(excinfo)

        with pytest.raises(struct.error) as excinfo:
            gc.lux = 70000
        # The upper bound is spelled differently on Python <= 3.10
        assert "format requires 0 <= number <=" in str(excinfo)

    def test_subclass_without_own_fields(self):
        class Sub(Temp):
            pass

        s = Sub(temp=10)
        assert bytes(s) == b"\x0a"
        assert Sub(b"\x14").temp == 20

        with pytest.raises(struct.error) as excinfo:
            s.temp = 256
        assert "format requires 0 <= number <= 255" in str(excinfo)

    def test_redeclared_field_uses_child_type(self):
        class Wider(Temp):
            temp: b_types.unsignedshort = 0

        w = Wider(temp=300)
        assert bytes(w) == b"\x01\x2c"
        assert Wider(b"\x01\x2c").temp == 300

        with pytest.raises(struct.error) as excinfo:
            w.temp = 70000
        assert "format requires 0 <= number <=" in str(excinfo)

    def test_multiple_inheritance(self):
        class First(binmap.BinmapDataclass):
            first: b_types.unsignedchar = 0

        class Second(binmap.BinmapDataclass):
            second: b_types.unsignedshort = 0

        class Both(First, Second):
            own: b_types.unsignedchar = 0

        # dataclasses collect fields in reverse MRO order, so the last base's
        # fields come first on the wire.
        b = Both(first=1, second=2, own=3)
        assert bytes(b) == b"\x00\x02\x01\x03"
        assert astuple(Both(b"\x00\x02\x01\x03")) == (2, 1, 3)

        with pytest.raises(struct.error) as excinfo:
            b.first = 256
        assert "format requires 0 <= number <= 255" in str(excinfo)

        with pytest.raises(struct.error) as excinfo:
            b.second = 70000
        assert "format requires 0 <= number <=" in str(excinfo)

    def test_multiple_inheritance_conflicting_types_without_own_fields(self):
        class Short(binmap.BinmapDataclass):
            value: b_types.unsignedshort = 0

        class Char(binmap.BinmapDataclass):
            value: b_types.unsignedchar = 0

        class Both(Short, Char):
            pass

        # Short comes first in the MRO, so value is an unsignedshort
        b = Both(value=300)
        assert bytes(b) == b"\x01\x2c"
        assert Both(b"\x01\x2c").value == 300

        with pytest.raises(struct.error) as excinfo:
            b.value = 70000
        assert "format requires 0 <= number <=" in str(excinfo)

    def test_multiple_inheritance_conflicting_types(self):
        class Short(binmap.BinmapDataclass):
            value: b_types.unsignedshort = 0

        class Char(binmap.BinmapDataclass):
            value: b_types.unsignedchar = 0

        class Both(Short, Char):
            own: b_types.unsignedchar = 0

        # Short comes first in the MRO, so value is an unsignedshort
        b = Both(value=300, own=1)
        assert bytes(b) == b"\x01\x2c\x01"
        assert Both(b"\x01\x2c\x01").value == 300


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


class CalculatedFieldMiddle(binmap.BinmapDataclass):
    temp: b_types.signedchar = 0

    def chk(self) -> b_types.unsignedchar:
        return (self.temp + self.hum) & 0xFF

    # Packed between temp and hum, but reads hum too
    checksum: b_types.unsignedchar = binmap.calculatedfield(chk)
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

    def test_calculated_field_last_binary(self):
        # checksum is declared before hum but packed after it
        cfl = CalculatedFieldLast(b"\x0a\x14\x1e")
        assert (cfl.temp, cfl.hum, cfl.checksum) == (10, 20, 30)
        assert bytes(cfl) == b"\x0a\x14\x1e"

    def test_calculated_field_last_inherit_binary(self):
        class CalculatedFieldLastInherit(CalculatedFieldLast):
            lux: b_types.unsignedinteger = 0

        c = CalculatedFieldLastInherit(b"\x0a\x14\x00\x00\x01\x91\xaf")
        assert (c.temp, c.hum, c.lux, c.checksum) == (10, 20, 401, 0xAF)

    def test_calculated_field_last_wrong_checksum(self):
        # The checksum byte (0x63) is wrong. The hum byte (0x0a) happens to
        # equal the checksum of the fields before it, so comparing the checksum
        # against the wrong byte would accept this corrupt data.
        with pytest.raises(ValueError) as excinfo:
            CalculatedFieldLast(b"\x0a\x0a\x63")
        assert "Wrong calculated value" in str(excinfo)

    def test_calculated_field_middle_binary(self):
        cfm = CalculatedFieldMiddle(b"\x0a\x1e\x14")
        assert (cfm.temp, cfm.checksum, cfm.hum) == (10, 30, 20)
        assert bytes(cfm) == b"\x0a\x1e\x14"

    def test_calculated_field_middle_wrong_checksum(self):
        # The checksum byte (0x0a) only matches if hum is still 0, so checking
        # it before hum (0x63) is set would accept this corrupt data.
        with pytest.raises(ValueError) as excinfo:
            CalculatedFieldMiddle(b"\x0a\x0a\x63")
        assert "Wrong calculated value" in str(excinfo)

    def test_failed_frombytes_keeps_values(self):
        cf = CalculatedField(temp=-27, hum=10)
        with pytest.raises(ValueError) as excinfo:
            cf.frombytes(b"\x01\x02\x00")  # checksum should be 0x03
        assert "Wrong calculated value" in str(excinfo)
        assert (cf.temp, cf.hum, cf.checksum) == (-27, 10, 239)
        assert bytes(cf) == b"\xe5\x0a\xef"

    def test_calculated_field_follows_changes(self):
        cf = CalculatedField(temp=-27, hum=10)
        assert cf.checksum == 239
        cf.temp = 5
        assert cf.checksum == 15
        cf.hum = 200
        assert cf.checksum == 205
        assert bytes(cf) == b"\x05\xc8\xcd"
        assert asdict(cf) == {"temp": 5, "hum": 200, "checksum": 205}
        assert CalculatedField(bytes(cf)) == cf

    def test_calculated_field_follows_changes_after_parsing(self):
        cf = CalculatedField(b"\xe2\x12\xf4")
        cf.hum = 20
        assert cf.checksum == 246  # (-30 + 20) & 0xFF
        assert bytes(cf) == b"\xe2\x14\xf6"
        assert CalculatedField(bytes(cf)) == cf

    def test_calculated_field_follows_frombytes(self):
        cf = CalculatedField(temp=1, hum=2)
        assert cf.checksum == 3
        cf.frombytes(b"\x0a\x14\x1e")
        assert cf.checksum == 30
        cf.temp = 11
        assert cf.checksum == 31
        assert bytes(cf) == b"\x0b\x14\x1f"

    def test_calculated_field_last_follows_changes(self):
        cfl = CalculatedFieldLast(b"\x0a\x14\x1e")
        cfl.temp = 1
        cfl.hum = 2
        assert cfl.checksum == 3
        assert bytes(cfl) == b"\x01\x02\x03"
        assert CalculatedFieldLast(bytes(cfl)).checksum == 3

    def test_calculated_field_middle_follows_changes(self):
        cfm = CalculatedFieldMiddle(b"\x0a\x1e\x14")
        cfm.hum = 30
        assert cfm.checksum == 40
        assert bytes(cfm) == b"\x0a\x28\x1e"
        assert CalculatedFieldMiddle(bytes(cfm)).hum == 30

    def test_calculated_field_after_rejected_change(self):
        cf = CalculatedField(temp=10, hum=20)
        with pytest.raises(struct.error):
            cf.hum = 256
        assert cf.checksum == 30
        assert bytes(cf) == b"\x0a\x14\x1e"

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


class TestInvalidClassDefinition:
    def test_unsupported_type(self):
        with pytest.raises(KeyError):

            class UnsupportedType(binmap.BinmapDataclass):
                values: list = None

    def test_undefined_annotation(self):
        # Python <= 3.13 fails while running the class body. Python 3.14+
        # defers annotations (PEP 649), so it fails when __init_subclass__
        # resolves them instead.
        with pytest.raises(NameError) as excinfo:

            class UndefinedAnnotation(binmap.BinmapDataclass):
                value: Undefined = 0  # noqa: F821

        assert "name 'Undefined' is not defined" in str(excinfo)


class TestClassBookkeeping:
    def test_instantiation_does_not_change_class_state(self):
        class Fresh(binmap.BinmapDataclass):
            temp: b_types.unsignedchar = 0
            hum: b_types.unsignedchar = 0

        def class_state():
            # binmap's per-class bookkeeping lives in name-mangled attributes.
            # Copy mutable values so later changes to them show up.
            return {
                name: value.copy() if hasattr(value, "copy") else value
                for name, value in vars(Fresh).items()
                if name.startswith("_BinmapDataclass__")
            }

        before = class_state()
        assert before  # guard against the attribute prefix changing
        for _ in range(3):
            Fresh()
            Fresh(b"\x01\x02")
        assert class_state() == before

    def test_parse_after_many_instances(self):
        for _ in range(1000):
            TempHum()
        th = TempHum(b"\x0a\x3c")
        assert (th.temp, th.humidity) == (10, 60)

    def test_parent_and_child_parse_independently(self):
        class Child(TempHum):
            lux: b_types.unsignedshort = 0

        for _ in range(3):
            TempHum()
            Child()
        assert astuple(TempHum(b"\x0a\x3c")) == (10, 60)
        assert astuple(Child(b"\x0a\x3c\x01\x90")) == (10, 60, 400)
