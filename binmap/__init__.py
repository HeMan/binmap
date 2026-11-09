import dataclasses
import struct
from enum import IntEnum, IntFlag
from functools import partial
from typing import (
    Callable,
    ClassVar,
    Dict,
    FrozenSet,
    List,
    Tuple,
    Type,
    Union,
    get_type_hints,
)

from binmap import types as b_types


class BaseDescriptor:
    """Base class for all descriptors

    :param name: Variable name"""

    def __set_name__(self, obj, name):
        self.name = name

    def __init__(self, name=""):
        self.name = name


class BinField(BaseDescriptor):
    """BinField descriptor tries to pack it into a struct before setting the
    value as a bounds checker"""

    def __get__(self, obj, owner):
        return obj.__dict__[self.name]

    def __set__(self, obj, value):
        # The class's type hints, resolved once by __init_subclass__ with
        # get_type_hints(cls). Never resolve them on the instance: Python 3.14+
        # (PEP 649) rejects that. The class lookup walks the MRO, so inherited
        # fields are found too.
        cls = type(obj)
        type_hints = cls._BinmapDataclass__typehints
        if self.name not in type_hints:
            raise ValueError(self.name)
        # Pack with the class's byte order, like bytes() does. A bare code would
        # use native sizes, which differ from the standard ones (e.g. "l" is 8
        # bytes natively on 64-bit Linux but 4 bytes with ">" or "<").
        code = datatypemapping[type_hints[self.name]][1]
        struct.pack(cls._BinmapDataclass__byteorder + code, value)
        obj.__dict__[self.name] = value


class StringField(BinField):
    """StringField descriptor is a BinField for string and pascalstring fields
    that also rejects values longer than the field holds, which struct.pack
    would otherwise cut silently.

    :raises struct.error: when the value is too long"""

    def __init__(self, name, maxlength):
        super().__init__(name)
        self.maxlength = maxlength

    def __set__(self, obj, value):
        if isinstance(value, (bytes, bytearray)) and len(value) > self.maxlength:
            raise struct.error(
                f"{self.name} holds at most {self.maxlength} bytes, got {len(value)}"
            )
        super().__set__(obj, value)


class PaddingField(BaseDescriptor):
    """PaddingField descriptor is used to "pad" data with values unused for real data

    :raises AttributeError: when trying to read, since it's only padding."""

    def __get__(self, obj, owner):
        """Getting values fails"""
        raise AttributeError(f"Padding ({self.name}) is not readable")

    def __set__(self, obj, value):
        """Setting values does nothing"""


class EnumField(BinField):
    """EnumField descriptor uses "enum" to map to and from strings. Accepts
    both strings and values when setting. Only values that has a corresponding
    string is allowed."""

    def __set__(self, obj, value):
        datafieldsmap = {f.name: f for f in dataclasses.fields(obj)}
        if isinstance(value, str):
            datafieldsmap[self.name].metadata["enum"][value]
        else:
            datafieldsmap[self.name].metadata["enum"](value)
        obj.__dict__[self.name] = value


class ConstField(BinField):
    """ConstField descriptor keeps it's value

    :raises AttributeError: Since it's a constant it raises and error when
      trying to set"""

    def __set__(self, obj, value):
        if self.name in obj.__dict__:
            raise AttributeError(f"{self.name} is a constant")
        obj.__dict__[self.name] = value


class CalculatedField(BinField):
    """CalculatedField calls a function when it's converted to bytes

    :raises AttributeError: Trying to set the value is not allowed"""

    def __init__(self, name, function):
        self.name = name
        self.function = function

    def __get__(self, obj, owner):
        return self.function(obj)

    def __set__(self, obj, value):
        if self.name in obj.__dict__:
            raise AttributeError("Can't set a calculated field")


datatypemapping: Dict[type, Tuple[Type[BaseDescriptor], str]] = {
    b_types.char: (BinField, "c"),
    b_types.signedchar: (BinField, "b"),
    b_types.unsignedchar: (BinField, "B"),
    b_types.boolean: (BinField, "?"),
    bool: (BinField, "?"),
    b_types.short: (BinField, "h"),
    b_types.unsignedshort: (BinField, "H"),
    b_types.integer: (BinField, "i"),
    int: (BinField, "i"),
    b_types.unsignedinteger: (BinField, "I"),
    b_types.long: (BinField, "l"),
    b_types.unsignedlong: (BinField, "L"),
    b_types.longlong: (BinField, "q"),
    b_types.unsignedlonglong: (BinField, "Q"),
    b_types.halffloat: (BinField, "e"),
    b_types.floating: (BinField, "f"),
    float: (BinField, "f"),
    b_types.double: (BinField, "d"),
    b_types.string: (BinField, "s"),
    str: (BinField, "s"),
    b_types.pascalstring: (BinField, "p"),
    b_types.pad: (PaddingField, "x"),
}

# Type hints for fixed-length byte strings, which take their length from
# stringfield() and use StringField to reject values that don't fit.
STRING_TYPES = (b_types.string, b_types.pascalstring, str)


def padding(length: int = 1) -> dataclasses.Field:
    """
    Field generator function for padding elements

    :param int lenght: Number of bytes of padded field
    :return: dataclass field
    """
    # compare=False: padding can't be read, so the generated __eq__ must skip it
    return dataclasses.field(default=length, repr=False, compare=False, metadata={"padding": True})  # type: ignore


def constant(value: Union[int, float, str]) -> dataclasses.Field:
    """
    Field generator function for constant elements

    :param value: Constant value for the field.
    :return: dataclass field
    """
    return dataclasses.field(default=value, init=False, metadata={"constant": True})  # type: ignore


def autolength(offset: int = 0) -> dataclasses.Field:
    """
    Field generator function for autolength fields

    :param offset: offset for the lenght calculation
    :return: dataclass field
    """
    return dataclasses.field(default=offset, init=False, metadata={"autolength": True})  # type: ignore


def stringfield(length: int = 1, default: bytes = b"") -> dataclasses.Field:
    """
    Field generator function for string and pascalstring fields.

    :param int length: size of the field in bytes. A pascalstring uses one of
      them for its length, so it holds at most ``length - 1`` bytes (and never
      more than 255).
    :param bytes default: default value. Left out (or ``b""``), a string
      defaults to ``length`` zero bytes and a pascalstring to ``b""``.
    :return: dataclass field
    """
    autodefault = default == b""
    if autodefault:
        default = b"\x00" * length
    return dataclasses.field(default=default, metadata={"length": length, "autodefault": autodefault})  # type: ignore


def enumfield(
    enumclass: Union[IntEnum, IntFlag], default: Union[IntEnum, IntFlag, int, None] = None
) -> dataclasses.Field:
    """
    Field generator function for enum field

    :param IntEnum enumclass: Class with enums.
    :param IntEnum default: default value
    :return: dataclass field
    """
    return dataclasses.field(default=default, metadata={"enum": enumclass})  # type: ignore


def calculatedfield(function: Callable, last=False) -> dataclasses.Field:
    """
    Field generator function for calculated fields

    :param Callable function: function that calculates the field.
    :return: dataclass field
    """
    return dataclasses.field(default=0, metadata={"function": function, "last": last})  # type: ignore


class _FieldsWithoutPaddingOnInstances:
    """
    Replaces ``__dataclass_fields__`` on every ``BinmapDataclass`` subclass.

    ``dataclasses.asdict()``, ``astuple()`` and ``replace()`` read every field
    that ``dataclasses.fields(instance)`` returns. Padding fields can't be read,
    so through an instance this returns the fields without padding. Through the
    class it returns all fields: ``dataclasses`` needs them to build subclasses,
    and binmap needs them for the struct format.
    """

    def __init__(self, fields: Dict[str, dataclasses.Field]):
        self.fields = fields
        self.instance_fields = {
            name: field_
            for name, field_ in fields.items()
            if "padding" not in field_.metadata
        }

    def __get__(self, obj, owner):
        return self.fields if obj is None else self.instance_fields


@dataclasses.dataclass
class BinmapDataclass:
    """
    Dataclass that does the converting to and from binary data
    """

    __binarydata: dataclasses.InitVar[bytes] = b""
    __datafields: ClassVar[Tuple[str, ...]]
    __datafieldsmap: ClassVar[Dict[str, dataclasses.Field]]
    __formatstring: ClassVar[str]
    __byteorder: ClassVar[str]
    __typehints: ClassVar[Dict[str, type]]
    __fieldnames: ClassVar[FrozenSet[str]] = frozenset()

    def __init_subclass__(cls, byteorder: str = ">"):
        """
        Subclass initiator. This makes the inheriting class a dataclass.
        :param str byteorder: byteorder for binary data
        """
        # stringfield() can't tell a string from a pascalstring, so it fills an
        # unspecified default with `length` zero bytes. A pascalstring holds one
        # byte less, so start it empty instead, before dataclass() captures the
        # defaults.
        own_hints = get_type_hints(cls)
        for name, value in vars(cls).items():
            if (
                isinstance(value, dataclasses.Field)
                and value.metadata.get("autodefault")
                and own_hints.get(name) is b_types.pascalstring
            ):
                value.default = b""
        dataclasses.dataclass(cls)
        setattr(
            cls,
            "__dataclass_fields__",
            _FieldsWithoutPaddingOnInstances(cls.__dict__["__dataclass_fields__"]),
        )
        type_hints = get_type_hints(cls)

        cls.__fieldnames = frozenset(f.name for f in dataclasses.fields(cls))
        cls.__typehints = type_hints
        cls.__byteorder = byteorder
        cls.__formatstring = byteorder
        cls.__datafieldsmap = {f.name: f for f in dataclasses.fields(cls)}
        # Names of the fields that have a value in the struct (everything but
        # padding), in wire order: the format string's order, with the "last"
        # field moved to the end. Built once per class; instances never change it.
        datafields: List[str] = []
        lastname = ""

        lastfield = ""
        for field_ in dataclasses.fields(cls):
            if field_.name.startswith("_BinmapDataclass__"):
                continue
            _base, _type = datatypemapping[type_hints[field_.name]]
            if "constant" in field_.metadata:
                _base = ConstField
            elif "enum" in field_.metadata:
                _base = EnumField
            elif "autolength" in field_.metadata:
                _base = ConstField
            elif "function" in field_.metadata:
                _base = partial(CalculatedField, function=field_.metadata["function"])  # type: ignore
            elif type_hints[field_.name] in STRING_TYPES:
                length = field_.metadata["length"]
                # A pascal string spends one byte on its length, which can't
                # count past 255.
                maxlength = length if _type == "s" else min(length - 1, 255)
                if len(field_.default) > maxlength:  # type: ignore
                    raise ValueError(
                        f"Default for {field_.name} is {len(field_.default)} bytes, "  # type: ignore
                        f"but it holds at most {maxlength}"
                    )
                _base = partial(StringField, maxlength=maxlength)  # type: ignore
            setattr(cls, field_.name, _base(name=field_.name))
            if type_hints[field_.name] is b_types.pad:
                _type = field_.default * _type  # type: ignore
            if type_hints[field_.name] in STRING_TYPES:
                _type = str(field_.metadata["length"]) + _type
            if "last" in field_.metadata and field_.metadata["last"]:
                if lastfield != "":
                    raise ValueError("Can't have more than one last")
                lastfield = _type
                lastname = field_.name
            else:
                cls.__formatstring += _type
                if "padding" not in field_.metadata:
                    datafields.append(field_.name)
        cls.__formatstring += lastfield
        if lastname:
            datafields.append(lastname)
        cls.__datafields = tuple(datafields)

    def __setattr__(self, name, value):
        """
        Only fields, and class attributes that handle assignment themselves
        (such as properties), can be assigned.

        :raises AttributeError: for any other name, so a typo can't silently add
          an attribute that ``bytes()`` later fails on.
        """
        if name not in self.__fieldnames and not hasattr(
            getattr(type(self), name, None), "__set__"
        ):
            raise AttributeError(
                f"{type(self).__name__} has no field {name!r}", name=name, obj=self
            )
        super().__setattr__(name, value)

    def __bytes__(self):
        """
        Packs the class' fields to a binary string
        :return: Binary string packed.
        :rtype: bytes
        """
        values = []
        lastvalue = None
        for k, v in self.__dict__.items():
            if k.startswith("_BinmapDataclass__"):
                continue
            if callable(v):
                v = v(self)
            if (
                "last" in self.__datafieldsmap[k].metadata
                and self.__datafieldsmap[k].metadata["last"]
            ):
                lastvalue = v
                continue
            values.append(v)
        if lastvalue is not None:
            values.append(lastvalue)

        return struct.pack(
            self.__formatstring,
            *values,
        )

    def __post_init__(self, _binarydata: bytes):
        """
        Initialises fields from a binary string
        :param bytes _binarydata: Binary string that will be unpacked.
        """
        # Kludgy hack to keep order
        for f in dataclasses.fields(type(self)):
            if f.name.startswith("_BinmapDataclass__"):
                continue
            if "padding" in f.metadata:
                continue
            if "constant" in f.metadata:
                self.__dict__.update({f.name: f.default})
            if "autolength" in f.metadata:
                self.__dict__.update(
                    {f.name: struct.calcsize(self.__formatstring) + f.default}  # type: ignore
                )
            if "function" in f.metadata:
                self.__dict__.update({f.name: f.metadata["function"]})
            else:
                val = getattr(self, f.name)
                del self.__dict__[f.name]
                self.__dict__.update({f.name: val})
        if _binarydata != b"":
            self.frombytes(_binarydata)

    def frombytes(self, value: bytes):
        """
        Unpacks value to each field. If the data is rejected, the instance is
        left unchanged.

        :param bytes value: binary string to unpack
        :raises ValueError: if a constant, autolength or calculated field
          doesn't match the data
        """
        args = struct.unpack(self.__formatstring, value)
        previous = self.__dict__.copy()
        try:
            calculated = []
            # strict: the struct has exactly one value per data field
            for arg, name in zip(args, self.__datafields, strict=True):
                field_ = self.__datafieldsmap[name]
                if "constant" in field_.metadata:
                    if arg != field_.default:
                        raise ValueError("Constant doesn't match binary data")
                elif "autolength" in field_.metadata:
                    if arg != getattr(self, name):
                        raise ValueError("Length doesn't match")
                elif "function" in field_.metadata:
                    # Checked once every other field is assigned: the function
                    # may read fields that come after it in the struct.
                    calculated.append((arg, field_.metadata["function"]))
                else:
                    setattr(self, name, arg)
            for arg, function in calculated:
                if arg != function(self):
                    raise ValueError("Wrong calculated value")
        except Exception:
            self.__dict__.clear()
            self.__dict__.update(previous)
            raise
