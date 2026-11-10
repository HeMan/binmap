# pyright: strict
import dataclasses
import struct
from dataclasses import InitVar
from enum import IntEnum, IntFlag
from functools import partial
from typing import (
    TYPE_CHECKING,
    Annotated,
    Callable,
    ClassVar,
    Dict,
    FrozenSet,
    List,
    Literal,
    NoReturn,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    dataclass_transform,
    get_args,
    get_origin,
    get_type_hints,
)

from binmap import types as b_types

# The public API. With py.typed, type checkers treat names a module merely
# imports (like b_types) as private unless they're listed here.
__all__ = [
    "BaseDescriptor",
    "BinField",
    "BinmapDataclass",
    "CalculatedField",
    "ConstField",
    "EnumField",
    "PaddingField",
    "StringField",
    "autolength",
    "b_types",
    "calculatedfield",
    "constant",
    "enumfield",
    "padding",
    "stringfield",
]


class BaseDescriptor:
    """Base class for all descriptors

    :param name: Variable name"""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def __init__(self, name: str = "") -> None:
        self.name = name


class BinField(BaseDescriptor):
    """BinField descriptor tries to pack it into a struct before setting the
    value as a bounds checker"""

    def __get__(self, obj: "BinmapDataclass", owner: type) -> object:
        return obj.__dict__[self.name]

    def __set__(self, obj: "BinmapDataclass", value: object) -> None:
        # _check_value belongs to the same machinery as this descriptor
        type(obj)._check_value(self.name, value)  # pyright: ignore[reportPrivateUsage]
        obj.__dict__[self.name] = value


class StringField(BinField):
    """StringField descriptor is a BinField for string and pascalstring fields
    that also rejects values longer than the field holds, which struct.pack
    would otherwise cut silently.

    :raises struct.error: when the value is too long"""

    def __init__(self, name: str, maxlength: int) -> None:
        super().__init__(name)
        self.maxlength = maxlength

    def __set__(self, obj: "BinmapDataclass", value: object) -> None:
        if isinstance(value, (bytes, bytearray)) and len(value) > self.maxlength:
            raise struct.error(
                f"{self.name} holds at most {self.maxlength} bytes, got {len(value)}"
            )
        super().__set__(obj, value)


class PaddingField(BaseDescriptor):
    """PaddingField descriptor is used to "pad" data with values unused for real data

    :raises AttributeError: when trying to read, since it's only padding."""

    def __get__(self, obj: "BinmapDataclass", owner: type) -> NoReturn:
        """Getting values fails"""
        raise AttributeError(f"Padding ({self.name}) is not readable")

    def __set__(self, obj: "BinmapDataclass", value: object) -> None:
        """Setting values does nothing"""


class EnumField(BinField):
    """EnumField descriptor for fields made with :func:`enumfield`. Accepts a
    member, a member's name or a number. A name stores the member it names; a
    number is stored as given. Either way the value must belong to the enum and
    fit the field, like any other field's value.

    :raises KeyError: for a name that isn't a member's
    :raises ValueError: for a number that isn't one of the enum's values
    :raises struct.error: for a value that doesn't fit the field"""

    def __init__(
        self, name: str, enumclass: Union[Type[IntEnum], Type[IntFlag]]
    ) -> None:
        super().__init__(name)
        self.enumclass = enumclass

    def __set__(self, obj: "BinmapDataclass", value: object) -> None:
        if isinstance(value, str):
            value = self.enumclass[value]
        elif isinstance(value, int):
            self.enumclass(value)
        else:
            # The enum would accept e.g. 2.0 for a member worth 2; the field can't
            raise ValueError(f"{value!r} is not a valid {self.enumclass.__qualname__}")
        # BinField checks that the value fits the field, then stores it
        super().__set__(obj, value)


class ConstField(BinField):
    """ConstField descriptor keeps it's value

    :raises AttributeError: Since it's a constant it raises and error when
      trying to set"""

    def __set__(self, obj: "BinmapDataclass", value: object) -> None:
        if self.name in obj.__dict__:
            raise AttributeError(f"{self.name} is a constant")
        obj.__dict__[self.name] = value


class CalculatedField(BinField):
    """CalculatedField calls a function when it's converted to bytes

    :raises AttributeError: Trying to set the value is not allowed"""

    def __init__(
        self, name: str, function: Callable[["BinmapDataclass"], object]
    ) -> None:
        self.name = name
        self.function = function

    def __get__(self, obj: "BinmapDataclass", owner: type) -> object:
        return self.function(obj)

    def __set__(self, obj: "BinmapDataclass", value: object) -> None:
        if self.name in obj.__dict__:
            raise AttributeError("Can't set a calculated field")


# Plain Python types binmap also accepts as field types.
_PLAIN_CODES: Dict[type, str] = {
    bool: "?",
    int: "i",
    float: "f",
    bytes: "s",
    str: "s",
}


def _struct_code(hint: object) -> str:
    """
    The struct format character for a field's type hint: the ``StructCode`` of
    an ``Annotated`` alias such as ``unsignedchar``, or the code for a plain
    type such as ``int``.

    :raises KeyError: for a type binmap can't pack
    """
    if get_origin(hint) is Annotated:
        python_type, *metadata = get_args(hint)
        for item in metadata:
            if isinstance(item, b_types.StructCode):
                return item.code
        hint = python_type
    if isinstance(hint, type):
        return _PLAIN_CODES[hint]
    raise KeyError(hint)


# S is the class a calculated field's function receives, T the field's value type
S = TypeVar("S")
T = TypeVar("T")

# The field factories return a dataclasses.Field at runtime, but are typed as
# returning the value the field holds, like dataclasses.field() itself in the
# standard type stubs. Type checkers then take a call for the field's default,
# so `name: string = stringfield(8)` type-checks, and a factory used on a field
# of the wrong type is reported.
#
# constant() and autolength() are also dataclass_transform field specifiers:
# their `init: Literal[False]` tells type checkers that, like at runtime, those
# fields aren't __init__ arguments. The other factories must not be specifiers:
# type checkers treat a specifier call without `default=` as a required field,
# and since the inherited __binarydata has a default, every class using one
# would be reported as invalid. That's why type checkers can't catch a missing
# value for an enumfield() without a default, which fails at runtime.


def padding(length: int = 1) -> int:
    """
    Field generator function for padding elements

    :param int length: Number of bytes of padded field
    :return: dataclass field
    """
    # compare=False: padding can't be read, so the generated __eq__ must skip it
    return dataclasses.field(
        default=length, repr=False, compare=False, metadata={"padding": True}
    )


def constant(value: T, *, init: Literal[False] = False) -> T:
    """
    Field generator function for constant elements

    :param value: Constant value for the field.
    :param init: Always ``False``; tells type checkers that the field isn't an
      ``__init__`` argument.
    :return: dataclass field
    """
    return dataclasses.field(default=value, init=False, metadata={"constant": True})


def autolength(offset: int = 0, *, init: Literal[False] = False) -> int:
    """
    Field generator function for autolength fields

    :param offset: offset for the length calculation
    :param init: Always ``False``; tells type checkers that the field isn't an
      ``__init__`` argument.
    :return: dataclass field
    """
    return dataclasses.field(default=offset, init=False, metadata={"autolength": True})


def stringfield(length: int = 1, default: bytes = b"") -> bytes:
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
    return dataclasses.field(
        default=default, metadata={"length": length, "autodefault": autodefault}
    )


def enumfield(
    enumclass: Union[Type[IntEnum], Type[IntFlag]],
    default: Union[IntEnum, IntFlag, int, None] = None,
) -> int:
    """
    Field generator function for enum field

    :param enumclass: The IntEnum or IntFlag class the values must belong to.
    :param default: default value. Without one, the field must be given when
      creating an instance.
    :return: dataclass field
    """
    # The field holds an IntEnum/IntFlag member or a plain int: int covers both.
    return cast(int, dataclasses.field(default=default, metadata={"enum": enumclass}))


def calculatedfield(function: Callable[[S], T], last: bool = False) -> T:
    """
    Field generator function for calculated fields

    :param Callable function: function that calculates the field. It's called
      with the instance and returns the field's value.
    :param bool last: pack the field last, whatever its position in the class
    :return: dataclass field
    """
    # The default 0 is never used: the value always comes from the function,
    # whose return type is the field's type.
    field_ = dataclasses.field(default=0, metadata={"function": function, "last": last})
    return cast(T, field_)


class _FieldsWithoutPaddingOnInstances:
    """
    Replaces ``__dataclass_fields__`` on every ``BinmapDataclass`` subclass.

    ``dataclasses.asdict()``, ``astuple()`` and ``replace()`` read every field
    that ``dataclasses.fields(instance)`` returns. Padding fields can't be read,
    so through an instance this returns the fields without padding. Through the
    class it returns all fields: ``dataclasses`` needs them to build subclasses,
    and binmap needs them for the struct format.
    """

    def __init__(self, fields: Dict[str, "dataclasses.Field[object]"]) -> None:
        self.fields = fields
        self.instance_fields = {
            name: field_
            for name, field_ in fields.items()
            if "padding" not in field_.metadata
        }

    def __get__(
        self, obj: Optional["BinmapDataclass"], owner: type
    ) -> Dict[str, "dataclasses.Field[object]"]:
        return self.fields if obj is None else self.instance_fields


# dataclass_transform tells type checkers and editors that every subclass is a
# dataclass, so they know its constructor (__init_subclass__ applies
# dataclasses.dataclass() at runtime, which they can't see).
@dataclass_transform(field_specifiers=(constant, autolength))
@dataclasses.dataclass
class BinmapDataclass:
    """
    Dataclass that does the converting to and from binary data
    """

    # Name-mangled on purpose: it can't clash with a subclass's fields, and type
    # checkers treat the parameter as positional-only (Cls(b"...")).
    __binarydata: InitVar[bytes] = b""  # pyright: ignore[reportGeneralTypeIssues]
    __datafields: ClassVar[Tuple[str, ...]]
    __datafieldsmap: ClassVar[Dict[str, "dataclasses.Field[object]"]]
    __formatstring: ClassVar[str]
    __byteorder: ClassVar[str]
    __codes: ClassVar[Dict[str, str]]
    __fieldnames: ClassVar[FrozenSet[str]] = frozenset()

    def __init_subclass__(cls, byteorder: str = ">") -> None:
        """
        Subclass initiator. This makes the inheriting class a dataclass.
        :param str byteorder: byteorder for binary data
        """
        # stringfield() can't tell a string from a pascalstring, so it fills an
        # unspecified default with `length` zero bytes. A pascalstring holds one
        # byte less, so start it empty instead, before dataclass() captures the
        # defaults. include_extras keeps the Annotated aliases' StructCode.
        own_hints = get_type_hints(cls, include_extras=True)
        for name, value in vars(cls).items():
            if (
                isinstance(value, dataclasses.Field)
                and value.metadata.get("autodefault")
                and name in own_hints
                and _struct_code(own_hints[name]) == "p"
            ):
                value.default = b""
        dataclasses.dataclass(cls)
        setattr(
            cls,
            "__dataclass_fields__",
            _FieldsWithoutPaddingOnInstances(cls.__dict__["__dataclass_fields__"]),
        )
        type_hints = get_type_hints(cls, include_extras=True)

        cls.__fieldnames = frozenset(f.name for f in dataclasses.fields(cls))
        cls.__byteorder = byteorder
        cls.__formatstring = byteorder
        cls.__datafieldsmap = {f.name: f for f in dataclasses.fields(cls)}
        # Names of the fields that have a value in the struct (everything but
        # padding), in wire order: the format string's order, with the "last"
        # field moved to the end. Built once per class; instances never change it.
        datafields: List[str] = []
        lastname = ""
        codes: Dict[str, str] = {}

        lastfield: str = ""
        for field_ in dataclasses.fields(cls):
            if field_.name.startswith("_BinmapDataclass__"):
                continue
            _type = _struct_code(type_hints[field_.name])
            codes[field_.name] = _type
            _base: Callable[[str], BaseDescriptor] = (
                PaddingField if _type == "x" else BinField
            )
            if "constant" in field_.metadata:
                _base = ConstField
            elif "enum" in field_.metadata:
                _base = partial(EnumField, enumclass=field_.metadata["enum"])
            elif "autolength" in field_.metadata:
                _base = ConstField
            elif "function" in field_.metadata:
                _base = partial(CalculatedField, function=field_.metadata["function"])
            elif _type in ("s", "p"):
                length: int = field_.metadata["length"]
                # A pascal string spends one byte on its length, which can't
                # count past 255.
                maxlength = length if _type == "s" else min(length - 1, 255)
                default = cast(bytes, field_.default)  # stringfield() sets bytes
                if len(default) > maxlength:
                    raise ValueError(
                        f"Default for {field_.name} is {len(default)} bytes, "
                        f"but it holds at most {maxlength}"
                    )
                _base = partial(StringField, maxlength=maxlength)
            setattr(cls, field_.name, _base(field_.name))
            if _type == "x":
                # padding()'s default is the number of bytes to pad
                _type *= cast(int, field_.default)
            elif _type in ("s", "p"):
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
        cls.__codes = codes

    @classmethod
    def _check_value(cls, name: str, value: object) -> None:
        """
        Raises if ``value`` can't be packed into field ``name``; used by
        :class:`BinField`.

        :raises struct.error: if the value doesn't fit the field's type
        """
        # Each field's struct code, worked out once by __init_subclass__ from
        # get_type_hints(cls). Never resolve type hints on the instance: Python
        # 3.14+ (PEP 649) rejects that. The class lookup walks the MRO, so
        # inherited fields are found too.
        code = cls.__codes.get(name)
        if code is None:
            raise ValueError(name)
        # Pack with the class's byte order, like bytes() does. A bare code would
        # use native sizes, which differ from the standard ones (e.g. "l" is 8
        # bytes natively on 64-bit Linux but 4 bytes with ">" or "<").
        struct.pack(cls.__byteorder + code, value)

    # Hidden from type checkers: a visible __setattr__ tells them any attribute
    # name with any value can be assigned, so they'd accept typos such as
    # `t.humidty = 5`. Without it they use the declared fields, as intended.
    if not TYPE_CHECKING:

        def __setattr__(self, name: str, value: object) -> None:
            """
            Only fields, and class attributes that handle assignment themselves
            (such as properties), can be assigned.

            :raises AttributeError: for any other name, so a typo can't silently
              add an attribute that ``bytes()`` later fails on.
            """
            if name not in self.__fieldnames and not hasattr(
                getattr(type(self), name, None), "__set__"
            ):
                raise AttributeError(
                    f"{type(self).__name__} has no field {name!r}", name=name, obj=self
                )
            super().__setattr__(name, value)

    def __bytes__(self) -> bytes:
        """
        Packs the class' fields to a binary string
        :return: Binary string packed.
        :rtype: bytes
        """
        values: List[object] = []
        lastvalue: object = None
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

    def __post_init__(self, _binarydata: bytes) -> None:
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
                    # autolength()'s default is the offset to add
                    {
                        f.name: struct.calcsize(self.__formatstring)
                        + cast(int, f.default)
                    }
                )
            if "function" in f.metadata:
                self.__dict__.update({f.name: f.metadata["function"]})
            else:
                val = getattr(self, f.name)
                del self.__dict__[f.name]
                self.__dict__.update({f.name: val})
        if _binarydata != b"":
            self.frombytes(_binarydata)

    def frombytes(self, value: bytes) -> None:
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
            calculated: List[Tuple[object, Callable[[BinmapDataclass], object]]] = []
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
