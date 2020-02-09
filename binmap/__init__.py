from inspect import Parameter, Signature
import struct


def make_signature(names):
    return Signature(
        Parameter(name, Parameter.KEYWORD_ONLY, default=Parameter.default)
        for name in names
    )


class Padding:
    def __init__(self, name=None):
        self.name = name

    def __get__(self, obj, type=None):
        raise AttributeError(f"Padding ({self.name}) is not readable")

    def __set__(self, obj, value):
        pass


class BinmapMetaclass(type):
    def __new__(cls, name, bases, clsdict):
        clsobject = super().__new__(cls, name, bases, clsdict)
        sig = make_signature(clsobject._datafields.keys())
        setattr(clsobject, "__signature__", sig)
        for key in clsobject._datafields.keys():
            if key.startswith("_pad"):
                setattr(clsobject, key, Padding(name=key))
        return clsobject


class Binmap(metaclass=BinmapMetaclass):
    _datafields = {}

    def __init__(self, *args, binarydata=None, **kwargs):
        self._formatstring = ""
        for fmt in self._datafields.values():
            self._formatstring += fmt

        bound = self.__signature__.bind(*args, **kwargs)
        for param in self.__signature__.parameters.values():
            if param.name in bound.arguments.keys():
                setattr(self, param.name, bound.arguments[param.name])
            else:
                setattr(self, param.name, 0)

        if binarydata:
            self._binarydata = binarydata
            self._unpacker(binarydata)
        else:
            self._binarydata = ""

    def _unpacker(self, value):
        args = struct.unpack(self._formatstring, value)
        datafields = [
            field for field in self._datafields.keys() if not field.startswith("_pad")
        ]
        for arg, name in zip(args, datafields):
            setattr(self, name, arg)

    @property
    def binarydata(self):
        datas = []
        for var in self._datafields.keys():
            if not var.startswith("_pad"):
                datas.append(getattr(self, var))
        return struct.pack(self._formatstring, *datas)

    @binarydata.setter
    def binarydata(self, value):
        self._unpacker(value)
        self._binarydata = value

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        if (not name.startswith("_pad")) and name in self._datafields.keys():
            struct.pack(self._datafields[name], value)

    def __eq__(self, other):
        if self.__signature__ != other.__signature__:
            return False
        for field in self._datafields.keys():
            v1 = getattr(self, field)
            v2 = getattr(other, field)
            if v1 != v2:
                return False
        return True
