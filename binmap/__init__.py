from inspect import Parameter, Signature
import struct


def make_signature(names):
    return Signature(
        Parameter(name, Parameter.KEYWORD_ONLY, default=Parameter.default)
        for name in names
    )


class BinmapMetaclass(type):
    def __new__(cls, name, bases, clsdict):
        clsobject = super().__new__(cls, name, bases, clsdict)
        sig = make_signature(clsobject._datafields.keys())
        setattr(clsobject, "__signature__", sig)
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
        for arg, name in zip(args, self._datafields.keys()):
            setattr(self, name, arg)

    @property
    def binarydata(self):
        datas = []
        for var, fmt in self._datafields.items():
            datas.append(getattr(self, var))
        return struct.pack(self._formatstring, *datas)

    @binarydata.setter
    def binarydata(self, value):
        self._unpacker(value)
        self._binarydata = value

    def __setattr__(self, name, value):
        self.__dict__[name] = value
        if name in self._datafields.keys():
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
