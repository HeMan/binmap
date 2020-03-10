import dataclasses
import struct
from enum import IntEnum
from typing import Dict, Tuple, Type, TypeVar, Union, get_type_hints

from binmap import types

T = TypeVar("T")


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
        type_hints = get_type_hints(obj)
        struct.pack(datatypemapping[type_hints[self.name]][1], value)
        obj.__dict__[self.name] = value


class PaddingField(BaseDescriptor):
    """PaddingField descriptor is used to "pad" data with values unused for real data"""

    def __get__(self, obj, owner):
        """Getting values fails"""
        raise AttributeError(f"Padding ({self.name}) is not readable")

    def __set__(self, obj, value):
        """Setting values does nothing"""
        pass


class EnumField(BinField):
    """EnumField descriptor uses "enum" to map to and from strings. Accepts
    both strings and values when setting. Only values that has a corresponding
    string is allowed."""

    def __set__(self, obj, value):
        datafieldsmap = {f.name: f for f in dataclasses.fields(obj)}
        if type(value) is str:
            datafieldsmap[self.name].metadata["enum"][value]
        else:
            datafieldsmap[self.name].metadata["enum"](value)
        obj.__dict__[self.name] = value


class ConstField(BinField):
    """ConstField descriptor keeps it's value"""

    def __set__(self, obj, value):
        if self.name in obj.__dict__:
            raise AttributeError(f"{self.name} is a constant")
        else:
            obj.__dict__[self.name] = value


datatypemapping: Dict[type, Tuple[Type[BaseDescriptor], str]] = {
    types.char: (BinField, "c"),
    types.signedchar: (BinField, "b"),
    types.unsignedchar: (BinField, "B"),
    types.boolean: (BinField, "?"),
    bool: (BinField, "?"),
    types.short: (BinField, "h"),
    types.unsignedshort: (BinField, "H"),
    types.integer: (BinField, "i"),
    int: (BinField, "i"),
    types.unsignedinteger: (BinField, "I"),
    types.long: (BinField, "l"),
    types.unsignedlong: (BinField, "L"),
    types.longlong: (BinField, "q"),
    types.unsignedlonglong: (BinField, "Q"),
    types.halffloat: (BinField, "e"),
    types.floating: (BinField, "f"),
    float: (BinField, "f"),
    types.double: (BinField, "d"),
    types.string: (BinField, "s"),
    str: (BinField, "s"),
    types.pascalstring: (BinField, "p"),
    types.pad: (PaddingField, "x"),
}


def padding(length: int = 1) -> dataclasses.Field:
    """
    Field generator function for padding elements

    :param int lenght: Number of bytes of padded field
    :return: dataclass field
    """
    return dataclasses.field(default=length, repr=False, metadata={"padding": True})


def constant(value: Union[int, float, str]) -> dataclasses.Field:
    """
    Field generator function for constant elements

    :param value: Constant value for the field.
    :return: dataclass field
    """
    return dataclasses.field(default=value, init=False, metadata={"constant": True})


def stringfield(
    length: int = 1, default: bytes = b"", fillchar: bytes = b" "
) -> dataclasses.Field:
    """
    Field generator function for string fields.

    :param int lenght: lengt of the string.
    :param bytes default: default value of the string
    :param bytes fillchar: char to pad the string with
    :return: dataclass field
    """
    if default == b"":
        _default = b"\x00" * length
    else:
        _default = bytes(f"{default:{fillchar}<{length}}")
    return dataclasses.field(default=_default, metadata={"length": length})


def enumfield(enumclass: IntEnum, default: IntEnum = None) -> dataclasses.Field:
    """
    Field generator function for enum field

    :param IntEnum enumclass: Class with enums.
    :param IntEnum default: default value
    :return: dataclass field
    """
    return dataclasses.field(default=default, metadata={"enum": enumclass})


@dataclasses.dataclass
class BinmapDataclass:
    """
    Dataclass that does the converting to and from binary data
    """

    _formatstring = ""
    _binarydata: dataclasses.InitVar[bytes] = b""

    def __init_subclass__(cls, byteorder: str = ">"):
        """
        Subclass initiator. This makes the inheriting class a dataclass.
        :param str byteorder: byteorder for binary data
        """
        dataclasses.dataclass(cls)
        type_hints = get_type_hints(cls)

        cls._datafields = []
        cls._datafieldsmap = {}
        cls._formatstring = byteorder

        for field_ in dataclasses.fields(cls):
            _base, _type = datatypemapping[type_hints[field_.name]]
            if "constant" in field_.metadata:
                _base = ConstField
            elif "enum" in field_.metadata:
                _base = EnumField
            setattr(cls, field_.name, _base(name=field_.name))
            if type_hints[field_.name] is types.pad:
                _type = field_.default * _type
            if type_hints[field_.name] in (types.string, types.pascalstring, str):
                _type = str(field_.metadata["length"]) + _type
            cls._formatstring += _type

    def __bytes__(self):
        """
        Packs the class' fields to a binary string
        :return: Binary string packed.
        :rtype: bytes
        """
        return struct.pack(
            # TODO: use datclass.fields
            self._formatstring,
            *(v for k, v in self.__dict__.items() if k not in ["_formatstring"]),
        )

    def __post_init__(self, _binarydata: bytes):
        """
        Initialises fields from a binary string
        :param bytes _binarydata: Binary string that will be unpacked.
        """
        if _binarydata != b"":
            self.frombytes(_binarydata)
        # Kludgy hack to keep order
        for f in dataclasses.fields(self):
            self._datafieldsmap.update({f.name: f})
            if "padding" in f.metadata:
                continue
            if "constant" in f.metadata:
                self.__dict__.update({f.name: f.default})
            else:
                val = getattr(self, f.name)
                del self.__dict__[f.name]
                self.__dict__.update({f.name: val})
            self._datafields.append(f.name)

    def frombytes(self, value: bytes):
        """
        Unpacks value to each field
        :param bytes value: binary string to unpack
        """
        args = struct.unpack(self._formatstring, value)
        for arg, name in zip(args, self._datafields):
            if "constant" in self._datafieldsmap[name].metadata:
                if arg != self._datafieldsmap[name].default:
                    raise ValueError("Constant doesn't match binary data")

            setattr(self, name, arg)
