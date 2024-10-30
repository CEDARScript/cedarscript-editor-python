class BaseConverter:
    def encode(self, i):
        neg, value = convert(i, self.decimal_digits, self.digits, "-")
    def decode(self, s):
        neg, value = convert(s, self.digits, self.decimal_digits, self.sign)
def convert(number, from_digits, to_digits, sign):
