import struct
from inspect import Parameter, Signature


class BaseDescriptor:
    """Base class for all descriptors

    :param name: Variable name"""

    def __init__(self, name):
        self.name = name


class BinField(BaseDescriptor):
    """BinField descriptor tries to pack it into a struct before setting the
    value as a bounds checker"""

    def __get__(self, obj, owner):
        return obj.__dict__[self.name]

    def __set__(self, obj, value):
        struct.pack(obj._datafields[self.name], value)
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
        elif value in obj._enums[self.name].values():
            for k, v in obj._enums[self.name].items():
                if v == value:
                    obj.__dict__[f"_{self.name}"] = k
        else:
            raise ValueError("Unknown enum or value")


class ConstField(BinField):
    """ConstField descriptor keeps it's value"""

    def __set__(self, obj, value):
        raise AttributeError(f"{self.name} is a constant")


class BinmapMetaclass(type):
    """Metaclass for :class:`Binmap` and all subclasses of :class:`Binmap`.

    :class:`BinmapMetaclass` responsibility is to add for adding variables from
    _datafields, _enums, _constants and add keyword only parameters.

    _datafields starting with ``_pad`` does't get any instance variable mapped.

    _enums get a variable called _{name} which has the binary data."""

    def __new__(cls, clsname, bases, clsdict):
        clsobject = super().__new__(cls, clsname, bases, clsdict)
        keys = clsobject._datafields.keys()
        sig = Signature(
            [
                Parameter(
                    "binarydata",
                    Parameter.POSITIONAL_OR_KEYWORD,
                    default=Parameter.default,
                )
            ]
            + [
                Parameter(name, Parameter.KEYWORD_ONLY, default=Parameter.default)
                for name in keys
            ]
        )
        setattr(clsobject, "__signature__", sig)
        for enum in clsobject._enums.keys():
            for value, const in clsobject._enums[enum].items():
                if hasattr(clsobject, const.upper()):
                    raise ValueError(f"{const} already defined")
                setattr(clsobject, const.upper(), value)
        for name in keys:
            if name.startswith("_pad"):
                setattr(clsobject, name, PaddingField(name=name))
            elif name in clsobject._constants:
                setattr(clsobject, name, ConstField(name=name))
            elif name in clsobject._enums:
                setattr(clsobject, name, EnumField(name=name))
                setattr(clsobject, f"_{name}", BinField(name=f"_{name}"))
            else:
                setattr(clsobject, name, BinField(name=name))
        return clsobject


class Binmap(metaclass=BinmapMetaclass):
    """A class that maps to and from binary data using :py:class:`struct`.
    All fields in :attr:`binmap.Binmap._datafields` gets a corresponding
    variable in instance, except variables starting with ``_pad``, which is
    just padding.

    To create an enum mapping you could add :attr:`binmap.Binmap._enums` with a
    map to your corresponing datafield:

    .. code-block:: python

        class TempWind(Binmap):
            _datafields = {"temp": "b", "wind": "B"}
            _enums = {"wind": {0: "North", 1: "East", 2: "South", 4: "West"}}

        tw = TempWind()
        tw.temp = 3
        tw.wind = "South"
        print(bytes(tw))
        b'\\x03\\x02'


    """

    #: _byteorder: charcter with byteorder
    _byteorder = ">"
    #: _datafields: dict with variable name as key and :py:class:`struct` `format strings`_ as value
    _datafields = {}
    #: _enums: dict of dicts containing maps of strings
    _enums = {}
    #: _constans: dict of constants. This creates a variable that is allways
    #: the same value. It won't accept binary data with any other value
    _constants = {}

    def __init__(self, *args, **kwargs):
        self._formatstring = self._byteorder
        for fmt in self._datafields.values():
            self._formatstring += fmt

        bound = self.__signature__.bind(*args, **kwargs)
        for param in self.__signature__.parameters.values():
            if param.name in bound.arguments:
                if param.name == "binarydata":
                    self._binarydata = bound.arguments[param.name]
                    self._unpacker(bound.arguments[param.name])
                elif param.name in self._constants:
                    raise AttributeError(f"{param.name} is a constant")
                else:
                    setattr(self, param.name, bound.arguments[param.name])
            elif param.name != "binarydata":
                elif param.name in self._constants:
                    self.__dict__[param.name] = self._constants[param.name]
                elif self._datafields[param.name] in "BbHhIiLlQq":
                    setattr(self, param.name, 0)
                elif self._datafields[param.name] in "efd":
                    setattr(self, param.name, 0.0)
                elif self._datafields[param.name] == "c":
                    setattr(self, param.name, b"\x00")
                else:
                    setattr(self, param.name, b"")

        if len(args) == 1:
            self._binarydata = args[0]
            self._unpacker(args[0])
        else:
            self._binarydata = ""

    def _unpacker(self, value):
        args = struct.unpack(self._formatstring, value)
        datafields = [
            field for field in self._datafields.keys() if not field.startswith("_pad")
        ]
        for arg, name in zip(args, datafields):
            if name in self._constants:
                if arg != self._constants[name]:
                    raise ValueError("Constant doesn't match binary data")
            else:
                setattr(self, name, arg)

    def __bytes__(self):
        """packs or unpacks all variables to a binary structure defined by
        _datafields' format values"""
        datas = []
        for var in self._datafields.keys():
            if not var.startswith("_pad"):
                if var in self._enums:
                    datas.append(getattr(self, f"_{var}"))
                else:
                    datas.append(getattr(self, var))
        return struct.pack(self._formatstring, *datas)

    def frombytes(self, value):
        self._unpacker(value)
        self._binarydata = value

    def __eq__(self, other):
        if self.__signature__ != other.__signature__:
            return False
        for field in self._datafields.keys():
            v1 = getattr(self, field)
            v2 = getattr(other, field)
            if v1 != v2:
                return False
        return True

    def __str__(self):
        retval = f"{self.__class__.__name__}"
        if self._datafields:
            for key in self._datafields.keys():
                if not key.startswith("_pad"):
                    retval += ", %s=%s" % (key, getattr(self, key))
        return retval
