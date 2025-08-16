import sys
from types import ModuleType


class SingletonMetaclass(type):
    _instance = {}

    def __call__(self, *args, **kwargs):
        if self not in self._instance:
            self._instance[self] = super().__call__(*args, **kwargs)
        return self._instance[self]


class MetaSingleton(metaclass=SingletonMetaclass):
    def __init__(self, value):
        self.value = value


class NewSingleton:
    _instance = None

    def __new__(cls, value):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.value = value
        return cls._instance


class ImportSingleton:
    def __init__(self, value):
        self.value = value


singleton_module = ModuleType("singleton_module")
singleton_module.singleton = ImportSingleton(5)
sys.modules[singleton_module.__name__] = singleton_module


if __name__ == "__main__":
    ms1 = MetaSingleton(5)
    ms2 = MetaSingleton(10)

    assert ms1 is ms2
    assert ms1.value == ms2.value == 5

    ns1 = NewSingleton(5)
    ns2 = NewSingleton(10)

    assert ns1 is ns2
    assert ns1.value == ns2.value == 5

    from singleton_module import singleton as is1
    from singleton_module import singleton as is2

    assert is1 is is2
    assert is1.value == is2.value == 5
