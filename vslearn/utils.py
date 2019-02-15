# -*- coding: utf-8 -*-
import dataclasses
import importlib
import sys


# https://stackoverflow.com/q/51564841
def nested_dataclass(*args, **kwargs):
    def wrapper(cls):
        cls = dataclasses.dataclass(cls, **kwargs)
        original_init = cls.__init__
        def __init__(self, *args, **kwargs):
            for name, value in kwargs.items():
                field_type = cls.__annotations__.get(name, None)
                if dataclasses.is_dataclass(field_type) and \
                        isinstance(value, dict):
                    new_obj = field_type(**value)
                    kwargs[name] = new_obj
            original_init(self, *args, **kwargs)
        cls.__init__ = __init__
        return cls
    return wrapper(args[0]) if args else wrapper


# https://stackoverflow.com/a/53505530
def dataclass_object_dump(ob):
    datacls = type(ob)
    if not dataclasses.is_dataclass(datacls):
        raise TypeError(f"Expected dataclass instance, got '{datacls!r}' object")
    mod = sys.modules.get(datacls.__module__)
    if mod is None or not hasattr(mod, datacls.__qualname__):
        raise ValueError(f"Can't resolve '{datacls!r}' reference")
    ref = f"{datacls.__module__}.{datacls.__qualname__}"
    fields = (f.name for f in dataclasses.fields(ob))
    return {**{f: getattr(ob, f) for f in fields}, '__dataclass__': ref}


def dataclass_object_load(d):
    ref = d.pop('__dataclass__', None)
    if ref is None:
        return d
    try:
        modname, hasdot, qualname = ref.rpartition('.')
        module = importlib.import_module(modname)
        datacls = getattr(module, qualname)
        if not dataclasses.is_dataclass(datacls) or not isinstance(datacls, type):
            raise ValueError
        return datacls(**d)
    except (ModuleNotFoundError, ValueError, AttributeError, TypeError):
        raise ValueError(f"Invalid dataclass reference {ref!r}") from None
