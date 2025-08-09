from datetime import datetime


class CreatedAtMetaclass(type):
    def __new__(cls, name, bases, namespace):
        namespace["created_at"] = datetime.now()
        return super().__new__(cls, name, bases, namespace)


class Class1(metaclass=CreatedAtMetaclass):
    pass


class Class2(metaclass=CreatedAtMetaclass):
    pass


if __name__ == "__main__":
    c1 = Class1()
    c2 = Class2()

    print(c1.created_at)
    print(c2.created_at)
