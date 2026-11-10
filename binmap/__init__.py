# pyright: strict
import dataclasses
import operator
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
    SupportsIndex,
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
    "AutolengthField",
    "BaseDescriptor",
    "BinField",
    "BinmapAttributeError",
    "BinmapDataclass",
    "BinmapError",
    "BinmapTypeError",
    "BinmapValueError",
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


class BinmapError(Exception):
    """Base class of every exception binmap raises."""


class BinmapValueError(BinmapError, ValueError, struct.error):
    """
    A value doesn't fit its field, binary data doesn't match the class, or a
    class is defined with a bad byteorder or default.

    Also a :class:`ValueError`, and a :class:`struct.error`, which binmap
    raised for these before 2.0.
    """


class BinmapTypeError(BinmapError, TypeError, struct.error):
    """
    A value has the wrong type for its field, or a class definition is invalid
    (a field type binmap can't pack, two ``last`` calculated fields).

    Also a :class:`TypeError`, and a :class:`struct.error`, which binmap raised
    for wrong types before 2.0.
    """


class BinmapAttributeError(BinmapError, AttributeError):
    """
    An attribute that isn't a field, or a field that can't be set (constant,
    autolength, calculated) or read (padding). Also an :class:`AttributeError`.
    """


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

    :raises BinmapValueError: when the value is too long"""

    def __init__(self, name: str, maxlength: int) -> None:
        super().__init__(name)
        self.maxlength = maxlength

    def __set__(self, obj: "BinmapDataclass", value: object) -> None:
        if isinstance(value, (bytes, bytearray)) and len(value) > self.maxlength:
            raise BinmapValueError(
                f"{self.name} holds at most {self.maxlength} bytes, got {len(value)}"
            )
        super().__set__(obj, value)


class PaddingField(BaseDescriptor):
    """PaddingField descriptor is used to "pad" data with values unused for real data

    :raises BinmapAttributeError: when trying to read, since it's only padding."""

    def __get__(self, obj: "BinmapDataclass", owner: type) -> NoReturn:
        """Getting values fails"""
        raise BinmapAttributeError(f"Padding ({self.name}) is not readable")

    def __set__(self, obj: "BinmapDataclass", value: object) -> None:
        """Setting values does nothing"""


class EnumField(BinField):
    """EnumField descriptor for fields made with :func:`enumfield`. Accepts a
    member, a member's name or a number. A name stores the member it names; a
    number is stored as given. Either way the value must belong to the enum and
    fit the field, like any other field's value.

    :raises BinmapValueError: for a name or number that isn't a member's, or a
      value that doesn't fit the field
    :raises BinmapTypeError: for anything but a name or an int"""

    def __init__(
        self, name: str, enumclass: Union[Type[IntEnum], Type[IntFlag]]
    ) -> None:
        super().__init__(name)
        self.enumclass = enumclass

    def __set__(self, obj: "BinmapDataclass", value: object) -> None:
        enum_name = self.enumclass.__qualname__
        if isinstance(value, str):
            try:
                value = self.enumclass[value]
            except KeyError:
                raise BinmapValueError(
                    f"{value!r} is not a member of {enum_name}"
                ) from None
        elif isinstance(value, int):
            try:
                self.enumclass(value)
            except ValueError as error:
                raise BinmapValueError(str(error)) from None
        else:
            # The enum would accept e.g. 2.0 for a member worth 2; the field can't
            raise BinmapTypeError(
                f"{self.name} needs an int or a member's name, "
                f"got {type(value).__name__}"
            )
        # BinField checks that the value fits the field, then stores it
        super().__set__(obj, value)


class ConstField(BinField):
    """ConstField descriptor keeps it's value

    :raises BinmapAttributeError: Since it's a constant it raises and error when
      trying to set"""

    def __set__(self, obj: "BinmapDataclass", value: object) -> None:
        if self.name in obj.__dict__:
            raise BinmapAttributeError(self._read_only_message())
        obj.__dict__[self.name] = value

    def _read_only_message(self) -> str:
        return f"{self.name} is a constant"


class AutolengthField(ConstField):
    """AutolengthField descriptor for fields made with :func:`autolength`: the
    value is the size of the packed data, so it can't be set.

    :raises BinmapAttributeError: when trying to set"""

    def _read_only_message(self) -> str:
        return f"{self.name} is set from the size of the data and can't be assigned"


class CalculatedField(BinField):
    """CalculatedField calls a function when it's converted to bytes

    :raises BinmapAttributeError: Trying to set the value is not allowed"""

    def __init__(
        self, name: str, function: Callable[["BinmapDataclass"], object]
    ) -> None:
        self.name = name
        self.function = function

    def __get__(self, obj: "BinmapDataclass", owner: type) -> object:
        return self.function(obj)

    def __set__(self, obj: "BinmapDataclass", value: object) -> None:
        if self.name in obj.__dict__:
            raise BinmapAttributeError(
                f"{self.name} is a calculated field and can't be set"
            )


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


def _field_code(name: str, hint: object) -> str:
    """
    :func:`_struct_code` for field ``name``.

    :raises BinmapTypeError: for a type binmap can't pack
    """
    try:
        return _struct_code(hint)
    except KeyError:
        type_name = getattr(hint, "__name__", None) or repr(hint)
        raise BinmapTypeError(
            f"{name}: {type_name} can't be packed; use a type from binmap.types, "
            "or int, float, bool or bytes"
        ) from None


_BYTEORDERS = ("@", "=", "<", ">", "!")
_INTEGER_CODES = frozenset("bBhHiIlLqQ")
_FLOAT_CODES = frozenset("efd")
_BYTES_CODES = frozenset("csp")


def _check_type(name: str, code: str, value: object) -> None:
    """
    Raises if ``value`` has the wrong type for a field packed as ``code``.
    struct itself would raise struct.error for both wrong types and
    out-of-range values; this tells them apart.

    :raises BinmapTypeError: for a value of the wrong type
    :raises BinmapValueError: for a boolean that isn't True/False/0/1, or a
      char that isn't exactly one byte
    """
    has_index = hasattr(type(value), "__index__")  # int, bool, NumPy ints...
    if code in _INTEGER_CODES:
        if not has_index:
            raise BinmapTypeError(f"{name} needs an int, got {type(value).__name__}")
    elif code in _FLOAT_CODES:
        if not (has_index or hasattr(type(value), "__float__")):
            raise BinmapTypeError(f"{name} needs a float, got {type(value).__name__}")
    elif code == "?":
        # struct packs the truth of any object; only accept booleans
        if not has_index:
            raise BinmapTypeError(f"{name} needs a bool, got {type(value).__name__}")
        if operator.index(cast(SupportsIndex, value)) not in (0, 1):
            raise BinmapValueError(f"{name} must be True, False, 0 or 1, got {value!r}")
    elif code in _BYTES_CODES:
        if not isinstance(value, (bytes, bytearray)):
            raise BinmapTypeError(f"{name} needs bytes, got {type(value).__name__}")
        if code == "c" and len(value) != 1:
            raise BinmapValueError(f"{name} holds 1 byte, got {len(value)}")


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
        :raises BinmapValueError: for an invalid byteorder or a default that
          doesn't fit its field
        :raises BinmapTypeError: for a field type binmap can't pack, or more
          than one ``calculatedfield(last=True)``
        """
        if byteorder not in _BYTEORDERS:
            raise BinmapValueError(
                "byteorder must be one of "
                f"{', '.join(repr(order) for order in _BYTEORDERS)}, got {byteorder!r}"
            )
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
                and _field_code(name, own_hints[name]) == "p"
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
            _type = _field_code(field_.name, type_hints[field_.name])
            codes[field_.name] = _type
            _base: Callable[[str], BaseDescriptor] = (
                PaddingField if _type == "x" else BinField
            )
            if "constant" in field_.metadata:
                _base = ConstField
            elif "enum" in field_.metadata:
                _base = partial(EnumField, enumclass=field_.metadata["enum"])
            elif "autolength" in field_.metadata:
                _base = AutolengthField
            elif "function" in field_.metadata:
                _base = partial(CalculatedField, function=field_.metadata["function"])
            elif _type in ("s", "p"):
                length: int = field_.metadata["length"]
                # A pascal string spends one byte on its length, which can't
                # count past 255.
                maxlength = length if _type == "s" else min(length - 1, 255)
                default = cast(bytes, field_.default)  # stringfield() sets bytes
                if len(default) > maxlength:
                    raise BinmapValueError(
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
                    raise BinmapTypeError(
                        "Only one calculatedfield(last=True) is allowed per "
                        f"class: {lastname} and {field_.name}"
                    )
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

        :raises BinmapTypeError: if the value has the wrong type
        :raises BinmapValueError: if the value doesn't fit the field
        """
        # Each field's struct code, worked out once by __init_subclass__ from
        # get_type_hints(cls). Never resolve type hints on the instance: Python
        # 3.14+ (PEP 649) rejects that. The class lookup walks the MRO, so
        # inherited fields are found too.
        code = cls.__codes.get(name)
        if code is None:
            raise BinmapAttributeError(f"{cls.__name__} has no field {name!r}")
        _check_type(name, code, value)
        # Pack with the class's byte order, like bytes() does. A bare code would
        # use native sizes, which differ from the standard ones (e.g. "l" is 8
        # bytes natively on 64-bit Linux but 4 bytes with ">" or "<").
        try:
            struct.pack(cls.__byteorder + code, value)
        except struct.error as error:
            raise BinmapValueError(f"{name}: {error}") from None

    # Hidden from type checkers: a visible __setattr__ tells them any attribute
    # name with any value can be assigned, so they'd accept typos such as
    # `t.humidty = 5`. Without it they use the declared fields, as intended.
    if not TYPE_CHECKING:

        def __setattr__(self, name: str, value: object) -> None:
            """
            Only fields, and class attributes that handle assignment themselves
            (such as properties), can be assigned.

            :raises BinmapAttributeError: for any other name, so a typo can't
              silently add an attribute that ``bytes()`` later fails on.
            """
            if name not in self.__fieldnames and not hasattr(
                getattr(type(self), name, None), "__set__"
            ):
                raise BinmapAttributeError(
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
        :raises BinmapTypeError: if value isn't bytes
        :raises BinmapValueError: if the data has the wrong size, a constant,
          autolength or calculated field doesn't match it, or a value in it
          doesn't fit its field
        """
        class_name = type(self).__name__
        # Typed bytes for type checkers, but untyped callers can pass anything
        if not isinstance(cast(object, value), (bytes, bytearray, memoryview)):
            raise BinmapTypeError(
                f"{class_name} needs bytes to parse, got {type(value).__name__}"
            )
        size = struct.calcsize(self.__formatstring)
        given = memoryview(value).nbytes
        if given != size:
            raise BinmapValueError(
                f"{class_name} needs {size} byte{'' if size == 1 else 's'} of data, "
                f"got {given}"
            )
        args = struct.unpack(self.__formatstring, value)
        previous = self.__dict__.copy()
        try:
            calculated: List[
                Tuple[str, object, Callable[[BinmapDataclass], object]]
            ] = []
            # strict: the struct has exactly one value per data field
            for arg, name in zip(args, self.__datafields, strict=True):
                field_ = self.__datafieldsmap[name]
                if "constant" in field_.metadata:
                    if arg != field_.default:
                        raise BinmapValueError(
                            f"{name}: the data has {arg!r}, "
                            f"but the constant is {field_.default!r}"
                        )
                elif "autolength" in field_.metadata:
                    length = getattr(self, name)
                    if arg != length:
                        raise BinmapValueError(
                            f"{name}: the data says {arg}, but the length is {length}"
                        )
                elif "function" in field_.metadata:
                    # Checked once every other field is assigned: the function
                    # may read fields that come after it in the struct.
                    calculated.append((name, arg, field_.metadata["function"]))
                else:
                    setattr(self, name, arg)
            for name, arg, function in calculated:
                expected = function(self)
                if arg != expected:
                    raise BinmapValueError(
                        f"{name}: the data has {arg!r}, "
                        f"but the calculated value is {expected!r}"
                    )
        except Exception:
            self.__dict__.clear()
            self.__dict__.update(previous)
            raise
