class A:
    def __init__(self, value):
        self._value = value


class B:
    def m1(self):
        pass
    def __init__(self):
        pass  # OK
    def m1(self):
        pass

class C:
    def __init__(self):
        pass
