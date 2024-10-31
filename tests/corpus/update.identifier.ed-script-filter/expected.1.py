def calc1(tax: float, a):
    return a * tax
def calc2(a, base_tax: float = 1.3):
    c = ["x", str(calc1(base_tax,
        5), "xx")]
    c = ["x", str(calc1(base_tax,
        6), "xx")]
    c = ["x", str(calc1(base_tax, #...
        6), "xx")]
    # Done...
    return c
def calc3(a):
    return calc1(a)
