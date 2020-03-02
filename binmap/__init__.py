import dataclasses
import struct
from abc import ABC
from typing import Dict, NewType, Tuple, Type, TypeVar, get_type_hints

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
        # struct.pack(obj._datafields[self.name], value)
        obj.__dict__[self.name] = value


class PaddingField(BaseDescriptor):
    """PaddingField descriptor is used to "pad" data with values unused for real data"""

    def __get__(self, obj, owner):
        """Getting values fails"""
        raise AttributeError(f"Padding ({self.name}) is not readable")

    def __set__(self, obj, value):
        """Setting values does nothing"""
        pass


class EnumField(BaseDescriptor):
    """EnumField descriptor uses "enum" to map to and from strings. Accepts
    both strings and values when setting. Only values that has a corresponding
    string is allowed."""

    def __get__(self, obj, owner):
        value = obj.__dict__[f"_{self.name}"]
        return obj._enums[self.name][value]

    def __set__(self, obj, value):
        if value in obj._enums[self.name]:
            obj.__dict__[f"_{self.name}"] = value
        else:
            for k, v in obj._enums[self.name].items():
                if v == value:
                    obj.__dict__[f"_{self.name}"] = k
                    return

            raise ValueError("Unknown enum or value")


class ConstField(BinField):
    """ConstField descriptor keeps it's value"""

    def __set__(self, obj, value):
        if self.name in obj.__dict__:
            raise AttributeError(f"{self.name} is a constant")
        else:
            obj.__dict__.update({self.name: value})


unsignedchar = NewType("unsingedchar", int)
longlong = NewType("longlong", int)
pad = NewType("pad", int)

datatypemapping: Dict[type, Tuple[BaseDescriptor, str]] = {
    unsignedchar: (BinField, "B"),
    longlong: (BinField, "q"),
    pad: (PaddingField, "x"),
}


def binmapdataclass(cls: Type[T]) -> Type[T]:
    dataclasses.dataclass(cls)
    type_hints = get_type_hints(cls)

    cls._formatstring = ""

    for field_ in dataclasses.fields(cls):
        _base, _type = datatypemapping[type_hints[field_.name]]
        if "constant" in field_.metadata:
            _base = ConstField
        setattr(cls, field_.name, _base(name=field_.name))
        if type_hints[field_.name] is pad:
            _type = field_.default * _type
        cls._formatstring += _type

    return cls


def padding(length=1):
    return dataclasses.field(default=length, repr=False, metadata={"padding": True})


def constant(value):
    return dataclasses.field(default=value, init=False, metadata={"constant": True})


@dataclasses.dataclass
class BinmapDataclass(ABC):
    _byteorder = ""
    _formatstring = ""
    __binarydata: dataclasses.InitVar[bytes] = b""

    def __init_subclass__(cls, byteorder=">"):
        cls._byteorder = byteorder

    def __bytes__(self):
        return struct.pack(
            # TODO: use datclass.fields
            self._byteorder + self._formatstring,
            *(
                v
                for k, v in self.__dict__.items()
                if k not in ["_byteorder", "_formatstring", "_binarydata"]
            ),
        )

    def __post_init__(self, _binarydata):
        if _binarydata != b"":
            self._unpacker(_binarydata)
        # Kludgy hack to keep order
        for f in dataclasses.fields(self):
            if "padding" in f.metadata:
                continue
            if "constant" in f.metadata:
                self.__dict__.update({f.name: f.default})
            else:
                val = getattr(self, f.name)
                del self.__dict__[f.name]
                self.__dict__.update({f.name: val})

    def _unpacker(self, value):
        type_hints = get_type_hints(self)
        datafieldsmap = {f.name: f for f in dataclasses.fields(self)}
        datafields = [
            f.name for f in dataclasses.fields(self) if not (type_hints[f.name] is pad)
        ]
        args = struct.unpack(self._byteorder + self._formatstring, value)
        for arg, name in zip(args, datafields):
            if "constant" in datafieldsmap[name].metadata:
                if arg != datafieldsmap[name].default:
                    raise ValueError("Constant doesn't match binary data")

            setattr(self, name, arg)

    def frombytes(self, value):
        self._unpacker(value)
        self._binarydata = value
