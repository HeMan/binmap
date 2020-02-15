import struct
from inspect import Parameter, Signature


class Padding:
    def __init__(self, name=None):
        self.name = name

    def __get__(self, obj, owner):
        raise AttributeError(f"Padding ({self.name}) is not readable")

    def __set__(self, obj, value):
        pass


class BinField:
    def __init__(self, name=None):
        self.name = name

    def __get__(self, obj, owner):
        return obj.__dict__[self.name]

    def __set__(self, obj, value):
        struct.pack(obj._datafields[self.name], value)
        obj.__dict__[self.name] = value


class BinmapMetaclass(type):
    def __new__(cls, clsname, bases, clsdict):
        clsobject = super().__new__(cls, clsname, bases, clsdict)
        keys = clsobject._datafields.keys()
        sig = Signature(
            Parameter(name, Parameter.KEYWORD_ONLY, default=Parameter.default)
            for name in keys
        )
        setattr(clsobject, "__signature__", sig)
        for name in keys:
            if name.startswith("_pad"):
                setattr(clsobject, name, Padding(name=name))
            else:
                setattr(clsobject, name, BinField(name=name))
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
                if self._datafields[param.name] in "BbHhIiLlQqNnP":
                    setattr(self, param.name, 0)
                elif self._datafields[param.name] in "efd":
                    setattr(self, param.name, 0.0)
                elif self._datafields[param.name] == "c":
                    setattr(self, param.name, b"\x00")
                else:
                    setattr(self, param.name, b"")

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
